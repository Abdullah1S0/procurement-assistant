# Data

| File | Committed | Purpose |
|---|---|---|
| `DATA_SCHEMA.md` | yes | Field reference + the "golden rules" used in the agent prompt |
| `eval_questions.json` | yes | 16 evaluation questions with reference pipelines and verified expected results |
| `scripts/clean_data.py` | yes | Raw Kaggle CSV → `purchases_clean.csv` |
| `purchases_clean.csv` | **no** (~210 MB, gitignored) | 346,018 cleaned line items, 51 columns |

## Recreate `purchases_clean.csv`

1. Download the Kaggle dataset **"Large Purchases by the State of CA"**
   (https://www.kaggle.com/datasets/sohier/large-purchases-by-the-state-of-ca), e.g.
   `kaggle datasets download -d sohier/large-purchases-by-the-state-of-ca && unzip large-purchases-by-the-state-of-ca.zip`
2. Clean it (Python 3.11+, pandas):
   ```bash
   python data/scripts/clean_data.py "<path to the raw CSV>" data
   ```
   → writes `data/purchases_clean.csv` (346,018 rows + header, 51 columns).
3. Load it into MongoDB (see the main README): `docker compose --profile seed run --rm seed`
   or `python backend/scripts/load_to_mongo.py data/purchases_clean.csv --uri mongodb://localhost:27017`.
