"""Transparent, assumption-based ThermoWise engineering calculations.

Units are explicit throughout. Pure functions allow independent unit tests.
No tariffs, equipment efficiencies, or emission factors are fetched remotely.
"""

from math import isfinite


def _number(name, value, *, minimum=None, maximum=None, strict_min=False):
    """Reject NaN/infinity/bools and out-of-range inputs."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    try:
        finite = isfinite(value)
    except (TypeError, OverflowError):
        finite = False
    if not finite:
        raise ValueError(f"{name} must be finite.")
    if minimum is not None and (value <= minimum if strict_min else value < minimum):
        relation = "greater than" if strict_min else "at least"
        raise ValueError(f"{name} must be {relation} {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must not exceed {maximum}.")


def _check_outputs(name_to_result):
    """Protect against overflow even when individual inputs were finite."""
    for name, value in name_to_result.items():
        if isinstance(value, (int, float)) and not isfinite(value):
            raise ValueError(f"Calculated {name} is not finite; reduce extreme inputs.")


def calculate_heat_recovery(
    mass_flow_kg_s,
    inlet_temp_c,
    outlet_temp_c,
    specific_heat_kj_kg_k,
    annual_hours,
    recovery_percent,
):
    """Steady, sensible thermal power and annual heat from a hot process stream.

    Output is thermal energy, not electricity saved or proven heat-exchanger output.
    """
    _number("Mass flow", mass_flow_kg_s, minimum=0, strict_min=True)
    _number("Specific heat", specific_heat_kj_kg_k, minimum=0, strict_min=True)
    _number("Inlet temperature", inlet_temp_c, minimum=-273.15)
    _number("Outlet temperature", outlet_temp_c, minimum=-273.15)
    _number("Annual operating hours", annual_hours, minimum=0, maximum=8760, strict_min=True)
    _number("Recovery factor", recovery_percent, minimum=0, maximum=100)
    if inlet_temp_c <= outlet_temp_c:
        raise ValueError("Inlet temperature must be higher than outlet temperature.")

    difference = inlet_temp_c - outlet_temp_c
    available_power = mass_flow_kg_s * specific_heat_kj_kg_k * difference
    recovered_power = available_power * recovery_percent / 100.0
    # Clamp insignificant floating-point subtraction noise at full recovery.
    unrecovered_power = max(0.0, available_power - recovered_power)
    results = {
        "temperature_difference_c": difference,
        "available_power_kw": available_power,
        "recovered_power_kw": recovered_power,
        "unrecovered_power_kw": unrecovered_power,
        "annual_available_kwh": available_power * annual_hours,
        "annual_recovered_kwh": recovered_power * annual_hours,
        "annual_unrecovered_kwh": unrecovered_power * annual_hours,
    }
    _check_outputs(results)
    return results


def check_heat_exchanger_approach(
    hot_inlet_c,
    hot_outlet_c,
    sink_return_c,
    sink_supply_c,
    min_approach_c,
):
    """Preliminary countercurrent terminal approach check, not HX sizing.

    Two terminal differences are *necessary*, but not sufficient, for a
    practical exchanger; the sink heat-capacity rate and pinch profile are
    unmodelled. This screen must not be used as detailed feasibility proof.
    """
    for name, temp in (
        ("Hot inlet temperature", hot_inlet_c),
        ("Hot outlet temperature", hot_outlet_c),
        ("Heat-sink return temperature", sink_return_c),
        ("Heat-sink supply temperature", sink_supply_c),
    ):
        _number(name, temp, minimum=-273.15)
    _number("Minimum exchanger approach", min_approach_c, minimum=0, strict_min=True)
    if hot_inlet_c <= hot_outlet_c:
        raise ValueError("Hot-side inlet temperature must exceed hot-side outlet temperature.")
    if sink_supply_c <= sink_return_c:
        raise ValueError("Heat-sink supply temperature must exceed return temperature.")

    hot_end_difference = hot_inlet_c - sink_supply_c
    cold_end_difference = hot_outlet_c - sink_return_c
    feasible = (
        hot_end_difference >= min_approach_c
        and cold_end_difference >= min_approach_c
    )
    return {
        "passes_temperature_screen": feasible,
        "hot_end_approach_c": hot_end_difference,
        "cold_end_approach_c": cold_end_difference,
        "minimum_required_approach_c": min_approach_c,
    }


def compare_heating_options(
    annual_demand_kwh,
    annual_recovered_kwh,
    annual_hours,
    boiler_efficiency_percent,
    heat_pump_cop,
    fuel_price_per_kwh,
    electricity_price_per_kwh,
    fuel_emission_kg_per_kwh,
    electricity_emission_kg_per_kwh,
    recovery_aux_power_kw,
    recovery_capital_cost,
    heat_pump_capital_cost,
    recovery_feasible=True,
):
    """Annual cost/emissions for equal useful heat demand.

    Assumes constant operating conditions and coincident demand and heat
    source. Recovery auxiliaries scale with used fraction of recoverable heat
    (a simplifying linear-part-load assumption). All prices are user inputs.
    """
    nonnegative = {
        "Annual heat demand": annual_demand_kwh,
        "Recovered heat": annual_recovered_kwh,
        "Fuel price": fuel_price_per_kwh,
        "Electricity price": electricity_price_per_kwh,
        "Fuel emission factor": fuel_emission_kg_per_kwh,
        "Electricity emission factor": electricity_emission_kg_per_kwh,
        "Recovery auxiliary power": recovery_aux_power_kw,
        "Recovery investment": recovery_capital_cost,
        "Heat pump investment": heat_pump_capital_cost,
    }
    for name, value in nonnegative.items():
        _number(name, value, minimum=0)
    _number("Annual heat demand", annual_demand_kwh, minimum=0, strict_min=True)
    _number("Operating hours", annual_hours, minimum=0, maximum=8760, strict_min=True)
    _number("Boiler efficiency", boiler_efficiency_percent, minimum=0, maximum=100, strict_min=True)
    _number("Heat pump COP", heat_pump_cop, minimum=1)
    if not isinstance(recovery_feasible, bool):
        raise ValueError("Heat-recovery screening result must be True or False.")

    efficiency = boiler_efficiency_percent / 100.0
    usable_heat = min(annual_demand_kwh, annual_recovered_kwh) if recovery_feasible else 0.0
    utilised_fraction = usable_heat / annual_recovered_kwh if annual_recovered_kwh > 0 else 0.0
    auxiliary_electricity = recovery_aux_power_kw * annual_hours * utilised_fraction

    baseline_fuel = annual_demand_kwh / efficiency
    recovery_fuel = (annual_demand_kwh - usable_heat) / efficiency
    heat_pump_electricity = annual_demand_kwh / heat_pump_cop

    options = {
        "Boiler only": {
            "fuel_kwh": baseline_fuel,
            "electricity_kwh": 0.0,
            "annual_cost": baseline_fuel * fuel_price_per_kwh,
            "emissions_kg": baseline_fuel * fuel_emission_kg_per_kwh,
            "capital_cost": 0.0,
        },
        "Electric heat pump": {
            "fuel_kwh": 0.0,
            "electricity_kwh": heat_pump_electricity,
            "annual_cost": heat_pump_electricity * electricity_price_per_kwh,
            "emissions_kg": heat_pump_electricity * electricity_emission_kg_per_kwh,
            "capital_cost": heat_pump_capital_cost,
        },
    }
    if recovery_feasible:
        options["Waste heat + boiler"] = {
            "fuel_kwh": recovery_fuel,
            "electricity_kwh": auxiliary_electricity,
            "annual_cost": recovery_fuel * fuel_price_per_kwh + auxiliary_electricity * electricity_price_per_kwh,
            "emissions_kg": recovery_fuel * fuel_emission_kg_per_kwh + auxiliary_electricity * electricity_emission_kg_per_kwh,
            "capital_cost": recovery_capital_cost,
        }

    baseline_cost = options["Boiler only"]["annual_cost"]
    baseline_emissions = options["Boiler only"]["emissions_kg"]
    for option in options.values():
        savings = baseline_cost - option["annual_cost"]
        option["annual_savings"] = savings
        option["emissions_saved_kg"] = baseline_emissions - option["emissions_kg"]
        # An immediately useful zero-investment upgrade has zero payback.
        option["simple_payback_years"] = (
            option["capital_cost"] / savings if savings > 0 else None
        )
        _check_outputs(option)

    results = {
        "options": options,
        "usable_recovered_kwh": usable_heat,
        "unused_potential_kwh": max(0.0, annual_recovered_kwh - usable_heat),
        "heat_demand_covered_percent": 100.0 * usable_heat / annual_demand_kwh,
        "auxiliary_electricity_kwh": auxiliary_electricity,
        "lowest_operating_cost": min(options, key=lambda x: options[x]["annual_cost"]),
        "lowest_emissions": min(options, key=lambda x: options[x]["emissions_kg"]),
        "recovery_feasible": recovery_feasible,
    }
    _check_outputs(results)
    return results
