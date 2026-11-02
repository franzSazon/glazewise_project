"""GLAZEWISE: compare the predicted cooling demand of two window and shading options.

Run with:  streamlit run app.py
Needs the folder  artifacts/  (glazewise_model.joblib, glazewise_meta.json) next to this file.
"""
import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
import streamlit as st

from glazewise_draw import build_svg, svg_to_img_html

BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
ARTIFACT_DIR = BASE_DIR / "artifacts"

st.set_page_config(page_title="GLAZEWISE", layout="wide")

SDT_NAMES = {"HSD": "Horizontal (overhangs)", "VSD": "Vertical (fins)"}
QTY_LABEL = {"HSD": "Number of overhangs", "VSD": "Number of fins"}


# ---------------------------------------------------------------- loading
@st.cache_resource
def load_artifacts():
    model = joblib.load(ARTIFACT_DIR / "glazewise_model.joblib")
    meta = json.loads((ARTIFACT_DIR / "glazewise_meta.json").read_text())
    return model, meta


try:
    model, meta = load_artifacts()
except FileNotFoundError:
    st.error(
        "Model files not found. Put the `artifacts` folder (glazewise_model.joblib and "
        "glazewise_meta.json) in the same folder as app.py, then reload."
    )
    st.stop()

DS = meta["design_space"]
WFO_LABELS = {int(k): v for k, v in meta["wfo_labels"].items()}
WWR_VALUES = [round(w, 2) for w in meta["wwr_values"]]
T_LOW = meta["inconclusive_threshold"]
T_HIGH = meta["clear_difference_threshold"]


# ---------------------------------------------------------------- state
def pick(options, preferred):
    return preferred if preferred in options else options[0]


def init_state():
    """Give every widget a valid starting value (re-applied if a widget was dropped)."""
    for p, wwr in (("a", 0.40), ("b", 0.30)):
        st.session_state.setdefault(f"{p}_wfo", pick(meta["wfo_values"], 180))
        st.session_state.setdefault(f"{p}_wwr", pick(WWR_VALUES, wwr))
        st.session_state.setdefault(f"{p}_sdt", "HSD")
        for sdt, sp in DS.items():
            st.session_state.setdefault(f"{p}_sdn_{sdt}", pick(sp["sdn"], 2))
            st.session_state.setdefault(f"{p}_sdd_{sdt}", pick(sp["sdd"], 0.6))
            st.session_state.setdefault(f"{p}_sda_{sdt}", pick(sp["sda"], 90))


def copy_a_to_b():
    suffixes = ["wfo", "wwr", "sdt"] + [f"{k}_{t}" for t in DS for k in ("sdn", "sdd", "sda")]
    for s in suffixes:
        if f"a_{s}" in st.session_state:
            st.session_state[f"b_{s}"] = st.session_state[f"a_{s}"]
        else:
            st.session_state.pop(f"b_{s}", None)


init_state()


# ---------------------------------------------------------------- inputs
def option_inputs(p, title):
    st.subheader(title)
    wfo = st.selectbox(
        "Window faces", meta["wfo_values"],
        format_func=lambda v: WFO_LABELS[v], key=f"{p}_wfo",
    )
    wwr = st.select_slider(
        "Window-to-wall ratio", options=WWR_VALUES,
        format_func=lambda v: f"{round(v * 100)}%", key=f"{p}_wwr",
    )
    sdt = st.radio(
        "Shading type", list(DS.keys()),
        format_func=lambda v: SDT_NAMES[v], key=f"{p}_sdt", horizontal=True,
    )
    sp = DS[sdt]
    sdn = st.selectbox(QTY_LABEL[sdt], sp["sdn"], key=f"{p}_sdn_{sdt}")
    sdd = st.select_slider(
        "Shading depth", options=sp["sdd"],
        format_func=lambda v: f"{v:g} m", key=f"{p}_sdd_{sdt}",
    )
    disp = meta["sda_display"][sdt]
    sda = st.selectbox(
        "Tilt angle from the window plane", sp["sda"],
        format_func=lambda v: f"{disp[str(v)]}°", key=f"{p}_sda_{sdt}",
    )
    return {"wfo": int(wfo), "wwr": float(wwr), "sdt": sdt,
            "sdn": int(sdn), "sdd": float(sdd), "sda": int(sda)}


