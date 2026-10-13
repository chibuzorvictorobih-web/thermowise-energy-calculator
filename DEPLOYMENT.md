# Publish ThermoWise 2.0 using the EXISTING GitHub repository

**Existing repository:** https://github.com/chibuzorvictorobih-web/thermowise-energy-calculator  
**Existing Streamlit app:** https://thermowise-energy-calculator.streamlit.app/

Do **not** create a new repository or a new Streamlit app. The existing `main` branch and existing website currently serve the original version until the upgraded files are committed. This release package has been checked locally at the code level; full UI smoke testing must happen after installation and again after deployment.

## Step 1 — Safeguard current version

On GitHub, use **Code → Download ZIP** to keep a copy of the current repository if desired. Streamlit normally automatically pulls GitHub changes, but deployment can fail if packages or runtime assumptions change.

## Step 2 — Open and test this complete folder

On a Windows laptop, extract the ZIP and double-click `RUN_THERMOWISE_WINDOWS.bat`. The script checks dependencies, runs all 58 tests, and launches the app. In the fifth tab, use default data and click **Run Hourly Energy Simulation**. Verify no errors and sample comparison results of approximately 256.59 / 167.46 / 43.24 currency units.

## Step 3 — Update the existing repository

There are two approaches:

**Simpler:** ask ChatGPT to publish the already verified release files directly to the connected GitHub repository once you approve. This requires an available and authorized GitHub connection; confirm the live update before it is performed.

**Manual:** open the existing repository on GitHub. Use **Add file → Upload files** for new files, and open each existing file and use its edit/update option for replacements if GitHub's uploader does not offer replacement. Keep every file in this folder at the repository root except `.github/workflows/tests.yml`, which must remain at that nested path. Do not upload the outer ZIP, `.venv`, `.env`, temporary bytecode, or private files.

Files changed from v1.0: `app.py`, `README.md`, `VALIDATION.md`, `DEPLOYMENT.md`, `.github/workflows/tests.yml`.
New files: `decentralised.py`, `test_decentralised.py`, `test_release.py`, `hourly_example.csv`, `DECENTRALISED_MODEL.md`, `RELEASE_CHECKLIST.md`, `START_HERE.txt`, and `RUN_THERMOWISE_WINDOWS.bat` (the launcher is optional in GitHub). The existing `calculations.py`, `test_calculations.py`, `requirements.txt` and `.gitignore` can stay as they are, or be copied from this package.

Suggested commit message: `Release ThermoWise 2.0 decentralised thermal simulator`

## Step 4 — Let Streamlit rebuild

Streamlit Community Cloud ordinarily detects changes to the GitHub branch connected to `app.py` and rebuilds or restarts. If the website is not updated automatically, check its Cloud management page, app logs and **Reboot** or **Rebuild** controls (label may vary). The website address normally remains the same.

## Step 5 — Verify the live version

Use [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) to confirm the five tabs, one 24-hour profile, results charts, hourly CSV export, invalid-temperature protection and the Actions green check. Compare default example results with the README figures. If the app fails, review Streamlit logs and return to the last working GitHub commit.

## Important boundaries

The included source package is **ready for user acceptance testing**, not a certificate that the hosted app will pass every possible browser/device combination. Automated numeric tests do not test the web user interface. Do not describe 24-hour example results as annual figures. Never upload employer-confidential operating data.
