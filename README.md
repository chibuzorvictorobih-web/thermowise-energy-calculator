# ThermoWise 2.0 🌡️
### Industrial energy calculator + decentralised thermal energy simulation

**Live website:** [ThermoWise on Streamlit](https://thermowise-energy-calculator.streamlit.app/)  
**Code repository:** [ThermoWise on GitHub](https://github.com/chibuzorvictorobih-web/thermowise-energy-calculator)

> **Release status:** This folder is the prepared **2.0 release package**. The live website will only show version 2.0 **after** this code is committed to the connected GitHub repository and Streamlit rebuilds the app. Do not assume the link already has the upgraded features.

## Overview

ThermoWise is an **educational engineering pre-feasibility application** built in Python and Streamlit. The original industrial waste-heat calculator remains intact. Version 2.0 adds a separate hourly, rule-based **decentralised thermal-energy system simulator** for solar PV, heat pumps, waste-heat recovery, thermal storage and backup boilers.

The application estimates energy balances, purchased energy, operating costs and **operational** greenhouse-gas emissions using user-defined assumptions. It **does not** certify equipment sizing, forecast real plant performance, optimise investment decisions, or solve global optimal control.

## Five tabs

1. **Engineering Inputs** — thermal and cost inputs for the original annual heat-recovery scenarios.
2. **Results** — original annual energy, cost and emissions comparison, graphs and CSV export.
3. **Methodology** — governing engineering formulas and simplifications.
4. **Validation** — five built-in consistency checks for the original annual model.
5. **Decentralised System** — new hour-by-hour hybrid thermal energy system with an editable example and hourly CSV upload.

## What's new in version 2.0

- **Solar PV:** installed kWp × irradiance × constant performance ratio.
- **Heat pump:** configurable heating COP and thermal output limit.
- **Waste heat:** hourly source availability subject to a preliminary exchanger temperature-approach screen.
- **Thermal energy storage (TES):** rated capacity, charge and discharge powers, initial stored heat, round-trip efficiency and hourly standby losses.
- **Controller:** either simple marginal **cost-aware** dispatch or **heat-pump-first** dispatch; **not** a globally optimal controller.
- **Three equal-demand comparisons:** boiler-only, grid-powered heat pump + boiler, and decentralised hybrid system.
- **Outputs:** costs, emissions, grid imports, fuel purchases, energy-flow charts, storage behaviour and downloadable hourly/results CSV files.
- **Data input:** editable 24-hour synthetic example or user-provided hourly CSV (1 to 8,760 one-hour records).

## Start in Windows (simplest)

1. **Extract the entire ZIP**. Do not run Python from inside the compressed ZIP.
2. Open the `ThermoWise_2.0_FINAL` extracted folder.
3. Double-click **`RUN_THERMOWISE_WINDOWS.bat`**. This creates `.venv` if necessary, installs dependencies, runs the engineering tests, and starts Streamlit. Internet is required the first time for installing packages.
4. Open the browser address from the terminal (usually `http://localhost:8501`).
5. Choose **Decentralised System** and click **Run Hourly Energy Simulation** with its defaults.

If Windows cannot locate Python, install Python 3.12 or 3.13 and use the manual commands in [START_HERE.txt](START_HERE.txt).

## Manual commands

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Sample result (synthetic 24-hour profile)

Default example heat demand is **2,181 kWh_th over 24 hours** (not annual energy). With the included example equipment, prices and emissions assumptions:

| Same-demand scenario | 24-hour energy-only cost (example currency units) | 24-hour operational emissions (kg CO₂e) |
| --- | ---: | ---: |
| Boiler only | 256.59 | 513.18 |
| Grid heat pump + boiler | 167.46 | 282.66 |
| PV + waste heat + TES + heat pump | 43.24 | 72.06 |

These are hypothetical educational outcomes, **not prices, operating savings, or carbon factors verified for any facility**. The hybrid is cheaper for this example only; other user inputs can reverse the comparison. The model has no capital cost calculation for this hybrid simulation and no net-present-value claims.

## Hourly CSV format

Three required numeric columns (optional `hour` column is ignored):

```csv
demand_kwh,irradiance_kw_m2,waste_availability
80,0.0,1.0
90,0.5,0.75
120,0.8,0.0
```

- `demand_kwh`: useful heat demand for each hour, kWh_th, ≥ 0.
- `irradiance_kw_m2`: average solar irradiance over the hour, 0–1.5 kW/m².
- `waste_availability`: fraction of rated usable recovered heat, 0–1.

There must be **1–8,760 rows**. Each row is an hour; the model does not infer or repair missing timestamps. Download the complete [example file](hourly_example.csv).

## Verification

**58 automated test methods** pass locally in the release package: 24 original annual-model tests, 22 hourly-component tests, and 12 additional release checks (including randomized hourly balance trials). Test locally with:

```powershell
py -m unittest discover -s . -p "test_*.py" -v
```

The automated GitHub workflow performs the same suite for Python 3.12 and 3.13 after publication. The **Streamlit browser interface and deployed website must still be manually smoke-tested** after release; numerical unit tests alone cannot prove UI or hosting compatibility.

See [VALIDATION.md](VALIDATION.md) and [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

## Engineering limitations

- Fixed time step: 1 hour; no forecasts, uncertainty, equipment start-up or minimum operating load.
- Fixed heat-pump COP and PV performance ratio; no module temperature correction, inverter clipping or changing source temperatures.
- Exchanger screening checks **terminal temperature approaches only**, not full exchanger feasibility, heat capacity rates, heat-transfer areas, fouling or pinch.
- Heat source and demand are assumed to match the hourly series; annual profiles require actual annual input rows.
- No electrical battery, general building electric loads, network power flow, grid export, PV investment costs or thermal-system capital economics in the new hourly simulator.
- TES energy loss and efficiency are simplified; initial stored heat must be supplied by the user and should not be mistaken for free energy.
- “Cost-aware” is a **rule-based heuristic**, not an economic optimisation solution. “Lowest cost” and “lowest emissions” mean among the **three simulated scenarios for the selected inputs**, not universally optimal engineering solutions.

## Folder contents

| File | Purpose |
| --- | --- |
| `app.py` | All five Streamlit tabs, graphs, inputs and exports |
| `calculations.py` | Original thermal/economic calculation functions |
| `decentralised.py` | New hourly dispatch and energy accounting |
| `test_calculations.py` | 24 original tests |
| `test_decentralised.py` | 22 hourly tests |
| `test_release.py` | 12 additional physics/edge-case tests |
| `hourly_example.csv` | Synthetic 24-hour sample profile |
| `DECENTRALISED_MODEL.md` | Engineering and controller description |
| `VALIDATION.md` | Verification evidence and limitations |
| `RELEASE_CHECKLIST.md` | Manual checks before/after publishing |
| `DEPLOYMENT.md` | Update existing GitHub and Streamlit application |
| `.github/workflows/tests.yml` | Automatically tests changes to `main` |

## Privacy

All example data is synthetic. No private laptop paths, employer-specific operating conditions, authentication tokens or database connections are required. **Never upload confidential industrial information** to a publicly hosted example application. Inputs are handled in the Streamlit session, subject to the hosting provider's normal platform processing and telemetry.

## Project status

**Prepared version 2.0 release candidate.** Numerical tests and syntax checks pass locally. Deployment requires updating the GitHub repository, after which Streamlit Community Cloud normally rebuilds the connected app. Only mark the release “Live” when post-deployment UI checks pass.
