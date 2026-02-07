from __future__ import annotations

import base64
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from libs.auth.dependencies import (
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_roles,
)
from libs.auth.security import create_access_token, create_refresh_token, decode_refresh_token
from libs.auth.types import AuthUser
from libs.common.audit import create_audit_event
from libs.common.config import get_settings
from libs.common.database import get_db, init_db
from libs.common.events import get_event_bus
from libs.common.idempotency import (
    IdempotencyConflictError,
    get_idempotent_response,
    hash_request,
    save_idempotent_response,
)
from libs.common.logging import configure_logging, log_event
from libs.common.metrics import InMemoryMetrics, RequestTimer
from libs.common.models import (
    AuditEvent,
    Document,
    Export,
    RefreshToken,
    ReviewTask,
    Role,
    Tenant,
    TenantMembership,
    User,
    VehicleImportCase,
)
from libs.common.rate_limit import InMemoryRateLimiter
from libs.common.storage import get_storage_provider
from libs.schemas.api import (
    ActiveLearningCurationResponse,
    AecaValidateRequest,
    AecaValidateResponse,
    AnalyticsOverviewResponse,
    AuditEventResponse,
    AviqmDecodeResponse,
    AwbValidateRequest,
    AwbValidateResponse,
    DgValidateRequest,
    DgValidateResponse,
    DiscrepancyCreateRequest,
    DiscrepancyCreateResponse,
    DiscrepancyScoreRequest,
    DiscrepancyScoreResponse,
    DisputeOpenResponse,
    DocumentSummary,
    ExportCaseCreateRequest,
    ExportCaseResponse,
    ExportSubmissionResponse,
    GlobalSearchResponse,
    IngestDocumentRequest,
    IngestDocumentResponse,
    PagedDocuments,
    RefreshTokenRequest,
    ReviewCompleteRequest,
    ReviewTaskResponse,
    SearchResultItem,
    SignedUrlResponse,
    StationThroughputRequest,
    StationThroughputResponse,
    ThreeWayMatchRequest,
    ThreeWayMatchResponse,
    TokenRequest,
    TokenResponse,
    VehicleImportCaseCreateRequest,
    VehicleImportCaseResponse,
    WebhookDispatchRequest,
    WebhookSubscriptionRequest,
)
from modules.aeca.service import AecaService
from modules.aeca.workflow import AecaWorkflowService
from modules.aviqm.service import AviqmService
from modules.aviqm.workflow import AviqmWorkflowService
from modules.awb.service import AwbService
from modules.dg.service import DangerousGoodsService
from modules.discrepancy.service import DiscrepancyService
from modules.discrepancy.workflow import DiscrepancyWorkflowService
from modules.fiar.service import FiarService
from modules.station_analytics.service import StationAnalyticsService
from services.analytics.active_learning import ActiveLearningService
from services.analytics.bigquery_pipeline import BigQueryPipeline
from services.analytics.service import AnalyticsService
from services.classification.service import ClassificationService
from services.extraction.service import ExtractionService
from services.ingestion.service import IngestionService
from services.preprocessing.service import PreprocessingService
from services.review.service import ReviewService
from services.validation.service import ValidationService
from services.webhooks.service import WebhookService

settings = get_settings()
logger = configure_logging()
event_bus = get_event_bus(settings)
storage_provider = get_storage_provider(settings)

preprocessing_service = PreprocessingService(event_bus)
classification_service = ClassificationService(event_bus)
extraction_service = ExtractionService(event_bus)
validation_service = ValidationService(event_bus)
review_service = ReviewService(event_bus)
ingestion_service = IngestionService(
    event_bus,
    storage_provider,
    preprocessing_service,
    classification_service,
    extraction_service,
    validation_service,
    review_service,
)
webhook_service = WebhookService()
analytics_service = AnalyticsService()
active_learning_service = ActiveLearningService()
bigquery_pipeline = BigQueryPipeline(settings)
awb_service = AwbService()
fiar_service = FiarService()
aeca_service = AecaService()
aviqm_service = AviqmService()
discrepancy_service = DiscrepancyService()
station_analytics_service = StationAnalyticsService()
dg_service = DangerousGoodsService()
aeca_workflow_service = AecaWorkflowService(event_bus)
aviqm_workflow_service = AviqmWorkflowService()
discrepancy_workflow_service = DiscrepancyWorkflowService(event_bus)
rate_limiter = InMemoryRateLimiter()
metrics = InMemoryMetrics()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    settings.validate_runtime_constraints()
    init_db()
    yield


