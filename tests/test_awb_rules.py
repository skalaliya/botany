from modules.awb.service import AwbService


def test_awb_validation_passes_for_valid_number() -> None:
    service = AwbService()
    valid, messages = service.validate_awb(awb_number="123-12345678", weight_kg=10.5)
    assert valid is True
    assert messages == []


def test_awb_validation_fails_for_invalid_inputs() -> None:
    service = AwbService()
    valid, messages = service.validate_awb(awb_number="123-abc", weight_kg=0)
    assert valid is False
    assert "AWB format must be XXX-XXXXXXXX" in messages
    assert "Weight must be positive" in messages
