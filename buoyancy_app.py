# ==============================================================================
# Naval Fluid Mechanics — Buoyancy & Stability Simulator
# Streamlit Web Application
# Author: Ilya Kavalchuk — Swinburne University of Technology
# Version: 4.0 (Academic Integrity + Geometry + GM Stability + Water Scenarios)
# ==============================================================================

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
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
    .main { background-color: #0a1628; }
    .stApp { background-color: #0a1628; }
    h1, h2, h3 { color: #a8dadc; }
    .metric-card {
        background: #1d3557;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 4px 0;
        border-left: 4px solid #457b9d;
    }
    .metric-value { color: #a8dadc; font-size: 1.1em; font-weight: bold; }
    .metric-label { color: #ccc; font-size: 0.85em; }
    .status-float  { background:#1a4731; border:2px solid #2ecc71; border-radius:8px; padding:10px; text-align:center; color:#2ecc71; font-size:1.3em; font-weight:bold; }
    .status-neutral{ background:#4a3a00; border:2px solid #f1c40f; border-radius:8px; padding:10px; text-align:center; color:#f1c40f; font-size:1.3em; font-weight:bold; }
    .status-sink   { background:#4a0000; border:2px solid #e63946; border-radius:8px; padding:10px; text-align:center; color:#e63946; font-size:1.3em; font-weight:bold; }
    .integrity-box { background:#1a2a1a; border:2px solid #2ecc71; border-radius:8px; padding:12px; margin:8px 0; }
    .theory-box    { background:#1d3557; border-radius:8px; padding:14px; margin:6px 0; border-left:4px solid #e63946; }
    .warning-box   { background:#3a1a00; border:2px solid #e67e22; border-radius:6px; padding:10px; color:#e67e22; }
    .stSelectbox label, .stNumberInput label, .stTextInput label { color: #a8dadc !important; font-weight: 600; }
    div[data-testid="metric-container"] { background:#1d3557; border-radius:8px; padding:8px; border-left:4px solid #457b9d; }
    div[data-testid="metric-container"] label { color: #a8dadc !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONSTANTS — WATER ENVIRONMENTS
# ==============================================================================
WATER_TYPES = {
    "🌊 Open Ocean (Seawater)":        {"rho": 1025, "desc": "Standard seawater — open ocean, typical naval operations"},
    "🏖️ Coastal / Harbour Water":      {"rho": 1015, "desc": "Slightly diluted by freshwater runoff near ports and estuaries"},
    "🌿 Brackish Water (Estuary)":      {"rho": 1005, "desc": "Mixed fresh/saltwater — river mouths, Baltic Sea, estuaries"},
    "🏞️ Freshwater (River / Lake)":    {"rho": 1000, "desc": "Rivers, lakes, inland waterways — lowest buoyancy environment"},
    "🧪 Dense Brine (Dead Sea / Salt Lake)": {"rho": 1240, "desc": "Hypersaline water — extreme buoyancy, rarely navigated by ships"},
}

MATERIAL_PRESETS = {
    "Custom (manual entry)":   None,
    "Mild Steel":              7850,
    "High-Strength Steel":     7950,
    "Aluminium Alloy":         2700,
    "GRP / Fibreglass":        1600,
    "Carbon Fibre Composite":  1550,
    "Timber (Teak)":           900,
    "Timber (Pine)":           530,
    "Reinforced Concrete":     2400,
}

G = 9.81  # m/s²

# ==============================================================================
# ACADEMIC INTEGRITY — STUDENT ID SEED
# ==============================================================================
def generate_student_params(student_id: str) -> dict:
    """
    Deterministically generate unique ship parameters from Student ID.
    Same ID → same parameters (reproducible/auditable).
    Different IDs → different parameters (prevents copying).
    """
    h = int(hashlib.sha256(student_id.strip().encode()).hexdigest(), 16)
    rng = random.Random(h % (2**32))

    # Ship dimensions — realistic naval vessel ranges
    L = round(rng.uniform(40.0, 180.0), 1)     # Length (m)
    B = round(rng.uniform(8.0,  28.0),  1)     # Beam (m)
    D = round(rng.uniform(4.0,  18.0),  1)     # Depth (m)
    hull_factor = round(rng.uniform(0.55, 0.82), 3)  # Block coefficient seed

    # Mass derived from geometry and realistic loading
    V_hull = L * B * D * hull_factor
    rho_ship = rng.choice([7850, 7950, 2700, 1600])
    wall_fraction = round(rng.uniform(0.08, 0.18), 3)
    V_material = V_hull * wall_fraction
    m = round(V_material * rho_ship / 1000) * 1000  # round to nearest tonne

    # KG — centre of gravity height (30–55% of depth)
    KG = round(rng.uniform(0.30, 0.55) * D, 2)

    # Integrity hash — 8-char fingerprint for submission verification
    integrity_seed = f"{student_id.strip()}|{L}|{B}|{D}|{m}|{rho_ship}"
    integrity_hash = hashlib.sha256(integrity_seed.encode()).hexdigest()[:8].upper()

    return {
        "L": L, "B": B, "D": D,
        "m": m, "rho_ship": rho_ship,
        "KG": KG,
        "hull_factor": hull_factor,
        "integrity_hash": integrity_hash,
        "material_name": {7850:"Mild Steel", 7950:"High-Strength Steel",
                          2700:"Aluminium Alloy", 1600:"GRP / Fibreglass"}[rho_ship]
    }

def result_hash(student_id, inputs, results) -> str:
    """Generate a verifiable submission fingerprint from inputs + outputs."""
    payload = f"{student_id}|" + "|".join(
        f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
        for k, v in {**inputs, **results}.items()
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12].upper()

# ==============================================================================
# PHYSICS ENGINE
# ==============================================================================
def compute_buoyancy(m, L, B, D, rho_ship, KG, rho_water):
    """
    Full buoyancy and stability computation.
    Box-hull approximation (valid for educational purposes).
    """
    # --- Volumes ---
    V_total    = L * B * D                     # Total hull envelope (m³)
    V_material = m / rho_ship                  # Solid material volume (m³)
    V_void     = V_total - V_material          # Air / void volume (m³)

    # --- Buoyancy ---
    V_theoretical = m / rho_water              # Volume needed to float (m³)
    V_submerged   = min(V_theoretical, V_total)
    T_actual      = V_submerged / (L * B)      # Actual draft (m)  [box hull]
    freeboard     = D - T_actual               # Freeboard (m)
    draft_ratio   = T_actual / D              # Dimensionless draft

    # --- Forces ---
    F_buoyancy = rho_water * G * V_submerged   # N
    F_gravity  = m * G                         # N
    F_net      = F_buoyancy - F_gravity         # N (+ve = floating)

    # --- Displacement ---
    displacement_t = rho_water * V_submerged / 1000  # tonnes

    # --- Load limits ---
    safe_load = rho_water * 0.66 * V_total - m   # kg (66% immersion safety)
    sink_load = rho_water * V_total - m           # kg (100% immersion = sinking)

    # --- Density metrics ---
    avg_density      = m / V_total
    flotation_factor = rho_water / avg_density
    Cb               = V_submerged / (L * B * T_actual) if T_actual > 0 else 0

    # --- GM Stability (box-hull approximation) ---
    KB  = T_actual / 2                         # Centre of buoyancy above keel
    BM  = (B**2) / (12 * T_actual) if T_actual > 0 else 0  # Metacentric radius
    KM  = KB + BM                              # Metacentre above keel
    GM  = KM - KG                              # Metacentric height

    # --- Status ---
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
        # Volumes
        "V_total":        V_total,
        "V_material":     V_material,
        "V_void":         V_void,
        "V_submerged":    V_submerged,
        # Draft & geometry
        "T_actual":       T_actual,
        "freeboard":      freeboard,
        "draft_ratio":    draft_ratio,
        "Cb":             Cb,
        # Forces
        "F_buoyancy":     F_buoyancy,
        "F_gravity":      F_gravity,
        "F_net":          F_net,
        # Displacement & loads
        "displacement_t": displacement_t,
        "safe_load":      safe_load,
        "sink_load":      sink_load,
        # Density
        "avg_density":    avg_density,
        "flotation_factor": flotation_factor,
        # Stability
        "KB": KB, "BM": BM, "KM": KM, "GM": GM,
        # Status
        "status": status,
    }

# ==============================================================================
# MATPLOTLIB FIGURE — HULL CROSS-SECTION
# ==============================================================================
def draw_hull_figure(L, B, D, T_actual, freeboard, GM, rho_water,
                     F_buoyancy, F_gravity, status, water_name):
    fig, axes = plt.subplots(1, 2, figsize=(13, 6),
                             facecolor="#0a1628")
    fig.suptitle("Ship Buoyancy & Stability — Visual Analysis",
                 color="#a8dadc", fontsize=14, fontweight="bold", y=1.01)

    # ── LEFT PANEL: Side-profile cross-section ─────────────────────────────
    ax = axes[0]
    ax.set_facecolor("#0d2137")
    ax.set_title("Hull Cross-Section (Side Profile)", color="#a8dadc", fontsize=11)

    # Water body
    water_top = 0.0
    water_rect = mpatches.FancyBboxPatch(
        (-L * 0.55, -T_actual * 1.6), L * 1.1, T_actual * 1.6 + water_top,
        boxstyle="square", linewidth=0,
        facecolor="#1a4a7a", alpha=0.6
    )
    ax.add_patch(water_rect)

    # Waterline
    ax.axhline(0, color="#4fc3f7", linewidth=2.0, linestyle="--", label="Waterline", zorder=5)

    # Hull shape (trapezoid — slightly wider at waterline than keel)
    keel_half   = B / 2 * 0.85
    wl_half     = B / 2
    hull_depth  = T_actual
    above_water = freeboard

    hull_x = [-keel_half, keel_half, wl_half, wl_half + B*0.05,
               wl_half + B*0.05, -wl_half - B*0.05, -wl_half - B*0.05, -wl_half, -keel_half]
    hull_y = [-hull_depth, -hull_depth, 0, 0,
               above_water, above_water, 0, 0, -hull_depth]

    hull_color = "#8d99ae" if "FLOATING" in status else "#e63946"
    ax.fill(hull_x, hull_y, color=hull_color, alpha=0.85, zorder=6, label="Hull")
    ax.plot(hull_x, hull_y, color="#ccc", linewidth=1.5, zorder=7)

    # Mast
    ax.plot([0, 0], [above_water, above_water + D * 0.4],
            color="#ccc", linewidth=2.5, zorder=8)
    ax.plot([-B * 0.18, B * 0.18],
            [above_water + D * 0.22, above_water + D * 0.22],
            color="#ccc", linewidth=1.5, zorder=8)

    # Draft arrow
    ax.annotate("", xy=(wl_half * 1.5, -T_actual),
                xytext=(wl_half * 1.5, 0),
                arrowprops=dict(arrowstyle="<->", color="#f1c40f", lw=1.5))
    ax.text(wl_half * 1.6, -T_actual / 2,
            f"T={T_actual:.2f}m", color="#f1c40f", fontsize=8, va="center")

    # Freeboard arrow
    if freeboard > 0:
        ax.annotate("", xy=(-wl_half * 1.5, above_water),
                    xytext=(-wl_half * 1.5, 0),
                    arrowprops=dict(arrowstyle="<->", color="#2ecc71", lw=1.5))
        ax.text(-wl_half * 1.6, above_water / 2,
                f"FB={freeboard:.2f}m", color="#2ecc71", fontsize=8,
                va="center", ha="right")

    # KB, KG markers on hull centreline
    ax.plot(0, -T_actual / 2, "o", color="#e74c3c", markersize=8, zorder=10, label=f"KB={T_actual/2:.2f}m")

    # Centre of buoyancy label
    ax.text(B * 0.08, -T_actual / 2, "B (KB)", color="#e74c3c", fontsize=8, va="center")

    # Force arrows (scaled)
    scale = D * 0.6 / max(F_buoyancy, F_gravity)
    F_b_len = F_buoyancy * scale
    F_g_len = F_gravity  * scale
    ax.annotate("", xy=(B * 0.7, F_b_len * 0.5),
                xytext=(B * 0.7, -F_b_len * 0.5),
                arrowprops=dict(arrowstyle="-|>", color="#2ecc71",
                                lw=2, mutation_scale=14))
    ax.text(B * 0.75, 0, f"Fb\n{F_buoyancy/1000:.0f}kN",
            color="#2ecc71", fontsize=7.5, va="center")

    ax.annotate("", xy=(-B * 0.7, -F_g_len * 0.5),
                xytext=(-B * 0.7, F_g_len * 0.5),
                arrowprops=dict(arrowstyle="-|>", color="#e63946",
                                lw=2, mutation_scale=14))
    ax.text(-B * 0.75, 0, f"Fg\n{F_gravity/1000:.0f}kN",
            color="#e63946", fontsize=7.5, va="center", ha="right")

    # Axes formatting
    margin = D * 0.7
    ax.set_xlim(-L * 0.5, L * 0.5)
    ax.set_ylim(-T_actual * 1.5 - margin * 0.3, above_water + D * 0.6 + margin * 0.2)
    ax.set_xlabel("Beam (m)", color="#a8dadc", fontsize=9)
    ax.set_ylabel("Height above Keel (m)", color="#a8dadc", fontsize=9)
    ax.tick_params(colors="#a8dadc", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#457b9d")
    ax.legend(loc="upper left", fontsize=7.5, facecolor="#1d3557",
              labelcolor="#a8dadc", edgecolor="#457b9d")

    # Water label
    ax.text(0, -T_actual * 1.35, water_name.split("(")[0].strip(),
            color="#4fc3f7", fontsize=8, ha="center", style="italic")

    # ── RIGHT PANEL: Stability diagram ────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#0d2137")
    ax2.set_title("Stability Diagram — GM Visualisation", color="#a8dadc", fontsize=11)

    # Hull outline (front view — rectangular cross-section)
    hull_w = B
    hull_d = D

    # Water fill
    water_h = T_actual
    ax2.fill_between([-hull_w/2, hull_w/2], [-hull_d/2, -hull_d/2],
                     [-hull_d/2 + water_h, -hull_d/2 + water_h],
                     color="#1a4a7a", alpha=0.5, zorder=3)

    # Hull rectangle
    rect = mpatches.Rectangle((-hull_w/2, -hull_d/2), hull_w, hull_d,
                               linewidth=2, edgecolor="#8d99ae",
                               facecolor="#3a4a5a", alpha=0.7, zorder=4)
    ax2.add_patch(rect)

    # Waterline
    ax2.axhline(-hull_d/2 + water_h, color="#4fc3f7", linewidth=1.5,
                linestyle="--", label="Waterline", zorder=5)

    # Key points on centreline
    keel_y  = -hull_d / 2
    KB_y    = keel_y + T_actual / 2
    KG_y    = keel_y  # KG is from keel
    from_keel = keel_y  # reference

    # Compute actual y positions from keel
    KB_plot = keel_y + T_actual / 2
    KG_plot = keel_y + (D * 0.5)    # approximate KG visual (mid-ship for diagram)

    # Use actual computed KG from input
    KG_val  = D * 0.5               # placeholder visual — actual KG shown as text
    KM_plot = keel_y + (T_actual / 2 + (B**2) / (12 * T_actual)) if T_actual > 0 else keel_y

    # Plot key points
    for y_pt, label_txt, col in [
        (keel_y,  "K (Keel)",          "#888"),
        (KB_plot, f"B (KB={T_actual/2:.2f}m)", "#e74c3c"),
        (KG_plot, f"G (KG≈{D*0.5:.2f}m)",     "#f39c12"),
        (KM_plot, f"M (KM={T_actual/2 + (B**2)/(12*T_actual) if T_actual>0 else 0:.2f}m)", "#9b59b6"),
    ]:
        ax2.plot(0, y_pt, "o", color=col, markersize=9, zorder=10)
        ax2.text(hull_w * 0.55, y_pt, label_txt, color=col,
                 fontsize=8.5, va="center")

    # GM arrow (K→M with G marked)
    ax2.annotate("", xy=(hull_w * 0.35, KM_plot),
                xytext=(hull_w * 0.35, keel_y),
                arrowprops=dict(arrowstyle="<->",
                                color="#9b59b6", lw=2))

    # GM label
    gm_color = "#2ecc71" if GM > 0.15 else ("#f1c40f" if GM > 0 else "#e63946")
    ax2.text(-hull_w * 0.55, (KM_plot + KB_plot) / 2,
             f"GM = {GM:.3f} m", color=gm_color, fontsize=10,
             fontweight="bold", ha="right", va="center",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#1d3557",
                       edgecolor=gm_color, alpha=0.9))

    # Stability status label
    gm_status = ("✅ STABLE" if GM > 0.15
                 else "⚠️ MARGINAL" if GM > 0
                 else "❌ UNSTABLE")
    ax2.text(0, KM_plot + hull_d * 0.12, gm_status,
             color=gm_color, fontsize=11, fontweight="bold",
             ha="center", va="bottom",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#0a1628",
                       edgecolor=gm_color, alpha=0.95))

    ax2.set_xlim(-hull_w * 1.2, hull_w * 1.2)
    ax2.set_ylim(keel_y - hull_d * 0.3, KM_plot + hull_d * 0.4)
    ax2.set_xlabel("Beam (m)", color="#a8dadc", fontsize=9)
    ax2.set_ylabel("Height above Keel (m)", color="#a8dadc", fontsize=9)
    ax2.tick_params(colors="#a8dadc", labelsize=8)
    for spine in ax2.spines.values():
        spine.set_edgecolor("#457b9d")
    ax2.legend(loc="upper left", fontsize=7.5, facecolor="#1d3557",
               labelcolor="#a8dadc", edgecolor="#457b9d")

    plt.tight_layout()
    return fig


# ==============================================================================
# WATER SCENARIO COMPARISON CHART
# ==============================================================================
def draw_water_comparison(m, L, B, D, rho_ship, KG):
    """Bar chart comparing key metrics across all water environments."""
    labels_w, drafts, GMs, Fbs, Cbs = [], [], [], [], []

    for name, props in WATER_TYPES.items():
        r = compute_buoyancy(m, L, B, D, rho_ship, KG, props["rho"])
        short = name.split("(")[0].strip().replace("🌊","").replace("🏖️","") \
                    .replace("🌿","").replace("🏞️","").replace("🧪","").strip()
        labels_w.append(short)
        drafts.append(r["T_actual"])
        GMs.append(r["GM"])
        Fbs.append(r["F_buoyancy"] / 1000)
        Cbs.append(r["Cb"])

    fig, axes = plt.subplots(2, 2, figsize=(13, 6), facecolor="#0a1628")
    fig.suptitle("Water Environment Comparison — Buoyancy Performance",
                 color="#a8dadc", fontsize=13, fontweight="bold")

    datasets = [
        (axes[0,0], drafts, "Draft T (m)",           "#4fc3f7", "Draft decreases in denser water"),
        (axes[0,1], GMs,    "GM — Metacentric Height (m)", "#2ecc71", "Stability improves in denser water"),
        (axes[1,0], Fbs,    "Buoyant Force (kN)",     "#e74c3c", "Force increases with water density"),
        (axes[1,1], Cbs,    "Block Coefficient Cb",   "#f39c12", "Cb varies with submerged volume"),
    ]

    for ax, vals, ylabel, color, note in datasets:
        ax.set_facecolor("#0d2137")
        bars = ax.bar(labels_w, vals, color=color, alpha=0.8, edgecolor="#333", width=0.5)
        ax.set_ylabel(ylabel, color="#a8dadc", fontsize=8)
        ax.tick_params(colors="#a8dadc", labelsize=7)
        ax.set_xticks(range(len(labels_w)))
        ax.set_xticklabels(labels_w, rotation=20, ha="right", fontsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#457b9d")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*0.01,
                    f"{val:.2f}", ha="center", va="bottom", color="#a8dadc", fontsize=7)
        ax.set_title(note, color="#888", fontsize=7.5, style="italic")

    plt.tight_layout()
    return fig


# ==============================================================================
# STREAMLIT UI — SIDEBAR
# ==============================================================================
st.title("⚓ Ship Buoyancy & Stability Simulator")
st.markdown("*Naval Fluid Mechanics — Educational Tool | Swinburne University of Technology*")
st.divider()

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Academic Integrity")
    st.markdown("""
    <div class='integrity-box'>
    Enter your <b>Student ID</b> to receive unique ship parameters.
    Your results are individually generated and verifiable.
    </div>
    """, unsafe_allow_html=True)

    student_id = st.text_input("Student ID", placeholder="e.g. 1234567",
                               help="Your unique ID seeds all ship parameters. Same ID = same ship. Different IDs = different ships.")

    use_generated = False
    gen_params = None

    if student_id.strip():
        gen_params = generate_student_params(student_id)
        use_generated = st.toggle("🔒 Use ID-Generated Parameters", value=True,
                                  help="Lock parameters to your Student ID for academic integrity.")
        if use_generated:
            st.markdown(f"""
            <div class='integrity-box'>
            <b>🔐 Your Assignment Parameters</b><br>
            L = <b>{gen_params['L']} m</b> &nbsp;|&nbsp; B = <b>{gen_params['B']} m</b> &nbsp;|&nbsp; D = <b>{gen_params['D']} m</b><br>
            Mass = <b>{gen_params['m']:,} kg</b><br>
            Material = <b>{gen_params['material_name']}</b> ({gen_params['rho_ship']} kg/m³)<br>
            KG = <b>{gen_params['KG']} m</b><br><br>
            <b>📋 Parameter Hash: <code>{gen_params['integrity_hash']}</code></b><br>
            <small>Include this hash in your report submission.</small>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("## 🌊 Water Environment")
    water_selection = st.selectbox(
        "Select Water Type",
        options=list(WATER_TYPES.keys()),
        index=0,
        help="Different water densities significantly affect buoyancy, draft, and stability."
    )
    rho_water = WATER_TYPES[water_selection]["rho"]
    st.info(f"ρ_water = **{rho_water} kg/m³**\n\n{WATER_TYPES[water_selection]['desc']}")

    st.divider()
    st.markdown("## 📐 Ship Geometry")

    if use_generated and gen_params:
        L       = gen_params["L"]
        B       = gen_params["B"]
        D       = gen_params["D"]
        m       = float(gen_params["m"])
        rho_ship_val = float(gen_params["rho_ship"])
        KG      = gen_params["KG"]
        st.markdown(f"*Parameters locked to Student ID `{student_id}`*")
        # Show read-only info
        st.markdown(f"**L** = {L} m &nbsp; **B** = {B} m &nbsp; **D** = {D} m")
        st.markdown(f"**Mass** = {m:,.0f} kg")
        st.markdown(f"**KG** = {KG} m")
        material_name = gen_params["material_name"]
        st.markdown(f"**Material** = {material_name}")
    else:
        L  = st.number_input("Length L (m)",  min_value=1.0, max_value=500.0, value=80.0,  step=1.0)
        B  = st.number_input("Beam B (m)",    min_value=1.0, max_value=100.0, value=14.0,  step=0.5)
        D  = st.number_input("Depth D (m)",   min_value=1.0, max_value=80.0,  value=8.0,   step=0.5)
        m  = st.number_input("Ship Mass (kg)",min_value=100.0, max_value=1e8, value=500000.0, step=1000.0, format="%.0f")
        KG = st.number_input("KG — Centre of Gravity above Keel (m)",
                             min_value=0.1, max_value=50.0, value=4.0, step=0.1,
                             help="Height of centre of gravity above keel. Typically 40–55% of depth.")

        st.markdown("#### 🔩 Hull Material")
        mat_choice = st.selectbox("Material Preset", options=list(MATERIAL_PRESETS.keys()))
        if MATERIAL_PRESETS[mat_choice] is not None:
            rho_ship_val = float(MATERIAL_PRESETS[mat_choice])
            st.info(f"ρ_material = **{rho_ship_val:.0f} kg/m³**")
        else:
            rho_ship_val = st.number_input("Custom Density (kg/m³)",
                                           min_value=100.0, max_value=20000.0,
                                           value=7850.0, step=10.0)
        material_name = mat_choice

# ==============================================================================
# VALIDATION & CALCULATION
# ==============================================================================
errors = []
if L <= 0 or B <= 0 or D <= 0:
    errors.append("Ship dimensions L, B, D must all be positive.")
if m <= 0:
    errors.append("Ship mass must be positive.")
if rho_ship_val <= 0:
    errors.append("Material density must be positive.")
if KG >= D:
    errors.append(f"KG ({KG} m) cannot exceed ship depth D ({D} m).")

V_material_check = m / rho_ship_val
V_total_check    = L * B * D
if V_material_check > V_total_check:
    errors.append(
        f"Material volume ({V_material_check:.1f} m³) exceeds total hull volume "
        f"({V_total_check:.1f} m³). Reduce mass, increase dimensions, or choose lighter material."
    )

if errors:
    for e in errors:
        st.error(f"⚠️ {e}")
    st.stop()

# Run computation
res = compute_buoyancy(m, L, B, D, rho_ship_val, KG, rho_water)

# ==============================================================================
# STATUS BANNER
# ==============================================================================
status = res["status"]
if "STABLE" in status and "FLOATING" in status:
    css_cls = "status-float"
elif "NEUTRAL" in status:
    css_cls = "status-neutral"
else:
    css_cls = "status-sink"

st.markdown(f"<div class='{css_cls}'>⚓ {status}</div>", unsafe_allow_html=True)
st.markdown("")

# ==============================================================================
# RESULTS — THREE COLUMNS
# ==============================================================================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📦 Volume Analysis")
    st.metric("Total Hull Volume",    f"{res['V_total']:.2f} m³")
    st.metric("Material Volume",      f"{res['V_material']:.2f} m³")
    st.metric("Void / Air Volume",    f"{res['V_void']:.2f} m³")
    st.metric("Submerged Volume",     f"{res['V_submerged']:.2f} m³")

    st.markdown("### 📏 Geometry")
    st.metric("Actual Draft T",       f"{res['T_actual']:.3f} m")
    st.metric("Freeboard",            f"{res['freeboard']:.3f} m",
              delta="OK" if res['freeboard'] > 0 else "FLOODED",
              delta_color="normal" if res['freeboard'] > 0 else "inverse")
    st.metric("Draft Ratio T/D",      f"{res['draft_ratio']:.4f}")
    st.metric("Block Coefficient Cb", f"{res['Cb']:.4f}",
              help="Cb = V_submerged / (L×B×T). Range: 0.5 (fast) to 0.85 (tanker).")

with col2:
    st.markdown("### ⚡ Forces")
    st.metric("Buoyant Force",        f"{res['F_buoyancy']/1000:.2f} kN")
    st.metric("Gravitational Force",  f"{res['F_gravity']/1000:.2f} kN")
    st.metric("Net Force",            f"{res['F_net']/1000:.2f} kN",
              delta="Positive = Floating" if res['F_net'] > 0 else "Negative = Sinking",
              delta_color="normal" if res['F_net'] > 0 else "inverse")
    st.metric("Displacement",         f"{res['displacement_t']:.1f} tonnes")

    st.markdown("### 🚢 Load Capacity")
    st.metric("Safe Additional Load", f"{res['safe_load']:,.0f} kg",
              help="Maximum load at 66% immersion safety margin.")
    st.metric("Load to Sink",         f"{res['sink_load']:,.0f} kg",
              help="Additional load that would cause total submersion.")
    st.metric("Average Ship Density", f"{res['avg_density']:.2f} kg/m³")
    st.metric("Flotation Factor",     f"{res['flotation_factor']:.4f}",
              help="ρ_water / ρ_avg_ship. > 1 = floating, < 1 = sinking.")

with col3:
    st.markdown("### 🎯 GM Stability (Box-Hull)")
    st.metric("KB — Centre of Buoyancy", f"{res['KB']:.3f} m",
              help="Height of centre of buoyancy above keel. KB = T/2 for box hull.")
    st.metric("BM — Metacentric Radius", f"{res['BM']:.3f} m",
              help="BM = B² / (12·T). Wider beam → larger BM → more stable.")
    st.metric("KM — Metacentre",         f"{res['KM']:.3f} m",
              help="KM = KB + BM. Height of metacentre above keel.")
    st.metric("KG — Centre of Gravity",  f"{KG:.3f} m")

    gm_val = res["GM"]
    gm_color = "normal" if gm_val > 0 else "inverse"
    gm_note  = ("✅ Stable" if gm_val > 0.15
                else "⚠️ Marginally stable" if gm_val > 0
                else "❌ UNSTABLE — vessel will capsize")
    st.metric("GM — Metacentric Height", f"{gm_val:.3f} m",
              delta=gm_note, delta_color=gm_color)

    st.markdown("### 💧 Water Environment")
    st.metric("Water Density ρ_w",   f"{rho_water} kg/m³")
    st.metric("Ship Material ρ_s",   f"{rho_ship_val:.0f} kg/m³",
              help=f"Material: {material_name}")

st.divider()

# ==============================================================================
# HULL FIGURE
# ==============================================================================
st.markdown("## 🖼️ Hull Visualisation & Stability Diagram")
fig_hull = draw_hull_figure(
    L, B, D, res["T_actual"], res["freeboard"],
    res["GM"], rho_water, res["F_buoyancy"], res["F_gravity"],
    status, water_selection
)
st.pyplot(fig_hull, use_container_width=True)
plt.close(fig_hull)

st.divider()

# ==============================================================================
# WATER SCENARIO COMPARISON
# ==============================================================================
st.markdown("## 🌊 Water Environment Comparison")
st.markdown(
    "*Analyse how your ship performs across all water types — "
    "from hypersaline brine to freshwater rivers. "
    "This section supports analytical and evaluation-level learning objectives.*"
)

fig_compare = draw_water_comparison(m, L, B, D, rho_ship_val, KG)
st.pyplot(fig_compare, use_container_width=True)
plt.close(fig_compare)

# Comparison table
st.markdown("#### 📊 Numerical Comparison Table")
table_rows = []
for name, props in WATER_TYPES.items():
    r = compute_buoyancy(m, L, B, D, rho_ship_val, KG, props["rho"])
    table_rows.append({
        "Water Environment":    name.split("(")[0].strip(),
        "ρ_w (kg/m³)":         props["rho"],
        "Draft T (m)":          round(r["T_actual"], 3),
        "Freeboard (m)":        round(r["freeboard"], 3),
        "Buoyant Force (kN)":   round(r["F_buoyancy"] / 1000, 2),
        "Displacement (t)":     round(r["displacement_t"], 1),
        "GM (m)":               round(r["GM"], 3),
        "Cb":                   round(r["Cb"], 4),
        "Flotation Factor":     round(r["flotation_factor"], 4),
        "Status":               r["status"],
    })
df = pd.DataFrame(table_rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ==============================================================================
# THEORY EXPANDER
# ==============================================================================
with st.expander("📚 Theory & Equations — Archimedes' Principle & GM Stability"):
    st.markdown("""
    ### Archimedes' Principle
    A body immersed in fluid experiences an upward buoyant force equal to the weight of fluid displaced:

    $$F_b = \\rho_w \\cdot g \\cdot V_{submerged}$$

    **Floating condition:** $F_b \\geq F_g = m \\cdot g$, which requires:

    $$\\frac{m}{V_{total}} \\leq \\rho_w \\quad \\Leftrightarrow \\quad \\bar{\\rho}_{ship} \\leq \\rho_w$$

    ---
    ### Draft Calculation (Box Hull)

    For a rectangular (box) hull of length $L$, beam $B$:

    $$T = \\frac{V_{submerged}}{L \\cdot B}$$

    **Freeboard** $= D - T$ (must remain positive to prevent flooding)

    ---
    ### Block Coefficient

    $$C_b = \\frac{V_{submerged}}{L \\cdot B \\cdot T}$$

    Typical values: 0.50–0.65 (fast vessels), 0.75–0.85 (bulk carriers/tankers)

    ---
    ### GM Stability — Box Hull Approximation

    | Symbol | Name | Formula |
    |--------|------|---------|
    | **K**  | Keel | Reference datum (0 m) |
    | **KB** | Centre of Buoyancy above Keel | $KB = T/2$ |
    | **BM** | Metacentric Radius | $BM = B^2 / (12T)$ |
    | **KM** | Metacentre above Keel | $KM = KB + BM$ |
    | **KG** | Centre of Gravity above Keel | Input parameter |
    | **GM** | Metacentric Height | $GM = KM - KG$ |

    **Stability criteria:**
    - $GM > 0.15$ m → ✅ Stable (vessel returns upright after heeling)
    - $0 < GM \\leq 0.15$ m → ⚠️ Marginally stable (tender ship)
    - $GM \\leq 0$ m → ❌ Unstable (vessel will capsize)

    > *Note: BM increases with beam squared — wider ships are inherently more stable.*

    ---
    ### Effect of Water Density on Buoyancy

    In denser water (higher $\\rho_w$), the same ship floats **higher** (reduced draft):

    $$T \\propto \\frac{1}{\\rho_w}$$

    A ship moving from freshwater ($\\rho = 1000$) to seawater ($\\rho = 1025$) rises approximately **2.4%** of its draft — this is accounted for by the **Plimsoll Line** on real vessels.
    """)

# ==============================================================================
# ACADEMIC INTEGRITY — SUBMISSION FINGERPRINT
# ==============================================================================
with st.expander("🔐 Academic Integrity — Submission Verification"):
    if student_id.strip():
        inputs_dict  = {"L": L, "B": B, "D": D, "m": m, "rho_ship": rho_ship_val, "KG": KG, "rho_water": float(rho_water)}
        results_dict = {k: v for k, v in res.items() if isinstance(v, (int, float))}
        sub_hash = result_hash(student_id, inputs_dict, results_dict)

        st.markdown(f"""
        <div class='integrity-box'>
        <b>📋 Submission Verification Details</b><br><br>
        Student ID: <code>{student_id}</code><br>
        Parameter Hash: <code>{gen_params['integrity_hash'] if gen_params else 'N/A'}</code><br>
        Result Fingerprint: <code>{sub_hash}</code><br><br>
        Water Environment: <b>{water_selection}</b><br>
        Ship: L={L}m, B={B}m, D={D}m, m={m:,.0f}kg, KG={KG}m<br>
        Material: {material_name} ({rho_ship_val:.0f} kg/m³)<br><br>
        <b>Include both hash codes in your report submission header.</b><br>
        <small>Your marker can verify these hashes in under 60 seconds.</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Enter your Student ID in the sidebar to generate a submission fingerprint.")

# ==============================================================================
# FOOTER
# ==============================================================================
st.divider()
st.markdown("""
<div style='text-align:center; color:#555; font-size:0.8em;'>
⚓ Ship Buoyancy & Stability Simulator v4.0 &nbsp;|&nbsp;
Naval Fluid Mechanics — Educational Tool &nbsp;|&nbsp;
Swinburne University of Technology &nbsp;|&nbsp;
<i>Box-hull approximation — for educational purposes</i>
</div>
""", unsafe_allow_html=True)
