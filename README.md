# AI-Based Dataset Selection and Fusion Recommendation System

An intelligent full-stack analytical application that helps data scientists and ML developers determine if a single CSV dataset is sufficient for training machine learning models or if combining multiple datasets yields an optimized target dataset.

---

## Key Features

1. **Analytical Dashboard**: Side-by-side comparison of Dataset A and B properties (rows, columns, file sizes, memory estimates, duplicate counts).
2. **Explainable Quality Score (0-100)**: Evaluates datasets based on customizable weights for:
   - Missing values
   - Duplicate rows
   - Data completeness
   - Feature diversity
   - Outliers ratio
   - Type consistency
   - Type validity
3. **Deep Compatibility Analysis**: Computes pairwise alignment scores based on Jaccard schemas, fuzzy name matching, type compatibility, column gains, row key overlaps, statistical correlation matrix comparisons, and missing value overlaps.
4. **AI-Based Decision Engine**: Recommends `USE_A`, `USE_B`, or `FUSE` with a confidence score, detailed reasoning bullets, and a net **Fusion Gain Score** representing estimated quality improvement.
5. **Relational Fusion Engine**: Automatically determines and executes optimal fusion:
   - Union (Row Concatenation)
   - Concatenation (Horizontal Side-by-Side)
   - Relational Joins (Left, Right, Inner, Outer)
6. **Multi-Format Exports**: Downloads fused datasets in CSV, Excel (`.xlsx`), and JSON formats.
7. **Professional PDF & HTML Reports**: Downloads ReportLab PDF sheets or prints custom layout HTML pages directly.
8. **Pluggable & Extensible**: Modular design allowing drop-in XGBoost ML recommenders or multi-dataset merges in future versions.

---

## Project Structure

```text
AI_Dataset_Recommendation_System/
├── app.py                     # Central Flask web app entrypoint
├── config.py                  # Project folders, size limits, and quality scoring weights
├── requirements.txt           # Python backend dependencies
├── uploads/                   # Holds raw uploaded CSV datasets
├── dataset_profiles/          # Cached JSON profiles of datasets
├── fused/                     # Exported fused sheets (CSV, Excel, JSON)
├── reports/                   # Compiled ReportLab PDF reports
├── results/                   # Cache metadata for active sessions
├── static/
│   ├── css/
│   │   └── style.css          # Dark/Light theme variable styles
│   └── js/
│       └── main.js            # AJAX handlers, dropzone setups, and Chart.js charts
├── templates/
│   ├── index.html             # Landing and uploader page
│   ├── dashboard.html         # Main workspace dashboard
│   ├── analysis.html          # Deep single-dataset column profile and heatmaps
│   ├── recommendation.html    # Full schema compatibility and Venn overlaps
│   └── report.html            # Printable HTML report template
├── verify_system.py           # Automated integration test script
└── README.md                  # System documentation
```

---

## Installation & Setup

1. **Clone or navigate** to the project workspace directory:
   ```bash
   cd C:\Users\RAMESH\.gemini\antigravity\scratch\AI_Dataset_Recommendation_System
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure you have Python 3.8+ and pip installed).*

3. **Configure scoring weights (optional)**:
   Open `config.py` to change the importance percentage of quality metrics (e.g. increase weight for `outlier_ratio` or decrease `duplicate_rows`).

---

## Running Automated Verification Checks

We provide a regression test suite that generates synthetic datasets, evaluates structural profiles, triggers the recommender heuristics, executes a join merge, and builds a mock PDF report:

```bash
python verify_system.py
```

If successful, you will see a console output:
`=== ALL SYSTEM TESTS COMPLETED SUCCESSFULLY ===`
And new files will be created in `uploads/`, `fused/`, and `reports/`.

---

## Running the Web Application

Start the Flask server locally:

```bash
python app.py
```

Open your web browser and navigate to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Extensibility for XGBoost Recommender

To plug in a trained ML model later:
1. Open `modules/recommender.py`.
2. Define a class `XGBoostRecommender(BaseRecommender)`.
3. In `app.py`, swap `recommender = RuleBasedRecommender()` with `recommender = XGBoostRecommender()`.
Since the inputs/outputs conform to the same interface, no routes or templates need modification!
