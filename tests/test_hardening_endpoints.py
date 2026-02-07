from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "user_id": "user_hardening",
            "email": "hardening@example.com",
            "tenant_ids": ["tenant_hardening"],
            "roles": ["admin", "operator", "compliance", "analyst", "finance", "reviewer"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    return {
        "Authorization": f"Bearer {body['access_token']}",
        "X-Tenant-Id": "tenant_hardening",
    }


def test_hardening_workflow_endpoints(client: TestClient) -> None:
    headers = _auth_headers(client)

    awb_submit = client.post(
        "/api/v1/awb/submit",
        json={
            "provider_key": "champ",
            "awb_number": "123-12345678",
            "payload": {"shipper": "Acme"},
        },
        headers=headers,
    )
    assert awb_submit.status_code == 200
    assert awb_submit.json()["status"] == "accepted"

    fiar_export = client.post(
        "/api/v1/fiar/invoices/export",
        json={"invoice_id": "inv-hard-1", "payload": {"amount": 100}},
        headers=headers,
    )
    assert fiar_export.status_code == 200
    assert fiar_export.json()["status"] in {"queued", "accepted", "exported"}

    export_ref = "EXP-HARD-001"
    create_export = client.post(
        "/api/v1/aeca/exports",
        json={
            "export_ref": export_ref,
            "destination_country": "AU",
            "hs_code": "123456",
            "required_declarations": ["DG_DECL"],
        },
        headers=headers,
    )
    assert create_export.status_code == 200
    export_id = create_export.json()["id"]

    list_exports = client.get("/api/v1/aeca/exports", headers=headers)
    assert list_exports.status_code == 200
    assert any(item["id"] == export_id for item in list_exports.json())

    submit_export = client.post(
        f"/api/v1/aeca/exports/{export_id}/submit",
        json={"submitted_by": "integration-test"},
        headers=headers,
    )
    assert submit_export.status_code == 200
    assert submit_export.json()["provider_status"] == "submitted"

    expiry = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
    create_vehicle_case = client.post(
        "/api/v1/aviqm/cases",
        json={
            "case_ref": "VIA-HARD-001",
            "vin": "JH4KA8270MC000000",
            "expiry_date": expiry,
            "bmsb_risk_month": 10,
        },
        headers=headers,
    )
    assert create_vehicle_case.status_code == 200
    vehicle_case_id = create_vehicle_case.json()["id"]

    list_vehicle_cases = client.get("/api/v1/aviqm/cases", headers=headers)
    assert list_vehicle_cases.status_code == 200
    assert any(item["id"] == vehicle_case_id for item in list_vehicle_cases.json())

    create_discrepancy = client.post(
        "/api/v1/discrepancies",
        json={
            "shipment_id": "shp-hard-1",
            "declared_weight": 100,
            "actual_weight": 130,
            "declared_value": 1000,
            "actual_value": 700,
        },
        headers=headers,
    )
    assert create_discrepancy.status_code == 200
    discrepancy_id = create_discrepancy.json()["discrepancy_id"]

    open_dispute = client.post(
        f"/api/v1/discrepancies/{discrepancy_id}/disputes",
        headers=headers,
    )
    assert open_dispute.status_code == 200
    assert open_dispute.json()["status"] == "open"

    run_station_transform = client.post("/api/v1/analytics/station-transform", headers=headers)
    assert run_station_transform.status_code == 200
    assert run_station_transform.json()["outcome"].startswith("skipped:")

    search = client.get("/api/v1/search", params={"q": "HARD"}, headers=headers)
    assert search.status_code == 200
    search_items = search.json()["items"]
    assert any(item["entity_type"] == "export" and item["label"] == export_ref for item in search_items)

    audit_events = client.get("/api/v1/audit/events", headers=headers)
    assert audit_events.status_code == 200
    assert len(audit_events.json()) > 0

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["total_requests"] >= 1
    assert body["failed_requests"] >= 0
