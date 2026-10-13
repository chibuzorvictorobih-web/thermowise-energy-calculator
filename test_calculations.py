"""Independent tests of ThermoWise's calculation engine.

Run: python -m unittest -v test_calculations.py
No additional test packages are required.
"""

import math
import unittest

from calculations import (
    calculate_heat_recovery,
    check_heat_exchanger_approach,
    compare_heating_options,
)


DEFAULT = dict(
    annual_demand_kwh=600000,
    annual_recovered_kwh=501600,
    annual_hours=4000,
    boiler_efficiency_percent=85,
    heat_pump_cop=3.5,
    fuel_price_per_kwh=0.12,
    electricity_price_per_kwh=0.18,
    fuel_emission_kg_per_kwh=0.20,
    electricity_emission_kg_per_kwh=0.40,
    recovery_aux_power_kw=2,
    recovery_capital_cost=60000,
    heat_pump_capital_cost=90000,
)


class ThermalTests(unittest.TestCase):
    def test_reference_example(self):
        r = calculate_heat_recovery(2, 80, 50, 4.18, 4000, 50)
        self.assertAlmostEqual(r["temperature_difference_c"], 30)
        self.assertAlmostEqual(r["available_power_kw"], 250.8)
        self.assertAlmostEqual(r["recovered_power_kw"], 125.4)
        self.assertAlmostEqual(r["annual_available_kwh"], 1003200)
        self.assertAlmostEqual(r["annual_recovered_kwh"], 501600)
        self.assertAlmostEqual(r["annual_unrecovered_kwh"], 501600)

    def test_zero_and_full_recovery(self):
        zero = calculate_heat_recovery(2, 80, 50, 4.18, 4000, 0)
        full = calculate_heat_recovery(2, 80, 50, 4.18, 4000, 100)
        self.assertEqual(zero["recovered_power_kw"], 0)
        self.assertEqual(full["unrecovered_power_kw"], 0)
        self.assertAlmostEqual(full["recovered_power_kw"], 250.8)

    def test_temperature_must_drop(self):
        with self.assertRaises(ValueError):
            calculate_heat_recovery(2, 50, 80, 4.18, 4000, 50)
        with self.assertRaises(ValueError):
            calculate_heat_recovery(2, 50, 50, 4.18, 4000, 50)

    def test_flow_and_cp_must_be_positive(self):
        with self.assertRaises(ValueError):
            calculate_heat_recovery(0, 80, 50, 4.18, 4000, 50)
        with self.assertRaises(ValueError):
            calculate_heat_recovery(2, 80, 50, 0, 4000, 50)

    def test_hours_bounds(self):
        self.assertAlmostEqual(calculate_heat_recovery(2, 80, 50, 4.18, 8760, 50)["annual_recovered_kwh"], 125.4 * 8760)
        with self.assertRaises(ValueError):
            calculate_heat_recovery(2, 80, 50, 4.18, 8761, 50)
        with self.assertRaises(ValueError):
            calculate_heat_recovery(2, 80, 50, 4.18, 0, 50)

    def test_recovery_fraction_bounds(self):
        for rate in (-1, 101):
            with self.assertRaises(ValueError):
                calculate_heat_recovery(2, 80, 50, 4.18, 4000, rate)

    def test_nan_inf_and_physical_absolute_zero(self):
        for bad in (math.inf, -math.inf, math.nan):
            with self.assertRaises(ValueError):
                calculate_heat_recovery(2, bad, 50, 4.18, 4000, 50)
        with self.assertRaises(ValueError):
            calculate_heat_recovery(2, -274, -275, 4.18, 4000, 50)

    def test_overflow_blocked(self):
        with self.assertRaises(ValueError):
            calculate_heat_recovery(1e308, 80, 50, 1e308, 4000, 50)


class HeatSinkScreenTests(unittest.TestCase):
    def test_default_passes(self):
        r = check_heat_exchanger_approach(80, 50, 35, 45, 5)
        self.assertTrue(r["passes_temperature_screen"])
        self.assertEqual(r["hot_end_approach_c"], 35)
        self.assertEqual(r["cold_end_approach_c"], 15)

    def test_hot_end_fail(self):
        r = check_heat_exchanger_approach(80, 50, 35, 78, 5)
        self.assertFalse(r["passes_temperature_screen"])

    def test_cold_end_fail(self):
        r = check_heat_exchanger_approach(80, 50, 48, 49, 5)
        self.assertFalse(r["passes_temperature_screen"])

    def test_exact_threshold_passes(self):
        self.assertTrue(check_heat_exchanger_approach(80, 50, 45, 75, 5)["passes_temperature_screen"])

    def test_invalid_sink_and_approach_rejected(self):
        with self.assertRaises(ValueError):
            check_heat_exchanger_approach(80, 50, 40, 30, 5)
        with self.assertRaises(ValueError):
            check_heat_exchanger_approach(80, 50, 35, 45, 0)


