# Deploy ThermoWise to GitHub and Streamlit Community Cloud

This guide assumes the project works locally and that its 24 unit tests pass.

## 1. Confirm the package before publication

1. Keep the files `app.py`, `calculations.py`, `test_calculations.py`, `requirements.txt`, `README.md`, `VALIDATION.md` and `.gitignore` in the **top level of the repository**. Do not upload a single ZIP as the only repository file.
2. Do **not** upload `.venv`, `__pycache__`, `.env`, personal file paths, screenshots containing private information, secrets, or company data.
3. Run `python -m unittest -v test_calculations.py` from the project root.
4. Run `python -m streamlit run app.py` and check the default scenario and charts in a browser.

## 2. Create the public GitHub repository

1. Open https://github.com/new and log in.
2. Choose repository name **thermowise-energy-calculator** (or another available name).
3. Enter description: `Interactive industrial heat-recovery, energy cost and emissions decision-support calculator built with Python and Streamlit.`
4. Choose **Public** for shareable access (you decide whether to make the source public).
5. For the easiest browser upload, don't initialize the repo with a separate README or .gitignore: the prepared project contains both.
6. Click **Create repository**.
7. On the new repository page, choose **uploading an existing file**, or **Add file → Upload files**.
8. Drag **the contents** of the extracted `ThermoWise_Ready_to_Publish` folder into GitHub, not the parent folder or the ZIP. Make sure hidden `.gitignore` and `.github/workflows/tests.yml` are included; you can add them separately later if Windows hides dotfiles.
9. Write commit message `Publish ThermoWise v1.0` and click **Commit changes**.
10. Check that `app.py`, `calculations.py`, `requirements.txt` and `README.md` appear on the repository main page at root level. If GitHub's web uploader doesn't preserve your nested `.github` folder, you can recreate the workflow via **Add file → Create new file** named `.github/workflows/tests.yml` and paste the content.

## 3. Deploy the working website

1. Go to https://share.streamlit.io and sign in / connect your GitHub account.
2. Choose **Create app** → **Yup, I have an app** (the exact UI label may vary).
3. Select your new public GitHub repo, set branch to `main` (or the branch you actually published), and set the main-file path to `app.py`.
4. Optionally choose a descriptive, available `*.streamlit.app` address.
5. Keep default Python 3.12 or choose 3.13 if you have tested it. The code targets both; dependencies install from `requirements.txt`.
6. Click **Deploy** and wait for the build to finish. If the build fails, inspect the deployment logs; confirm dependencies and file path.
7. Open the deployed URL, submit the default scenario, check Results, charts and Validation, then test the temperature-screen rejection.
8. Edit `README.md` on GitHub to replace the two link placeholders with the real website and repository URLs.

## 4. Post-deployment checks

- Visit the Streamlit URL from another browser or device without local VS Code.
- Ensure the first page loads without Python tracebacks.
- Test default inputs and click **Calculate and Compare**.
- Download the CSV and verify its values.
- On GitHub, open **Actions** to confirm the unit-test workflow has passed, if the workflow is included and actions are enabled.

### Official resources

- Streamlit Cloud deployment: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Streamlit Cloud dependencies: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies

**Note:** The application is not publicly hosted until deployment succeeds. GitHub publishing alone does not create the interactive website.