app = FastAPI(
    title="NexusCargo API Gateway",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)


@app.middleware("http")
async def tenant_header_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    timer = RequestTimer()
    path = request.url.path
    if path.startswith("/api/v1") and not (
        path.startswith("/api/v1/auth")
        or path.startswith("/api/v1/docs")
        or path.startswith("/api/v1/openapi")
        or path in {"/healthz", "/readyz"}
    ):
        client_fingerprint = request.headers.get(
            "Authorization", request.client.host if request.client else "anon"
        )
        if not rate_limiter.allow(f"{path}:{client_fingerprint}"):
            return Response(
                content='{"detail":"rate limit exceeded"}',
                media_type="application/json",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        tenant_id = request.headers.get(settings.tenant_header_name, "").strip()
        if not tenant_id:
            return Response(
                content='{"detail":"missing tenant header"}',
                media_type="application/json",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        request.state.tenant_id = tenant_id
    response = await call_next(request)
    metrics.record_request(duration_ms=timer.elapsed_ms(), status_code=response.status_code)
    return response


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    settings.validate_runtime_constraints()
    return {"status": "ready"}


@app.get("/metrics")
def metrics_snapshot() -> dict[str, object]:
    snapshot = metrics.snapshot()
    return {
        "total_requests": snapshot.total_requests,
        "failed_requests": snapshot.failed_requests,
        "avg_latency_ms": snapshot.avg_latency_ms,
    }


def _ensure_user_membership(db: Session, token_request: TokenRequest) -> None:
    tenant_stmt = select(Tenant).where(Tenant.id == token_request.tenant_ids[0])
    tenant = db.execute(tenant_stmt).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            id=token_request.tenant_ids[0], name=f"Tenant {token_request.tenant_ids[0]}"
        )
        db.add(tenant)

    user_stmt = select(User).where(User.id == token_request.user_id)
    user = db.execute(user_stmt).scalar_one_or_none()
    if not user:
        user = User(
            id=token_request.user_id, email=token_request.email, display_name=token_request.email
        )
        db.add(user)

    for role_name in token_request.roles:
        role_stmt = select(Role).where(Role.name == role_name)
        role = db.execute(role_stmt).scalar_one_or_none()
        if not role:
            role = Role(id=f"role_{role_name}", name=role_name)
            db.add(role)
            db.flush()

        member_stmt = select(TenantMembership).where(
            TenantMembership.tenant_id == token_request.tenant_ids[0],
            TenantMembership.user_id == token_request.user_id,
            TenantMembership.role_id == role.id,
        )
        membership = db.execute(member_stmt).scalar_one_or_none()
        if not membership:
            db.add(
                TenantMembership(
                    id=f"mbr_{token_request.user_id}_{role.name}",
                    tenant_id=token_request.tenant_ids[0],
                    user_id=token_request.user_id,
                    role_id=role.id,
                )
            )


@app.post("/api/v1/auth/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _ensure_user_membership(db, payload)

    user = AuthUser(
        user_id=payload.user_id,
        email=payload.email,
        tenant_ids=payload.tenant_ids,
        roles=payload.roles,
    )
    access_token, access_expiry = create_access_token(user)
    refresh_token, refresh_jti, refresh_expiry = create_refresh_token(user)
    db.add(
        RefreshToken(
            id=f"rft_{refresh_jti}",
            user_id=user.user_id,
            token_jti=refresh_jti,
            revoked=False,
            expires_at=refresh_expiry,
        )
    )
    db.commit()

    expires_in = int((access_expiry - datetime.now(timezone.utc)).total_seconds())
    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, expires_in=expires_in
    )


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
def refresh_auth_token(
    payload: RefreshTokenRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    try:
        user, refresh_jti = decode_refresh_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    stmt = select(RefreshToken).where(
        RefreshToken.token_jti == refresh_jti,
        RefreshToken.user_id == user.user_id,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if not existing or existing.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token revoked"
        )
    if existing.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token expired"
        )

    existing.revoked = True
    new_access, access_expiry = create_access_token(user)
    new_refresh, new_jti, new_refresh_expiry = create_refresh_token(user)
    db.add(
        RefreshToken(
            id=f"rft_{new_jti}",
            user_id=user.user_id,
            token_jti=new_jti,
            revoked=False,
            expires_at=new_refresh_expiry,
        )
    )
    db.commit()

    expires_in = int((access_expiry - datetime.now(timezone.utc)).total_seconds())
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, expires_in=expires_in)


