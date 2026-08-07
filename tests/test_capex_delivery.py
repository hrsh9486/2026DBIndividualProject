import unittest

from builders.real_economy_outputs import (
    build_allocation_payload,
    build_delivery_payload,
    build_production_payload,
)
from validators import validate_payload
from config.capex_analysis import OUTPUTS
from extractors.delivery_reference import extract_delivery_sources


class CapexDeliveryTests(unittest.TestCase):
    def test_delivery_payload_separates_money_from_physical_outputs(self):
        sources = extract_delivery_sources()
        allocation = build_allocation_payload(sources.allocation)
        delivery = build_delivery_payload(sources.delivery)
        validate_payload(allocation, "dated_multi_series.schema.json")
        validate_payload(delivery, "dated_multi_series.schema.json")
        self.assertEqual(set(allocation["series"]), {"roads_budget_capex", "railways_budget_capex"})
        self.assertEqual(set(delivery["series"]), {
            "national_highways_constructed_km",
            "railway_route_km_electrified",
        })
        self.assertEqual(allocation["series"]["roads_budget_capex"]["unit"], "INR_crore")
        self.assertEqual(delivery["series"]["national_highways_constructed_km"]["unit"], "kilometres")
        self.assertEqual(allocation["series"]["railways_budget_capex"]["values"][-1]["status"], "budget")
        self.assertEqual(allocation["series"]["roads_budget_capex"]["values"][4]["value"], 187744)
        self.assertEqual(allocation["series"]["railways_budget_capex"]["values"][0]["value"], 53060)

    def test_capital_goods_iip_keeps_pandemic_observation(self):
        sources = extract_delivery_sources()
        payload = build_production_payload(sources.production)
        validate_payload(payload, "dated_multi_series.schema.json")
        rows = payload["series"]["capital_goods_iip"]["values"]
        value = next(row["value"] for row in rows if row["period_label"] == "FY2020-21")
        self.assertEqual(value, 75.9)

    def test_delivery_observations_exist_only_behind_the_extraction_boundary(self):
        sources = extract_delivery_sources()
        self.assertEqual(sources.reference_path.name, "capex_delivery_reference.json")
        self.assertEqual(len(sources.checksum), 64)
        self.assertEqual(tuple(series.key for series in sources.allocation.series), (
            "railways_budget_capex",
            "roads_budget_capex",
        ))

    def test_new_layers_remain_registered_in_main_capex_output_map(self):
        self.assertEqual(OUTPUTS["allocation"], "capex-analysis/sector-capex-allocation.json")
        self.assertEqual(OUTPUTS["delivery"], "capex-analysis/physical-delivery.json")
        self.assertEqual(OUTPUTS["production"], "capex-analysis/capital-goods-production.json")
        self.assertEqual(OUTPUTS["quality"], "capex-analysis/investment-quality.json")
        self.assertEqual(OUTPUTS["states"], "capex-analysis/state-capex-evaluation.json")
        self.assertEqual(OUTPUTS["crowding_in"], "capex-analysis/crowding-in-evidence.json")


if __name__ == "__main__":
    unittest.main()
