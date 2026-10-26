"""
Clean the raw "Large Purchases by the State of CA" CSV.
Usage: python clean_data.py "<raw.csv>" <out_dir>
Produces: purchases_clean.csv (one row per purchase line item)
"""
import sys, re
import numpy as np
import pandas as pd

raw, out_dir = sys.argv[1], sys.argv[2]
df = pd.read_csv(raw, dtype=str, low_memory=False)

# 1. trim strings, empty -> NaN
for c in df.columns:
    df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True) if c not in ("Location", "Classification Codes") else df[c].str.strip()
    df.loc[df[c] == "", c] = np.nan

dup_mask = df.duplicated(keep="first")

def money(s):
    return pd.to_numeric(s.str.replace(r"[$,]", "", regex=True), errors="coerce")

out = pd.DataFrame()
# 2. dates
cd = pd.to_datetime(df["Creation Date"], format="%m/%d/%Y", errors="coerce")
pdt = pd.to_datetime(df["Purchase Date"], format="%m/%d/%Y", errors="coerce")
bad_pd = pdt.notna() & ((pdt.dt.year < 2000) | (pdt.dt.year > 2016))
out["creation_date"] = cd.dt.strftime("%Y-%m-%d")
out["purchase_date"] = pdt.where(~bad_pd).dt.strftime("%Y-%m-%d")
out["purchase_date_raw_invalid"] = bad_pd

# 3. derived time fields (based on creation_date, as the data dictionary recommends)
out["calendar_year"] = cd.dt.year
out["calendar_month"] = cd.dt.month
out["calendar_quarter"] = cd.dt.quarter
out["year_month"] = cd.dt.strftime("%Y-%m")
out["fiscal_year"] = df["Fiscal Year"]                       # e.g. "2013-2014"
out["fiscal_year_start"] = df["Fiscal Year"].str[:4].astype(int)
out["fiscal_quarter"] = ((cd.dt.month - 7) % 12) // 3 + 1     # FQ1 = Jul-Sep
out["fiscal_quarter_label"] = "FY" + df["Fiscal Year"].str[2:4] + "-" + df["Fiscal Year"].str[7:9] + " Q" + out["fiscal_quarter"].astype(str)

# 4. identifiers
out["lpa_number"] = df["LPA Number"]
out["is_contract_spend"] = df["LPA Number"].notna()
out["purchase_order_number"] = df["Purchase Order Number"]
out["requisition_number"] = df["Requisition Number"]
out["department_name"] = df["Department Name"]
out["po_key"] = df["Department Name"] + "|" + df["Purchase Order Number"]   # PO numbers are NOT unique across departments

# 5. acquisition
out["acquisition_type"] = df["Acquisition Type"]
out["sub_acquisition_type"] = df["Sub-Acquisition Type"]
out["acquisition_method"] = df["Acquisition Method"]
out["sub_acquisition_method"] = df["Sub-Acquisition Method"]

# 6. supplier
out["supplier_code"] = pd.to_numeric(df["Supplier Code"], errors="coerce").astype("Int64")
out["supplier_name"] = df["Supplier Name"]
q = df["Supplier Qualifications"].fillna("")
out["supplier_qualifications"] = q.str.split().str.join(";").replace("", np.nan)
tok = q.str.split()
out["is_small_business"] = tok.apply(lambda t: any(x in ("CA-SB", "SB", "CA-SBE") for x in t))
out["is_micro_business"] = tok.apply(lambda t: "CA-MB" in t)
out["is_dvbe"] = tok.apply(lambda t: any(x in ("CA-DVBE", "CDVBE", "SDVOSB") for x in t))
out["is_nonprofit"] = tok.apply(lambda t: "CA-NP" in t)
z = df["Supplier Zip Code"].str.extract(r"^(\d{1,5})")[0]
out["supplier_zip"] = z.str.zfill(5)
ll = df["Location"].str.extract(r"\(([-\d.]+),\s*([-\d.]+)\)")
out["supplier_lat"] = pd.to_numeric(ll[0], errors="coerce")
out["supplier_lon"] = pd.to_numeric(ll[1], errors="coerce")

# 7. item + amounts
out["calcard"] = df["CalCard"].str.upper().eq("YES")
out["item_name"] = df["Item Name"]
out["item_name_normalized"] = df["Item Name"].str.lower().str.replace(r"[^\w\s/&-]", "", regex=True).str.strip()
out["item_description"] = df["Item Description"]
out["quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
out["unit_price"] = money(df["Unit Price"])
out["total_price"] = money(df["Total Price"])
out["is_negative_amount"] = out["total_price"] < 0
exp = out["quantity"] * out["unit_price"]
out["price_mismatch"] = (exp - out["total_price"]).abs() > np.maximum(1, 0.01 * out["total_price"].abs())
out["is_duplicate_row"] = dup_mask

# 8. UNSPSC classification
out["classification_codes"] = df["Classification Codes"].str.split(r"\s+").str.join(";")
def code(s, n):
    v = pd.to_numeric(s, errors="coerce").astype("Int64").astype(str).replace("<NA>", np.nan)
    return v.str.zfill(n)
out["normalized_unspsc"] = code(df["Normalized UNSPSC"], 8)
out["commodity_title"] = df["Commodity Title"]
out["class_code"] = code(df["Class"], 8)
out["class_title"] = df["Class Title"]
out["family_code"] = code(df["Family"], 8)
out["family_title"] = df["Family Title"]
out["segment_code"] = code(df["Segment"], 8)
out["segment_title"] = df["Segment Title"]

out.insert(0, "row_id", np.arange(1, len(out) + 1))
out.to_csv(f"{out_dir}/purchases_clean.csv", index=False)
print(out.shape)
print(out.isna().sum()[lambda s: s > 0])
print("flags:", {c: int(out[c].sum()) for c in ["purchase_date_raw_invalid","is_negative_amount","price_mismatch","is_duplicate_row"]})
