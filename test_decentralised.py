"""Tests for ThermoWise decentralised hourly energy model."""
import copy
import math
import unittest

from decentralised import default_settings, example_profile, simulate_hourly, validate_profile


class TestHourlyProfile(unittest.TestCase):
    def setUp(self):
        self.p = example_profile()
        self.cfg = default_settings()

    def test_example_profile_has_24_hours(self):
        self.assertEqual(len(self.p), 24)
        self.assertEqual(len(validate_profile(self.p)), 24)

    def test_invalid_profile_length(self):
        with self.assertRaises(ValueError):
            validate_profile([])
        with self.assertRaises(ValueError):
            validate_profile(self.p * 366)

    def test_missing_column(self):
        with self.assertRaises(ValueError):
            validate_profile([{"demand_kwh": 1, "irradiance_kw_m2": .2}])

    def test_invalid_nan_negative_and_availability(self):
        for row in [dict(demand_kwh=float("nan"), irradiance_kw_m2=.2, waste_availability=.4),
                    dict(demand_kwh=-1, irradiance_kw_m2=.2, waste_availability=.4),
                    dict(demand_kwh=3, irradiance_kw_m2=.2, waste_availability=1.1),
                    dict(demand_kwh=3, irradiance_kw_m2=2, waste_availability=.4)]:
            with self.assertRaises(ValueError):
                validate_profile([row])

    def test_demand_fully_supplied_each_hour(self):
        r = simulate_hourly(self.p, self.cfg)
        for row in r["hourly"]:
            self.assertAlmostEqual(row["demand_kwh"], sum(row[k] for k in (
                "waste_direct_kwh", "hp_pv_direct_heat_kwh", "tes_discharge_heat_kwh",
                "hp_grid_heat_kwh", "boiler_heat_kwh"
            )), places=8)

    def test_three_scenarios_have_equal_demand(self):
        r = simulate_hourly(self.p, self.cfg)
        demands = [x["demand_kwh_th"] for x in r["summaries"].values()]
        self.assertEqual(len(r["summaries"]), 3)
        self.assertTrue(all(math.isclose(d, demands[0]) for d in demands))

    def test_storage_state_and_power_limits(self):
        r = simulate_hourly(self.p, self.cfg)
        for x in r["hourly"]:
            self.assertGreaterEqual(x["tes_soc_kwh"], -1e-8)
            self.assertLessEqual(x["tes_soc_kwh"], self.cfg["tes_capacity_kwh_th"]+1e-8)
            self.assertLessEqual(x["tes_charge_input_kwh"], self.cfg["tes_charge_kw_th"]+1e-8)
            self.assertLessEqual(x["tes_discharge_heat_kwh"], self.cfg["tes_discharge_kw_th"]+1e-8)

    def test_hourly_pv_electricity_conservation(self):
        r = simulate_hourly(self.p, self.cfg)
        for x in r["hourly"]:
            self.assertAlmostEqual(x["pv_generation_kwh"], x["pv_to_hp_kwh"]+x["pv_unused_kwh"], places=8)

    def test_initial_and_end_soc_balances(self):
        r = simulate_hourly(self.p, self.cfg)
        eta = math.sqrt(self.cfg["tes_roundtrip_efficiency"])
        soc = self.cfg["tes_initial_soc_kwh"]
        for row in r["hourly"]:
            soc = soc-row["tes_loss_kwh"]+eta*row["tes_charge_input_kwh"]-row["tes_discharge_heat_kwh"]/eta
            self.assertAlmostEqual(row["tes_soc_kwh"], soc, places=8)

    def test_baseline_boiler_is_demand_divided_by_efficiency(self):
        r = simulate_hourly(self.p, self.cfg)
        b = r["summaries"]["Boiler only"]
        self.assertAlmostEqual(b["boiler_fuel_kwh"], sum(x["demand_kwh"] for x in self.p)/self.cfg["boiler_efficiency"])
        self.assertEqual(b["grid_import_kwh_e"], 0)

    def test_without_pv_no_solar_electricity(self):
        self.cfg["pv_kwp"] = 0
        r = simulate_hourly(self.p, self.cfg)
        self.assertTrue(all(x["pv_to_hp_kwh"] == 0 for x in r["hourly"]))

    def test_zero_storage_no_charging_or_discharge(self):
        self.cfg.update(tes_capacity_kwh_th=0, tes_initial_soc_kwh=0)
        r = simulate_hourly(self.p, self.cfg)
        self.assertTrue(all(x["tes_charge_input_kwh"] == 0 and x["tes_discharge_heat_kwh"] == 0 for x in r["hourly"]))

    def test_infeasible_temperature_eliminates_waste_heat(self):
        self.cfg["sink_supply_c"] = 78
        r = simulate_hourly(self.p, self.cfg)
        self.assertFalse(r["temperature_screen"]["passes_temperature_screen"])
        self.assertEqual(r["waste_recovery_rating_kw"], 0)
        self.assertTrue(all(x["waste_direct_kwh"] == 0 for x in r["hourly"]))

    def test_no_waste_factor(self):
        self.cfg["recovery_fraction"] = 0
        r = simulate_hourly(self.p, self.cfg)
        self.assertTrue(all(x["waste_potential_kwh"] == 0 for x in r["hourly"]))

    def test_cost_priority_switches_to_boiler_when_grid_expensive(self):
        self.cfg.update(pv_kwp=0, mass_flow_kg_s=0.0001, tes_capacity_kwh_th=0,
                        tes_initial_soc_kwh=0, electricity_price=1.0, fuel_price=0.05)
        r = simulate_hourly(self.p, self.cfg, "cost_aware")
        self.assertTrue(all(x["hp_grid_heat_kwh"] == 0 for x in r["hourly"]))
        r_hp = simulate_hourly(self.p, self.cfg, "hp_first")
        self.assertGreater(sum(x["hp_grid_heat_kwh"] for x in r_hp["hourly"]), 0)

    def test_pv_drives_heat_pump_with_no_grid_if_fully_covered(self):
        p = [dict(demand_kwh=8, irradiance_kw_m2=1, waste_availability=0)]
        self.cfg.update(pv_kwp=10, hp_capacity_kw_th=20, tes_capacity_kwh_th=0,
                        tes_initial_soc_kwh=0)
        r = simulate_hourly(p, self.cfg)
        row = r["hourly"][0]
        self.assertAlmostEqual(row["hp_pv_direct_heat_kwh"], 8)
        self.assertAlmostEqual(row["grid_import_kwh"], 0)
        self.assertAlmostEqual(row["boiler_heat_kwh"], 0)

    def test_pv_surplus_charges_thermal_storage(self):
        p = [dict(demand_kwh=0, irradiance_kw_m2=1, waste_availability=0),
             dict(demand_kwh=20, irradiance_kw_m2=0, waste_availability=0)]
        self.cfg.update(pv_kwp=30, hp_capacity_kw_th=100, tes_capacity_kwh_th=100)
        r = simulate_hourly(p, self.cfg)
        self.assertGreater(r["hourly"][0]["pv_hp_tes_input_kwh"], 0)
        self.assertGreater(r["hourly"][1]["tes_discharge_heat_kwh"], 0)

    def test_waste_surplus_charges_storage_and_used_later(self):
        p = [dict(demand_kwh=0, irradiance_kw_m2=0, waste_availability=1),
             dict(demand_kwh=30, irradiance_kw_m2=0, waste_availability=0)]
        self.cfg.update(pv_kwp=0)
        r = simulate_hourly(p, self.cfg)
        self.assertGreater(r["hourly"][0]["waste_tes_input_kwh"], 0)
        self.assertGreater(r["hourly"][1]["tes_discharge_heat_kwh"], 0)

    def test_standby_loss_reduces_initial_soc(self):
        p = [dict(demand_kwh=0, irradiance_kw_m2=0, waste_availability=0)]
        self.cfg.update(tes_initial_soc_kwh=80, tes_loss_fraction_per_h=0.01, pv_kwp=0)
        r = simulate_hourly(p, self.cfg)
        self.assertAlmostEqual(r["hourly"][0]["tes_loss_kwh"], 0.8)
        self.assertAlmostEqual(r["hourly"][0]["tes_soc_kwh"], 79.2)

    def test_run_8760_profile(self):
        p = [dict(demand_kwh=5, irradiance_kw_m2=0, waste_availability=0)]*8760
        self.cfg.update(pv_kwp=0, mass_flow_kg_s=0.01, tes_capacity_kwh_th=0)
        r = simulate_hourly(p, self.cfg)
        self.assertEqual(len(r["hourly"]), 8760)
        self.assertAlmostEqual(r["summaries"]["Boiler only"]["demand_kwh_th"], 43800)

    def test_invalid_settings_and_dispatch_rejected(self):
        for k, value in [("heat_pump_cop", .8), ("boiler_efficiency", 1.2),
                         ("tes_roundtrip_efficiency", 0), ("tes_initial_soc_kwh", 500),
                         ("pv_kwp", -1), ("tes_loss_fraction_per_h", 1)]:
            cfg = copy.deepcopy(self.cfg)
            cfg[k] = value
            with self.subTest(k=k), self.assertRaises(ValueError):
                simulate_hourly(self.p, cfg)
        with self.assertRaises(ValueError):
            simulate_hourly(self.p, self.cfg, dispatch="global_optimum")

    def test_no_negative_energy_flows(self):
        r = simulate_hourly(self.p, self.cfg)
        for row in r["hourly"]:
            for key, val in row.items():
                if isinstance(val, (float, int)) and key != "hour":
                    self.assertGreaterEqual(val, -1e-8, msg=key)


if __name__ == "__main__":
    unittest.main()
