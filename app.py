"""ThermoWise: educational, assumption-based industrial heating comparison."""

import math

import altair as alt
import pandas as pd
import streamlit as st

from decentralised import default_settings, example_profile, simulate_hourly

from calculations import (
    calculate_heat_recovery,
    check_heat_exchanger_approach,
    compare_heating_options,
)

st.set_page_config(
    page_title="ThermoWise | Energy Calculator", page_icon="🌡️", layout="wide"
)
st.title("🌡️ ThermoWise")
st.subheader("Industrial Energy Calculator and Decentralised Thermal System Simulator")
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

inputs_tab, results_tab, methodology_tab, validation_tab, decentralised_tab = st.tabs(
    ["Engineering Inputs", "Results", "Methodology", "Validation", "Decentralised System"]
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


# ================================================================
# THERMOWISE 2.0: HOURLY DECENTRALISED ENERGY SYSTEM
# ================================================================

with decentralised_tab:
    st.header("Decentralised Energy Management — Hourly Simulator")
    st.write(
        "Simulate solar PV, a heat pump, industrial waste-heat recovery, "
        "thermal energy storage and boiler backup on the **same hourly heat demand**. "
        "This is a transparent rule-based dispatcher, not a global optimiser."
    )
    st.caption(
        "One time step = one hour. Thermal energy is kWh_th; electric energy is "
        "kWh_e. No battery, grid export revenue or electricity demand other than "
        "the heat pump is modelled."
    )

    defaults = default_settings()
    st.subheader("1 · Choose an hourly profile")
    st.write(
        "Edit the 24-hour synthetic example or upload a CSV with **1–8,760 hourly rows**. "
        "Required columns: `demand_kwh`, `irradiance_kw_m2`, `waste_availability`. "
        "Availability is a fraction from 0 to 1; irradiance is the average "
        "solar irradiance in kW/m² during each hour."
    )
    example_df = pd.DataFrame(example_profile())
    st.download_button(
        "Download sample hourly CSV",
        example_df.to_csv(index=False).encode("utf-8"),
        file_name="thermowise_hourly_example.csv",
        mime="text/csv",
        key="download_example_profile",
    )
    uploaded_profile = st.file_uploader(
        "Upload hourly profile CSV (optional)", type=["csv"], key="hourly_csv_upload"
    )
    if uploaded_profile is not None:
        try:
            profile_df = pd.read_csv(uploaded_profile)
            if not 1 <= len(profile_df) <= 8760:
                raise ValueError("The CSV must contain between 1 and 8,760 hourly rows.")
            st.dataframe(profile_df.head(36), hide_index=True, use_container_width=True)
            st.caption(f"Showing up to 36 of {len(profile_df):,} uploaded hours.")
        except Exception as error:
            profile_df = None
            st.error(f"Cannot read the CSV: {error}")
    else:
        st.caption("Edit the synthetic example below. Click Run Hourly Energy Simulation to refresh results after edits.")
        profile_df = st.data_editor(
            example_df,
            key="editable_hourly_profile",
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            disabled=["hour"],
            column_config={
                "hour": st.column_config.NumberColumn("Hour", format="%d"),
                "demand_kwh": st.column_config.NumberColumn("Heat demand (kWh_th)", min_value=0.0),
                "irradiance_kw_m2": st.column_config.NumberColumn("Irradiance (kW/m²)", min_value=0.0, max_value=1.5),
                "waste_availability": st.column_config.NumberColumn("Waste availability (0–1)", min_value=0.0, max_value=1.0),
            },
        )

    with st.form("decentralised_form"):
        st.subheader("2 · Equipment and thermal-system settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            pv_kwp = st.number_input("Solar PV capacity (kWp)", min_value=0.0, value=defaults["pv_kwp"], step=5.0)
            pv_pr = st.number_input("PV performance ratio (0–1)", min_value=0.01, max_value=1.0, value=defaults["pv_performance_ratio"], step=0.01)
            hp_kw = st.number_input("Heat-pump heating capacity (kW_th)", min_value=0.0, value=defaults["hp_capacity_kw_th"], step=5.0)
            hp_cop = st.number_input("Hybrid heat-pump heating COP", min_value=1.0, value=defaults["heat_pump_cop"], step=0.1)
        with col2:
            tes_kwh = st.number_input("Thermal storage capacity (kWh_th)", min_value=0.0, value=defaults["tes_capacity_kwh_th"], step=10.0)
            tes_charge_kw = st.number_input("Thermal-storage max charging input (kW_th)", min_value=0.0, value=defaults["tes_charge_kw_th"], step=5.0)
            tes_discharge_kw = st.number_input("Thermal-storage max useful output (kW_th)", min_value=0.0, value=defaults["tes_discharge_kw_th"], step=5.0)
            tes_soc_initial = st.number_input("Starting storage energy (kWh_th)", min_value=0.0, max_value=float(tes_kwh), value=min(defaults["tes_initial_soc_kwh"], float(tes_kwh)), step=5.0)
            tes_eff = st.number_input("TES round-trip efficiency (0–1)", min_value=0.01, max_value=1.0, value=defaults["tes_roundtrip_efficiency"], step=0.01)
            tes_loss = st.number_input("TES standing loss (%/hour)", min_value=0.0, max_value=99.0, value=100*defaults["tes_loss_fraction_per_h"], step=0.1)
        with col3:
            hot_flow = st.number_input("Waste stream mass flow (kg/s)", min_value=0.01, value=defaults["mass_flow_kg_s"], step=0.05)
            hot_tin = st.number_input("Hot stream inlet (°C)", value=defaults["hot_inlet_c"], step=1.0)
            hot_tout = st.number_input("Hot stream outlet (°C)", value=defaults["hot_outlet_c"], step=1.0)
            hot_cp = st.number_input("Specific heat (kJ/kg·K)", min_value=0.01, value=defaults["specific_heat_kj_kg_k"], step=0.01)
            recovery_pct = st.number_input("Assumed waste-heat recovery (%)", min_value=0.0, max_value=100.0, value=100*defaults["recovery_fraction"], step=5.0)
            sink_return = st.number_input("Heat sink return (°C)", value=defaults["sink_return_c"], step=1.0)
            sink_supply = st.number_input("Heat sink target supply (°C)", value=defaults["sink_supply_c"], step=1.0)
            approach = st.number_input("Minimum exchanger approach (K)", min_value=0.1, value=defaults["min_approach_k"], step=0.5)

        st.subheader("3 · Energy prices, emissions and dispatch policy")
        a, b, c = st.columns(3)
        with a:
            boiler_eff_pct = st.number_input("Hybrid boiler efficiency (%)", min_value=1.0, max_value=100.0, value=100*defaults["boiler_efficiency"], step=1.0)
            elec_price = st.number_input("Grid electricity price (currency/kWh_e)", min_value=0.0, value=defaults["electricity_price"], format="%.3f", step=0.01)
        with b:
            fuel_price = st.number_input("Boiler fuel price (currency/kWh_fuel)", min_value=0.0, value=defaults["fuel_price"], format="%.3f", step=0.01)
            grid_factor = st.number_input("Grid emissions (kg CO₂e/kWh_e)", min_value=0.0, value=defaults["grid_emissions_kg_kwh"], step=0.05)
        with c:
            fuel_factor = st.number_input("Fuel emissions (kg CO₂e/kWh_fuel)", min_value=0.0, value=defaults["fuel_emissions_kg_kwh"], step=0.05)
            policy_label = st.selectbox("Rule-based dispatch", ["Cost-aware", "Heat-pump-first"])
        currency_hourly = st.text_input("Currency label", value="USD", max_chars=10)
        run_hourly = st.form_submit_button("Run Hourly Energy Simulation", type="primary")

    if run_hourly:
        try:
            if profile_df is None:
                raise ValueError("Provide a valid hourly CSV or use the editable example.")
            records = profile_df.to_dict(orient="records")
            cfg = dict(
                pv_kwp=pv_kwp, pv_performance_ratio=pv_pr,
                hp_capacity_kw_th=hp_kw, heat_pump_cop=hp_cop,
                tes_capacity_kwh_th=tes_kwh, tes_charge_kw_th=tes_charge_kw,
                tes_discharge_kw_th=tes_discharge_kw, tes_initial_soc_kwh=tes_soc_initial,
                tes_roundtrip_efficiency=tes_eff, tes_loss_fraction_per_h=tes_loss/100.0,
                boiler_efficiency=boiler_eff_pct/100.0, electricity_price=elec_price,
                fuel_price=fuel_price, grid_emissions_kg_kwh=grid_factor,
                fuel_emissions_kg_kwh=fuel_factor,
                mass_flow_kg_s=hot_flow, hot_inlet_c=hot_tin, hot_outlet_c=hot_tout,
                specific_heat_kj_kg_k=hot_cp, recovery_fraction=recovery_pct/100.0,
                sink_return_c=sink_return, sink_supply_c=sink_supply,
                min_approach_k=approach,
            )
            hourly_run = simulate_hourly(
                records, cfg,
                dispatch="cost_aware" if policy_label == "Cost-aware" else "hp_first",
            )
        except (ValueError, TypeError, KeyError, OverflowError, ArithmeticError) as error:
            st.session_state.pop("decentralised_run", None)
            st.error(f"Simulation inputs need correction: {error}")
        else:
            st.session_state["decentralised_run"] = hourly_run
            st.session_state["decentralised_currency"] = currency_hourly.strip() or "units"
            st.success("Hourly energy balances calculated. Results are shown below.")

    run = st.session_state.get("decentralised_run")
    if run is not None:
        unit = st.session_state.get("decentralised_currency", "units")
        screen_ok = run["temperature_screen"]["passes_temperature_screen"]
        if not screen_ok:
            st.warning("Heat-exchanger temperature screen failed: industrial waste-heat input was set to zero for this scenario.")
        st.caption(
            f"Last submitted run: {run['profile_hours']:,} one-hour records · Dispatch: {run['dispatch']} · "
            "Results apply only to these hours. Re-run after changing inputs; 24-hour examples are not annual forecasts."
        )
        summaries = run["summaries"]
        hybrid = summaries["PV + waste heat + TES + HP"]
        base_grid = summaries["Grid heat pump + boiler"]
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Heat served", f"{hybrid['demand_kwh_th']:,.1f} kWh_th")
        x2.metric("Hybrid operating cost", f"{hybrid['total_cost']:,.2f} {unit}")
        x3.metric("Grid purchased", f"{hybrid['grid_import_kwh_e']:,.1f} kWh_e")
        x4.metric("Grid reduction vs grid-HP", f"{base_grid['grid_import_kwh_e']-hybrid['grid_import_kwh_e']:,.1f} kWh_e")
        st.caption("The boiler-only baseline purchases fuel, not grid electricity. Grid comparison is therefore made against a grid-powered heat-pump alternative.")

        st.subheader("Comparison of three equal-demand scenarios")
        comparison_rows = []
        for scenario, values in summaries.items():
            comparison_rows.append({
                "Scenario": scenario,
                f"Cost ({unit}; profile period)": round(values["total_cost"], 2),
                "Grid imports (kWh_e)": round(values["grid_import_kwh_e"], 2),
                "Fuel purchased (kWh_fuel)": round(values["boiler_fuel_kwh"], 2),
                "Emissions (kg CO₂e)": round(values["emissions_kg_co2e"], 2),
                "Cost saving vs boiler": round(values["savings_vs_boiler"], 2),
            })
        comparison_df = pd.DataFrame(comparison_rows)
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)
        st.download_button(
            "Download scenario comparison (CSV)",
            comparison_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="thermowise_decentralised_scenarios.csv", mime="text/csv",
            key="decentralised_summary_download",
        )
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Operating cost over selected hours**")
            plot = alt.Chart(comparison_df).mark_bar().encode(
                y=alt.Y("Scenario:N", title=None),
                x=alt.X(f"Cost ({unit}; profile period):Q", title=f"Cost ({unit})", scale=alt.Scale(zero=True)),
            ).properties(height=220)
            st.altair_chart(plot, use_container_width=True)
        with c2:
            st.write("**Operational emissions**")
            plot = alt.Chart(comparison_df).mark_bar().encode(
                y=alt.Y("Scenario:N", title=None),
                x=alt.X("Emissions (kg CO₂e):Q", title="kg CO₂e", scale=alt.Scale(zero=True)),
            ).properties(height=220)
            st.altair_chart(plot, use_container_width=True)

        st.subheader("Hourly heat dispatch and storage behaviour")
        flows = pd.DataFrame(run["hourly"])
        heat_fields = {
            "waste_direct_kwh": "Waste heat directly used",
            "hp_pv_direct_heat_kwh": "Solar-powered heat pump",
            "tes_discharge_heat_kwh": "Thermal storage discharged",
            "hp_grid_heat_kwh": "Grid-powered heat pump",
            "boiler_heat_kwh": "Backup boiler",
        }
        heat_dispatch = flows[["hour", *heat_fields]].rename(columns=heat_fields)
        heat_long = heat_dispatch.melt("hour", var_name="Source", value_name="Heat supplied (kWh_th)")
        chart = alt.Chart(heat_long).mark_area().encode(
            x=alt.X("hour:Q", title="Simulation hour"),
            y=alt.Y("Heat supplied (kWh_th):Q", stack="zero"),
            color=alt.Color("Source:N"),
            tooltip=["hour:Q", "Source:N", alt.Tooltip("Heat supplied (kWh_th):Q", format=",.2f")],
        ).properties(height=260)
        st.altair_chart(chart, use_container_width=True)
        state_chart = alt.Chart(flows).transform_fold(
            ["tes_soc_kwh", "demand_kwh"], as_=["Metric", "Energy (kWh_th)"]
        ).mark_line().encode(
            x=alt.X("hour:Q", title="Simulation hour"),
            y=alt.Y("Energy (kWh_th):Q", title="Energy (kWh_th)"),
            color=alt.Color("Metric:N"),
            tooltip=["hour:Q", "Metric:N", alt.Tooltip("Energy (kWh_th):Q", format=",.2f")],
        ).properties(height=260)
        st.altair_chart(state_chart, use_container_width=True)
        st.caption("Stored thermal energy (kWh_th) and thermal energy demanded in each one-hour interval (kWh_th) are shown together; these represent different physical quantities.")

        st.subheader("Energy accounting and controller results")
        m1, m2, m3 = st.columns(3)
        m1.metric("PV generation", f"{hybrid['pv_generated_kwh_e']:,.1f} kWh_e")
        m2.metric("PV electricity consumed", f"{hybrid['pv_used_kwh_e']:,.1f} kWh_e")
        m3.metric("PV self-consumption", f"{hybrid['pv_self_consumption_pct']:,.1f}%")
        st.write(
            f"Lowest modelled operating cost: **{run['lowest_cost']}**. "
            f"Lowest operational emissions: **{run['lowest_emissions']}**. "
            "These are comparisons, not proof of global optimisation."
        )
        st.info(
            "Controller order: use available waste heat; use PV heat-pump output for immediate heating; "
            "draw stored heat; choose grid heat-pump heating or boiler backup using the selected priority; "
            "use surplus PV to charge storage when capacity remains. Waste heat surplus also charges storage. "
            "Storage charging/discharging rates, round-trip losses and standing losses are enforced."
        )
        st.download_button(
            "Download hourly energy flows (CSV)",
            flows.to_csv(index=False).encode("utf-8-sig"),
            file_name="thermowise_decentralised_hourly.csv", mime="text/csv",
            key="decentralised_hourly_download",
        )
        with st.expander("See hourly energy-flow table"):
            st.dataframe(flows, hide_index=True, use_container_width=True)
        st.warning(
            "Educational screening only: hourly PV is estimated from irradiance × installed kWp × performance ratio. "
            "Heat-pump COP is constant; fuel emissions and grid emissions are user-defined operational factors. "
            "Thermal-storage losses are simplified; no PV inverter clipping, heat-pump source constraints, "
            "demand uncertainty, capital economics, battery or grid export is modelled. "
            "The dispatch is rule-based, not an optimal control solver."
        )


st.divider()
st.caption("ThermoWise 2.0 | Educational Decentralised Thermal Energy Simulation | Rule-based controller")
