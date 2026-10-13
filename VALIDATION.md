# ThermoWise — Engineering validation (v1.0)

## What the application estimates

This is an **educational pre-feasibility calculator**, not a heat-exchanger design or an investment recommendation. It compares alternatives supplying the **same annual useful heat demand**:

- Boiler only (reference)
- Waste-heat recovery plus backup boiler **only when the countercurrent terminal approach screen passes**
- Electric heat pump

Thermal recovery is capped at useful annual heating demand. An assumed linear reduction in recovery-auxiliary electricity is applied if less than the recovered thermal potential is used. This part-load assumption may differ from real plant operation.

## Reference example (illustrative inputs)

| Input | Value |
|---|---:|
| Hot-stream mass flow rate | 2 kg/s |
| Hot-stream inlet / outlet | 80°C / 50°C |
| Specific heat | 4.18 kJ/(kg·K) |
| Annual operating hours | 4,000 |
| Assumed recovery factor | 50% |
| Sink return / target supply | 35°C / 45°C |
| Required minimum terminal approach | 5 K |
| Annual useful heating demand | 600,000 kWh_th |
| Boiler efficiency / heat-pump COP | 85% / 3.5 |
| Fuel / electricity prices | 0.12 / 0.18 currency per kWh purchased |
| Fuel / electricity emissions factors | 0.20 / 0.40 kg CO2e per kWh purchased |
| Recovery auxiliary power (at full use) | 2 kW |
| Recovery / heat-pump capital costs | 60,000 / 90,000 currency units |

Independent calculations:

- Temperature difference = 30 K
- Available sensible thermal power = 2 × 4.18 × 30 = **250.80 kW**
- Recovery potential at 50% = **125.40 kW**, or **501,600 kWh_th/year**
- Hot-end temperature difference = 80 − 45 = **35 K**; cold-end = 50 − 35 = **15 K**; the terminal screen passes (minimum 5 K)
- Baseline purchased boiler fuel = 600,000 / 0.85 = **705,882.35 kWh/year**
- Waste-heat-backup boiler fuel = (600,000 − 501,600) / 0.85 = **115,764.71 kWh/year**
- Recovery auxiliary electricity = 2 × 4,000 = **8,000 kWh/year**
- Heat-pump electricity = 600,000 / 3.5 = **171,428.57 kWh/year**

| Technology | Annual operating cost | Annual operational emissions | Simple payback vs boiler |
|---|---:|---:|---:|
| Boiler only | 84,705.88 | 141.18 t CO2e | N/A |
| Waste heat + boiler | 15,331.76 | 26.35 t CO2e | 0.86 years |
| Electric heat pump | 30,857.14 | 68.57 t CO2e | 1.67 years |

Costs above use a **hypothetical currency** and user-defined tariffs and emissions factors, not current quotes or measured site data.

## Automated test suite

From the project's VS Code terminal, run:

```powershell
python -m unittest -v test_calculations.py
```

There are **24 automated test cases**, covering the reference values, conservation checks, invalid temperature direction, nonpositive flow and specific heat, 0% and 100% recovery, annual hours bounds, temperature limits, numeric NaN/Infinity/overflow, countercurrent approach screening, heat demand caps, auxiliary load scaling, infeasible recovery exclusion, no-savings payback, zero-investment payback, zero emission factors, and invalid costs/COP/boiler efficiency.

## Manual app checks

1. Default values → `Calculate and Compare` → **Results**: check 250.80 kW available, 125.40 kW potential and the three costs shown above.
2. **Validation** tab after running: verify all five built-in consistency checks pass.
3. Set **hot-stream outlet temperature to 90°C** while the inlet is 80°C. The app must display an input error and not outdated results.
4. Restore outlet to 50°C. Set **sink target supply temperature to 78°C**. The app must warn that the terminal approach screen fails and **remove “Waste heat + boiler”** from the comparison and recommendations.
5. Restore sink supply to 45°C. Set **recovery factor to 0%**. The waste-heat option must have **no auxiliary electricity**, no recovery benefit and no positive payback.
6. Restore recovery factor to 50%, change useful heat demand to **100,000 kWh_th/year**. Useful recovered heat must be limited to **100,000 kWh_th**, even though thermal potential is 501,600 kWh_th/year.
7. Ensure horizontal graph category names are readable. Try exporting **Download scenario results (CSV)**.

## Engineering limitations

- The thermal calculation assumes a steady sensible-heat stream, constant specific heat, and a specified temperature change. It does not handle latent heat, varying fluid properties or plant heat balances.
- Terminal temperature differences are a **necessary but insufficient** heat-exchanger feasibility check. Exchanger sizing, both-side mass flow rates, heat-transfer coefficients, full temperature profiles, pinch constraints and fouling are not modelled.
- The model assumes heat supply and heat demand coincide throughout the specified operating hours, with no time-series matching or thermal storage.
- Heat-pump COP and boiler efficiency are fixed input assumptions; heat-pump temperature lift, capacity, and performance changes are not evaluated.
- Savings cover purchased-energy expenditure only. Capital costs are approximate and the simple-payback metric excludes discounting, financing, maintenance, equipment lifetime, and other lifecycle costs.
- Emissions represent assumed *operational* emissions, not embodied or lifecycle emissions. Users must supply credible site-specific factors before any real-world assessment.

## Version and privacy

No personal computer paths, credentials, confidential plant operating data, or proprietary site figures are included. All example inputs are synthetic; do not enter confidential employer information into a public demo.
