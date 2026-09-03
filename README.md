# ⚓ Ship Buoyancy & Stability Simulator

**An interactive web-based educational tool for Naval Fluid Mechanics**  
*Developed for engineering education research — Swinburne University of Technology*

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://shipbuoysim.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📖 Overview

This simulator provides an accessible, web-based environment for students to explore the fundamental principles of **naval fluid mechanics**, including buoyancy, hydrostatic forces, hull geometry, and transverse stability. The tool is designed to support **analytical and evaluative learning** by allowing students to investigate how ship parameters and water environment interact to determine vessel performance and safety.

The application was developed as part of an engineering education research project investigating the effectiveness of **simulation-based learning tools** in undergraduate fluid mechanics and naval architecture curricula.

---

## 🎯 Learning Objectives

Upon completing activities using this simulator, students will be able to:

1. **Apply** Archimedes' Principle to calculate buoyant force and predict floating behaviour
2. **Compute** actual draft, freeboard, and block coefficient from ship geometry inputs
3. **Evaluate** transverse stability using the KB → BM → KM → GM chain (box-hull approximation)
4. **Analyse** the effect of water density on draft, buoyant force, displacement, and metacentric height
5. **Interpret** force diagrams and stability visualisations to assess vessel safety
6. **Justify** engineering design decisions based on quantitative stability criteria

---

## ✨ Features

### 🔐 Academic Integrity — Student ID Parameterisation
Each student enters their **Student ID**, which seeds a SHA-256 deterministic random number generator to produce a **unique set of ship parameters** (length, beam, depth, mass, material, centre of gravity). The same ID always produces the same ship — ensuring reproducibility and auditability — while different IDs produce different ships, eliminating the benefit of copying between students.

A **Parameter Hash** and **Result Fingerprint** are generated for each session, which students include in their report submission header for rapid marker verification.

### 🌊 Water Environment Selector
Students can switch between five realistic water environments and observe how buoyancy performance changes:

| Environment | Density (kg/m³) | Context |
|---|---|---|
| Open Ocean (Seawater) | 1025 | Standard naval operations |
| Coastal / Harbour | 1015 | Ports and estuaries |
| Brackish Water | 1005 | River mouths, Baltic Sea |
| Freshwater (River/Lake) | 1000 | Inland waterways |
| Dense Brine (Dead Sea) | 1240 | Hypersaline environments |

### 📐 Full Geometry Inputs
- Length (L), Beam (B), Depth (D) — realistic hull envelope
- Actual draft T computed from box-hull model: $T = V_{sub} / (L \times B)$
- Freeboard, Block Coefficient $C_b$, Draft Ratio
- Nine hull material presets (mild steel, aluminium, GRP, timber, etc.)

### 🎯 GM Stability Analysis (Box-Hull Approximation)
Full metacentric height chain:

$$KB = \frac{T}{2} \quad BM = \frac{B^2}{12T} \quad KM = KB + BM \quad GM = KM - KG$$

Stability classification:
- ✅ **Stable**: GM > 0.15 m
- ⚠️ **Marginally Stable**: 0 < GM ≤ 0.15 m
- ❌ **Unstable**: GM ≤ 0 (vessel will capsize)

### 📊 Visualisations
- **Hull cross-section** — side profile with scaled force arrows (F_b ↑, F_g ↓), draft and freeboard annotations, waterline marker
- **Stability diagram** — front-view showing K, B, G, M points with GM arrow and colour-coded verdict
- **Water environment comparison** — 4-panel bar chart comparing Draft, GM, Buoyant Force, and Block Coefficient across all five water types
- **Numerical comparison table** — all metrics side-by-side for analytical exercises

---

## 🚀 Getting Started

### Run Online (Recommended)
Click the **Streamlit badge** at the top of this page — no installation required. The app runs in any modern web browser on desktop, tablet, or mobile.

### Run Locally
```bash
# 1. Clone the repository
git clone https://github.com/ilkavalchuk/ship-buoyancy-simulator.git
cd ship-buoyancy-simulator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run buoyancy_app.py
```
The app will open automatically at `http://localhost:8501`

---

## 📋 Assignment Usage Guide

1. **Enter your Student ID** in the sidebar — your unique ship parameters will be generated automatically
2. **Record your Parameter Hash** — include this in your report submission header
3. **Select a water environment** to begin your analysis
4. **Record all outputs** from the results panel and figures
5. **Switch water environments** and compare performance using the comparison chart and table
6. **Copy your Result Fingerprint** from the Academic Integrity panel before closing

> ⚠️ Parameters are locked to your Student ID. Using another student's ID constitutes academic misconduct and is detectable by the marker through hash verification.

---

## 🧮 Theoretical Background

### Archimedes' Principle
$$F_b = \rho_w \cdot g \cdot V_{submerged}$$

A vessel floats when the buoyant force equals or exceeds gravitational force:
$$\frac{m}{V_{total}} \leq \rho_w$$

### Effect of Water Density on Draft
$$T \propto \frac{1}{\rho_w}$$

A vessel moving from freshwater (ρ = 1000 kg/m³) to seawater (ρ = 1025 kg/m³) rises approximately **2.4% of its draft** — the physical principle underlying the international **Plimsoll Line** load marking system.

### Stability Criteria
The metacentric height GM is the primary indicator of initial transverse stability. For merchant vessels, classification societies typically require GM ≥ 0.15 m under all loading conditions. A negative GM indicates the vessel's centre of gravity lies above the metacentre, producing an overturning rather than restoring moment when heeled.

> **Note:** This simulator uses a box-hull (rectangular cross-section) approximation. Real vessel stability calculations require full hydrostatic tables, inclining experiments, and free surface corrections. This tool is intended for educational illustration of fundamental principles only.

---

## 🗂️ Repository Structure

```
ship-buoyancy-simulator/
├── buoyancy_app.py      # Main Streamlit application
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| streamlit | 1.35.0 | Web application framework |
| matplotlib | 3.8.4 | Hull and stability visualisations |
| numpy | 1.26.4 | Numerical computation |
| pandas | 2.2.2 | Comparison table rendering |

---

## 📄 Citation

If you use this tool in academic work, please cite:

```
Kavalchuk, I. (2026). Ship Buoyancy & Stability Simulator [Web application].
Swinburne University of Technology.
https://github.com/YOUR_USERNAME/ship-buoyancy-simulator
```

---

## 🔬 Research Context

This tool was developed as part of a research study investigating simulation-based learning in undergraduate engineering education. The academic integrity parameterisation mechanism — in which student-specific parameters are deterministically generated from Student ID using cryptographic hashing — is described in detail in the associated publication.

The water environment comparison feature was specifically designed to support **analytical and evaluative learning outcomes** (Bloom's Taxonomy levels 4–5), moving beyond recall and application toward cross-scenario reasoning and design justification.

---

## 📜 License

This project is licensed under the **MIT License** — free to use, adapt, and redistribute with attribution.

---

## 👤 Author

**Ilya Kavalchuk**  
Lecturer — Robotics and Mechatronics Engineering  
Swinburne University of Technology, Melbourne, Australia  

---

*⚓ Box-hull approximation — for educational purposes | Swinburne University of Technology*