def describe(o):
    tilt = meta["sda_display"][o["sdt"]][str(o["sda"])]
    return (f"{WFO_LABELS[o['wfo']]}, {round(o['wwr'] * 100)}% window, "
            f"{o['sdn']} {'overhang' if o['sdt'] == 'HSD' else 'fin'}"
            f"{'s' if o['sdn'] > 1 else ''}, {o['sdd']:g} m deep, {tilt}° tilt")


def show_graphic(o):
    """Schematic of the selected option, redrawn on every change."""
    tilt = meta["sda_display"][o["sdt"]][str(o["sda"])]
    svg = build_svg(o, WFO_LABELS[o["wfo"]], tilt)
    st.markdown(svg_to_img_html(svg, describe(o)), unsafe_allow_html=True)
    st.caption(f"{describe(o)}. Schematic of the simulated room, drawn to scale.")


# ---------------------------------------------------------------- prediction
def predict_index(o):
    row = pd.DataFrame([o])[meta["features"]]
    return float(model.predict(row)[0])


def interpret(diff, idx_a, same):
    """Return (tier, message). diff = B minus A, in index points."""
    gap = abs(diff)
    lower = "Option B" if diff < 0 else "Option A"
    pct_of_a = gap / idx_a * 100
    if same:
        return "same", "The two options are identical, so there is no difference to report."
    if gap < T_LOW:
        return "inconclusive", (
            f"Too close to call. The predicted gap is {gap:.3f} index points "
            f"({pct_of_a:.2f}% of Option A), below the {T_LOW} the model can separate reliably. "
            "Treat the two options as equivalent for this comparison."
        )
    if gap < T_HIGH:
        return "leans", (
            f"{lower} leans lower. It is predicted to need {gap:.3f} index points "
            f"({pct_of_a:.2f}% of Option A) less cooling. In held-out tests, gaps this size were "
            "ranked correctly roughly 9 times in 10 or better, but the difference is small. "
            "Shortlist it, then confirm with detailed simulation."
        )
    return "clear", (
        f"{lower} is clearly lower. It is predicted to need {gap:.3f} index points "
        f"({pct_of_a:.2f}% of Option A) less cooling. In held-out tests, gaps this size were "
        "ranked correctly about 97% of the time or better."
    )


# ---------------------------------------------------------------- page
st.title("GLAZEWISE")
st.write(
    "Compare the predicted cooling demand of two window and shading options for an office. "
    "Use the result to shortlist options for detailed energy and daylight evaluation."
)

st.button("Copy Option A into Option B", on_click=copy_a_to_b)
col_a, col_b = st.columns(2, gap="large")
with col_a:
    opt_a = option_inputs("a", "Option A")
    show_graphic(opt_a)
with col_b:
    opt_b = option_inputs("b", "Option B")
    show_graphic(opt_b)

idx_a, idx_b = predict_index(opt_a), predict_index(opt_b)
diff = idx_b - idx_a
pct_signed = diff / idx_a * 100
same = opt_a == opt_b
tier, message = interpret(diff, idx_a, same)

st.divider()
st.header("Comparison")
m1, m2, m3 = st.columns(3)
m1.metric("Option A cooling index", f"{idx_a:.2f}")
m2.metric("Option B cooling index", f"{idx_b:.2f}")
m3.metric(
    "Difference (B minus A)", f"{diff:+.3f}",
    delta=f"{pct_signed:+.2f}% of A",
    delta_color="off" if tier in ("inconclusive", "same") else "inverse",
    help="A negative difference means Option B is predicted to need less cooling.",
)

if tier == "clear":
    st.success(message)
elif tier == "leans":
    st.info(message)
else:
    st.warning(message)

