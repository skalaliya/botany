from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "user_id": "user_phase34",
            "email": "phase34@example.com",
            "tenant_ids": ["tenant_1"],
            "roles": ["admin", "operator", "compliance", "analyst"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    return {
        "Authorization": f"Bearer {body['access_token']}",
        "X-Tenant-Id": "tenant_1",
    }


def test_phase3_phase4_endpoints(client: TestClient) -> None:
    headers = _auth_headers(client)

    aeca_response = client.post(
        "/api/v1/aeca/validate",
        json={"hs_code": "123456", "destination_country": "AU"},
        headers=headers,
    )
    assert aeca_response.status_code == 200
    assert aeca_response.json()["valid"] is True

    aviqm_response = client.get("/api/v1/aviqm/vin/JH4KA8270MC000000", headers=headers)
    assert aviqm_response.status_code == 200
    assert aviqm_response.json()["status"] == "decoded"

    discrepancy_response = client.post(
        "/api/v1/discrepancy/score",
        json={
            "declared_weight": 100,
            "actual_weight": 120,
            "declared_value": 1000,
            "actual_value": 900,
        },
        headers=headers,
    )
    assert discrepancy_response.status_code == 200
    assert discrepancy_response.json()["anomaly_score"] > 0

    station_response = client.post(
        "/api/v1/station-analytics/throughput",
        json={"processed": 100, "delayed": 5},
        headers=headers,
    )
    assert station_response.status_code == 200
    assert station_response.json()["sla_risk"] == 0.05

    dg_response = client.post(
        "/api/v1/dg/validate",
        json={"un_number": "UN1993", "packing_group": "II"},
        headers=headers,
    )
    assert dg_response.status_code == 200
    assert dg_response.json()["valid"] is True

    curate_response = client.post("/api/v1/active-learning/curate", headers=headers)
    assert curate_response.status_code == 200
    assert curate_response.json()["output_uri"].startswith("file://")
