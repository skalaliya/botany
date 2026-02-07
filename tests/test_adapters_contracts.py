from __future__ import annotations

import httpx

from libs.common.integrations import AdapterHttpConfig, JsonHttpAdapter
from modules.aeca.adapters import HttpAbfIcsAdapter, MockAbfIcsAdapter
from modules.awb.adapters import HttpCargoAdapter, MockCargoAdapter
from modules.fiar.adapters import HttpAccountingExportAdapter, MockAccountingExportAdapter


def test_awb_mock_adapters_contract_shape() -> None:
    payload: dict[str, object] = {"k": "v"}
    adapters = (
        MockCargoAdapter(provider_name="CHAMP"),
        MockCargoAdapter(provider_name="IBS iCargo"),
        MockCargoAdapter(provider_name="CargoWise"),
    )
    for adapter in adapters:
        response = adapter.submit_awb(
            tenant_id="tenant_1",
            awb_number="123-12345678",
            payload=payload,
        )
        assert response["status"] == "accepted"
        assert response["awb_number"] == "123-12345678"


def test_fiar_accounting_export_contract_shape() -> None:
    adapter = MockAccountingExportAdapter()
    response = adapter.export_invoice(
        tenant_id="tenant_1",
        invoice_id="inv-1",
        payload={"amount": 10},
    )
    assert response["invoice_id"] == "inv-1"
    assert response["status"] == "queued"


def test_aeca_adapter_contract_shape() -> None:
    adapter = MockAbfIcsAdapter()
    response = adapter.submit_export_case(
        tenant_id="tenant_1",
        export_ref="exp-1",
        payload={"hs": "010101"},
    )
    assert response["provider"] == "ABF/ICS-mock"
    assert response["status"] == "submitted"


def test_http_awb_adapter_contract_with_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Idempotency-Key"].startswith("tenant_1:CHAMP")
        return httpx.Response(200, json={"status": "accepted", "external_id": "ext-001"})

    adapter = HttpCargoAdapter(
        provider_name="CHAMP",
        client=JsonHttpAdapter(
            config=AdapterHttpConfig(
                provider_name="CHAMP",
                base_url="https://example.com",
                client_id="client",
                bearer_token="token",
            ),
            transport=httpx.MockTransport(handler),
        ),
    )

    response = adapter.submit_awb(
        tenant_id="tenant_1",
        awb_number="123-12345678",
        payload={"x": 1},
    )
    assert response["status"] == "accepted"


def test_http_aeca_and_fiar_contract_status_validation() -> None:
    abf_transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={"status": "submitted", "submission_id": "sbm-1", "external_id": "acct-1"},
        )
    )

    abf_adapter = HttpAbfIcsAdapter(
        client=JsonHttpAdapter(
            config=AdapterHttpConfig(
                provider_name="ABF/ICS",
                base_url="https://abf.example",
                client_id="abf-client",
                bearer_token="token",
            ),
            transport=abf_transport,
        )
    )
    abf_response = abf_adapter.submit_export_case(
        tenant_id="tenant_1",
        export_ref="exp-1",
        payload={"hs": "010101"},
    )
    assert abf_response["status"] == "submitted"

    accounting_transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"status": "queued", "external_id": "acct-1"})
    )

    accounting_adapter = HttpAccountingExportAdapter(
        provider_name="Accounting",
        client=JsonHttpAdapter(
            config=AdapterHttpConfig(
                provider_name="Accounting",
                base_url="https://acct.example",
                client_id="acct-client",
                bearer_token="token",
            ),
            transport=accounting_transport,
        ),
    )
    accounting_response = accounting_adapter.export_invoice(
        tenant_id="tenant_1",
        invoice_id="inv-1",
        payload={"amount": 10},
    )
    assert accounting_response["status"] in {"queued", "exported", "accepted", "submitted"}
