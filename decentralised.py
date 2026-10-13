"""Hourly decentralised thermal-energy simulation for ThermoWise.

All balances are per one-hour time step. Electricity and heat are tracked
separately in kWh_e and kWh_th. No battery, grid export or capital-cost model.
The dispatch is a transparent *heuristic*, not a global optimum.
"""
from math import isfinite, sqrt

from calculations import calculate_heat_recovery, check_heat_exchanger_approach


PROFILE_COLUMNS = ("demand_kwh", "irradiance_kw_m2", "waste_availability")


def example_profile():
    """Synthetic 24-hour heat load, solar resource and waste heat availability."""
    demand = [65, 60, 57, 54, 56, 62, 80, 105, 113, 108, 100, 95,
              92, 96, 105, 116, 130, 132, 122, 105, 94, 86, 78, 70]
    sun = [0, 0, 0, 0, 0, 0.04, 0.18, 0.38, 0.58, 0.78, 0.91, 1.0,
           0.96, 0.84, 0.68, 0.44, 0.23, 0.07, 0, 0, 0, 0, 0, 0]
    availability = [0.85, 0.85, 0.85, 0.85, 0.85, 0.9, 1, 1, 1, 1, 1, 1,
                    1, 1, 1, 1, 1, 0.75, 0.4, 0.1, 0, 0, 0.5, 0.8]
    return [dict(hour=i, demand_kwh=float(demand[i]),
                 irradiance_kw_m2=float(sun[i]),
                 waste_availability=float(availability[i])) for i in range(24)]


