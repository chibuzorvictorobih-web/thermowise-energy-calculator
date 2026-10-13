"""ThermoWise: educational, assumption-based industrial heating comparison."""

import math

import altair as alt
import pandas as pd
import streamlit as st

from calculations import (
    calculate_heat_recovery,
    check_heat_exchanger_approach,
    compare_heating_options,
)

st.set_page_config(
    page_title="ThermoWise | Energy Calculator", page_icon="🌡️", layout="wide"
)
st.title("🌡️ ThermoWise")
st.subheader("Smart Industrial Energy Optimisation Calculator")
st.write(
    "Estimate sensible heat recovery and compare heating options using "
    "your own engineering, cost, and emissions assumptions."
)
st.caption(
    "Educational pre-feasibility tool, not a heat-exchanger design, "
    "equipment-sizing calculation, or investment recommendation."
)

with st.sidebar:
    st.header("About ThermoWise")
    st.write("Compare conventional boiler heating, waste heat with boiler backup, and an electric heat pump.")
    st.info("Assumes constant annual operating conditions and heat supply coincident with demand.")
    st.caption("Tariffs, emission factors, COP, efficiencies and investment amounts are user assumptions.")

for name in ("thermal_results", "economic_results", "screen_results", "currency"):
    if name not in st.session_state:
        st.session_state[name] = None

inputs_tab, results_tab, methodology_tab, validation_tab = st.tabs(
    ["Engineering Inputs", "Results", "Methodology", "Validation"]
)

with inputs_tab:
    with st.form("energy_form"):
        st.header("1. Hot process stream")
        a, b = st.columns(2)
        with a:
            mass_flow = st.number_input("Mass flow rate (kg/s)", min_value=0.01, value=2.0, step=0.1)
            inlet_temp = st.number_input("Hot-stream inlet temperature (°C)", min_value=-273.15, value=80.0, step=1.0)
            annual_hours = st.number_input("Annual operating hours (h/year)", min_value=1, max_value=8760, value=4000, step=100)
        with b:
            outlet_temp = st.number_input("Hot-stream proposed outlet temperature (°C)", min_value=-273.15, value=50.0, step=1.0)
            cp = st.number_input("Specific heat capacity (kJ/kg·K)", min_value=0.01, value=4.18, step=0.01)
            recovery_percent = st.number_input("Assumed heat recovery factor (%)", min_value=0.0, max_value=100.0, value=50.0, step=5.0)

        st.header("2. Preliminary heat-exchanger temperature screening")
        st.caption("Necessary terminal temperature differences for a countercurrent exchanger. Passing does not prove an exchanger is practical.")
        a, b, c = st.columns(3)
        with a:
            sink_return = st.number_input("Heat-sink return temperature (°C)", min_value=-273.15, value=35.0, step=1.0)
        with b:
            sink_supply = st.number_input("Heat-sink target supply temperature (°C)", min_value=-273.15, value=45.0, step=1.0)
        with c:
            min_approach = st.number_input("Minimum terminal approach (K)", min_value=0.1, value=5.0, step=0.5)

        st.header("3. Heating technologies")
        a, b = st.columns(2)
        with a:
            demand = st.number_input("Annual useful heating demand (kWh_th/year)", min_value=1.0, value=600000.0, step=10000.0)
            boiler_eff = st.number_input("Boiler efficiency (%)", min_value=1.0, max_value=100.0, value=85.0, step=1.0)
        with b:
            cop = st.number_input("Heat-pump heating COP", min_value=1.0, value=3.5, step=0.1)
            aux_kw = st.number_input("Recovery auxiliary electricity at full use (kW)", min_value=0.0, value=2.0, step=0.5)

        st.header("4. User-defined energy costs and emission factors")
        currency = st.text_input("Currency label (e.g., USD, NGN, EUR)", value="USD", max_chars=10)
        a, b = st.columns(2)
        with a:
            fuel_price = st.number_input("Fuel price (currency/kWh_fuel)", min_value=0.0, value=0.12, step=0.01, format="%.3f")
            fuel_emissions = st.number_input("Fuel emission factor (kg CO₂e/kWh_fuel)", min_value=0.0, value=0.20, step=0.01, format="%.3f")
        with b:
            electricity_price = st.number_input("Electricity price (currency/kWh_electric)", min_value=0.0, value=0.18, step=0.01, format="%.3f")
            electricity_emissions = st.number_input("Electricity emission factor (kg CO₂e/kWh_electric)", min_value=0.0, value=0.40, step=0.01, format="%.3f")

        st.header("5. Assumed upfront investments")
        a, b = st.columns(2)
        with a:
            recovery_capex = st.number_input("Waste-heat system capital cost (currency)", min_value=0.0, value=60000.0, step=1000.0)
        with b:
            hp_capex = st.number_input("Heat-pump capital cost (currency)", min_value=0.0, value=90000.0, step=1000.0)
        submitted = st.form_submit_button("Calculate and Compare", type="primary")

    if submitted:
        try:
            thermal = calculate_heat_recovery(
                mass_flow, inlet_temp, outlet_temp, cp, annual_hours, recovery_percent
            )
            screen = check_heat_exchanger_approach(
                inlet_temp, outlet_temp, sink_return, sink_supply, min_approach
            )
            economic = compare_heating_options(
                annual_demand_kwh=demand,
                annual_recovered_kwh=thermal["annual_recovered_kwh"],
                annual_hours=annual_hours,
                boiler_efficiency_percent=boiler_eff,
                heat_pump_cop=cop,
                fuel_price_per_kwh=fuel_price,
                electricity_price_per_kwh=electricity_price,
                fuel_emission_kg_per_kwh=fuel_emissions,
                electricity_emission_kg_per_kwh=electricity_emissions,
                recovery_aux_power_kw=aux_kw,
                recovery_capital_cost=recovery_capex,
                heat_pump_capital_cost=hp_capex,
                recovery_feasible=screen["passes_temperature_screen"],
            )
        except ValueError as error:
            st.session_state.thermal_results = None
            st.session_state.economic_results = None
            st.session_state.screen_results = None
            st.error(str(error))
        else:
            st.session_state.thermal_results = thermal
            st.session_state.economic_results = economic
            st.session_state.screen_results = screen
            st.session_state.currency = currency.strip() or "units"
            if screen["passes_temperature_screen"]:
                st.success("Calculations complete. The preliminary temperature screen passes. Open Results.")
            else:
                st.warning("Temperature screen failed. Waste-heat recovery is excluded from the technology comparison. Open Results for details.")

