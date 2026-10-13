# ThermoWise 2.0 — Release acceptance checklist

## Before publishing (Windows / VS Code)

- [ ] Run `RUN_THERMOWISE_WINDOWS.bat`; it installs dependencies and prints `Ran 58 tests` followed by `OK`.
- [ ] Launch `http://localhost:8501`: five tabs appear (Engineering Inputs, Results, Methodology, Validation, Decentralised System).
- [ ] In **Decentralised System**, use defaults and click **Run Hourly Energy Simulation**; 24 one-hour records show **2,181 kWh_th** heat demand.
- [ ] Check cost comparison: boiler-only ≈ **256.59**, grid HP + boiler ≈ **167.46**, hybrid ≈ **43.24** in the default example currency.
- [ ] The two cost/emissions charts, hourly heat-dispatch chart, TES chart and downloadable CSV files work.
- [ ] Set **heat sink supply temperature to 78°C** (not return): waste-heat screen fails and hybrid waste input goes to zero.
- [ ] Reset and set **PV capacity = 0**: solar generation and solar heat-pump usage are zero.
- [ ] Set **TES capacity = 0**, initial SOC = 0: charging/discharging vanish and the simulation still completes.
- [ ] Existing original calculator tabs still work; validation tab passes its five consistency checks after the annual input form runs.

## After GitHub publication

- [ ] GitHub's Actions → `ThermoWise validation` shows all Python jobs green (3.12 and 3.13).
- [ ] https://thermowise-energy-calculator.streamlit.app/ shows **Decentralised System** as the fifth tab (indicates the release is live).
- [ ] Test 24-hour defaults and export in the publicly hosted app, ideally in a second browser.
- [ ] Confirm `README.md` contains correct source and live links.
- [ ] Do not claim global optimization, equipment-sizing accuracy, investment payback for the hybrid, or guaranteed carbon savings.

## Engineering uncertainty

The 58 test methods include 60 deterministic randomized model settings evaluated in one of the methods. The original 24 tests and 22 hourly unit tests were retained; 12 new release methods verify energy conservation, overflow handling, bounds, and the worked example. These tests verify the described model under selected cases, not real-world field accuracy.
