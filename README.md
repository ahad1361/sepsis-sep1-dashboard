# 🏥 SEP-1 Sepsis Hospital Quality Tracker

An interactive dashboard built with **Streamlit** and **Plotly** that visualises U.S. hospital compliance
with the CMS SEP-1 Early Management Bundle for Severe Sepsis/Septic Shock — using real, publicly
available data from CMS Care Compare.

---

## Why SEP-1 Matters

Sepsis is the **single most expensive condition** treated in U.S. hospitals (>$30 billion annually)
and a leading cause of in-hospital mortality. The SEP-1 bundle requires hospitals to administer
antibiotics, obtain blood cultures, and initiate IV fluids **within 3 hours** of sepsis recognition.

CMS incorporates SEP-1 compliance into its **Value-Based Purchasing (VBP)** programme, meaning
hospitals that fall short of national benchmarks face direct Medicare reimbursement reductions.
Hospital executives, quality officers, and payers watch this metric closely.

---

## Dashboard Features

| Feature | Description |
|---------|-------------|
| **KPI Cards** | National average, total reporting hospitals, best and worst states |
| **Interactive Map** | Every hospital plotted as a colour-coded dot (green / amber / red) |
| **State Bar Chart** | All states ranked against the national average dashed reference line |
| **Score Histogram** | Distribution of SEP-1 scores across all hospitals |
| **Top / Bottom 10** | Sortable tables of highest and lowest performing hospitals |
| **Sidebar Filters** | Filter by state, score range, and minimum sample size |
| **CSV Export** | Download any filtered view as a CSV file |
| **Methodology Tab** | Plain-English explanation of the SEP-1 bundle and score limitations |

---

## Screenshot

> _Dashboard screenshot — run the app to see the live version._

```
streamlit run app.py
```

---

## Data Source

**CMS Care Compare — Timely and Effective Care – Hospital**  
<https://data.cms.gov/provider-data/dataset/f31ab9d1-e7fb-4ea8-aff2-e00bdfa7cef3>

The dataset is downloaded automatically on first launch and cached in `data/`. It is updated
quarterly by CMS. Hospital geocoordinates are sourced from the CMS Hospital General Information
dataset; hospitals without exact coordinates are plotted near their state centroid.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/ahad1361/sepsis-sep1-dashboard.git
cd sepsis-sep1-dashboard

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Dashboard

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.  
On first launch it downloads the CMS dataset (~30 MB) — this takes about 15–30 seconds
depending on your connection. Subsequent launches use the cached copy.

---

## Project Structure

```
sepsis-sep1-dashboard/
├── app.py                  # Streamlit entry point
├── requirements.txt        # Python dependencies
├── README.md
├── LICENSE
├── .gitignore
├── data/                   # Auto-downloaded CMS CSVs (git-ignored)
│   └── .gitkeep
└── src/
    ├── __init__.py
    ├── data_loader.py      # CMS data download, caching, and processing
    └── visualizations.py   # All Plotly chart builders
```

---

## Methodology Notes

### Score Calculation
SEP-1 is an **all-or-nothing** bundle: every required element must be completed within the
time window for a case to count as compliant. Partial completion is scored as a failure.

### Score Thresholds Used in This Dashboard
| Tier | Score Range | Interpretation |
|------|-------------|----------------|
| Excellent | ≥ 80% | Consistent protocol adherence |
| Moderate  | 50–79% | Improvement opportunities exist |
| Poor      | < 50% | Significant protocol gaps; CMS scrutiny risk |

### Suppressed Scores
Hospitals with **fewer than 25 eligible cases** per quarter may have suppressed scores
("Not Available") per CMS statistical reliability rules. These appear as grey dots on the map.

### State Averages
State averages are calculated by taking the mean score of all reporting hospitals in that state,
weighted equally regardless of hospital volume.

### Map Coordinates
Exact hospital coordinates come from the CMS Hospital General Information dataset.
Hospitals without exact coordinates are plotted near their state centroid with random jitter
(marked ⚠ in the hover tooltip) — these positions are approximate.

---

## License

MIT — see [LICENSE](LICENSE)

---

## Author

**ahad1361** · [github.com/ahad1361](https://github.com/ahad1361)