@app.post("/api/v1/ingestion/documents", response_model=IngestDocumentResponse)
def ingest_document(
    payload: IngestDocumentRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "admin")),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
) -> IngestDocumentResponse:
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="missing idempotency key"
        )

    request_hash = hash_request(payload.model_dump())
    try:
        existing_response = get_idempotent_response(
            db,
            tenant_id=context.tenant_id,
            key=idempotency_key,
            request_hash=request_hash,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if existing_response is not None:
        return IngestDocumentResponse.model_validate(existing_response)

    try:
        payload_bytes = base64.b64decode(payload.content_base64.encode("utf-8"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid base64 payload"
        ) from exc

    try:
        response_payload = ingestion_service.ingest_and_process(
            db,
            tenant_id=context.tenant_id,
            actor_id=context.user.user_id,
            file_name=payload.file_name,
            content_type=payload.content_type,
            payload_bytes=payload_bytes,
            text_hint=payload.file_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response_model = IngestDocumentResponse.model_validate(response_payload)

    save_idempotent_response(
        db,
        tenant_id=context.tenant_id,
        key=idempotency_key,
        request_hash=request_hash,
        response_payload=response_model.model_dump(),
    )
    db.commit()

    log_event(
        logger,
        "document_ingested",
        {
            "tenant_id": context.tenant_id,
            "actor_id": context.user.user_id,
            "document_id": response_model.document_id,
            "status": response_model.status,
        },
    )

    return response_model


@app.get("/api/v1/documents", response_model=PagedDocuments)
def list_documents(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> PagedDocuments:
    offset = (page - 1) * page_size
    stmt = (
        select(Document)
        .where(Document.tenant_id == context.tenant_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    documents = list(db.execute(stmt).scalars().all())
    total = db.scalar(
        select(func.count()).select_from(Document).where(Document.tenant_id == context.tenant_id)
    )
    return PagedDocuments(
        items=[
            DocumentSummary(
                id=document.id,
                status=document.status,
                file_name=document.file_name,
                created_at=document.created_at,
            )
            for document in documents
        ],
        page=page,
        page_size=page_size,
        total=int(total or 0),
    )


@app.get("/api/v1/search", response_model=GlobalSearchResponse)
def global_search(
    q: str = Query(min_length=2),
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(get_current_user),
) -> GlobalSearchResponse:
    pattern = f"%{q}%"
    documents = db.execute(
        select(Document)
        .where(Document.tenant_id == context.tenant_id, Document.file_name.ilike(pattern))
        .limit(10)
    ).scalars()
    exports = db.execute(
        select(Export)
        .where(Export.tenant_id == context.tenant_id, Export.export_ref.ilike(pattern))
        .limit(10)
    ).scalars()
    vehicle_cases = db.execute(
        select(VehicleImportCase)
        .where(
            VehicleImportCase.tenant_id == context.tenant_id,
            or_(VehicleImportCase.case_ref.ilike(pattern), VehicleImportCase.vin.ilike(pattern)),
        )
        .limit(10)
    ).scalars()
    items = [
        SearchResultItem(entity_type="document", entity_id=item.id, label=item.file_name)
        for item in documents
    ]
    items.extend(
        SearchResultItem(entity_type="export", entity_id=item.id, label=item.export_ref)
        for item in exports
    )
    items.extend(
        SearchResultItem(entity_type="vehicle_import_case", entity_id=item.id, label=item.case_ref)
        for item in vehicle_cases
    )
    return GlobalSearchResponse(items=items)


@app.get("/api/v1/documents/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    stmt = select(Document).where(
        Document.id == document_id, Document.tenant_id == context.tenant_id
    )
    document = db.execute(stmt).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
    return {"id": document.id, "status": document.status, "file_name": document.file_name}


@app.get("/api/v1/documents/{document_id}/signed-url", response_model=SignedUrlResponse)
def get_document_signed_url(
    document_id: str,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "admin", "reviewer")),
) -> SignedUrlResponse:
    stmt = select(Document).where(
        Document.id == document_id, Document.tenant_id == context.tenant_id
    )
    document = db.execute(stmt).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
    return SignedUrlResponse(
        document_id=document.id,
        signed_url=storage_provider.generate_signed_url(document.storage_uri),
    )


@app.get("/api/v1/review/tasks", response_model=list[ReviewTaskResponse])
def list_review_tasks(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("reviewer", "admin")),
) -> list[ReviewTaskResponse]:
    stmt = (
        select(ReviewTask)
        .where(ReviewTask.tenant_id == context.tenant_id, ReviewTask.status == "open")
        .order_by(ReviewTask.created_at.asc())
    )
    tasks = list(db.execute(stmt).scalars().all())
    return [
        ReviewTaskResponse(
            id=task.id,
            document_id=task.document_id,
            reason=task.reason,
            source=task.source,
            status=task.status,
            confidence=task.confidence,
        )
        for task in tasks
    ]


@app.post("/api/v1/review/tasks/{task_id}/complete", response_model=ReviewTaskResponse)
def complete_review(
    task_id: str,
    payload: ReviewCompleteRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("reviewer", "admin")),
) -> ReviewTaskResponse:
    try:
        task = review_service.complete_review(
            db,
            tenant_id=context.tenant_id,
            actor_id=context.user.user_id,
            review_task_id=task_id,
            approved=payload.approved,
            corrections=[correction.model_dump() for correction in payload.corrections],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    db.commit()
    return ReviewTaskResponse(
        id=task.id,
        document_id=task.document_id,
        reason=task.reason,
        source=task.source,
        status=task.status,
        confidence=task.confidence,
    )


@app.get("/api/v1/audit/events", response_model=list[AuditEventResponse])
def list_audit_events(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("admin", "analyst")),
    page_size: int = Query(default=50, ge=1, le=200),
) -> list[AuditEventResponse]:
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.tenant_id == context.tenant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(page_size)
    )
    events = db.execute(stmt).scalars().all()
    return [
        AuditEventResponse(
            id=event.id,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            created_at=event.created_at,
        )
        for event in events
    ]


@app.post("/api/v1/awb/validate", response_model=AwbValidateResponse)
def validate_awb(
    payload: AwbValidateRequest,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "admin")),
) -> AwbValidateResponse:
    valid, messages = awb_service.validate_awb(
        awb_number=payload.awb_number, weight_kg=payload.weight_kg
    )
    return AwbValidateResponse(valid=valid, messages=messages)


