# ==============================================================================
# Naval Fluid Mechanics — Buoyancy & Stability Simulator
# Streamlit Web Application
# Author: Ilya Kavalchuk — Swinburne University of Technology
# Version: 4.1 (Performance-optimised with st.cache_data)
# ==============================================================================

import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — required on cloud
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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

MATERIAL_NAMES = {7850:"Mild Steel", 7950:"High-Strength Steel",
                  2700:"Aluminium Alloy", 1600:"GRP / Fibreglass"}

G = 9.81  # m/s²

# ==============================================================================
# ACADEMIC INTEGRITY — STUDENT ID SEED
# ==============================================================================
@st.cache_data(show_spinner=False)
def generate_student_params(student_id: str) -> dict:
    """Deterministic unique ship parameters from Student ID (SHA-256 seeded)."""
    h   = int(hashlib.sha256(student_id.strip().encode()).hexdigest(), 16)
    rng = random.Random(h % (2**32))

    L            = round(rng.uniform(40.0, 180.0), 1)
    B            = round(rng.uniform(8.0,   28.0), 1)
    D            = round(rng.uniform(4.0,   18.0), 1)
    hull_factor  = round(rng.uniform(0.55,  0.82), 3)
    V_hull       = L * B * D * hull_factor
    rho_ship     = rng.choice([7850, 7950, 2700, 1600])
    wall_frac    = round(rng.uniform(0.08,  0.18), 3)
    m            = round((V_hull * wall_frac * rho_ship) / 1000) * 1000
    KG           = round(rng.uniform(0.30,  0.55) * D, 2)

    seed_str     = f"{student_id.strip()}|{L}|{B}|{D}|{m}|{rho_ship}"
    param_hash   = hashlib.sha256(seed_str.encode()).hexdigest()[:8].upper()

    return {"L": L, "B": B, "D": D, "m": float(m),
            "rho_ship": float(rho_ship), "KG": KG,
            "material_name": MATERIAL_NAMES.get(rho_ship, "Steel"),
            "param_hash": param_hash}


def result_fingerprint(student_id: str, inputs: dict, results: dict) -> str:
    payload = student_id + "|" + "|".join(
        f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
        for k, v in {**inputs, **results}.items()
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12].upper()

# ==============================================================================
# PHYSICS ENGINE  (cached — only reruns when inputs change)
# ==============================================================================
@st.cache_data(show_spinner=False)
def compute_buoyancy(m: float, L: float, B: float, D: float,
                     rho_ship: float, KG: float, rho_water: float) -> dict:
    V_total       = L * B * D
    V_material    = m / rho_ship
    V_void        = V_total - V_material
    V_submerged   = min(m / rho_water, V_total)
    T_actual      = V_submerged / (L * B)
    freeboard     = D - T_actual
    draft_ratio   = T_actual / D

    F_buoyancy    = rho_water * G * V_submerged
    F_gravity     = m * G
    F_net         = F_buoyancy - F_gravity

    displacement_t = rho_water * V_submerged / 1000
    safe_load      = rho_water * 0.66 * V_total - m
    sink_load      = rho_water * V_total - m
    avg_density    = m / V_total
    flotation_fac  = rho_water / avg_density
    Cb             = V_submerged / (L * B * T_actual) if T_actual > 0 else 0.0

    KB  = T_actual / 2
    BM  = (B ** 2) / (12 * T_actual) if T_actual > 0 else 0.0
    KM  = KB + BM
    GM  = KM - KG

    if freeboard < 0:
        status = "SINKING"
    elif F_net > 1:
        if GM > 0.15:
            status = "FLOATING — STABLE"
        elif GM > 0:
            status = "FLOATING — MARGINALLY STABLE"
        else:
            status = "FLOATING — UNSTABLE (GM < 0)"
    elif abs(F_net) <= 1:
        status = "NEUTRAL BUOYANCY"
    else:
        status = "SINKING"

    return {
        "V_total": V_total, "V_material": V_material,
        "V_void": V_void,   "V_submerged": V_submerged,
        "T_actual": T_actual, "freeboard": freeboard,
        "draft_ratio": draft_ratio, "Cb": Cb,
        "F_buoyancy": F_buoyancy, "F_gravity": F_gravity, "F_net": F_net,
        "displacement_t": displacement_t,
        "safe_load": safe_load, "sink_load": sink_load,
        "avg_density": avg_density, "flotation_fac": flotation_fac,
        "KB": KB, "BM": BM, "KM": KM, "GM": GM,
        "status": status,
    }

