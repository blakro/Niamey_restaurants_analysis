# 🍽️ Niamey Restaurant Market Analysis

> **Can data help identify the best restaurant concept to open in Niamey, Niger?**
> This project analyzes 490+ Google Maps listings to answer that question.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas)](https://pandas.pydata.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-SQL-FFC600)](https://duckdb.org)
[![Folium](https://img.shields.io/badge/Maps-Folium-77B829)](https://python-visualization.github.io/folium/)
[![Jupyter](https://img.shields.io/badge/Notebooks-Jupyter-F37626?logo=jupyter)](https://jupyter.org)

---

## 🗺️ Live Map

👉 **[Open interactive map](docs/map_PORTFOLIO.html)**
_(markers · density heatmap · quality heatmap · DBSCAN clusters)_

---

## 🔑 Key Findings

| # | Finding |
|---|---------|
| 1 | **72%** of restaurants fall in the 3.5–4.9 star range — overall positive market perception |
| 2 | **~78 restaurants** display 5.0★ but with ≤5 reviews — Bayesian scoring corrects this bias |
| 3 | **Median review count is 3** — 60% of establishments have <10 reviews (highly informal market) |
| 4 | Restaurants with a website score **+0.15 pts** higher on average (Mann-Whitney, p<0.05) |
| 5 | **Grillades / BBQ** is the #1 market opportunity (MCDA score: 0.771) |

---

## 🎯 Top Market Opportunities (MCDA Model)

| Rank | Category | Score | Market Share | Avg ★ |
|------|----------|-------|-------------|-------|
| 1 | **Grillades / BBQ** | `0.771` | 2.0% | 4.11 |
| 2 | **Restaurant halal** | `0.737` | 0.8% | 4.07 |
| 3 | **Pizzeria** | `0.670` | 1.4% | 4.12 |

> **MCDA model weights:** Quality 35% · Market scarcity 30% · Demand signal 20% · Digital gap 15%

---

## 📊 Dashboard

![Portfolio Dashboard](data/processed/figures/06_portfolio_dashboard.png)

---

## 📁 Repository Structure

```
niamey-restaurants-analysis/
├── README.md
├── data/
│   ├── raw/                    ← Original CSV (Google Maps export)
│   └── processed/
│       ├── restaurants_clean.csv
│       ├── restaurants_geo.csv
│       ├── market_gap.csv
│       ├── mcda_report.csv
│       ├── figures/            ← All generated charts
│       └── maps/               ← Folium HTML maps
├── notebooks/
│   ├── 01_cleaning.ipynb       ← Data cleaning + Bayesian score
│   ├── 02_eda.ipynb            ← EDA + DuckDB SQL + stats tests
│   ├── 03_geospatial.ipynb     ← Plus Code geocoding + Folium maps
│   └── 04_market_gaps.ipynb    ← MCDA model + recommendations
└── docs/
    └── map_PORTFOLIO.html      ← GitHub Pages interactive map
```

---

## ⚙️ Setup

```bash
git clone https://github.com/blakro/Niamey_restaurants_analysis
cd Niamey_restaurants_analysis
pip install -r requirements.txt
jupyter lab
```

---

## 🛠️ Stack

`Python 3.11` · `Pandas` · `DuckDB (SQL)` · `Matplotlib / Seaborn` ·
`Folium` · `openlocationcode` · `scikit-learn (DBSCAN)` · `SciPy`

---

*Data source: Google Maps export · Niamey, Niger*