from build_capex_delivery import (
    build_allocation_payload,
    build_delivery_payload,
    build_production_payload,
)
from validators import validate_payload
from config.capex_analysis import OUTPUTS


def test_delivery_payload_separates_money_from_physical_outputs():
    allocation = build_allocation_payload()
    delivery = build_delivery_payload()
    validate_payload(allocation, "dated_multi_series.schema.json")
    validate_payload(delivery, "dated_multi_series.schema.json")
    assert set(allocation["series"]) == {"roads_budget_capex", "railways_budget_capex"}
    assert set(delivery["series"]) == {
        "national_highways_constructed_km",
        "railway_route_km_electrified",
    }
    assert allocation["series"]["roads_budget_capex"]["unit"] == "INR_crore"
    assert delivery["series"]["national_highways_constructed_km"]["unit"] == "kilometres"
    assert allocation["series"]["railways_budget_capex"]["values"][-1]["status"] == "budget"
    assert allocation["series"]["roads_budget_capex"]["values"][4]["value"] == 187744
    assert allocation["series"]["railways_budget_capex"]["values"][0]["value"] == 53060


def test_capital_goods_iip_keeps_pandemic_observation():
    payload = build_production_payload()
    validate_payload(payload, "dated_multi_series.schema.json")
    rows = payload["series"]["capital_goods_iip"]["values"]
    assert next(row["value"] for row in rows if row["period_label"] == "FY2020-21") == 75.9


def test_new_layers_remain_registered_in_main_capex_output_map():
    assert OUTPUTS["allocation"] == "capex-analysis/sector-capex-allocation.json"
    assert OUTPUTS["delivery"] == "capex-analysis/physical-delivery.json"
    assert OUTPUTS["production"] == "capex-analysis/capital-goods-production.json"