k = meta["kwh_m2_per_index_point"]
st.caption(
    f"Index 100 is the average of all {11760:,} simulated configurations. A lower index means lower "
    f"cooling demand. On the dataset's scale, this gap is about {abs(diff) * k:.2f} kWh/m² per year "
    f"({abs(diff) * k * meta['floor_area_m2']:.0f} kWh for the {meta['floor_area_m2']:.0f} m² room). "
    "Use this only to compare options, not as an energy bill."
)

# ---------------------------------------------------------------- export
rows = []
for name, o, idx in (("A", opt_a, idx_a), ("B", opt_b, idx_b)):
    rows.append({
        "option": name,
        "window_faces": WFO_LABELS[o["wfo"]],
        "window_to_wall_ratio_pct": round(o["wwr"] * 100),
        "shading_type": SDT_NAMES[o["sdt"]],
        "shading_quantity": o["sdn"],
        "shading_depth_m": o["sdd"],
        "tilt_angle_deg": meta["sda_display"][o["sdt"]][str(o["sda"])],
        "cooling_index": round(idx, 4),
        "difference_B_minus_A_index": round(diff, 4),
        "difference_pct_of_A": round(pct_signed, 3),
        "interpretation": message,
        "note": meta["note"],
    })
st.download_button(
    "Download comparison (CSV)",
    data=pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
    file_name="glazewise_comparison.csv",
    mime="text/csv",
)

# ---------------------------------------------------------------- explanations
with st.expander("How to read the result"):
    st.markdown(
        f"""
- **Cooling index** - Annual cooling demand relative to the dataset average, which is set to 100.
- **Difference** - Option B minus Option A. Negative means Option B needs less cooling.
- **Inconclusive** - Gap below {T_LOW} index points. The model cannot rank the options reliably.
- **Leans** - Gap from {T_LOW} to {T_HIGH}. One option looks lower, but the margin is small.
- **Clear**  - Gap above {T_HIGH}. The ranking was reliable in held-out tests.

Orientation, quantity, depth and tilt each change cooling only slightly, so many
  single-input changes will come back inconclusive. Window size and shading type move it most.
"""
    )

with st.expander("About the model and its limits"):
    h = meta["heldout_random_split"]
    st.markdown(
        f"""
- **Source** - Yi, Yeboah and Tang (2024), EnergyPlus simulations of a 48 m² office
  (BESTEST Case 600FF) with Shanghai weather, a 26 °C cooling setpoint and annual totals.
- **Model** - Random Forest, {meta.get('n_estimators', 100)} trees, trained on all 11,760 simulated configurations.
  Held-out random split: R² {h['R2']}, MAE {h['MAE']} index points.
- **Grid only** - Every selectable value appears in the training data. The model does not work
  for in-between values such as a 27% window ratio, so the app does not offer them.
- **Surrogate** - Predictions approximate what the simulation returned for these exact
  configurations. They are not a new analysis.
- **Relative index** - The cooling values in the source file are higher than the paper reports,
  so only the comparison between options is meaningful, not the absolute number.
- **Climate**  - Shanghai weather. Projects in the Philippines need further validation.
- **No unshaded case** - The data has no option without shading, so every comparison is between
  two shaded options.
- **Drawings** - Schematics of the simulated room, to scale. Window size, shade depth and tilt follow
  the simulation inputs. Shade spacing and the lean direction of tilted devices are drawn from the
  paper's description and are not an architectural detail.
"""
    )

with st.sidebar:
    st.header("GLAZEWISE")
    st.caption(f"An AI-Based Window and Shading Comparison Tool for Office Cooling-Energy Demand trained on {meta['trained_on']}, based on Yi et al. (2024) Dataset.")
    st.caption(f"scikit-learn {meta['sklearn_version']}")
    if sklearn.__version__ != meta["sklearn_version"]:
        st.warning(
            f"The model was saved with scikit-learn {meta['sklearn_version']}, but this "
            f"environment has {sklearn.__version__}. Install the saved version if loading fails "
            "or predictions look wrong."
        )