def _nonnegative_finite(value, name, strictly_positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    if value < 0 or (strictly_positive and value == 0):
        raise ValueError(f"{name} must be {'positive' if strictly_positive else 'non-negative'}.")
    return float(value)


def validate_profile(profile):
    """Require 1–8760 consecutive one-hour records; optional hour column ignored."""
    if not isinstance(profile, (list, tuple)) or not 1 <= len(profile) <= 8760:
        raise ValueError("The hourly profile must contain 1 to 8760 rows.")
    validated = []
    for i, record in enumerate(profile):
        if not isinstance(record, dict):
            raise ValueError(f"Row {i+1} is not a data record.")
        row = {}
        for column in PROFILE_COLUMNS:
            if column not in record:
                raise ValueError(f"Hourly profile needs column '{column}'.")
            row[column] = _nonnegative_finite(record[column], f"Row {i+1} {column}")
        if row["irradiance_kw_m2"] > 1.5:
            raise ValueError(f"Row {i+1}: irradiance exceeds the accepted range of 1.5 kW/m².")
        if row["waste_availability"] > 1:
            raise ValueError(f"Row {i+1}: waste availability must be between 0 and 1.")
        validated.append(row)
    return validated


def validate_settings(cfg):
    """Validate physically meaningful scenario values before simulation."""
    positives = ("heat_pump_cop", "boiler_efficiency",)
    for name in positives:
        _nonnegative_finite(cfg[name], name, strictly_positive=True)
    if not 0 < cfg["boiler_efficiency"] <= 1:
        raise ValueError("Boiler efficiency must be a fraction between 0 and 1.")
    if cfg["heat_pump_cop"] < 1:
        raise ValueError("Heat-pump COP must be at least 1.")
    for name in ("pv_kwp", "pv_performance_ratio", "hp_capacity_kw_th",
                 "tes_capacity_kwh_th", "tes_charge_kw_th", "tes_discharge_kw_th",
                 "tes_initial_soc_kwh", "tes_roundtrip_efficiency", "tes_loss_fraction_per_h",
                 "electricity_price", "fuel_price", "grid_emissions_kg_kwh",
                 "fuel_emissions_kg_kwh", "mass_flow_kg_s", "specific_heat_kj_kg_k",
                 "recovery_fraction", "min_approach_k"):
        _nonnegative_finite(cfg[name], name)
    if not 0 <= cfg["pv_performance_ratio"] <= 1:
        raise ValueError("PV performance ratio must be 0–1.")
    if not 0 < cfg["tes_roundtrip_efficiency"] <= 1:
        raise ValueError("TES round-trip efficiency must be greater than 0 and at most 1.")
    if not 0 <= cfg["tes_loss_fraction_per_h"] < 1:
        raise ValueError("TES hourly fractional loss must be between 0 and 1 (exclusive).")
    if not 0 <= cfg["tes_initial_soc_kwh"] <= cfg["tes_capacity_kwh_th"]:
        raise ValueError("Initial storage energy cannot exceed thermal-storage capacity.")
    if not 0 <= cfg["recovery_fraction"] <= 1:
        raise ValueError("Recovery fraction must be between 0 and 1.")
    if cfg["pv_kwp"] > 0 and cfg["pv_performance_ratio"] == 0:
        raise ValueError("PV performance ratio must exceed zero when solar PV is installed.")
    if cfg["min_approach_k"] <= 0:
        raise ValueError("Minimum heat-exchanger approach must be positive.")
    # The existing engine performs the detailed hot/sink temperature validation.


def default_settings():
    return dict(
        pv_kwp=80.0,
        pv_performance_ratio=0.82,
        hp_capacity_kw_th=105.0,
        heat_pump_cop=3.2,
        tes_capacity_kwh_th=180.0,
        tes_charge_kw_th=65.0,
        tes_discharge_kw_th=65.0,
        tes_initial_soc_kwh=0.0,
        tes_roundtrip_efficiency=0.9,
        tes_loss_fraction_per_h=0.002,
        boiler_efficiency=0.85,
        electricity_price=0.24,
        fuel_price=0.10,
        grid_emissions_kg_kwh=0.40,
        fuel_emissions_kg_kwh=0.20,
        mass_flow_kg_s=0.65,
        hot_inlet_c=80.0,
        hot_outlet_c=50.0,
        specific_heat_kj_kg_k=4.18,
        recovery_fraction=0.50,
        sink_return_c=35.0,
        sink_supply_c=45.0,
        min_approach_k=5.0,
    )


def _summarise(rows, cfg, label):
    def total(key):
        return sum(r.get(key, 0.0) for r in rows)
    demand = total("demand_kwh")
    grid = total("grid_import_kwh")
    fuel = total("boiler_fuel_kwh")
    pv = total("pv_generation_kwh")
    pv_used = total("pv_to_hp_kwh")
    cost = grid * cfg["electricity_price"] + fuel * cfg["fuel_price"]
    emissions = grid * cfg["grid_emissions_kg_kwh"] + fuel * cfg["fuel_emissions_kg_kwh"]
    if not all(isfinite(x) for x in (demand, grid, fuel, pv, pv_used, cost, emissions)):
        raise ValueError("Scenario totals overflowed; reduce extreme inputs.")
    return dict(
        name=label,
        demand_kwh_th=demand,
        grid_import_kwh_e=grid,
        boiler_fuel_kwh=fuel,
        pv_generated_kwh_e=pv,
        pv_used_kwh_e=pv_used,
        pv_self_consumption_pct=(100 * pv_used / pv if pv > 0 else 0.0),
        total_cost=cost,
        emissions_kg_co2e=emissions,
        heat_from_waste_kwh=total("waste_direct_kwh"),
        heat_from_pv_hp_kwh=total("hp_pv_direct_heat_kwh"),
        heat_from_storage_kwh=total("tes_discharge_heat_kwh"),
        heat_from_grid_hp_kwh=total("hp_grid_heat_kwh"),
        heat_from_boiler_kwh=total("boiler_heat_kwh"),
        tes_charged_from_waste_kwh=total("waste_tes_input_kwh"),
        tes_charged_from_pv_hp_kwh=total("pv_hp_tes_input_kwh"),
        tes_losses_kwh=total("tes_loss_kwh"),
        tes_end_soc_kwh=(rows[-1].get("tes_soc_kwh", 0.0) if rows else 0.0),
    )


def simulate_hourly(profile, settings, dispatch="cost_aware"):
    """Return physical hourly flows and 3 comparable operating scenarios.

    'cost_aware' uses grid heat-pump energy only when cheaper than boiler heat;
    'hp_first' uses the grid heat pump up to capacity before boiler backup.
    This is *rule-based* priority dispatch, not horizon-wide optimisation.
    """
    profile = validate_profile(profile)
    cfg = dict(settings)
    validate_settings(cfg)
    if dispatch not in ("cost_aware", "hp_first"):
        raise ValueError("Choose either 'cost_aware' or 'hp_first' dispatch.")

    # Reuse published ThermoWise thermal equations and HX temperature screening.
    thermal = calculate_heat_recovery(
        cfg["mass_flow_kg_s"], cfg["hot_inlet_c"], cfg["hot_outlet_c"],
        cfg["specific_heat_kj_kg_k"], len(profile), 100 * cfg["recovery_fraction"]
    )
    screen = check_heat_exchanger_approach(
        cfg["hot_inlet_c"], cfg["hot_outlet_c"], cfg["sink_return_c"],
        cfg["sink_supply_c"], cfg["min_approach_k"]
    )
    waste_kw = thermal["recovered_power_kw"] if screen["passes_temperature_screen"] else 0.0
    eta_c = sqrt(cfg["tes_roundtrip_efficiency"])
    eta_d = eta_c
    soc = cfg["tes_initial_soc_kwh"]
    hybrid = []
    boiler_only = []
    hp_grid = []

    for hour, p in enumerate(profile):
        demand = p["demand_kwh"]
        pv = cfg["pv_kwp"] * cfg["pv_performance_ratio"] * p["irradiance_kw_m2"]
        waste = waste_kw * p["waste_availability"]
        hp_limit = cfg["hp_capacity_kw_th"]
        if not all(isfinite(x) for x in (pv, waste, hp_limit)):
            raise ValueError(f"Calculated energy overflowed in hour {hour}; reduce extreme inputs.")

        # Scenario A: same demand served entirely by the conventional boiler.
        boiler_only.append(dict(hour=hour, demand_kwh=demand,
                                boiler_heat_kwh=demand,
                                boiler_fuel_kwh=demand/cfg["boiler_efficiency"],
                                grid_import_kwh=0.0))

        # Scenario B: the identical heat pump is powered only from the grid.
        hp_heat = min(demand, hp_limit)
        backup_heat = demand - hp_heat
        hp_grid.append(dict(hour=hour, demand_kwh=demand, hp_grid_heat_kwh=hp_heat,
                            boiler_heat_kwh=backup_heat,
                            grid_import_kwh=hp_heat/cfg["heat_pump_cop"],
                            boiler_fuel_kwh=backup_heat/cfg["boiler_efficiency"]))

        # Scenario C: hybrid, rule-based priority controller.
        soc_before = soc
        standby_loss = soc * cfg["tes_loss_fraction_per_h"]
        soc -= standby_loss
        charge_input = 0.0  # thermal kWh entering TES (before eta_c)
        used_hp_heat = 0.0

        waste_direct = min(demand, waste)
        unmet = demand - waste_direct
        excess_waste = waste - waste_direct

        # Store excess recoverable waste heat, limited by input charge rating and capacity.
        waste_to_tes = min(
            excess_waste,
            cfg["tes_charge_kw_th"],
            max(0.0, (cfg["tes_capacity_kwh_th"]-soc)/eta_c),
        )
        soc += waste_to_tes*eta_c
        charge_input += waste_to_tes

        # Use PV-driven heat pump for current heating demand.
        hp_pv_direct = min(unmet, hp_limit, pv*cfg["heat_pump_cop"])
        pv_to_hp_direct = hp_pv_direct/cfg["heat_pump_cop"]
        unmet -= hp_pv_direct
        used_hp_heat += hp_pv_direct

        # Discharge TES (stored energy decreases before discharge efficiency).
        discharge_heat = min(unmet, cfg["tes_discharge_kw_th"], soc*eta_d)
        soc -= discharge_heat/eta_d
        unmet -= discharge_heat

        # Optional grid-driven heat pump, or conventional boiler if grid heat is dearer.
        grid_hp_cost_per_kwh_heat = cfg["electricity_price"] / cfg["heat_pump_cop"]
        boiler_cost_per_kwh_heat = cfg["fuel_price"] / cfg["boiler_efficiency"]
        prefer_grid_hp = dispatch == "hp_first" or grid_hp_cost_per_kwh_heat < boiler_cost_per_kwh_heat
        hp_grid_direct = min(unmet, max(0.0, hp_limit - used_hp_heat)) if prefer_grid_hp else 0.0
        unmet -= hp_grid_direct
        used_hp_heat += hp_grid_direct
        boiler_heat = max(0.0, unmet)

        # Any *unused* PV may make heat for future use, within same HP/TES ratings.
        pv_remaining = max(0.0, pv-pv_to_hp_direct)
        hp_remaining = max(0.0, hp_limit-used_hp_heat)
        pv_hp_to_tes = min(
            hp_remaining,
            pv_remaining*cfg["heat_pump_cop"],
            max(0.0, cfg["tes_charge_kw_th"]-charge_input),
            max(0.0, (cfg["tes_capacity_kwh_th"]-soc)/eta_c),
        )
        soc += pv_hp_to_tes*eta_c
        charge_input += pv_hp_to_tes
        pv_to_hp_storage = pv_hp_to_tes/cfg["heat_pump_cop"]
        pv_used = pv_to_hp_direct + pv_to_hp_storage
        unused_pv = max(0.0, pv-pv_used)
        grid_electricity = hp_grid_direct/cfg["heat_pump_cop"]
        fuel = boiler_heat/cfg["boiler_efficiency"]

        row = dict(
            hour=hour, demand_kwh=demand,
            pv_generation_kwh=pv, pv_to_hp_kwh=pv_used,
            pv_to_hp_direct_kwh=pv_to_hp_direct,
            pv_to_hp_storage_kwh=pv_to_hp_storage, pv_unused_kwh=unused_pv,
            waste_potential_kwh=waste, waste_direct_kwh=waste_direct,
            waste_tes_input_kwh=waste_to_tes,
            waste_unused_kwh=max(0.0, excess_waste-waste_to_tes),
            hp_pv_direct_heat_kwh=hp_pv_direct,
            hp_grid_heat_kwh=hp_grid_direct,
            tes_discharge_heat_kwh=discharge_heat,
            boiler_heat_kwh=boiler_heat,
            boiler_fuel_kwh=fuel,
            grid_import_kwh=grid_electricity,
            pv_hp_tes_input_kwh=pv_hp_to_tes,
            tes_charge_input_kwh=charge_input,
            tes_soc_before_kwh=soc_before,
            tes_soc_kwh=soc,
            tes_loss_kwh=standby_loss,
        )
        if any(isinstance(value, (int, float)) and not isfinite(value)
               for value in row.values()):
            raise ValueError(f"Energy calculation overflowed in hour {hour}; reduce extreme inputs.")
        # Simulation self-checks: preserve heat and electric energy balance.
        supplied = waste_direct+hp_pv_direct+discharge_heat+hp_grid_direct+boiler_heat
        if abs(supplied-demand) > 1e-7*max(1,demand):
            raise ArithmeticError(f"Heating energy mismatch in hour {hour}.")
        if not (-1e-7 <= soc <= cfg["tes_capacity_kwh_th"]+1e-7):
            raise ArithmeticError(f"Thermal storage exceeds bounds in hour {hour}.")
        if abs(pv - pv_used-unused_pv) > 1e-7*max(1,pv):
            raise ArithmeticError(f"PV energy mismatch in hour {hour}.")
        # Charge and discharge must individually respect their hourly ratings.
        if charge_input > cfg["tes_charge_kw_th"] + 1e-7 or discharge_heat > cfg["tes_discharge_kw_th"]+1e-7:
            raise ArithmeticError(f"TES hourly power rating exceeded in hour {hour}.")
        hybrid.append(row)

    summaries = {
        "Boiler only": _summarise(boiler_only, cfg, "Boiler only"),
        "Grid heat pump + boiler": _summarise(hp_grid, cfg, "Grid heat pump + boiler"),
        "PV + waste heat + TES + HP": _summarise(hybrid, cfg, "PV + waste heat + TES + HP"),
    }
    for name, s in summaries.items():
        s["savings_vs_boiler"] = summaries["Boiler only"]["total_cost"]-s["total_cost"]
        s["emissions_reduction_vs_boiler_kg"] = summaries["Boiler only"]["emissions_kg_co2e"]-s["emissions_kg_co2e"]
    return dict(
        profile_hours=len(profile),
        settings=cfg,
        dispatch=dispatch,
        temperature_screen=screen,
        waste_recovery_rating_kw=waste_kw,
        hourly=hybrid,
        summaries=summaries,
        lowest_cost=min(summaries, key=lambda n:summaries[n]["total_cost"]),
        lowest_emissions=min(summaries, key=lambda n:summaries[n]["emissions_kg_co2e"]),
    )