with results_tab:
    st.header("Engineering Results")
    thermal = st.session_state.thermal_results
    comparison = st.session_state.economic_results
    screen = st.session_state.screen_results
    if thermal is None or comparison is None or screen is None:
        st.warning("Enter assumptions and click Calculate and Compare first.")
    else:
        unit = st.session_state.currency
        c1, c2, c3 = st.columns(3)
        c1.metric("Available sensible power", f"{thermal['available_power_kw']:,.2f} kW")
        c2.metric("Estimated recoverable power", f"{thermal['recovered_power_kw']:,.2f} kW")
        c3.metric("Annual recovery potential", f"{thermal['annual_recovered_kwh']/1000:,.2f} MWh_th")

        st.subheader("Heat-exchanger temperature screen")
        c1, c2 = st.columns(2)
        c1.metric("Hot-end temperature difference", f"{screen['hot_end_approach_c']:,.2f} K")
        c2.metric("Cold-end temperature difference", f"{screen['cold_end_approach_c']:,.2f} K")
        if screen["passes_temperature_screen"]:
            st.info("Terminal temperature approach screen passes. Full exchanger feasibility still requires further design checks.")
        else:
            st.error("Terminal temperature approach screen fails: waste heat + boiler is excluded from the ranking and cost charts.")

        st.metric("Useful recovered heat (limited by demand)", f"{comparison['usable_recovered_kwh']/1000:,.2f} MWh_th/year")
        st.write(f"Annual heating demand covered by recovered heat: **{comparison['heat_demand_covered_percent']:.1f}%**")
        if comparison["unused_potential_kwh"] > 0:
            st.warning("Some theoretical heat-recovery potential cannot be counted as useful with the stated heat demand and temperature screen.")

        st.subheader("Annual scenario comparison")
        rows = []
        for name, option in comparison["options"].items():
            payback = option["simple_payback_years"]
            rows.append({
                "Option": name,
                f"Operating cost ({unit}/year)": round(option["annual_cost"], 2),
                "Operational emissions (t CO₂e/year)": round(option["emissions_kg"] / 1000, 2),
                f"Savings vs boiler ({unit}/year)": round(option["annual_savings"], 2),
                "Simple payback (years)": round(payback, 2) if payback is not None else "No positive payback",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button(
            "Download scenario results (CSV)",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="thermowise_results.csv",
            mime="text/csv",
        )

        st.subheader("Readable cost and emissions comparisons")
        chart_records = [
            {"Option": name, "Annual cost": opt["annual_cost"], "Emissions tonnes": opt["emissions_kg"] / 1000}
            for name, opt in comparison["options"].items()
        ]
        chart_data = pd.DataFrame(chart_records)
        sort_order = [record["Option"] for record in chart_records]
        chart_height = max(180, len(sort_order) * 65)
        cost_chart = alt.Chart(chart_data).mark_bar().encode(
            y=alt.Y("Option:N", sort=sort_order, title=None),
            x=alt.X("Annual cost:Q", title=f"Annual cost ({unit}/year)", scale=alt.Scale(zero=True)),
            tooltip=["Option:N", alt.Tooltip("Annual cost:Q", format=",.2f")],
        ).properties(height=chart_height)
        emissions_chart = alt.Chart(chart_data).mark_bar().encode(
            y=alt.Y("Option:N", sort=sort_order, title=None),
            x=alt.X("Emissions tonnes:Q", title="Operational emissions (t CO₂e/year)", scale=alt.Scale(zero=True)),
            tooltip=["Option:N", alt.Tooltip("Emissions tonnes:Q", format=",.2f")],
        ).properties(height=chart_height)
        st.write("**Energy-only operating cost**")
        st.altair_chart(cost_chart, use_container_width=True)
        st.write("**Annual operational emissions**")
        st.altair_chart(emissions_chart, use_container_width=True)

        st.subheader("Model-based recommendations")
        st.success(f"Lowest annual operating cost: **{comparison['lowest_operating_cost']}**")
        st.success(f"Lowest annual operational emissions: **{comparison['lowest_emissions']}**")
        st.caption(
            "Recommendations consider annual operating cost or operational emissions only; "
            "not lifetime cost, equipment limits, time-varying supply, or full technical feasibility. "
            "A tie is resolved by the order in which options are displayed."
        )

with methodology_tab:
    st.header("Equations, scope, and assumptions")
    st.latex(r"\dot{Q}_{\mathrm{available}}=\dot{m}\,c_p\,(T_{\mathrm{hot,in}}-T_{\mathrm{hot,out}})")
    st.latex(r"E_{\mathrm{potential}}=\dot{Q}_{\mathrm{available}}\,(\eta/100)\,t")
    st.latex(r"E_{\mathrm{useful}}=\min(E_{\mathrm{potential}},E_{\mathrm{demand}})")
    st.latex(r"\Delta T_{\mathrm{hot\ end}}=T_{\mathrm{hot,in}}-T_{\mathrm{sink,supply}}")
    st.latex(r"\Delta T_{\mathrm{cold\ end}}=T_{\mathrm{hot,out}}-T_{\mathrm{sink,return}}")
    st.write("Both terminal differences must reach the user-specified minimum approach for a countercurrent heat exchanger; this is a screening test only.")
    st.latex(r"E_{\mathrm{boiler,fuel}}=E_{\mathrm{demand}}/\eta_{\mathrm{boiler}}")
    st.latex(r"E_{\mathrm{WHR,fuel}}=(E_{\mathrm{demand}}-E_{\mathrm{useful}})/\eta_{\mathrm{boiler}}")
    st.latex(r"E_{\mathrm{HP,electric}}=E_{\mathrm{demand}}/COP")
    st.write("Annual cost = purchased fuel × fuel price + purchased electricity × electricity price.")
    st.write("Annual operational emissions = fuel × fuel factor + electricity × electricity factor.")
    st.write("Simple payback = assumed capital cost / positive annual operating-cost saving; it excludes financing, maintenance, depreciation, and equipment life.")
    st.warning(
        "Assumptions: sensible heat only; constant flow and heat capacity; fixed recovery factor, boiler efficiency and heat-pump COP; "
        "coincident heat supply and heating demand; simplified auxiliary electricity proportional to useful heat utilisation; "
        "no thermal storage; no heat exchanger sizing or pinch analysis; no lifecycle emissions or economic discounting. "
        "Prices, costs and emissions factors are examples supplied by the user, not market data."
    )

with validation_tab:
    st.header("Built-in consistency checks")
    st.write("These checks supplement (but do not replace) independently executed unit tests included with the project.")
    thermal = st.session_state.thermal_results
    comparison = st.session_state.economic_results
    if thermal is None or comparison is None:
        st.info("Run a calculation first.")
    else:
        checks = {
            "Thermal power balance": math.isclose(
                thermal["available_power_kw"],
                thermal["recovered_power_kw"] + thermal["unrecovered_power_kw"],
                rel_tol=1e-10, abs_tol=1e-9,
            ),
            "Annual thermal energy balance": math.isclose(
                thermal["annual_available_kwh"],
                thermal["annual_recovered_kwh"] + thermal["annual_unrecovered_kwh"],
                rel_tol=1e-10, abs_tol=1e-6,
            ),
            "Useful heat cannot exceed annual demand": (
                0 <= comparison["heat_demand_covered_percent"] <= 100 + 1e-10
            ),
            "Purchased energy and emissions are non-negative": all(
                option["fuel_kwh"] >= 0
                and option["electricity_kwh"] >= 0
                and option["emissions_kg"] >= 0
                for option in comparison["options"].values()
            ),
            "Ineligible waste-heat option is excluded": (
                comparison["recovery_feasible"] or "Waste heat + boiler" not in comparison["options"]
            ),
        }
        for label, passed in checks.items():
            st.write(f"{'✅' if passed else '❌'} {label}")
        if all(checks.values()):
            st.success("All five built-in checks passed for the current inputs.")
        else:
            st.error("One or more consistency checks failed; do not rely on these results.")

st.divider()
st.caption("ThermoWise | Educational Industrial Energy Decision-Support Prototype | v1.0")