class FinancialTests(unittest.TestCase):
    def test_reference_operating_costs_and_emissions(self):
        r = compare_heating_options(**DEFAULT)
        o = r["options"]
        self.assertAlmostEqual(o["Boiler only"]["annual_cost"], 600000 / .85 * .12)
        self.assertAlmostEqual(o["Waste heat + boiler"]["annual_cost"], (600000 - 501600) / .85 * .12 + 8000 * .18)
        self.assertAlmostEqual(o["Electric heat pump"]["annual_cost"], 600000 / 3.5 * .18)
        self.assertAlmostEqual(o["Boiler only"]["emissions_kg"], 600000 / .85 * .20)
        self.assertAlmostEqual(o["Waste heat + boiler"]["emissions_kg"], (600000 - 501600) / .85 * .20 + 8000 * .40)
        self.assertAlmostEqual(o["Electric heat pump"]["emissions_kg"], 600000 / 3.5 * .40)
        self.assertEqual(r["lowest_operating_cost"], "Waste heat + boiler")
        self.assertEqual(r["lowest_emissions"], "Waste heat + boiler")

    def test_reference_simple_paybacks(self):
        o = compare_heating_options(**DEFAULT)["options"]
        w = o["Waste heat + boiler"]
        hp = o["Electric heat pump"]
        self.assertAlmostEqual(w["simple_payback_years"], 60000 / (600000 / .85 * .12 - w["annual_cost"]))
        self.assertAlmostEqual(hp["simple_payback_years"], 90000 / (600000 / .85 * .12 - hp["annual_cost"]))

    def test_heat_cannot_exceed_demand(self):
        params = {**DEFAULT, "annual_recovered_kwh": 1e6}
        r = compare_heating_options(**params)
        self.assertEqual(r["usable_recovered_kwh"], 600000)
        self.assertEqual(r["heat_demand_covered_percent"], 100)
        self.assertEqual(r["unused_potential_kwh"], 400000)
        self.assertAlmostEqual(r["auxiliary_electricity_kwh"], 8000 * .6)
        self.assertEqual(r["options"]["Waste heat + boiler"]["fuel_kwh"], 0)

    def test_no_heat_recovery_no_auxiliary_energy(self):
        r = compare_heating_options(**{**DEFAULT, "annual_recovered_kwh": 0})
        self.assertEqual(r["auxiliary_electricity_kwh"], 0)
        self.assertAlmostEqual(r["options"]["Waste heat + boiler"]["annual_cost"], r["options"]["Boiler only"]["annual_cost"])
        self.assertIsNone(r["options"]["Waste heat + boiler"]["simple_payback_years"])

    def test_infeasible_recovery_is_excluded(self):
        r = compare_heating_options(**{**DEFAULT, "recovery_feasible": False})
        self.assertEqual(r["usable_recovered_kwh"], 0)
        self.assertEqual(r["auxiliary_electricity_kwh"], 0)
        self.assertNotIn("Waste heat + boiler", r["options"])

    def test_no_savings_no_payback(self):
        params = {**DEFAULT, "fuel_price_per_kwh": 0, "electricity_price_per_kwh": 2}
        r = compare_heating_options(**params)
        self.assertIsNone(r["options"]["Electric heat pump"]["simple_payback_years"])
        self.assertEqual(r["lowest_operating_cost"], "Boiler only")

    def test_zero_cost_upgrade_payback_zero_if_savings(self):
        r = compare_heating_options(**{**DEFAULT, "recovery_capital_cost": 0})
        self.assertEqual(r["options"]["Waste heat + boiler"]["simple_payback_years"], 0)

    def test_zero_emission_factors(self):
        r = compare_heating_options(**{
            **DEFAULT, "fuel_emission_kg_per_kwh": 0, "electricity_emission_kg_per_kwh": 0
        })
        self.assertTrue(all(x["emissions_kg"] == 0 for x in r["options"].values()))

    def test_zero_efficiency_and_cop_below_one_rejected(self):
        with self.assertRaises(ValueError):
            compare_heating_options(**{**DEFAULT, "boiler_efficiency_percent": 0})
        with self.assertRaises(ValueError):
            compare_heating_options(**{**DEFAULT, "heat_pump_cop": 0.9})

    def test_negative_price_and_nan_rejected(self):
        with self.assertRaises(ValueError):
            compare_heating_options(**{**DEFAULT, "electricity_price_per_kwh": -0.1})
        with self.assertRaises(ValueError):
            compare_heating_options(**{**DEFAULT, "fuel_emission_kg_per_kwh": float("nan")})

    def test_huge_inputs_raise_safe_error(self):
        with self.assertRaises(ValueError):
            compare_heating_options(**{**DEFAULT, "annual_demand_kwh": 1e308, "fuel_price_per_kwh": 1e308})


if __name__ == "__main__":
    unittest.main()