# ==============================================================================
# FIGURE 1 — HULL CROSS-SECTION + STABILITY DIAGRAM  (cached)
# ==============================================================================
@st.cache_data(show_spinner=False)
def draw_hull_figure(L: float, B: float, D: float,
                     T_actual: float, freeboard: float, GM: float,
                     rho_water: int, F_buoyancy: float, F_gravity: float,
                     status: str, water_name: str):

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 6), facecolor="#0a1628")
    fig.suptitle("Ship Buoyancy & Stability — Visual Analysis",
                 color="#a8dadc", fontsize=14, fontweight="bold")

    # ── LEFT: Side-profile ────────────────────────────────────────────────────
    ax.set_facecolor("#0d2137")
    ax.set_title("Hull Cross-Section (Side Profile)", color="#a8dadc", fontsize=11)

    # Water body
    ax.add_patch(mpatches.FancyBboxPatch(
        (-L * 0.55, -T_actual * 1.6), L * 1.1, T_actual * 1.6,
        boxstyle="square", linewidth=0, facecolor="#1a4a7a", alpha=0.55))
    ax.axhline(0, color="#4fc3f7", linewidth=2.0, linestyle="--",
               label="Waterline", zorder=5)

    # Hull trapezoid
    keel_h = B / 2 * 0.85
    wl_h   = B / 2
    ow     = B * 0.05
    hx = [-keel_h, keel_h, wl_h, wl_h+ow,  wl_h+ow,  -wl_h-ow, -wl_h-ow, -wl_h, -keel_h]
    hy = [-T_actual, -T_actual, 0, 0, freeboard, freeboard, 0, 0, -T_actual]
    hull_col = "#8d99ae" if "FLOATING" in status else "#e63946"
    ax.fill(hx, hy, color=hull_col, alpha=0.85, zorder=6, label="Hull")
    ax.plot(hx, hy, color="#ccc", linewidth=1.5, zorder=7)

    # Mast
    ax.plot([0, 0], [freeboard, freeboard + D*0.4], color="#ccc", lw=2.5, zorder=8)
    ax.plot([-B*0.18, B*0.18], [freeboard+D*0.22]*2, color="#ccc", lw=1.5, zorder=8)

    # Draft annotation
    ax.annotate("", xy=(wl_h*1.5, -T_actual), xytext=(wl_h*1.5, 0),
                arrowprops=dict(arrowstyle="<->", color="#f1c40f", lw=1.5))
    ax.text(wl_h*1.65, -T_actual/2, f"T={T_actual:.2f}m",
            color="#f1c40f", fontsize=8, va="center")

    # Freeboard annotation
    if freeboard > 0:
        ax.annotate("", xy=(-wl_h*1.5, freeboard), xytext=(-wl_h*1.5, 0),
                    arrowprops=dict(arrowstyle="<->", color="#2ecc71", lw=1.5))
        ax.text(-wl_h*1.65, freeboard/2, f"FB={freeboard:.2f}m",
                color="#2ecc71", fontsize=8, va="center", ha="right")

    # Centre of Buoyancy marker
    ax.plot(0, -T_actual/2, "o", color="#e74c3c", ms=8, zorder=10)
    ax.text(B*0.1, -T_actual/2, "B (KB)", color="#e74c3c", fontsize=8, va="center")

    # Force arrows (scaled to D)
    scale  = D * 0.5 / max(F_buoyancy, F_gravity)
    fb_len = F_buoyancy * scale
    fg_len = F_gravity  * scale
    ax.annotate("", xy=(B*0.7,  fb_len*0.5), xytext=(B*0.7,  -fb_len*0.5),
                arrowprops=dict(arrowstyle="-|>", color="#2ecc71", lw=2, mutation_scale=14))
    ax.text(B*0.76, 0, f"Fb\n{F_buoyancy/1000:.0f}kN",
            color="#2ecc71", fontsize=7.5, va="center")
    ax.annotate("", xy=(-B*0.7, -fg_len*0.5), xytext=(-B*0.7,  fg_len*0.5),
                arrowprops=dict(arrowstyle="-|>", color="#e63946", lw=2, mutation_scale=14))
    ax.text(-B*0.76, 0, f"Fg\n{F_gravity/1000:.0f}kN",
            color="#e63946", fontsize=7.5, va="center", ha="right")

    ax.text(0, -T_actual*1.35,
            water_name.split("(")[0].strip().replace("🌊","").replace("🏖️","")
                      .replace("🌿","").replace("🏞️","").replace("🧪","").strip(),
            color="#4fc3f7", fontsize=8, ha="center", style="italic")

    ax.set_xlim(-L*0.5, L*0.5)
    ax.set_ylim(-T_actual*1.5 - D*0.3, freeboard + D*0.65)
    ax.set_xlabel("Beam (m)", color="#a8dadc", fontsize=9)
    ax.set_ylabel("Height above Keel (m)", color="#a8dadc", fontsize=9)
    ax.tick_params(colors="#a8dadc", labelsize=8)
    for sp in ax.spines.values(): sp.set_edgecolor("#457b9d")
    ax.legend(loc="upper left", fontsize=7.5, facecolor="#1d3557",
              labelcolor="#a8dadc", edgecolor="#457b9d")

    # ── RIGHT: Stability diagram ──────────────────────────────────────────────
    ax2.set_facecolor("#0d2137")
    ax2.set_title("Stability Diagram — GM Visualisation", color="#a8dadc", fontsize=11)

    keel_y  = -D / 2
    KB_y    = keel_y + T_actual / 2
    KG_y    = keel_y + (D * 0.45)           # representative visual position
    BM_val  = (B**2) / (12 * T_actual) if T_actual > 0 else 0
    KM_y    = keel_y + T_actual/2 + BM_val

    # Hull rectangle
    ax2.add_patch(mpatches.Rectangle(
        (-B/2, keel_y), B, D,
        linewidth=2, edgecolor="#8d99ae", facecolor="#3a4a5a", alpha=0.7, zorder=4))

    # Water fill inside hull up to waterline
    ax2.fill_between([-B/2, B/2], [keel_y, keel_y],
                     [keel_y + T_actual]*2,
                     color="#1a4a7a", alpha=0.5, zorder=3)
    ax2.axhline(keel_y + T_actual, color="#4fc3f7", lw=1.5,
                linestyle="--", label="Waterline", zorder=5)

    # Key points
    gm_color = "#2ecc71" if GM > 0.15 else ("#f1c40f" if GM > 0 else "#e63946")
    for y_pt, lbl, col in [
        (keel_y, "K  (Keel)",                     "#888888"),
        (KB_y,   f"B  KB = {T_actual/2:.2f} m",   "#e74c3c"),
        (KG_y,   f"G  KG = {KG_y - keel_y:.2f} m (approx)", "#f39c12"),
        (KM_y,   f"M  KM = {T_actual/2+BM_val:.2f} m",  "#9b59b6"),
    ]:
        ax2.plot(0, y_pt, "o", color=col, ms=9, zorder=10)
        ax2.text(B*0.58, y_pt, lbl, color=col, fontsize=8.5, va="center")

    # KM ↔ K arrow
    ax2.annotate("", xy=(B*0.38, KM_y), xytext=(B*0.38, keel_y),
                arrowprops=dict(arrowstyle="<->", color="#9b59b6", lw=2))

    # GM label
    ax2.text(-B*0.58, (KM_y + KB_y)/2, f"GM = {GM:.3f} m",
             color=gm_color, fontsize=10, fontweight="bold",
             ha="right", va="center",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#1d3557",
                       edgecolor=gm_color, alpha=0.9))

    gm_verdict = "✅ STABLE" if GM > 0.15 else ("⚠️ MARGINAL" if GM > 0 else "❌ UNSTABLE")
    ax2.text(0, KM_y + D*0.12, gm_verdict,
             color=gm_color, fontsize=11, fontweight="bold", ha="center",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#0a1628",
                       edgecolor=gm_color, alpha=0.95))

    ax2.set_xlim(-B*1.25, B*1.25)
    ax2.set_ylim(keel_y - D*0.3, KM_y + D*0.45)
    ax2.set_xlabel("Beam (m)", color="#a8dadc", fontsize=9)
    ax2.set_ylabel("Height above Keel (m)", color="#a8dadc", fontsize=9)
    ax2.tick_params(colors="#a8dadc", labelsize=8)
    for sp in ax2.spines.values(): sp.set_edgecolor("#457b9d")
    ax2.legend(loc="upper left", fontsize=7.5, facecolor="#1d3557",
               labelcolor="#a8dadc", edgecolor="#457b9d")

    plt.tight_layout()
    return fig

