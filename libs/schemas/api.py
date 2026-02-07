from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class TokenRequest(BaseModel):
    user_id: str
    email: str
    tenant_ids: list[str]
    roles: list[str] = Field(default_factory=lambda: ["operator"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class IngestDocumentRequest(BaseModel):
    file_name: str
    content_type: str
    content_base64: str


class IngestDocumentResponse(BaseModel):
    document_id: str
    status: str
    review_required: bool
    doc_type: str


class DocumentSummary(BaseModel):
    id: str
    status: str
    file_name: str
    created_at: datetime


class SignedUrlResponse(BaseModel):
    document_id: str
    signed_url: str


class PagedDocuments(BaseModel):
    items: list[DocumentSummary]
    page: int
    page_size: int
    total: int


class ReviewTaskResponse(BaseModel):
    id: str
    document_id: str
    reason: str
    source: str
    status: str
    confidence: float


class CorrectionPayload(BaseModel):
    field_name: str
    old_value: str
    new_value: str
    reason_tag: str


class ReviewCompleteRequest(BaseModel):
    approved: bool
    corrections: list[CorrectionPayload] = Field(default_factory=list)


class WebhookSubscriptionRequest(BaseModel):
    target_url: HttpUrl
    event_filter: str


class WebhookDispatchRequest(BaseModel):
    event_type: str
    payload: dict[str, Any]


class WebhookWorkerRunRequest(BaseModel):
    batch_size: int = Field(default=100, ge=1, le=1000)


class WebhookWorkerRunResponse(BaseModel):
    processed: int
    delivered: int
    retried: int
    dead_lettered: int


class WebhookReplayRequest(BaseModel):
    delivery_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1, le=1000)


class WebhookReplayResponse(BaseModel):
    requeued: int


class AwbValidateRequest(BaseModel):
    awb_number: str
    weight_kg: float


class AwbValidateResponse(BaseModel):
    valid: bool
    messages: list[str]


class AwbProviderSubmitRequest(BaseModel):
    provider_key: str
    awb_number: str
    payload: dict[str, Any]


class AwbProviderSubmitResponse(BaseModel):
    provider: str
    status: str
    awb_number: str
    external_id: Optional[str] = None


class ThreeWayMatchRequest(BaseModel):
    invoice_amount: float
    contract_amount: float
    delivered_amount: float
    tolerance_percent: float = 1.0


class ThreeWayMatchResponse(BaseModel):
    matched: bool
    discrepancies: list[str]


class FiarExportInvoiceRequest(BaseModel):
    invoice_id: str
    payload: dict[str, Any]


class FiarExportInvoiceResponse(BaseModel):
    provider: str
    invoice_id: str
    status: str
    external_id: Optional[str] = None
    error: Optional[str] = None


class AnalyticsOverviewResponse(BaseModel):
    total_documents: int
    open_review_tasks: int
    discrepancy_rate: float


class AecaValidateRequest(BaseModel):
    hs_code: str
    destination_country: str


class AecaValidateResponse(BaseModel):
    valid: bool
    issues: list[str]


class AviqmDecodeResponse(BaseModel):
    status: str
    wmi: Optional[str] = None
    vds: Optional[str] = None
    vis: Optional[str] = None
    reason: Optional[str] = None


class DiscrepancyScoreRequest(BaseModel):
    declared_weight: float
    actual_weight: float
    declared_value: float
    actual_value: float


class DiscrepancyScoreResponse(BaseModel):
    mismatch: bool
    anomaly_score: float
    weight_delta: float
    value_delta: float


class StationThroughputRequest(BaseModel):
    processed: int
    delayed: int


class StationThroughputResponse(BaseModel):
    processed: int
    delayed: int
    sla_risk: float


class DgValidateRequest(BaseModel):
    un_number: str
    packing_group: str


class DgValidateResponse(BaseModel):
    valid: bool
    issues: list[str]


class ActiveLearningCurationResponse(BaseModel):
    records_curated: int
    output_uri: str


class ExportCaseCreateRequest(BaseModel):
    export_ref: str
    destination_country: str
    hs_code: str
    required_declarations: list[str] = Field(default_factory=list)


class ExportCaseResponse(BaseModel):
    id: str
    export_ref: str
    destination_country: str
    status: str


class ExportSubmissionResponse(BaseModel):
    export_id: str
    provider_status: str


class VehicleImportCaseCreateRequest(BaseModel):
    case_ref: str
    vin: str
    expiry_date: Optional[str] = None
    bmsb_risk_month: Optional[int] = None


class VehicleImportCaseResponse(BaseModel):
    id: str
    case_ref: str
    vin: str
    status: str
    expiry_date: Optional[str] = None


class DiscrepancyCreateRequest(BaseModel):
    shipment_id: str
    declared_weight: float
    actual_weight: float
    declared_value: float
    actual_value: float


class DiscrepancyCreateResponse(BaseModel):
    discrepancy_id: str
    score: float
    status: str


class DisputeOpenResponse(BaseModel):
    dispute_id: str
    discrepancy_id: str
    status: str


class SearchResultItem(BaseModel):
    entity_type: str
    entity_id: str
    label: str


class GlobalSearchResponse(BaseModel):
    items: list[SearchResultItem]


class AuditEventResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    created_at: datetime
