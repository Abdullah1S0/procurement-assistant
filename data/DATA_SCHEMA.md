# Procurement Dataset: Schema and Rules

Source: "Large Purchases by the State of CA" (Kaggle), fiscal years 2012-13 to 2014-15.
After cleaning: **346,018 documents** in MongoDB collection `procurement.purchases`.
**One document = one purchase line item**, not one order.

## Golden rules (put these in the agent's system prompt)

1. **Counting orders**: `purchase_order_number` is NOT unique across departments. Count orders as **distinct `po_key`** (`department_name|purchase_order_number`).
   Pattern: `[{$match:...},{$group:{_id:"$po_key"}},{$count:"orders"}]`. 204,002 orders in total.
2. **Dates**: use `creation_date` (a real Date) or the derived fields below. Don't use `purchase_date` for time filters, because it can be back-dated.
3. **Fiscal year** runs from July 1 to June 30. `fiscal_quarter` 1 = Jul–Sep, 2 = Oct–Dec, 3 = Jan–Mar, 4 = Apr–Jun.
   "Quarter" without qualification: answer with the fiscal quarter and also state the calendar equivalent.
4. **Spend** = `$sum` of `total_price` (USD, excludes tax and shipping). Add `{is_duplicate_row:false}` to spend and line-count queries.
5. **Negative amounts** (1,438 lines) are adjustments or credits. They are included in spend sums by default; mention them when relevant.
6. **Outliers**: Health Care Services has single lines worth billions (max $7.34B). Any spend ranking is dominated by Medi-Cal health plans. Say so when it matters.
7. **Items**: group "most ordered items" by `item_name_normalized` (lowercased). Free-text item names are messy: "ew" = expert witness, plus typos such as "pharmacuetical". For topic searches, use `$regex` (case-insensitive) or the text index on `item_name`, `item_description` and `commodity_title`.
8. **Supplier "Unknown"**: a placeholder supplier name with ~$3B in spend. Mention it when it shows up in rankings.
9. **Department names** are in the format `"<Name>, Department of"` (e.g. `"Corrections and Rehabilitation, Department of"`). Use a case-insensitive `$regex` when the user gives a partial name.

## Fields

| Field | Type | Notes |
|---|---|---|
| row_id | int | 1..346018 |
| creation_date | Date | system entry date, 2012-07-02 → 2015-06-30 (**use this**) |
| purchase_date | Date \| null | user-entered; 5% missing; 282 impossible values (years 1911, 6070…) set to null |
| purchase_date_raw_invalid | bool | true where the raw purchase date was impossible |
| calendar_year | int | 2012–2015 |
| calendar_month | int | 1–12 |
| calendar_quarter | int | 1–4 (Jan–Mar = 1) |
| year_month | string | "2014-03" |
| fiscal_year | string | "2012-2013", "2013-2014", "2014-2015" |
| fiscal_year_start | int | 2012, 2013, 2014 |
| fiscal_quarter | int | 1–4 (Jul–Sep = 1) |
| fiscal_quarter_label | string | "FY13-14 Q3" |
| lpa_number | string \| null | contract number; 73% null |
| is_contract_spend | bool | lpa_number present |
| purchase_order_number | string | not unique across departments |
| requisition_number | string \| null | 96% null |
| department_name | string | 111 distinct |
| po_key | string | `department_name|purchase_order_number` = unique order id |
| acquisition_type | string | `NON-IT Goods`, `NON-IT Services`, `IT Goods`, `IT Services`, `IT Telecommunications` |
| sub_acquisition_type | string \| null | e.g. Personal Services, Emergency Contract, Public Works |
| acquisition_method | string | 20 values: Informal Competitive, Statewide Contract, SB/DVBE Option, Formal Competitive, WSCA/Coop, Emergency Purchase, NCB, CMAS, Fair and Reasonable, … |
| sub_acquisition_method | string \| null | e.g. Fleet, Prison Industry Authority (PIA) |
| supplier_code | int | |
| supplier_name | string | ~24.7k distinct |
| supplier_qualifications | array<string> | e.g. ["CA-MB","CA-SB"]; empty = none |
| is_small_business | bool | has CA-SB / SB / CA-SBE |
| is_micro_business | bool | CA-MB |
| is_dvbe | bool | disabled veteran business (CA-DVBE / CDVBE / SDVOSB) |
| is_nonprofit | bool | CA-NP |
| supplier_zip | string \| null | 5-digit, leading zeros restored |
| supplier_lat, supplier_lon | float \| null | parsed from raw Location |
| calcard | bool | paid with the state credit card |
| item_name | string | raw |
| item_name_normalized | string | lowercased, punctuation stripped; use for grouping |
| item_description | string | |
| quantity | float | |
| unit_price | float | USD |
| total_price | float | USD, can be negative |
| is_negative_amount | bool | |
| price_mismatch | bool | quantity × unit_price ≠ total_price (617 lines) |
| is_duplicate_row | bool | exact duplicate of an earlier row (2,101); exclude from sums |
| classification_codes | array<string> | all UNSPSC codes on the order line |
| normalized_unspsc | string | 8-digit UNSPSC |
| commodity_title, class_title, family_title, segment_title | string | UNSPSC hierarchy, most specific → broadest |
| class_code, family_code, segment_code | string | 8-digit codes |

## Quick facts (verified)

- Orders per fiscal year: 2012-13 = 66,238 · 2013-14 = 68,749 · 2014-15 = 69,015
- Spend per fiscal year: $61.88B · $42.46B · $46.84B
- Highest-spend quarter: **FY14-15 Q4 (Apr–Jun 2015) = $28.80B**
- Most frequent items: medical supplies (3,839 lines), contract (3,103), toner (1,899), ew (1,606), office supplies (1,571)
- Top department by spend: Health Care Services ($99.76B)
- Spend by type: NON-IT Services $140.6B · NON-IT Goods $4.56B · IT Services $4.45B · IT Goods $1.57B
- Contract spend share: 2.64% · CalCard: 5,353 lines, $28.56M

See `eval_questions.json` for reference pipelines and exact expected results.