# ==============================================================================
# FIGURE 2 — WATER SCENARIO COMPARISON  (cached)
# ==============================================================================
@st.cache_data(show_spinner=False)
def draw_water_comparison(m: float, L: float, B: float,
                           D: float, rho_ship: float, KG: float):
    names, drafts, GMs, Fbs, Cbs = [], [], [], [], []
    for name, props in WATER_TYPES.items():
        r = compute_buoyancy(m, L, B, D, rho_ship, KG, float(props["rho"]))
        short = (name.split("(")[0].strip()
                     .replace("🌊","").replace("🏖️","")
                     .replace("🌿","").replace("🏞️","").replace("🧪","").strip())
        names.append(short)
        drafts.append(r["T_actual"])
        GMs.append(r["GM"])
        Fbs.append(r["F_buoyancy"] / 1000)
        Cbs.append(r["Cb"])

    fig, axes = plt.subplots(2, 2, figsize=(13, 6), facecolor="#0a1628")
    fig.suptitle("Water Environment Comparison — Buoyancy Performance",
                 color="#a8dadc", fontsize=13, fontweight="bold")

    panels = [
        (axes[0,0], drafts, "Draft T (m)",                "#4fc3f7", "Draft decreases in denser water"),
        (axes[0,1], GMs,    "GM — Metacentric Height (m)","#2ecc71", "Stability improves in denser water"),
        (axes[1,0], Fbs,    "Buoyant Force (kN)",         "#e74c3c", "Force increases with water density"),
        (axes[1,1], Cbs,    "Block Coefficient Cb",       "#f39c12", "Cb varies with submerged volume"),
    ]
    for ax, vals, ylabel, color, note in panels:
        ax.set_facecolor("#0d2137")
        bars = ax.bar(names, vals, color=color, alpha=0.8, edgecolor="#333", width=0.5)
        ax.set_ylabel(ylabel, color="#a8dadc", fontsize=8)
        ax.set_title(note, color="#888", fontsize=7.5, style="italic")
        ax.tick_params(colors="#a8dadc", labelsize=7)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=22, ha="right", fontsize=7)
        for sp in ax.spines.values(): sp.set_edgecolor("#457b9d")
        top = max(abs(v) for v in vals) if vals else 1
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + top * 0.02,
                    f"{val:.2f}", ha="center", va="bottom",
                    color="#a8dadc", fontsize=7)

    plt.tight_layout()
    return fig

