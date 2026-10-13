# ThermoWise 🌡️
### Industrial Heat-Recovery and Energy Decision-Support Calculator

**ThermoWise** is an interactive **Python + Streamlit** educational application. A user can provide their own thermal-process, financial, and emissions assumptions to estimate sensible waste-heat potential and compare three ways of supplying the same annual useful heating demand.

> **Scope:** an educational **pre-feasibility tool**. It is not a certified heat-exchanger design, a plant energy audit, or a basis for an investment or operating decision without further engineering verification.

## What users can calculate

- Available sensible thermal power from mass flow, specific heat, and hot-fluid temperature drop.
- Estimated annual recovered heat and the amount actually useful toward a specified annual heat demand.
- Preliminary countercurrent heat-exchanger **terminal temperature-approach screening**.
- Purchased energy, energy-only operating expenditure, and operational CO₂-equivalent emissions for:
  - Boiler-only heating (reference scenario)
  - Waste-heat recovery with a backup boiler (when screening passes)
  - Electric heat pump
- Annual savings versus the boiler reference, **simple** capital payback, and minimum annual operating-cost and operational-emissions choices.
- Downloadable comparison results in CSV format and visual comparisons with horizontal bar charts.

## Quick start

Requires **Python 3.12 or 3.13** and an internet connection for the initial package installation.

```bash
python -m venv .venv
```

**Windows (PowerShell):** install packages with the environment's Python (no shell activation required):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**macOS / Linux:**

```bash
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m streamlit run app.py
```

Then open the local address shown in the terminal, commonly `http://localhost:8501`.

## Example (synthetic inputs)

| Input | Example value |
| --- | ---: |
| Hot fluid mass flow | 2 kg/s |
| Hot inlet / outlet temperature | 80°C / 50°C |
| Specific heat capacity | 4.18 kJ/(kg·K) |
| Annual operating hours | 4,000 h |
| Assumed heat-recovery factor | 50% |
| Heat sink return / supply temperature | 35°C / 45°C |
| Minimum exchanger temperature approach | 5 K |
| Annual useful heat demand | 600,000 kWh_th |
| Boiler efficiency | 85% |
| Heat pump coefficient of performance (COP) | 3.5 |
| Fuel / electricity tariff | 0.12 / 0.18 currency units per kWh |
| Fuel / electricity emission factor | 0.20 / 0.40 kg CO₂e per purchased kWh |
| Recovery auxiliary electrical load | 2 kW at full use |
| Recovery / heat pump capital cost | 60,000 / 90,000 currency units |

**Expected outputs from the example:**

- Available sensible heat: **250.80 kW**.
- Estimated recovered heat: **125.40 kW**, or **501,600 kWh_th/year**.
- Temperature-approach screen: **passes** (35 K at the hot end, 15 K at the cold end).

| Option | Energy-only operating cost (currency/year) | Operational emissions (t CO₂e/year) | Simple payback (years) |
| --- | ---: | ---: | ---: |
| Boiler only | 84,705.88 | 141.18 | — |
| Waste heat + boiler | 15,331.76 | 26.35 | 0.86 |
| Electric heat pump | 30,857.14 | 68.57 | 1.67 |

All inputs are **illustrative** and **not measured data**. The currency is a placeholder; changing its label does **not** convert exchange rates.

## Engineering equations

For constant-specific-heat sensible cooling of a hot fluid stream:

```text
Available thermal power (kW) = mass flow (kg/s) × cp (kJ/(kg·K)) × (hot inlet − hot outlet) (K)
Potential recovered heat (kWh/year) = available thermal power × (recovery factor/100) × operating hours
Useful recovered heat = min(potential recovered heat, annual heat demand), if temperature screen passes
Boiler fuel input = heating demand / boiler efficiency
Heat pump electricity = heating demand / heat pump COP
Annual operating cost = purchased fuel × fuel price + purchased electricity × electricity price
Operational emissions = purchased fuel × fuel factor + purchased electricity × electricity factor
Simple payback = initial investment / positive annual operating-cost saving
```

Waste-heat recovery is **excluded from the comparison** when the hot-end or cold-end terminal temperature difference is smaller than the user-defined minimum approach. Passing this screen is **not proof of exchanger feasibility**.

## Validation and limitations

To run the **24 automated calculation tests**:

```bash
python -m unittest -v test_calculations.py
```

See [VALIDATION.md](VALIDATION.md) for the independent worked example, test coverage, manual checks, and limitations.

**Key limitations:** steady sensible heat, constant cp, no phase change; annual source and demand assumed coincident; no heat-exchanger sizing or whole-profile pinch analysis; fixed COP and boiler efficiency; simplified recovery auxiliaries; no thermal storage, maintenance, tax, finance, discount rate, embodied emissions, or lifecycle analysis. A lower modeled cost is **not a general recommendation** for a real facility.

## Privacy and source data

- The repository uses **synthetic, user-editable example values**. No proprietary refinery data, organization-specific performance data, or private computer paths are required.
- User calculations occur in the app session; the project code does not implement a database for storing user entries. Hosting providers may process ordinary service telemetry.
- Do **not** submit employer-confidential data to a publicly hosted demonstration.
- The `.gitignore` file keeps local Python environments, temporary files and `.env` files out of a standard Git commit. Review all files manually before uploading.

## Repository files

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit interface and interactive charts |
| `calculations.py` | Pure engineering and economic functions |
| `test_calculations.py` | 24 automated unit tests |
| `requirements.txt` | Python dependencies |
| `VALIDATION.md` | Verification cases, equations, constraints and limitations |
| `DEPLOYMENT.md` | GitHub + Streamlit Community Cloud publishing instructions |
| `.github/workflows/tests.yml` | GitHub Actions test automation on push |

## Deploy and share

Follow [DEPLOYMENT.md](DEPLOYMENT.md) to put the repository on GitHub and deploy `app.py` to Streamlit Community Cloud. Add the actual live links here **after** deployment:

- **Live application:** _Add live Streamlit URL_
- **Source repository:** _Add published GitHub URL_

## Project status

**Version 1.0 — educational demonstrator.** This project demonstrates integration of thermal engineering, numerical modelling, comparative energy economics, environmental indicators, input validation, and a usable web interface. It does not claim to solve a full plant optimisation problem.

