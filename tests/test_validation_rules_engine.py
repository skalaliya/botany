from services.validation.rules_engine import RulePack, ValidationRulesEngine


def test_awb_rule_pack_evaluation() -> None:
    engine = ValidationRulesEngine(pack=RulePack(id="awb-default", version="2026-02-07"))
    results = engine.evaluate(
        doc_type="awb",
        fields={"awb_number": "123-12345678", "weight_kg": "120.5"},
    )
    assert any(item.code == "awb.format" and item.passed for item in results)
    assert any(item.code == "shipment.weight" and item.passed for item in results)
    assert any(item.code == "compliance.sanctions" and item.passed for item in results)
    assert all(item.version == "2026-02-07" for item in results)


def test_sanctions_hook_failure() -> None:
    engine = ValidationRulesEngine(pack=RulePack(id="awb-default", version="2026-02-07"))
    results = engine.evaluate(doc_type="invoice", fields={"description": "restricted shipment"})
    sanctions_result = next(item for item in results if item.code == "compliance.sanctions")
    assert sanctions_result.passed is False
    assert "restricted keyword" in sanctions_result.explanation