@app.post("/api/v1/fiar/three-way-match", response_model=ThreeWayMatchResponse)
def three_way_match(
    payload: ThreeWayMatchRequest,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "finance", "admin")),
) -> ThreeWayMatchResponse:
    matched, discrepancies = fiar_service.three_way_match(
        invoice_amount=payload.invoice_amount,
        contract_amount=payload.contract_amount,
        delivered_amount=payload.delivered_amount,
        tolerance_percent=payload.tolerance_percent,
    )
    return ThreeWayMatchResponse(matched=matched, discrepancies=discrepancies)


@app.post("/api/v1/aeca/validate", response_model=AecaValidateResponse)
def validate_export_compliance(
    payload: AecaValidateRequest,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> AecaValidateResponse:
    valid, issues = aeca_service.validate_export(
        hs_code=payload.hs_code,
        destination_country=payload.destination_country,
    )
    return AecaValidateResponse(valid=valid, issues=issues)


@app.post("/api/v1/aeca/exports", response_model=ExportCaseResponse)
def create_export_case(
    payload: ExportCaseCreateRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> ExportCaseResponse:
    export_case = aeca_workflow_service.create_export_case(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        export_ref=payload.export_ref,
        destination_country=payload.destination_country,
        hs_code=payload.hs_code,
        required_declarations=payload.required_declarations,
    )
    db.commit()
    return ExportCaseResponse(
        id=export_case.id,
        export_ref=export_case.export_ref,
        destination_country=export_case.destination_country,
        status=export_case.status,
    )


@app.get("/api/v1/aeca/exports", response_model=list[ExportCaseResponse])
def list_export_cases(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> list[ExportCaseResponse]:
    cases = db.execute(
        select(Export)
        .where(Export.tenant_id == context.tenant_id)
        .order_by(Export.created_at.desc())
        .limit(100)
    ).scalars()
    return [
        ExportCaseResponse(
            id=item.id,
            export_ref=item.export_ref,
            destination_country=item.destination_country,
            status=item.status,
        )
        for item in cases
    ]


@app.post("/api/v1/aeca/exports/{export_id}/submit", response_model=ExportSubmissionResponse)
def submit_export_case(
    export_id: str,
    payload: dict[str, object],
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("compliance", "admin")),
) -> ExportSubmissionResponse:
    export_case = db.execute(
        select(Export).where(Export.id == export_id, Export.tenant_id == context.tenant_id)
    ).scalar_one_or_none()
    if not export_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="export case not found")
    provider_response = aeca_workflow_service.submit_export_case(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        export_case=export_case,
        payload=payload,
    )
    db.commit()
    return ExportSubmissionResponse(
        export_id=export_case.id,
        provider_status=str(provider_response.get("status", "unknown")),
    )


@app.get("/api/v1/aviqm/vin/{vin}", response_model=AviqmDecodeResponse)
def decode_vehicle_vin(
    vin: str,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> AviqmDecodeResponse:
    return AviqmDecodeResponse(**aviqm_service.decode_vin(vin))


@app.post("/api/v1/aviqm/cases", response_model=VehicleImportCaseResponse)
def create_vehicle_import_case(
    payload: VehicleImportCaseCreateRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> VehicleImportCaseResponse:
    parsed_expiry = (
        date.fromisoformat(payload.expiry_date) if payload.expiry_date else None
    )
    case = aviqm_workflow_service.create_case(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        case_ref=payload.case_ref,
        vin=payload.vin,
        expiry_date=parsed_expiry,
        bmsb_risk_month=payload.bmsb_risk_month,
    )
    db.commit()
    return VehicleImportCaseResponse(
        id=case.id,
        case_ref=case.case_ref,
        vin=case.vin,
        status=case.status,
        expiry_date=case.expiry_date.isoformat() if case.expiry_date else None,
    )


@app.get("/api/v1/aviqm/cases", response_model=list[VehicleImportCaseResponse])
def list_vehicle_import_cases(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> list[VehicleImportCaseResponse]:
    cases = db.execute(
        select(VehicleImportCase)
        .where(VehicleImportCase.tenant_id == context.tenant_id)
        .order_by(VehicleImportCase.created_at.desc())
        .limit(100)
    ).scalars()
    return [
        VehicleImportCaseResponse(
            id=item.id,
            case_ref=item.case_ref,
            vin=item.vin,
            status=item.status,
            expiry_date=item.expiry_date.isoformat() if item.expiry_date else None,
        )
        for item in cases
    ]


@app.post("/api/v1/discrepancy/score", response_model=DiscrepancyScoreResponse)
def score_discrepancy(
    payload: DiscrepancyScoreRequest,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "analyst", "admin")),
) -> DiscrepancyScoreResponse:
    score = discrepancy_service.detect_mismatch(
        declared_weight=payload.declared_weight,
        actual_weight=payload.actual_weight,
        declared_value=payload.declared_value,
        actual_value=payload.actual_value,
    )
    return DiscrepancyScoreResponse(
        mismatch=bool(score["mismatch"]),
        anomaly_score=float(score["anomaly_score"]),
        weight_delta=float(score["weight_delta"]),
        value_delta=float(score["value_delta"]),
    )


@app.post("/api/v1/discrepancies", response_model=DiscrepancyCreateResponse)
def create_discrepancy(
    payload: DiscrepancyCreateRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "analyst", "admin")),
) -> DiscrepancyCreateResponse:
    discrepancy = discrepancy_workflow_service.create_discrepancy(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        shipment_id=payload.shipment_id,
        declared_weight=payload.declared_weight,
        actual_weight=payload.actual_weight,
        declared_value=payload.declared_value,
        actual_value=payload.actual_value,
    )
    db.commit()
    return DiscrepancyCreateResponse(
        discrepancy_id=discrepancy.id,
        score=discrepancy.score,
        status=discrepancy.status,
    )


