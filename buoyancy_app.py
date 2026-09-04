# ==============================================================================
# Naval Fluid Mechanics — Buoyancy & Stability Simulator
# Streamlit Web Application
# Author: Ilya Kavalchuk — Swinburne University of Technology
# Version: 4.2 (Plotly — no C-extension dependencies)
# ==============================================================================

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import random
import pandas as pd

# ==============================================================================
# PAGE CONFIG
# ==============================================================================
st.set_page_config(
    page_title="⚓ Ship Buoyancy & Stability Simulator",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CUSTOM CSS
# ==============================================================================
st.markdown("""
<style>
    .stApp { background-color: #0a1628; }
    h1, h2, h3 { color: #a8dadc; }
    .status-float   { background:#1a4731; border:2px solid #2ecc71; border-radius:8px;
                      padding:10px; text-align:center; color:#2ecc71;
                      font-size:1.3em; font-weight:bold; }
    .status-neutral { background:#4a3a00; border:2px solid #f1c40f; border-radius:8px;
                      padding:10px; text-align:center; color:#f1c40f;
                      font-size:1.3em; font-weight:bold; }
    .status-sink    { background:#4a0000; border:2px solid #e63946; border-radius:8px;
                      padding:10px; text-align:center; color:#e63946;
                      font-size:1.3em; font-weight:bold; }
    .integrity-box  { background:#1a2a1a; border:2px solid #2ecc71;
                      border-radius:8px; padding:12px; margin:8px 0; }
    div[data-testid="metric-container"] {
                      background:#1d3557; border-radius:8px; padding:8px;
                      border-left:4px solid #457b9d; }
    div[data-testid="metric-container"] label { color: #a8dadc !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONSTANTS
# ==============================================================================
WATER_TYPES = {
    "🌊 Open Ocean (Seawater)":              {"rho": 1025, "desc": "Standard seawater — open ocean, typical naval operations"},
    "🏖️ Coastal / Harbour Water":            {"rho": 1015, "desc": "Slightly diluted near ports and estuaries"},
    "🌿 Brackish Water (Estuary)":           {"rho": 1005, "desc": "Mixed fresh/saltwater — river mouths, Baltic Sea"},
    "🏞️ Freshwater (River / Lake)":         {"rho": 1000, "desc": "Rivers, lakes, inland waterways — lowest buoyancy"},
    "🧪 Dense Brine (Dead Sea / Salt Lake)": {"rho": 1240, "desc": "Hypersaline — extreme buoyancy, rarely navigated"},
}

MATERIAL_PRESETS = {
    "Custom (manual entry)":  None,
    "Mild Steel":             7850,
    "High-Strength Steel":    7950,
    "Aluminium Alloy":        2700,
    "GRP / Fibreglass":       1600,
    "Carbon Fibre Composite": 1550,
    "Timber (Teak)":          900,
    "Timber (Pine)":          530,
    "Reinforced Concrete":    2400,
}

MATERIAL_NAMES = {
    7850: "Mild Steel", 7950: "High-Strength Steel",
    2700: "Aluminium Alloy", 1600: "GRP / Fibreglass"
}

G = 9.81  # m/s²

PLOTLY_BG    = "#0d2137"
PLOTLY_PAPER = "#0a1628"
PLOTLY_GRID  = "#1d3557"
PLOTLY_TEXT  = "#a8dadc"

# ==============================================================================
# ACADEMIC INTEGRITY
# ==============================================================================
@st.cache_data(show_spinner=False)
def generate_student_params(student_id: str) -> dict:
    h   = int(hashlib.sha256(student_id.strip().encode()).hexdigest(), 16)
    rng = random.Random(h % (2**32))
    L           = round(rng.uniform(40.0, 180.0), 1)
    B           = round(rng.uniform(8.0,   28.0), 1)
    D           = round(rng.uniform(4.0,   18.0), 1)
    hull_factor = round(rng.uniform(0.55,  0.82), 3)
    rho_ship    = rng.choice([7850, 7950, 2700, 1600])
    wall_frac   = round(rng.uniform(0.08,  0.18), 3)
    m           = round((L * B * D * hull_factor * wall_frac * rho_ship) / 1000) * 1000
    KG          = round(rng.uniform(0.30,  0.55) * D, 2)
    seed_str    = f"{student_id.strip()}|{L}|{B}|{D}|{m}|{rho_ship}"
    param_hash  = hashlib.sha256(seed_str.encode()).hexdigest()[:8].upper()
    return {
        "L": L, "B": B, "D": D, "m": float(m),
        "rho_ship": float(rho_ship), "KG": KG,
        "material_name": MATERIAL_NAMES.get(rho_ship, "Steel"),
        "param_hash": param_hash
    }

def result_fingerprint(student_id, inputs, results) -> str:
    payload = student_id + "|" + "|".join(
        f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
        for k, v in {**inputs, **results}.items()
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12].upper()

# ==============================================================================
# PHYSICS ENGINE
# ==============================================================================
@st.cache_data(show_spinner=False)
def compute_buoyancy(m, L, B, D, rho_ship, KG, rho_water):
    V_total      = L * B * D
    V_material   = m / rho_ship
    V_void       = V_total - V_material
    V_submerged  = min(m / rho_water, V_total)
    T_actual     = V_submerged / (L * B)
    freeboard    = D - T_actual
    draft_ratio  = T_actual / D
    F_buoyancy   = rho_water * G * V_submerged
    F_gravity    = m * G
    F_net        = F_buoyancy - F_gravity
    disp_t       = rho_water * V_submerged / 1000
    safe_load    = rho_water * 0.66 * V_total - m
    sink_load    = rho_water * V_total - m
    avg_density  = m / V_total
    flotation    = rho_water / avg_density
    Cb           = V_submerged / (L * B * T_actual) if T_actual > 0 else 0.0
    KB           = T_actual / 2
    BM           = (B ** 2) / (12 * T_actual) if T_actual > 0 else 0.0
    KM           = KB + BM
    GM           = KM - KG

    if freeboard < 0:
        status = "SINKING"
    elif F_net > 1:
        status = ("FLOATING — STABLE" if GM > 0.15
                  else "FLOATING — MARGINALLY STABLE" if GM > 0
                  else "FLOATING — UNSTABLE (GM < 0)")
    elif abs(F_net) <= 1:
        status = "NEUTRAL BUOYANCY"
    else:
        status = "SINKING"

    return {
        "V_total": V_total, "V_material": V_material,
        "V_void": V_void, "V_submerged": V_submerged,
        "T_actual": T_actual, "freeboard": freeboard,
        "draft_ratio": draft_ratio, "Cb": Cb,
        "F_buoyancy": F_buoyancy, "F_gravity": F_gravity, "F_net": F_net,
        "disp_t": disp_t, "safe_load": safe_load, "sink_load": sink_load,
        "avg_density": avg_density, "flotation": flotation,
        "KB": KB, "BM": BM, "KM": KM, "GM": GM,
        "status": status,
    }

# ==============================================================================
# PLOTLY — HULL CROSS-SECTION + STABILITY DIAGRAM
# ==============================================================================
@st.cache_data(show_spinner=False)
def draw_hull_figure(L, B, D, T_actual, freeboard, GM,
                     F_buoyancy, F_gravity, status, water_name, KG):

    hull_col = "#8d99ae" if "FLOATING" in status else "#e63946"
    gm_color = "#2ecc71" if GM > 0.15 else ("#f1c40f" if GM > 0 else "#e63946")
    gm_verdict = "✅ STABLE" if GM > 0.15 else ("⚠️ MARGINAL" if GM > 0 else "❌ UNSTABLE")

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Hull Cross-Section (Side Profile)",
                        "Stability Diagram — GM Visualisation"),
        horizontal_spacing=0.08
    )

    # ── LEFT: Side profile ────────────────────────────────────────────────────
    # Water body
    fig.add_trace(go.Scatter(
        x=[-L*0.5, L*0.5, L*0.5, -L*0.5, -L*0.5],
        y=[-T_actual*1.6, -T_actual*1.6, 0, 0, -T_actual*1.6],
        fill="toself", fillcolor="rgba(26,74,122,0.55)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Water", showlegend=False
    ), row=1, col=1)

    # Waterline
    fig.add_hline(y=0, line=dict(color="#4fc3f7", width=2, dash="dash"),
                  row=1, col=1, annotation_text="Waterline",
                  annotation_font_color="#4fc3f7")

    # Hull shape
    keel_h = B / 2 * 0.85
    wl_h   = B / 2
    ow     = B * 0.05
    hx = [-keel_h, keel_h, wl_h, wl_h+ow,  wl_h+ow,  -wl_h-ow, -wl_h-ow, -wl_h, -keel_h]
    hy = [-T_actual, -T_actual, 0, 0, freeboard, freeboard, 0, 0, -T_actual]
    fig.add_trace(go.Scatter(
        x=hx, y=hy, fill="toself",
        fillcolor=hull_col, opacity=0.85,
        line=dict(color="#cccccc", width=1.5),
        name="Hull", showlegend=False
    ), row=1, col=1)

    # Mast
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[freeboard, freeboard + D*0.4],
        line=dict(color="#cccccc", width=2.5),
        showlegend=False
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[-B*0.18, B*0.18], y=[freeboard+D*0.22]*2,
        line=dict(color="#cccccc", width=1.5),
        showlegend=False
    ), row=1, col=1)

    # Draft annotation arrow
    fig.add_annotation(
        x=wl_h*1.6, y=-T_actual/2, ax=wl_h*1.6, ay=0,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowcolor="#f1c40f", arrowwidth=2,
        text=f"T={T_actual:.2f}m", font=dict(color="#f1c40f", size=9),
        row=1, col=1
    )

    # Freeboard annotation
    if freeboard > 0:
        fig.add_annotation(
            x=-wl_h*1.6, y=freeboard/2, ax=-wl_h*1.6, ay=0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowcolor="#2ecc71", arrowwidth=2,
            text=f"FB={freeboard:.2f}m", font=dict(color="#2ecc71", size=9),
            row=1, col=1
        )

    # Force arrows — buoyancy up
    fb_len = D * 0.45
    fig.add_annotation(
        x=B*0.75, y=fb_len*0.5, ax=B*0.75, ay=-fb_len*0.5,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowcolor="#2ecc71", arrowwidth=3,
        text=f"Fb={F_buoyancy/1000:.0f}kN",
        font=dict(color="#2ecc71", size=9), row=1, col=1
    )
    # Gravity down
    fig.add_annotation(
        x=-B*0.75, y=-fb_len*0.5, ax=-B*0.75, ay=fb_len*0.5,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowcolor="#e63946", arrowwidth=3,
        text=f"Fg={F_gravity/1000:.0f}kN",
        font=dict(color="#e63946", size=9), row=1, col=1
    )

    # Centre of buoyancy marker
    fig.add_trace(go.Scatter(
        x=[0], y=[-T_actual/2],
        mode="markers+text",
        marker=dict(color="#e74c3c", size=10),
        text=["B (KB)"], textposition="middle right",
        textfont=dict(color="#e74c3c", size=9),
        showlegend=False
    ), row=1, col=1)

    # Water label
    wlabel = (water_name.split("(")[0].strip()
              .replace("🌊","").replace("🏖️","")
              .replace("🌿","").replace("🏞️","").replace("🧪","").strip())
    fig.add_annotation(
        x=0, y=-T_actual*1.3, text=wlabel,
        font=dict(color="#4fc3f7", size=9), showarrow=False,
        row=1, col=1
    )

    # ── RIGHT: Stability diagram ──────────────────────────────────────────────
    keel_y = -D / 2
    KB_y   = keel_y + T_actual / 2
    BM_val = (B**2) / (12 * T_actual) if T_actual > 0 else 0
    KM_y   = keel_y + T_actual/2 + BM_val
    KG_y   = keel_y + KG          # actual KG position in plot coords

    # Hull rectangle
    fig.add_trace(go.Scatter(
        x=[-B/2, B/2, B/2, -B/2, -B/2],
        y=[keel_y, keel_y, keel_y+D, keel_y+D, keel_y],
        fill="toself", fillcolor="rgba(58,74,90,0.7)",
        line=dict(color="#8d99ae", width=2),
        showlegend=False
    ), row=1, col=2)

    # Water fill inside hull
    fig.add_trace(go.Scatter(
        x=[-B/2, B/2, B/2, -B/2, -B/2],
        y=[keel_y, keel_y, keel_y+T_actual, keel_y+T_actual, keel_y],
        fill="toself", fillcolor="rgba(26,74,122,0.5)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False
    ), row=1, col=2)

    # Waterline
    fig.add_hline(y=keel_y + T_actual,
                  line=dict(color="#4fc3f7", width=1.5, dash="dash"),
                  row=1, col=2)

    # KM arrow (K to M)
    fig.add_annotation(
        x=B*0.4, y=KM_y, ax=B*0.4, ay=keel_y,
        xref="x2", yref="y2", axref="x2", ayref="y2",
        showarrow=True, arrowhead=3, arrowcolor="#9b59b6", arrowwidth=2,
        text="", row=1, col=2
    )

    # Key points K, B, G, M
    points = [
        (keel_y, "K  Keel",                      "#888888"),
        (KB_y,   f"B  KB={T_actual/2:.2f}m",     "#e74c3c"),
        (KG_y,   f"G  KG={KG:.2f}m",             "#f39c12"),
        (KM_y,   f"M  KM={T_actual/2+BM_val:.2f}m", "#9b59b6"),
    ]
    for y_pt, lbl, col in points:
        fig.add_trace(go.Scatter(
            x=[0], y=[y_pt],
            mode="markers+text",
            marker=dict(color=col, size=10),
            text=[lbl], textposition="middle right",
            textfont=dict(color=col, size=9),
            showlegend=False
        ), row=1, col=2)

    # GM label box
    fig.add_annotation(
        x=-B*0.55, y=(KM_y + KB_y)/2,
        text=f"<b>GM = {GM:.3f} m</b><br>{gm_verdict}",
        font=dict(color=gm_color, size=11),
        bgcolor="#1d3557", bordercolor=gm_color, borderwidth=2,
        showarrow=False, xref="x2", yref="y2"
    )

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    fig.update_layout(
        height=500,
        paper_bgcolor=PLOTLY_PAPER,
        plot_bgcolor=PLOTLY_BG,
        font=dict(color=PLOTLY_TEXT),
        title=dict(
            text="Ship Buoyancy & Stability — Visual Analysis",
            font=dict(color=PLOTLY_TEXT, size=15), x=0.5
        ),
        margin=dict(l=20, r=20, t=60, b=20),
    )

    # Left panel axes
    fig.update_xaxes(range=[-L*0.5, L*0.5], title_text="Beam (m)",
                     gridcolor=PLOTLY_GRID, row=1, col=1)
    fig.update_yaxes(range=[-T_actual*1.6 - D*0.1, freeboard + D*0.7],
                     title_text="Height above Keel (m)",
                     gridcolor=PLOTLY_GRID, row=1, col=1)

    # Right panel axes
    fig.update_xaxes(range=[-B*1.3, B*1.3], title_text="Beam (m)",
                     gridcolor=PLOTLY_GRID, row=1, col=2)
    fig.update_yaxes(range=[keel_y - D*0.25, KM_y + D*0.4],
                     title_text="Height above Keel (m)",
                     gridcolor=PLOTLY_GRID, row=1, col=2)

    for ann in fig.layout.annotations:
        ann.font.color = PLOTLY_TEXT

    return fig

# ==============================================================================
# PLOTLY — WATER SCENARIO COMPARISON
# ==============================================================================
@st.cache_data(show_spinner=False)
def draw_water_comparison(m, L, B, D, rho_ship, KG):
    names, drafts, GMs, Fbs, Cbs = [], [], [], [], []
    for name, props in WATER_TYPES.items():
        r = compute_buoyancy(m, L, B, D, rho_ship, KG, float(props["rho"]))
        short = (name.split("(")[0].strip()
                     .replace("🌊","").replace("🏖️","")
                     .replace("🌿","").replace("🏞️","").replace("🧪","").strip())
        names.append(short)
        drafts.append(round(r["T_actual"], 3))
        GMs.append(round(r["GM"], 3))
        Fbs.append(round(r["F_buoyancy"] / 1000, 2))
        Cbs.append(round(r["Cb"], 4))

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Draft T (m) — decreases in denser water",
            "GM Metacentric Height (m) — stability improves in denser water",
            "Buoyant Force (kN) — increases with water density",
            "Block Coefficient Cb — varies with submerged volume",
        ),
        vertical_spacing=0.18, horizontal_spacing=0.1
    )

    panels = [
        (1, 1, drafts, "#4fc3f7"),
        (1, 2, GMs,    "#2ecc71"),
        (2, 1, Fbs,    "#e74c3c"),
        (2, 2, Cbs,    "#f39c12"),
    ]
    for row, col, vals, color in panels:
        fig.add_trace(go.Bar(
            x=names, y=vals,
            marker=dict(color=color, opacity=0.85,
                        line=dict(color="#333", width=1)),
            text=[str(v) for v in vals],
            textposition="outside",
            textfont=dict(color=PLOTLY_TEXT, size=9),
            showlegend=False
        ), row=row, col=col)

    fig.update_layout(
        height=520,
        paper_bgcolor=PLOTLY_PAPER,
        plot_bgcolor=PLOTLY_BG,
        font=dict(color=PLOTLY_TEXT),
        title=dict(
            text="Water Environment Comparison — Buoyancy Performance",
            font=dict(color=PLOTLY_TEXT, size=14), x=0.5
        ),
        margin=dict(l=20, r=20, t=80, b=20),
    )
    fig.update_xaxes(tickfont=dict(size=9), gridcolor=PLOTLY_GRID)
    fig.update_yaxes(gridcolor=PLOTLY_GRID)
    for ann in fig.layout.annotations:
        ann.font.color = "#aaaaaa"
        ann.font.size  = 10

    return fig

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("## 🎓 Academic Integrity")
    st.markdown("""<div class='integrity-box'>Enter your <b>Student ID</b> to receive
    unique, verifiable ship parameters for your assignment.</div>""",
    unsafe_allow_html=True)

    student_id = st.text_input("Student ID", placeholder="e.g. 1234567")
    use_gen    = False
    gen_params = None

    if student_id.strip():
        gen_params = generate_student_params(student_id.strip())
        use_gen    = st.toggle("🔒 Use ID-Generated Parameters", value=True)
        if use_gen:
            st.markdown(f"""<div class='integrity-box'>
            <b>🔐 Your Assignment Ship</b><br>
            L = <b>{gen_params['L']} m</b> &nbsp;|&nbsp;
            B = <b>{gen_params['B']} m</b> &nbsp;|&nbsp;
            D = <b>{gen_params['D']} m</b><br>
            Mass = <b>{gen_params['m']:,.0f} kg</b><br>
            Material = <b>{gen_params['material_name']}</b>
            ({gen_params['rho_ship']:.0f} kg/m³)<br>
            KG = <b>{gen_params['KG']} m</b><br><br>
            📋 <b>Parameter Hash: <code>{gen_params['param_hash']}</code></b><br>
            <small>Include this in your report submission.</small>
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("## 🌊 Water Environment")
    water_sel = st.selectbox("Select Water Type", list(WATER_TYPES.keys()), index=0)
    rho_water = float(WATER_TYPES[water_sel]["rho"])
    st.info(f"ρ_water = **{rho_water:.0f} kg/m³**\n\n{WATER_TYPES[water_sel]['desc']}")

    st.divider()
    st.markdown("## 📐 Ship Geometry & Mass")

    if use_gen and gen_params:
        L        = gen_params["L"]
        B        = gen_params["B"]
        D        = gen_params["D"]
        m        = gen_params["m"]
        rho_ship = gen_params["rho_ship"]
        KG       = gen_params["KG"]
        mat_name = gen_params["material_name"]
        st.caption(f"*Locked to Student ID `{student_id}`*")
        st.markdown(f"**L** = {L} m | **B** = {B} m | **D** = {D} m")
        st.markdown(f"**Mass** = {m:,.0f} kg | **KG** = {KG} m")
        st.markdown(f"**Material** = {mat_name} ({rho_ship:.0f} kg/m³)")
    else:
        L        = st.number_input("Length L (m)",    1.0, 500.0,  80.0, 1.0)
        B        = st.number_input("Beam B (m)",      1.0, 100.0,  14.0, 0.5)
        D        = st.number_input("Depth D (m)",     1.0,  80.0,   8.0, 0.5)
        m        = st.number_input("Ship Mass (kg)",  100.0, 1e8, 500000.0, 1000.0, format="%.0f")
        KG       = st.number_input("KG — CoG above Keel (m)", 0.1, 50.0, 4.0, 0.1,
                                   help="Typically 40–55% of ship depth.")
        mat_sel  = st.selectbox("Material Preset", list(MATERIAL_PRESETS.keys()))
        if MATERIAL_PRESETS[mat_sel] is not None:
            rho_ship = float(MATERIAL_PRESETS[mat_sel])
            mat_name = mat_sel
            st.info(f"ρ = **{rho_ship:.0f} kg/m³**")
        else:
            rho_ship = st.number_input("Custom Density (kg/m³)", 100.0, 20000.0, 7850.0, 10.0)
            mat_name = "Custom"

# ==============================================================================
# VALIDATION
# ==============================================================================
errors = []
if m / rho_ship > L * B * D:
    errors.append(
        f"Material volume ({m/rho_ship:.1f} m³) exceeds hull envelope "
        f"({L*B*D:.1f} m³). Reduce mass or choose a lighter material.")
if KG >= D:
    errors.append(f"KG ({KG} m) must be less than ship depth D ({D} m).")
if errors:
    for e in errors: st.error(f"⚠️ {e}")
    st.stop()

# ==============================================================================
# COMPUTE
# ==============================================================================
res = compute_buoyancy(float(m), float(L), float(B), float(D),
                       float(rho_ship), float(KG), rho_water)

# ==============================================================================
# MAIN UI
# ==============================================================================
st.title("⚓ Ship Buoyancy & Stability Simulator")
st.markdown("*Naval Fluid Mechanics — Educational Tool | Swinburne University of Technology*")
st.divider()

status  = res["status"]
css_cls = ("status-float"   if "FLOATING" in status
           else "status-neutral" if "NEUTRAL" in status
           else "status-sink")
st.markdown(f"<div class='{css_cls}'>⚓ {status}</div>", unsafe_allow_html=True)
st.markdown("")

# ==============================================================================
# RESULTS — THREE COLUMNS
# ==============================================================================
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("### 📦 Volume Analysis")
    st.metric("Total Hull Volume",    f"{res['V_total']:.2f} m³")
    st.metric("Material Volume",      f"{res['V_material']:.2f} m³")
    st.metric("Void / Air Volume",    f"{res['V_void']:.2f} m³")
    st.metric("Submerged Volume",     f"{res['V_submerged']:.2f} m³")
    st.markdown("### 📏 Geometry")
    st.metric("Actual Draft T",       f"{res['T_actual']:.3f} m")
    st.metric("Freeboard",            f"{res['freeboard']:.3f} m",
              delta="Safe" if res['freeboard'] > 0 else "FLOODED",
              delta_color="normal"  if res['freeboard'] > 0 else "inverse")
    st.metric("Draft Ratio T/D",      f"{res['draft_ratio']:.4f}")
    st.metric("Block Coefficient Cb", f"{res['Cb']:.4f}",
              help="0.50–0.65 fast vessels | 0.75–0.85 bulk carriers")

with c2:
    st.markdown("### ⚡ Forces")
    st.metric("Buoyant Force",        f"{res['F_buoyancy']/1000:.2f} kN")
    st.metric("Gravitational Force",  f"{res['F_gravity']/1000:.2f} kN")
    st.metric("Net Force",            f"{res['F_net']/1000:.2f} kN",
              delta="Floating" if res['F_net'] > 0 else "Sinking",
              delta_color="normal"  if res['F_net'] > 0 else "inverse")
    st.metric("Displacement",         f"{res['disp_t']:.1f} t")
    st.markdown("### 🚢 Load Capacity")
    st.metric("Safe Additional Load", f"{res['safe_load']:,.0f} kg",
              help="At 66% immersion safety margin")
    st.metric("Load to Sink",         f"{res['sink_load']:,.0f} kg")
    st.metric("Average Ship Density", f"{res['avg_density']:.2f} kg/m³")
    st.metric("Flotation Factor",     f"{res['flotation']:.4f}",
              help="ρ_water / ρ_avg. > 1 = floating")

with c3:
    st.markdown("### 🎯 GM Stability")
    st.metric("KB — Centre of Buoyancy", f"{res['KB']:.3f} m",
              help="KB = T/2 (box-hull approximation)")
    st.metric("BM — Metacentric Radius", f"{res['BM']:.3f} m",
              help="BM = B² / (12·T). Wider beam → more stable.")
    st.metric("KM — Metacentre",         f"{res['KM']:.3f} m")
    st.metric("KG — Centre of Gravity",  f"{KG:.3f} m")
    gm = res["GM"]
    gm_note = ("✅ Stable" if gm > 0.15
               else "⚠️ Marginal" if gm > 0
               else "❌ UNSTABLE — will capsize")
    st.metric("GM — Metacentric Height", f"{gm:.3f} m",
              delta=gm_note,
              delta_color="normal" if gm > 0 else "inverse")
    if gm <= 0:
        st.markdown("""<div style='background:#3a1a00;border:1px solid #e67e22;
        border-radius:6px;padding:8px;color:#e67e22;font-size:0.85em;'>
        ⚠️ <b>To improve GM:</b> increase Beam B (BM ∝ B²),
        reduce KG (lower ballast), or reduce draft T.
        </div>""", unsafe_allow_html=True)
    st.markdown("### 💧 Environment")
    st.metric("Water ρ_w",    f"{rho_water:.0f} kg/m³")
    st.metric("Material ρ_s", f"{rho_ship:.0f} kg/m³")

st.divider()

# ==============================================================================
# HULL FIGURE
# ==============================================================================
st.markdown("## 🖼️ Hull Visualisation & Stability Diagram")
fig1 = draw_hull_figure(
    float(L), float(B), float(D),
    res["T_actual"], res["freeboard"], res["GM"],
    res["F_buoyancy"], res["F_gravity"],
    status, water_sel, float(KG)
)
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ==============================================================================
# WATER SCENARIO COMPARISON
# ==============================================================================
st.markdown("## 🌊 Water Environment Comparison")
st.caption("Analyse how your ship performs across all five water environments — "
           "supports analytical and evaluation-level learning objectives.")

fig2 = draw_water_comparison(
    float(m), float(L), float(B), float(D), float(rho_ship), float(KG))
st.plotly_chart(fig2, use_container_width=True)

# Comparison table
st.markdown("#### 📊 Numerical Comparison Table")
rows = []
for name, props in WATER_TYPES.items():
    r = compute_buoyancy(float(m), float(L), float(B), float(D),
                         float(rho_ship), float(KG), float(props["rho"]))
    rows.append({
        "Water Environment":  name.split("(")[0].strip(),
        "ρ_w (kg/m³)":       props["rho"],
        "Draft T (m)":        round(r["T_actual"], 3),
        "Freeboard (m)":      round(r["freeboard"], 3),
        "Buoyant Force (kN)": round(r["F_buoyancy"]/1000, 2),
        "Displacement (t)":   round(r["disp_t"], 1),
        "GM (m)":             round(r["GM"], 3),
        "Cb":                 round(r["Cb"], 4),
        "Flotation Factor":   round(r["flotation"], 4),
        "Status":             r["status"],
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

# ==============================================================================
# THEORY EXPANDER
# ==============================================================================
with st.expander("📚 Theory & Equations — Archimedes' Principle & GM Stability"):
    st.markdown(r"""
### Archimedes' Principle
$$F_b = \rho_w \cdot g \cdot V_{submerged}$$

Floating condition: $\bar{\rho}_{ship} \leq \rho_w$

---
### Draft — Box Hull
$$T = \frac{V_{submerged}}{L \cdot B} \qquad \text{Freeboard} = D - T$$

---
### Block Coefficient
$$C_b = \frac{V_{submerged}}{L \cdot B \cdot T}$$

---
### GM Stability Chain

| Symbol | Meaning | Formula |
|--------|---------|---------|
| **KB** | Centre of Buoyancy above Keel | $T/2$ |
| **BM** | Metacentric Radius | $B^2/(12T)$ |
| **KM** | Metacentre above Keel | $KB + BM$ |
| **GM** | Metacentric Height | $KM - KG$ |

- $GM > 0.15$ m → ✅ Stable
- $0 < GM \leq 0.15$ m → ⚠️ Marginally stable
- $GM \leq 0$ m → ❌ Unstable (capsizes)

---
### Effect of Water Density on Draft
$$T \propto \frac{1}{\rho_w}$$
Moving from freshwater (1000) to seawater (1025) reduces draft ~2.4% — basis of the **Plimsoll Line**.
""")

# ==============================================================================
# SUBMISSION FINGERPRINT
# ==============================================================================
with st.expander("🔐 Academic Integrity — Submission Verification"):
    if student_id.strip() and gen_params:
        inputs_d  = {"L":L,"B":B,"D":D,"m":m,"rho_ship":rho_ship,"KG":KG,"rho_water":rho_water}
        results_d = {k:v for k,v in res.items() if isinstance(v,(int,float))}
        r_hash    = result_fingerprint(student_id, inputs_d, results_d)
        st.markdown(f"""<div class='integrity-box'>
        <b>📋 Submission Verification</b><br><br>
        Student ID: <code>{student_id}</code><br>
        Parameter Hash: <code>{gen_params['param_hash']}</code><br>
        Result Fingerprint: <code>{r_hash}</code><br><br>
        Water: <b>{water_sel}</b><br>
        Ship: L={L}m, B={B}m, D={D}m | Mass: {m:,.0f} kg | KG: {KG}m<br>
        Material: {mat_name} ({rho_ship:.0f} kg/m³)<br><br>
        <b>Include both hash codes in your report submission header.</b>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Enter your Student ID in the sidebar to generate a submission fingerprint.")

# ==============================================================================
# FOOTER
# ==============================================================================
st.divider()
st.markdown("""<div style='text-align:center;color:#555;font-size:0.8em;'>
⚓ Ship Buoyancy & Stability Simulator v4.2 &nbsp;|&nbsp;
Naval Fluid Mechanics — Educational Tool &nbsp;|&nbsp;
Swinburne University of Technology &nbsp;|&nbsp;
<i>Box-hull approximation — for educational purposes</i>
</div>""", unsafe_allow_html=True)