# ==============================================================================
# SIDEBAR — INPUTS
# ==============================================================================
with st.sidebar:
    st.markdown("## 🎓 Academic Integrity")
    st.markdown("""<div class='integrity-box'>Enter your <b>Student ID</b> to receive
    unique, verifiable ship parameters for your assignment.</div>""",
    unsafe_allow_html=True)

    student_id  = st.text_input("Student ID", placeholder="e.g. 1234567")
    use_gen     = False
    gen_params  = None

    if student_id.strip():
        gen_params  = generate_student_params(student_id.strip())
        use_gen     = st.toggle("🔒 Use ID-Generated Parameters", value=True)
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
        L          = gen_params["L"]
        B          = gen_params["B"]
        D          = gen_params["D"]
        m          = gen_params["m"]
        rho_ship   = gen_params["rho_ship"]
        KG         = gen_params["KG"]
        mat_name   = gen_params["material_name"]
        st.caption(f"*Locked to Student ID `{student_id}`*")
        st.markdown(f"**L** = {L} m | **B** = {B} m | **D** = {D} m")
        st.markdown(f"**Mass** = {m:,.0f} kg | **KG** = {KG} m")
        st.markdown(f"**Material** = {mat_name} ({rho_ship:.0f} kg/m³)")
    else:
        L        = st.number_input("Length L (m)",   1.0, 500.0,  80.0, 1.0)
        B        = st.number_input("Beam B (m)",     1.0, 100.0,  14.0, 0.5)
        D        = st.number_input("Depth D (m)",    1.0,  80.0,   8.0, 0.5)
        m        = st.number_input("Ship Mass (kg)", 100.0, 1e8, 500000.0,
                                   1000.0, format="%.0f")
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
# HEADER
# ==============================================================================
st.title("⚓ Ship Buoyancy & Stability Simulator")
st.markdown("*Naval Fluid Mechanics — Educational Tool | Swinburne University of Technology*")
st.divider()

