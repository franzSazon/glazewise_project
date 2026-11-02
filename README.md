# GLAZEWISE

An AI-based window and shading comparison tool for office cooling-energy demand.

GLAZEWISE lets architecture students compare two façade options (Option A and Option B) during preliminary design. For each option the user picks the window orientation, window-to-wall ratio, shading type (horizontal overhangs or vertical fins), number of devices, depth and tilt angle. A Random Forest model predicts a relative cooling-demand index for each option. The app reports which option is lower, by how much, and whether the difference is large enough to trust. It also draws a schematic of each option.

The tool supports shortlisting options for detailed energy and daylight simulation. It does not replace that simulation.

## Data and model

- **Source:** Yi, X., Yeboah, S., & Tang, L. (2024). *Simulation dataset on fenestration and shading device variation on ventilation and energy performance of an office in cooling and heating seasons.* Mendeley Data, V1. https://doi.org/10.17632/rbn5hypgp6.1
- **Companion paper:** Yi, X., Tang, L., & Yeboah, S. (2024). *Solar Energy, 276, 112646.* https://doi.org/10.1016/j.solener.2024.112646
- **Simulation setup:** EnergyPlus, BESTEST Case 600FF office (48 m²), Shanghai weather file, annual totals.
- **Training data:** the Parametric Analysis file `combined_ed` (11,760 configurations, one row each). The original dataset is not included in this repository.
- **Target:** cooling demand, expressed as an index where the dataset mean is 100.
- **Model:** Random Forest (100 trees) in a pipeline with one-hot encoding, compared against a mean baseline and Linear Regression.

## Files

| File | Description |
|---|---|
| `app.py` | Streamlit web app: two option panels, schematic drawings, comparison, interpretation and CSV export. |
| `glazewise_draw.py` | Generates the schematic SVG drawings (front view, side section or plan view, and orientation compass) from the selected inputs. |
| `01_data_audit.ipynb` | Data audit and cleaning: file checks, unit conversion, input values, grid completeness and the exploratory summary. Produces `clean_cooling.csv`. |
| `02_modelling.ipynb` | Modelling: train/test split, baseline and Random Forest models, unseen-WWR tests, pairwise ranking tests, threshold selection, and saving the model. |
| `clean_cooling.csv` | Cleaned dataset used for modelling: orientation, WWR, shading type, quantity, depth, tilt and cooling demand. |
| `artifacts/` | Saved model (`glazewise_model.joblib`) and its metadata (`glazewise_meta.json`: allowed input values, labels, thresholds, held-out metrics and notes). |
| `.streamlit/` | Streamlit configuration (app theme). |
| `requirements.txt` | Python package requirements. |
| `.gitignore` | Files and folders excluded from version control. |

## Limitations

- The output is a **relative index**, not an energy bill. The cooling values in the source file are higher than the paper reports, while heating and electricity match.
- Predictions are valid only for the **values offered in the app** (the dataset grid). The model does not interpolate reliably between them.
- The data comes from **Shanghai weather** and one reference office. Projects in the Philippines need further validation.
- The data has **no unshaded case**, so every comparison is between two shaded options.
- Small differences are reported as inconclusive. Orientation, quantity, depth and tilt each change cooling only slightly.
- The drawings are schematics. The vertical placement of extra overhangs and the lean direction of tilted devices are approximate.

## Project note

This project was done for a commission by architecture students. Claude, an AI assistant made by Anthropic, was used to assist in creating the project, including the data audit, modelling, app and documentation.