@app.post("/api/v1/discrepancies/{discrepancy_id}/disputes", response_model=DisputeOpenResponse)
def open_dispute(
    discrepancy_id: str,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("finance", "admin")),
) -> DisputeOpenResponse:
    try:
        dispute = discrepancy_workflow_service.open_dispute(
            db,
            tenant_id=context.tenant_id,
            actor_id=context.user.user_id,
            discrepancy_id=discrepancy_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return DisputeOpenResponse(
        dispute_id=dispute.id,
        discrepancy_id=dispute.discrepancy_id,
        status=dispute.status,
    )


@app.post(
    "/api/v1/station-analytics/throughput",
    response_model=StationThroughputResponse,
)
def station_throughput(
    payload: StationThroughputRequest,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("analyst", "admin")),
) -> StationThroughputResponse:
    metrics = station_analytics_service.throughput_metrics(
        processed=payload.processed,
        delayed=payload.delayed,
    )
    return StationThroughputResponse(
        processed=int(metrics["processed"]),
        delayed=int(metrics["delayed"]),
        sla_risk=float(metrics["sla_risk"]),
    )


@app.post("/api/v1/dg/validate", response_model=DgValidateResponse)
def validate_dg_declaration(
    payload: DgValidateRequest,
    _context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "compliance", "admin")),
) -> DgValidateResponse:
    valid, issues = dg_service.validate_declaration(
        un_number=payload.un_number,
        packing_group=payload.packing_group,
    )
    return DgValidateResponse(valid=valid, issues=issues)


