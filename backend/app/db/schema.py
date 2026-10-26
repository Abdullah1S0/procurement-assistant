"""Static description of the `purchases` collection, shared by the prompt and the `/api/schema` endpoint."""
import re
from typing import Literal, TypedDict


class FieldInfo(TypedDict):
    name: str
    type: str
    notes: str


FIELDS: list[FieldInfo] = [
    {"name": "creation_date", "type": "Date", "notes": "system entry date 2012-07-02..2015-06-30; USE THIS for time filters"},
    {"name": "purchase_date", "type": "Date|null", "notes": "user-entered, may be back-dated; do not use for time filters"},
    {"name": "calendar_year", "type": "int", "notes": "2012-2015"},
    {"name": "calendar_month", "type": "int", "notes": "1-12"},
    {"name": "calendar_quarter", "type": "int", "notes": "1-4 (Jan-Mar=1)"},
    {"name": "year_month", "type": "string", "notes": '"2014-03"'},
    {"name": "fiscal_year", "type": "string", "notes": '"2012-2013" | "2013-2014" | "2014-2015"'},
    {"name": "fiscal_year_start", "type": "int", "notes": "2012 | 2013 | 2014"},
    {"name": "fiscal_quarter", "type": "int", "notes": "1-4 (Jul-Sep=1, Oct-Dec=2, Jan-Mar=3, Apr-Jun=4)"},
    {"name": "fiscal_quarter_label", "type": "string", "notes": '"FY13-14 Q3"'},
    {"name": "lpa_number", "type": "string|null", "notes": "contract number, 73% null"},
    {"name": "is_contract_spend", "type": "bool", "notes": "lpa_number present"},
    {"name": "purchase_order_number", "type": "string", "notes": "NOT unique across departments"},
    {"name": "requisition_number", "type": "string|null", "notes": "96% null"},
    {"name": "department_name", "type": "string", "notes": '111 values, e.g. "Corrections and Rehabilitation, Department of"'},
    {"name": "po_key", "type": "string", "notes": "department_name|purchase_order_number = unique order id"},
    {"name": "acquisition_type", "type": "string", "notes": "NON-IT Goods | NON-IT Services | IT Goods | IT Services | IT Telecommunications"},
    {"name": "sub_acquisition_type", "type": "string|null", "notes": "e.g. Personal Services, Emergency Contract"},
    {"name": "acquisition_method", "type": "string", "notes": "20 values, e.g. Informal Competitive, Statewide Contract, SB/DVBE Option, NCB, CMAS"},
    {"name": "sub_acquisition_method", "type": "string|null", "notes": "e.g. Fleet"},
    {"name": "supplier_code", "type": "int", "notes": ""},
    {"name": "supplier_name", "type": "string", "notes": '~24.7k values; "Unknown" is a placeholder'},
    {"name": "supplier_qualifications", "type": "array<string>", "notes": 'e.g. ["CA-MB","CA-SB"]'},
    {"name": "is_small_business", "type": "bool", "notes": "CA-SB / SB / CA-SBE"},
    {"name": "is_micro_business", "type": "bool", "notes": "CA-MB"},
    {"name": "is_dvbe", "type": "bool", "notes": "disabled veteran business enterprise"},
    {"name": "is_nonprofit", "type": "bool", "notes": "CA-NP"},
    {"name": "supplier_zip", "type": "string|null", "notes": "5-digit"},
    {"name": "supplier_lat", "type": "float|null", "notes": ""},
    {"name": "supplier_lon", "type": "float|null", "notes": ""},
    {"name": "calcard", "type": "bool", "notes": "paid with the state credit card (CalCard)"},
    {"name": "item_name", "type": "string", "notes": "raw free text"},
    {"name": "item_name_normalized", "type": "string", "notes": "lowercased, punctuation stripped; use for grouping items"},
    {"name": "item_description", "type": "string", "notes": "free text"},
    {"name": "quantity", "type": "float", "notes": ""},
    {"name": "unit_price", "type": "float", "notes": "USD"},
    {"name": "total_price", "type": "float", "notes": "USD line total, can be negative; SPEND = $sum of this"},
    {"name": "is_negative_amount", "type": "bool", "notes": "credit/adjustment line"},
    {"name": "price_mismatch", "type": "bool", "notes": "quantity*unit_price != total_price"},
    {"name": "is_duplicate_row", "type": "bool", "notes": "exact duplicate row; exclude from sums/line counts"},
    {"name": "classification_codes", "type": "array<string>", "notes": "all UNSPSC codes"},
    {"name": "normalized_unspsc", "type": "string", "notes": "8-digit UNSPSC"},
    {"name": "commodity_title", "type": "string", "notes": "UNSPSC most specific"},
    {"name": "class_title", "type": "string", "notes": "UNSPSC class"},
    {"name": "family_title", "type": "string", "notes": "UNSPSC family"},
    {"name": "segment_title", "type": "string", "notes": "UNSPSC broadest, 57 values, e.g. Healthcare Services"},
]

