from modules.fiar.service import FiarService


def test_three_way_match_success() -> None:
    service = FiarService()
    matched, discrepancies = service.three_way_match(
        invoice_amount=100.0,
        contract_amount=100.4,
        delivered_amount=100.3,
        tolerance_percent=1.0,
    )
    assert matched is True
    assert discrepancies == []


def test_three_way_match_detects_discrepancies() -> None:
    service = FiarService()
    matched, discrepancies = service.three_way_match(
        invoice_amount=120.0,
        contract_amount=100.0,
        delivered_amount=101.0,
        tolerance_percent=1.0,
    )
    assert matched is False
    assert "invoice_vs_contract" in discrepancies
    assert "invoice_vs_delivery" in discrepancies