@app.post(
    "/api/v1/active-learning/curate",
    response_model=ActiveLearningCurationResponse,
)
def curate_active_learning_dataset(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("admin", "analyst")),
) -> ActiveLearningCurationResponse:
    records, output_uri = active_learning_service.curate_dataset(
        db,
        tenant_id=context.tenant_id,
    )
    create_audit_event(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        action="active_learning.curated",
        entity_type="dataset",
        entity_id=context.tenant_id,
        payload={"records_curated": records, "output_uri": output_uri},
    )
    db.commit()
    return ActiveLearningCurationResponse(
        records_curated=records,
        output_uri=output_uri,
    )


@app.post("/api/v1/webhooks/subscriptions")
def create_webhook_subscription(
    payload: WebhookSubscriptionRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("admin")),
) -> dict[str, str]:
    subscription = webhook_service.create_subscription(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        target_url=str(payload.target_url),
        event_filter=payload.event_filter,
    )
    db.commit()
    return {"id": subscription.id, "status": "active"}


@app.post("/api/v1/webhooks/dispatch")
def dispatch_webhook_event(
    payload: WebhookDispatchRequest,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("admin")),
) -> dict[str, int]:
    count = webhook_service.dispatch_event(
        db,
        tenant_id=context.tenant_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    create_audit_event(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        action="webhook.dispatch.requested",
        entity_type="webhook",
        entity_id=payload.event_type,
        payload={"subscription_count": count},
    )
    db.commit()
    return {"subscriptions_targeted": count}


@app.get("/api/v1/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("operator", "analyst", "admin")),
) -> AnalyticsOverviewResponse:
    metrics = analytics_service.overview(db, tenant_id=context.tenant_id)
    return AnalyticsOverviewResponse(
        total_documents=int(metrics["total_documents"]),
        open_review_tasks=int(metrics["open_review_tasks"]),
        discrepancy_rate=float(metrics["discrepancy_rate"]),
    )


@app.post("/api/v1/analytics/station-transform")
def run_station_transform(
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context),
    _: AuthUser = Depends(require_roles("admin")),
) -> dict[str, str]:
    outcome = bigquery_pipeline.run_station_analytics_transform()
    create_audit_event(
        db,
        tenant_id=context.tenant_id,
        actor_id=context.user.user_id,
        action="analytics.station_transform.triggered",
        entity_type="analytics_job",
        entity_id="station_transform",
        payload={"outcome": outcome},
    )
    db.commit()
    return {"outcome": outcome}
