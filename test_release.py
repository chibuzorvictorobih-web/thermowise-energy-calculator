"""Release validation of scenario energy conservation and numerical safety."""
import math
import random
import unittest
from pathlib import Path
from decentralised import simulate_hourly, default_settings, example_profile, validate_profile

class ReleasePhysicsTests(unittest.TestCase):
    def setUp(self):
        self.cfg = default_settings()

    def test_reference_demand_2181(self):
        self.assertAlmostEqual(sum(row["demand_kwh"] for row in example_profile()), 2181)

    def test_reference_summaries_physics(self):
        result = simulate_hourly(example_profile(), self.cfg)
        summaries = result["summaries"]
        self.assertEqual(len(summaries), 3)
        for name, row in summaries.items():
            self.assertAlmostEqual(row["demand_kwh_th"], 2181, places=6, msg=name)
            self.assertGreaterEqual(row["total_cost"], 0)
            self.assertGreaterEqual(row["emissions_kg_co2e"], 0)

    def test_daily_reference_costs(self):
        result = simulate_hourly(example_profile(), self.cfg)
        sums = result["summaries"]
        self.assertAlmostEqual(sums["Boiler only"]["total_cost"], 256.5882352941177, places=6)
        self.assertAlmostEqual(sums["Grid heat pump + boiler"]["total_cost"], 167.4558823529412, places=6)
        self.assertAlmostEqual(sums["PV + waste heat + TES + HP"]["total_cost"], 43.23629600824367, places=5)

    def test_full_hourly_storage_heat_and_solar_conservation(self):
        run = simulate_hourly(example_profile(), self.cfg)
        eta = math.sqrt(self.cfg["tes_roundtrip_efficiency"])
        previous_soc = self.cfg["tes_initial_soc_kwh"]
        for hour in run["hourly"]:
            with self.subTest(hour=hour["hour"]):
                delivered = sum(hour[k] for k in (
                    "waste_direct_kwh", "hp_pv_direct_heat_kwh", "tes_discharge_heat_kwh",
                    "hp_grid_heat_kwh", "boiler_heat_kwh"))
                self.assertAlmostEqual(delivered, hour["demand_kwh"], places=6)
                self.assertAlmostEqual(hour["pv_generation_kwh"],
                    hour["pv_to_hp_kwh"] + hour["pv_unused_kwh"], places=6)
                self.assertAlmostEqual(hour["waste_potential_kwh"],
                    hour["waste_direct_kwh"] + hour["waste_tes_input_kwh"] + hour["waste_unused_kwh"], places=6)
                self.assertAlmostEqual(hour["tes_soc_kwh"], previous_soc - hour["tes_loss_kwh"]
                    + eta * hour["tes_charge_input_kwh"] - hour["tes_discharge_heat_kwh"] / eta, places=6)
                self.assertAlmostEqual(hour["pv_to_hp_kwh"],
                    hour["pv_to_hp_direct_kwh"] + hour["pv_to_hp_storage_kwh"], places=6)
                self.assertAlmostEqual(hour["hp_pv_direct_heat_kwh"],
                    self.cfg["heat_pump_cop"] * hour["pv_to_hp_direct_kwh"], places=6)
                self.assertAlmostEqual(hour["boiler_heat_kwh"],
                    self.cfg["boiler_efficiency"] * hour["boiler_fuel_kwh"], places=6)
                self.assertAlmostEqual(hour["hp_grid_heat_kwh"],
                    self.cfg["heat_pump_cop"] * hour["grid_import_kwh"], places=6)
                hp_heat = (hour["hp_pv_direct_heat_kwh"] + hour["hp_grid_heat_kwh"]
                          + hour["pv_hp_tes_input_kwh"])
                self.assertLessEqual(hp_heat, self.cfg["hp_capacity_kw_th"] + 1e-7)
                previous_soc = hour["tes_soc_kwh"]

    def test_free_initial_storage_is_identified_but_bounded(self):
        self.cfg.update(tes_initial_soc_kwh=120)
        run = simulate_hourly([dict(demand_kwh=0, irradiance_kw_m2=0,waste_availability=0)],self.cfg)
        self.assertLessEqual(run["hourly"][0]["tes_soc_kwh"], 120)

    def test_randomized_hourly_balances_60_scenarios(self):
        rng = random.Random(2026)
        for trial in range(60):
            cfg = default_settings()
            cfg.update(pv_kwp=rng.uniform(0, 200), hp_capacity_kw_th=rng.uniform(0, 200),
                       tes_capacity_kwh_th=rng.uniform(0, 500),
                       tes_charge_kw_th=rng.uniform(0, 150), tes_discharge_kw_th=rng.uniform(0, 150),
                       electricity_price=rng.uniform(0, 1.0), fuel_price=rng.uniform(0, 1.0),
                       tes_loss_fraction_per_h=rng.uniform(0, .05))
            count = rng.randrange(1, 72)
            profile = [dict(demand_kwh=rng.uniform(0, 300),
                           irradiance_kw_m2=rng.uniform(0, 1.1),
                           waste_availability=rng.random()) for _ in range(count)]
            dispatch = "hp_first" if trial % 2 else "cost_aware"
            result = simulate_hourly(profile, cfg, dispatch)
            for row in result["hourly"]:
                heat = sum(row[key] for key in ("waste_direct_kwh", "hp_pv_direct_heat_kwh",
                            "tes_discharge_heat_kwh", "hp_grid_heat_kwh", "boiler_heat_kwh"))
                self.assertAlmostEqual(heat, row["demand_kwh"], delta=1e-5)
                self.assertAlmostEqual(row["pv_generation_kwh"],
                    row["pv_to_hp_kwh"] + row["pv_unused_kwh"], delta=1e-5)
                self.assertGreaterEqual(row["tes_soc_kwh"], -1e-6)
                self.assertLessEqual(row["tes_soc_kwh"], cfg["tes_capacity_kwh_th"] + 1e-6)

    def test_extreme_pv_overflow_rejected(self):
        self.cfg["pv_kwp"] = 1.5e308
        with self.assertRaises(ValueError):
            simulate_hourly([dict(demand_kwh=1,irradiance_kw_m2=1.5,waste_availability=0)], self.cfg)

    def test_zero_demand_day_can_still_charge_storage(self):
        profile = [dict(demand_kwh=0,irradiance_kw_m2=1,waste_availability=0)]
        r=simulate_hourly(profile,self.cfg)
        self.assertEqual(r["summaries"]["Boiler only"]["total_cost"],0)
        self.assertEqual(r["hourly"][0]["boiler_heat_kwh"],0)

    def test_partial_storage_power_limits(self):
        self.cfg.update(tes_capacity_kwh_th=30,tes_charge_kw_th=10,
                        tes_discharge_kw_th=6,tes_initial_soc_kwh=20)
        r=simulate_hourly(example_profile(),self.cfg)
        self.assertTrue(all(x["tes_charge_input_kwh"] <= 10+1e-7 for x in r["hourly"]))
        self.assertTrue(all(x["tes_discharge_heat_kwh"] <= 6+1e-7 for x in r["hourly"]))

    def test_nongrid_baseline_emissions_factor(self):
        r=simulate_hourly(example_profile(),self.cfg)
        baseline=r["summaries"]["Boiler only"]
        self.assertAlmostEqual(baseline["grid_import_kwh_e"],0)
        self.assertAlmostEqual(baseline["emissions_kg_co2e"],
            baseline["boiler_fuel_kwh"]*self.cfg["fuel_emissions_kg_kwh"])

    def test_invalid_csv_row_values_rejected(self):
        cases=[dict(demand_kwh=3,irradiance_kw_m2=-1,waste_availability=.5),
               dict(demand_kwh=-1,irradiance_kw_m2=.2,waste_availability=.5),
               dict(demand_kwh=3,irradiance_kw_m2=.2,waste_availability=1.3)]
        for p in cases:
            with self.assertRaises(ValueError):validate_profile([p])

    def test_all_profile_data_finite(self):
        data=example_profile()
        self.assertEqual(len(data),24)
        self.assertTrue(all(math.isfinite(r[k]) for r in data for k in (
            "demand_kwh","irradiance_kw_m2","waste_availability")))

if __name__ == "__main__":unittest.main()
