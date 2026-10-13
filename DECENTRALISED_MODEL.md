# ThermoWise 2.0 — decentralised energy system model

This version **extends**, rather than replaces, the original ThermoWise v1.0 calculator. The four original tabs remain available; the fifth tab is named **Decentralised System**. All values are synthetic educational inputs, not plant measurements.

## Task 1 — System architecture, time step, user inputs

One row represents **one hour**. The model accepts 1–8,760 rows in a CSV file, or lets visitors edit an included **24-hour synthetic example**. Each row must have exactly these numerical inputs (a separate `hour` column is optional):

| CSV column | Unit | Allowed range | Meaning |
|---|---|---|---|
| `demand_kwh` | kWh_th/hour | >= 0 | Useful heat required during hour |
| `irradiance_kw_m2` | kW/m² (hourly average) | 0–1.5 | Solar irradiation intensity averaged over the hour |
| `waste_availability` | fraction | 0–1 | Fraction of rated waste-heat availability for this hour |

The system combines solar PV, a finite-capacity electric heat pump, screened industrial waste-heat recovery, sensible thermal-energy storage, and a backup boiler. The user supplies capacities, prices, emission factors, COP, efficiency, and storage losses. The annual v1.0 tool remains separate; the new tab only compares **the user-selected time horizon** (24 hours in the provided example), not automatically an entire year.

## Task 2 — Hourly component physics

- PV generation, kWh_e in one hour = PV installed capacity (kWp) × PV performance ratio × average irradiance (kW/m²) / (1 kW/m²) × 1 hour. The reference irradiance is implicit in the numeric expression. No export payments, battery, module temperature, clipping or inverter overload effects.
- Maximum recoverable sensible waste heat rating, kW_th = hot mass flow (kg/s) × specific heat (kJ/(kg·K)) × (hot inlet − hot outlet) (K) × assumed recovery fraction. For hour *t*, the available useful potential is this rating × `waste_availability[t]` × 1 hour. The pre-existing countercurrent terminal-temperature screen must pass; otherwise waste heat is set to zero. This is **not** full exchanger sizing or a guarantee of thermal deliverability.
- Heat-pump useful heating output, kWh_th = COP × electric input (kWh_e), capped by thermal heating capacity (kW_th × 1 hour). COP is constant and does not depend on ambient temperature or temperature lift.
- Boiler fuel consumption, kWh_fuel = thermal output (kWh_th) / boiler efficiency (fraction).
- TES state of charge is **stored thermal energy** (kWh_th), capped by TES thermal capacity. Round-trip efficiency is split evenly between charging and discharging: eta_charge = eta_discharge = sqrt(eta_roundtrip). Each hour begins with standby heat loss `SOC × hourly_loss_fraction`. Input charging rate (kW_th), delivered discharge rate (kW_th), and SOC are all limited. At the start of the profile, SOC is the user input (0 by default). Unused stored heat at the end is reported, not converted into savings.
- Solar electricity to the heat pump (kWh_e) + unused PV electricity (kWh_e) = generated solar electricity (kWh_e). No grid export or income is represented.
- Every hour: waste direct + solar-HP direct + TES delivered heat + grid-HP direct + boiler heat = demanded heat (kWh_th). Charge flows are **not** counted as heat supplied to the load in the same hour.

## Task 3 — Rule-based hourly dispatch and comparisons

The controller executes a documented **heuristic**, not dynamic programming or globally optimal scheduling:

1. Meet current heating demand from directly recovered waste heat; charge TES from excess waste heat, subject to ratings.
2. Use available solar PV electricity to drive the heat pump to meet remaining heating demand (within HP capacity).
3. Discharge TES to serve remaining demand (within TES rate/SOC limits).
4. In **cost-aware** mode, use grid-powered heat pump only when unit purchased-electricity cost / COP is less than fuel cost / boiler efficiency, otherwise use the boiler. In **heat-pump-first** mode, use grid electricity within remaining HP capacity first; the boiler covers any balance.
5. Charge remaining TES capacity with surplus solar PV via the heat pump if HP capacity is available. Unused PV is curtailed with no credit.

The model compares the **same** hourly heating-demand series under:
- Conventional **boiler only** (purchases fuel, no grid electricity).
- **Grid-only heat pump with backup boiler** (same HP thermal capacity, no PV, storage or waste heat).
- **Decentralised hybrid** (PV + heat pump + screened waste heat + TES + backup boiler).

Comparisons include operating costs, operational CO2e emissions, fuel energy, grid electricity, PV self-consumption and per-hour dispatch. The economically lowest listed scenario and emissions-lowest listed scenario are shown, but they are **not** globally optimised configurations. The boiler baseline has zero grid electricity by definition; always compare grid-import reductions against the **grid-HP scenario**, not against boiler-only.

### Limitations and responsible interpretation

This is a **concept-stage thermal energy management prototype**, not equipment-sizing software, a robust MPC controller, a dispatch optimizer with look-ahead, an industrial design or a financial investment model. Perfectly predictable hourly quantities are assumed; the cost-aware rule does not consider future solar, availability, storage opportunity cost, degradation or stochasticity. The PV model uses user-supplied solar irradiance with a fixed performance ratio. No PV inverter clipping or panel temperature correction, demand response, actual electrical network, dynamic COP, dynamic fuel emissions, auxiliary parasitics, circulation electricity, thermal stratification, pinch analysis, or variable heat-exchanger effectiveness is represented. Annualised results require genuine hour-by-hour annual inputs; do not multiply one day by 365 and claim a validated annual forecast.

If the site only has a heat pump and thermal store with **no other electric demand**, the model does not represent a complete electricity microgrid. Consequently, this is an important expansion toward decentralised thermal system modelling, but not a comprehensive decentralised multi-energy optimisation solver.

## Validation

Run **all 58** automated tests (24 original, 22 hourly and 12 release checks):

```powershell
python -m unittest discover -s . -p "test_*.py" -v
```

Run the app:

```powershell
python -m streamlit run app.py
```

For the supplied 24-hour example, expect **2,181 kWh_th** total heat demand and an initial state of charge of **0 kWh_th**. Under the default hypothetical tariffs, the costs are approximately **256.59** (boiler), **167.46** (grid heat pump + boiler), and **43.24** (hybrid) currency units over 24 hours. These illustrative costs are not market prices. Check exact numbers after installing Python requirements.

Try changing heat-sink supply temperature to 78°C: the waste-heat channel should be disabled by the existing temperature-screen logic. Try a profile with zero solar irradiance: the solar heat-pump energy should drop to zero. Try zero TES capacity: there should be no storage charging or discharging.
