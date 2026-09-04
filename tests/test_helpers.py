"""Tests for Bituo device payload normalization."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HELPERS_PATH = (
    Path(__file__).parents[1] / "custom_components" / "bituopmd" / "helpers.py"
)
SPEC = importlib.util.spec_from_file_location("bituopmd_helpers", HELPERS_PATH)
assert SPEC is not None and SPEC.loader is not None
helpers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helpers)


class HelpersTest(unittest.TestCase):
    """Exercise normalization with synthetic, non-user device data."""

    def test_normalize_spm02_payload_shape(self) -> None:
        """Power is converted to HA units and missing totals are restored."""
        payload = {
            "ProductModel": "SPM02",
            "VoltageX": "230.0",
            "VoltageY": "231.0",
            "VoltageZ": "229.0",
            "CurrentX": "1.0",
            "CurrentY": "2.0",
            "CurrentZ": "3.0",
            "ActivePowerX": "0.100",
            "ActivePowerY": "0.200",
            "ActivePowerZ": "0.300",
            "ReactivePowerX": "-0.010",
            "ReactivePowerY": "0.020",
            "ReactivePowerZ": "0.030",
            "ApparentPowerX": "0.110",
            "ApparentPowerY": "0.220",
            "ApparentPowerZ": "0.330",
            "PowerFactorX": "0.90",
            "PowerFactorY": "0.80",
            "PowerFactorZ": "0.70",
            "ForwardEnergyX": "10.0",
            "ForwardEnergyY": "20.0",
            "ForwardEnergyZ": "30.0",
            "ReverseEnergyX": "0.1",
            "ReverseEnergyY": "0.2",
            "ReverseEnergyZ": "0.3",
        }

        data = helpers.normalize_meter_data(payload)

        self.assertEqual(data["ActivePowerX"], 100.0)
        self.assertEqual(data["TotalActivePower"], 600.0)
        self.assertEqual(data["TotalReactivePower"], 40.0)
        self.assertEqual(data["TotalApparentPower"], 660.0)
        self.assertEqual(data["PowerFactorX"], "0.90")
        self.assertEqual(data["TotalCurrent"], 6.0)
        self.assertEqual(data["AverageLineCurrent"], 2.0)
        self.assertEqual(data["AverageVoltageLN"], 230.0)
        self.assertEqual(data["TotalForwardEnergy"], 60.0)
        self.assertAlmostEqual(data["TotalReverseEnergy"], 0.6)
        self.assertAlmostEqual(data["TotalEnergyX"], 10.1)
        self.assertAlmostEqual(data["TotalEnergyY"], 20.2)
        self.assertAlmostEqual(data["TotalEnergyZ"], 30.3)
        self.assertAlmostEqual(data["TotalEnergy"], 60.6)

    def test_total_energy_prefers_native_vendor_values(self) -> None:
        """A firmware-provided TotalEnergy remains authoritative."""
        data = helpers.normalize_meter_data(
            {
                "ForwardEnergyX": 10.0,
                "ReverseEnergyX": 0.5,
                "TotalEnergyX": 99.0,
                "TotalForwardEnergy": 100.0,
                "TotalReverseEnergy": 5.0,
                "TotalEnergy": 95.0,
            }
        )
        self.assertEqual(data["TotalEnergyX"], 99.0)
        self.assertEqual(data["TotalEnergy"], 95.0)

    def test_existing_vendor_totals_are_not_overwritten(self) -> None:
        """A firmware-provided total remains authoritative."""
        data = helpers.normalize_meter_data(
            {
                "CurrentX": 1,
                "CurrentY": 2,
                "CurrentZ": 3,
                "TotalCurrent": 99,
            }
        )
        self.assertEqual(data["TotalCurrent"], 99)

    def test_partial_phases_do_not_create_misleading_total(self) -> None:
        """A missing phase must not be silently treated as zero."""
        data = helpers.normalize_meter_data({"ActivePowerX": "1", "ActivePowerY": "2"})
        self.assertNotIn("TotalActivePower", data)

    def test_entity_id_format_is_backward_compatible(self) -> None:
        """Existing entity IDs continue to resolve after replacement."""
        self.assertEqual(
            helpers.format_field_entity_id("AverageVoltageLN"),
            "average_voltage_ln",
        )
        self.assertEqual(
            helpers.format_field_entity_id("UnbalanceLineCurrents"),
            "unbalance_line_currents",
        )

    def test_field_name_formatting_has_no_double_spaces(self) -> None:
        """Phase labels remain readable."""
        self.assertEqual(helpers.format_field_name("ActivePowerX"), "Active Power X")


if __name__ == "__main__":
    unittest.main()
