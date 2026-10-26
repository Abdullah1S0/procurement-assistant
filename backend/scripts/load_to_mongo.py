"""
Load purchases_clean.csv into MongoDB with proper types + indexes.
Usage:
  pip install pymongo pandas
  python load_to_mongo.py purchases_clean.csv --uri mongodb://localhost:27017 --db procurement --collection purchases
"""
import argparse
import numpy as np
import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING

BOOL_COLS = ["purchase_date_raw_invalid", "is_contract_spend", "is_small_business", "is_micro_business",
             "is_dvbe", "is_nonprofit", "calcard", "is_negative_amount", "price_mismatch", "is_duplicate_row"]
INT_COLS = ["row_id", "calendar_year", "calendar_month", "calendar_quarter", "fiscal_year_start",
            "fiscal_quarter", "supplier_code"]
FLOAT_COLS = ["quantity", "unit_price", "total_price", "supplier_lat", "supplier_lon"]
DATE_COLS = ["creation_date", "purchase_date"]
LIST_COLS = ["supplier_qualifications", "classification_codes"]
STR_COLS_KEEP_ZEROS = ["supplier_zip", "normalized_unspsc", "class_code", "family_code", "segment_code",
                       "purchase_order_number", "requisition_number", "lpa_number"]


def to_docs(df):
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in BOOL_COLS:
        df[c] = df[c].astype(str).str.lower().eq("true")
    for c in INT_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in FLOAT_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in LIST_COLS:
        df[c] = df[c].apply(lambda v: v.split(";") if isinstance(v, str) and v else [])
    df = df.astype(object).where(pd.notna(df), None)
    recs = df.to_dict("records")
    for r in recs:
        for c in DATE_COLS:
            if r[c] is not None:
                r[c] = r[c].to_pydatetime()
        for c in INT_COLS:
            if r[c] is not None:
                r[c] = int(r[c])
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--uri", default="mongodb://localhost:27017")
    ap.add_argument("--db", default="procurement")
    ap.add_argument("--collection", default="purchases")
    ap.add_argument("--batch", type=int, default=20000)
    ap.add_argument("--client", default=None, help=argparse.SUPPRESS)  # testing hook
    a = ap.parse_args()

    client = MongoClient(a.uri)
    col = client[a.db][a.collection]
    col.drop()
    total = 0
    for chunk in pd.read_csv(a.csv, dtype=str, chunksize=a.batch, keep_default_na=True):
        docs = to_docs(chunk)
        col.insert_many(docs, ordered=False)
        total += len(docs)
        print(f"inserted {total:,}")

    for keys in [[("creation_date", ASCENDING)], [("fiscal_year", ASCENDING), ("fiscal_quarter", ASCENDING)],
                 [("calendar_year", ASCENDING), ("calendar_quarter", ASCENDING)], [("year_month", ASCENDING)],
                 [("department_name", ASCENDING)], [("supplier_name", ASCENDING)], [("po_key", ASCENDING)],
                 [("acquisition_type", ASCENDING)], [("acquisition_method", ASCENDING)],
                 [("item_name_normalized", ASCENDING)], [("segment_title", ASCENDING)],
                 [("total_price", DESCENDING)]]:
        col.create_index(keys)
    col.create_index([("item_name", "text"), ("item_description", "text"), ("commodity_title", "text")],
                     name="item_text")
    print("done:", col.count_documents({}), "documents")


if __name__ == "__main__":
    main()
