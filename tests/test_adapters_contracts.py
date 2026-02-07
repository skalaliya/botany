from modules.aeca.adapters import MockAbfIcsAdapter
from modules.awb.adapters import MockCargoWiseAdapter, MockChampAdapter, MockIbsICargoAdapter
from modules.fiar.adapters import MockAccountingExportAdapter


def test_awb_adapters_contract_shape() -> None:
    payload: dict[str, object] = {"k": "v"}
    for adapter in (MockChampAdapter(), MockIbsICargoAdapter(), MockCargoWiseAdapter()):
        response = adapter.submit_awb("123-12345678", payload)
        assert response["status"] == "accepted"
        assert response["awb_number"] == "123-12345678"


def test_fiar_accounting_export_contract_shape() -> None:
    adapter = MockAccountingExportAdapter()
    response = adapter.export_invoice("inv-1", {"amount": 10})
    assert response["invoice_id"] == "inv-1"
    assert response["status"] == "queued"


def test_aeca_adapter_contract_shape() -> None:
    adapter = MockAbfIcsAdapter()
    response = adapter.submit_export_case("exp-1", {"hs": "010101"})
    assert response["provider"] == "ABF/ICS-mock"
    assert response["status"] == "submitted"