# Fields the `get_distinct_values` tool may be called on (low/medium cardinality, user-facing names).
LOOKUP_FIELDS: tuple[str, ...] = (
    "department_name", "acquisition_type", "sub_acquisition_type", "acquisition_method",
    "sub_acquisition_method", "segment_title", "family_title", "class_title", "commodity_title",
    "supplier_name", "fiscal_year", "fiscal_quarter_label", "item_name_normalized",
)


def schema_for_prompt() -> str:
    """Compact one-line-per-field schema used inside the system prompt."""
    return "\n".join(f"- {f['name']} ({f['type']}){': ' + f['notes'] if f['notes'] else ''}" for f in FIELDS)


# Dataset-level facts (see data/DATA_SCHEMA.md), used to answer meta-questions about the data
# itself ("what date range do you have?") without running a query.
DATASET_META = {
    "date_start": "2012-07-02",
    "date_end": "2015-06-30",
    "fiscal_years": {"en": "2012-13 to 2014-15", "ar": "2012-13 إلى 2014-15"},
    "total_docs": 346_018,
}


def meta_reply(language: Literal["en", "ar"]) -> str:
    """Canned, factual answer to "what data do you have / what date range / what fields" questions,
    built from the known dataset metadata above (no LLM call, no query)."""
    m = DATASET_META
    if language == "ar":
        return (
            f"البيانات المتوفرة هي سجلات شراء لولاية كاليفورنيا، من {m['date_start']} إلى {m['date_end']} "
            f"(السنوات المالية {m['fiscal_years']['ar']}) — {m['total_docs']:,} سطر شراء (كل سطر = بند واحد ضمن طلب شراء). "
            "تشمل الحقول: الجهة الحكومية، المورد، اسم/وصف الصنف، الكمية والسعر والإجمالي، تاريخ الإنشاء، نوع ووسيلة "
            "الشراء، فئة UNSPSC، وأعلام مثل المنشآت الصغيرة وبطاقة CalCard. مثال على سؤال يمكنك طرحه: "
            '"ما هو الربع الأعلى إنفاقاً؟"'
        )
    return (
        f"The data covers California state purchases from {m['date_start']} to {m['date_end']} "
        f"(fiscal years {m['fiscal_years']['en']}) — {m['total_docs']:,} purchase line items (each row is one line "
        "within a purchase order). Fields include department, supplier, item name/description, quantity/unit "
        "price/total, creation date, acquisition type & method, UNSPSC category, and flags like small-business "
        "and CalCard. Try asking, e.g. \"Which quarter had the highest spending?\""
    )


# Heuristic safety net: used only when the forced-tool-call retry (generate_query/plan) also
# fails, to decide whether to answer with `meta_reply()` or a generic "please rephrase" message,
# without ever showing the model's own (possibly hallucinated) text. Deliberately loose /
# typo-tolerant - a false negative just falls through to the safe generic message, never to
# fabricated content.
_META_HINTS = re.compile(
    r"date range|time period|what (data|fields|columns|information)|which fields|coverage|"
    r"sample (row|document)|what.*look like|"
    r"تاريخ|حقول|اعمد|أعمد|عمود|صفوف|صف واحد|اي بيانات|أي بيانات|وش البيانات|عينة|نموذج",
    re.IGNORECASE,
)
# Within a meta question, these additionally ask to *see* real rows/columns (not just coverage).
_SAMPLE_ROWS_HINTS = re.compile(
    r"\brows?\b|\bcolumns?\b|sample (row|document)|example (row|document)|what.*look like|"
    r"صفوف|صف واحد|اعمد|أعمد|عمود|عينة|نموذج",
    re.IGNORECASE,
)


def looks_like_meta_question(text: str) -> bool:
    """True if `text` reads as a question about the dataset itself (coverage, fields, shape)."""
    return bool(_META_HINTS.search(text or ""))


def wants_sample_rows(text: str) -> bool:
    """True if a meta-question is specifically asking to see example rows/columns."""
    return bool(_SAMPLE_ROWS_HINTS.search(text or ""))