status = res["status"]
css_cls = ("status-float" if "FLOATING" in status
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
    st.metric("Total Hull Volume",   f"{res['V_total']:.2f} m³")
    st.metric("Material Volume",     f"{res['V_material']:.2f} m³")
    st.metric("Void / Air Volume",   f"{res['V_void']:.2f} m³")
    st.metric("Submerged Volume",    f"{res['V_submerged']:.2f} m³")
    st.markdown("### 📏 Geometry")
    st.metric("Actual Draft T",      f"{res['T_actual']:.3f} m")
    st.metric("Freeboard",           f"{res['freeboard']:.3f} m",
              delta="Safe" if res['freeboard'] > 0 else "FLOODED",
              delta_color="normal"  if res['freeboard'] > 0 else "inverse")
    st.metric("Draft Ratio T/D",     f"{res['draft_ratio']:.4f}")
    st.metric("Block Coefficient Cb",f"{res['Cb']:.4f}",
              help="0.50–0.65 fast vessels | 0.75–0.85 bulk carriers")

with c2:
    st.markdown("### ⚡ Forces")
    st.metric("Buoyant Force",       f"{res['F_buoyancy']/1000:.2f} kN")
    st.metric("Gravitational Force", f"{res['F_gravity']/1000:.2f} kN")
    st.metric("Net Force",           f"{res['F_net']/1000:.2f} kN",
              delta="Floating" if res['F_net'] > 0 else "Sinking",
              delta_color="normal"  if res['F_net'] > 0 else "inverse")
    st.metric("Displacement",        f"{res['displacement_t']:.1f} t")
    st.markdown("### 🚢 Load Capacity")
    st.metric("Safe Additional Load",f"{res['safe_load']:,.0f} kg",
              help="At 66% immersion safety margin")
    st.metric("Load to Sink",        f"{res['sink_load']:,.0f} kg")
    st.metric("Average Ship Density",f"{res['avg_density']:.2f} kg/m³")
    st.metric("Flotation Factor",    f"{res['flotation_fac']:.4f}",
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

    # GM remediation hint
    if gm <= 0:
        st.markdown("""<div style='background:#3a1a00;border:1px solid #e67e22;
        border-radius:6px;padding:8px;color:#e67e22;font-size:0.85em;'>
        ⚠️ <b>To improve GM:</b> increase Beam B (BM ∝ B²),
        reduce KG (lower cargo/ballast), or reduce draft T.
        </div>""", unsafe_allow_html=True)

    st.markdown("### 💧 Environment")
    st.metric("Water ρ_w",   f"{rho_water:.0f} kg/m³")
    st.metric("Material ρ_s",f"{rho_ship:.0f} kg/m³")

st.divider()

# ==============================================================================
# HULL FIGURE
# ==============================================================================
st.markdown("## 🖼️ Hull Visualisation & Stability Diagram")
with st.spinner("Rendering hull diagram…"):
    fig1 = draw_hull_figure(
        float(L), float(B), float(D),
        res["T_actual"], res["freeboard"], res["GM"],
        int(rho_water), res["F_buoyancy"], res["F_gravity"],
        status, water_sel)
    st.pyplot(fig1, use_container_width=True)
    plt.close(fig1)

st.divider()

# ==============================================================================
# WATER SCENARIO COMPARISON
# ==============================================================================
st.markdown("## 🌊 Water Environment Comparison")
st.caption("Analytical exercise: observe how your ship's performance changes "
           "across five water environments — from Dead Sea brine to freshwater rivers.")

with st.spinner("Computing water scenarios…"):
    fig2 = draw_water_comparison(
        float(m), float(L), float(B), float(D), float(rho_ship), float(KG))
    st.pyplot(fig2, use_container_width=True)
    plt.close(fig2)

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
        "Displacement (t)":   round(r["displacement_t"], 1),
        "GM (m)":             round(r["GM"], 3),
        "Cb":                 round(r["Cb"], 4),
        "Flotation Factor":   round(r["flotation_fac"], 4),
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

Floating condition requires: $\bar{\rho}_{ship} \leq \rho_w$

---
### Draft — Box Hull
$$T = \frac{V_{submerged}}{L \cdot B} \qquad \text{Freeboard} = D - T$$

---
### Block Coefficient
$$C_b = \frac{V_{submerged}}{L \cdot B \cdot T}$$
Typical range: 0.50–0.65 (fast vessels) → 0.75–0.85 (bulk carriers)

---
### GM Stability Chain

| Symbol | Meaning | Formula |
|--------|---------|---------|
| **KB** | Centre of Buoyancy above Keel | $T/2$ |
| **BM** | Metacentric Radius | $B^2 / (12T)$ |
| **KM** | Metacentre above Keel | $KB + BM$ |
| **GM** | Metacentric Height | $KM - KG$ |

- $GM > 0.15$ m → ✅ Stable
- $0 < GM \leq 0.15$ m → ⚠️ Tender (marginally stable)
- $GM \leq 0$ m → ❌ Unstable (capsizes)

> BM increases with $B^2$ — doubling the beam quadruples metacentric radius.

---
### Effect of Water Density on Draft
$$T \propto \frac{1}{\rho_w}$$
Moving from freshwater (1000) to seawater (1025) reduces draft by ~2.4% — the basis of the **Plimsoll Line**.
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
        Water: <b>{water_sel}</b> | Ship: L={L}m, B={B}m, D={D}m<br>
        Mass: {m:,.0f} kg | KG: {KG} m | Material: {mat_name}<br><br>
        <b>Include both hash codes in your report submission header.</b>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Enter your Student ID in the sidebar to generate a submission fingerprint.")

# ==============================================================================
# FOOTER
# ==============================================================================
st.divider()
st.markdown("""<div style='text-align:center;color:#555;font-size:0.8em;'>
⚓ Ship Buoyancy & Stability Simulator v4.1 &nbsp;|&nbsp;
Naval Fluid Mechanics — Educational Tool &nbsp;|&nbsp;
Swinburne University of Technology &nbsp;|&nbsp;
<i>Box-hull approximation — for educational purposes</i>
</div>""", unsafe_allow_html=True)
