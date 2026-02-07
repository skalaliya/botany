from services.validation.rules_engine import RulePack, ValidationRulesEngine


def test_awb_rule_pack_evaluation() -> None:
    engine = ValidationRulesEngine(
        default_pack=RulePack(
            id="global-default",
            version="2026-02-08",
            description="Default",
            regulation="Baseline",
        )
    )
    results = engine.evaluate(
        doc_type="awb",
        fields={"awb_number": "123-12345678", "weight_kg": "120.5"},
    )
    assert any(item.code == "awb.format" and item.passed for item in results)
    assert any(item.code == "shipment.weight" and item.passed for item in results)
    assert any(item.code == "compliance.sanctions" and item.passed for item in results)
    assert all(item.version == "2026-02-08" for item in results)
    assert all(item.pack_id == "global-default" for item in results)


def test_sanctions_hook_failure() -> None:
    engine = ValidationRulesEngine(
        default_pack=RulePack(
            id="global-default",
            version="2026-02-08",
            description="Default",
            regulation="Baseline",
        )
    )
    results = engine.evaluate(doc_type="invoice", fields={"description": "restricted shipment"})
    sanctions_result = next(item for item in results if item.code == "compliance.sanctions")
    assert sanctions_result.passed is False
    assert "restricted keyword" in sanctions_result.explanation


def test_pack_specific_rules_for_dg_and_aeca() -> None:
    engine = ValidationRulesEngine(
        default_pack=RulePack(
            id="global-default",
            version="2026-02-08",
            description="Default",
            regulation="Baseline",
        )
    )
    dg_results = engine.evaluate(
        doc_type="dg_declaration",
        fields={"un_number": "UN1993", "packing_group": "II"},
        pack_id="dg-iata",
        pack_version="2026-02-08",
    )
    assert any(item.code == "dg.un_number" and item.passed for item in dg_results)
    assert any(item.code == "dg.packing_group" and item.passed for item in dg_results)

    aeca_results = engine.evaluate(
        doc_type="export",
        fields={"destination_country": "IR"},
        pack_id="australia-export",
        pack_version="2026-02-08",
    )
    restricted = next(item for item in aeca_results if item.code == "aeca.restricted_destination")
    assert restricted.passed is False
