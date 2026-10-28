import type { Row } from './api'

/** Bilingual, human-readable labels for schema fields, used to replace raw _id/group column
 * headers in the results table (e.g. "group" -> "Month" / "الشهر"). */
const FIELD_LABELS: Record<string, { en: string; ar: string }> = {
  creation_date: { en: 'Date', ar: 'التاريخ' },
  purchase_date: { en: 'Purchase Date', ar: 'تاريخ الشراء' },
  calendar_year: { en: 'Year', ar: 'السنة' },
  calendar_month: { en: 'Month', ar: 'الشهر' },
  calendar_quarter: { en: 'Quarter', ar: 'الربع' },
  year_month: { en: 'Month', ar: 'الشهر' },
  fiscal_year: { en: 'Fiscal Year', ar: 'السنة المالية' },
  fiscal_year_start: { en: 'Fiscal Year', ar: 'السنة المالية' },
  fiscal_quarter: { en: 'Fiscal Quarter', ar: 'الربع المالي' },
  fiscal_quarter_label: { en: 'Fiscal Quarter', ar: 'الربع المالي' },
  department_name: { en: 'Department', ar: 'الجهة الحكومية' },
  po_key: { en: 'Order', ar: 'الطلب' },
  purchase_order_number: { en: 'PO Number', ar: 'رقم أمر الشراء' },
  acquisition_type: { en: 'Acquisition Type', ar: 'نوع الشراء' },
  sub_acquisition_type: { en: 'Acquisition Sub-Type', ar: 'النوع الفرعي للشراء' },
  acquisition_method: { en: 'Acquisition Method', ar: 'طريقة الشراء' },
  sub_acquisition_method: { en: 'Acquisition Sub-Method', ar: 'الطريقة الفرعية للشراء' },
  supplier_code: { en: 'Supplier Code', ar: 'رمز المورد' },
  supplier_name: { en: 'Supplier', ar: 'المورد' },
  supplier_zip: { en: 'Supplier ZIP', ar: 'الرمز البريدي للمورد' },
  is_small_business: { en: 'Small Business', ar: 'منشأة صغيرة' },
  is_micro_business: { en: 'Micro Business', ar: 'منشأة صغرى' },
  is_dvbe: { en: 'DVBE', ar: 'منشأة قدامى المحاربين' },
  is_nonprofit: { en: 'Nonprofit', ar: 'منظمة غير ربحية' },
  is_contract_spend: { en: 'Contract Spend', ar: 'إنفاق العقود' },
  calcard: { en: 'CalCard', ar: 'بطاقة CalCard' },
  item_name: { en: 'Item', ar: 'الصنف' },
  item_name_normalized: { en: 'Item', ar: 'الصنف' },
  item_description: { en: 'Item Description', ar: 'وصف الصنف' },
  is_negative_amount: { en: 'Adjustment', ar: 'تسوية' },
  is_duplicate_row: { en: 'Duplicate', ar: 'سطر مكرر' },
  normalized_unspsc: { en: 'UNSPSC Code', ar: 'رمز UNSPSC' },
  commodity_title: { en: 'Commodity', ar: 'السلعة' },
  class_title: { en: 'UNSPSC Class', ar: 'فئة UNSPSC' },
  family_title: { en: 'UNSPSC Family', ar: 'عائلة UNSPSC' },
  segment_title: { en: 'UNSPSC Segment', ar: 'قطاع UNSPSC' },
}

function fieldRef(value: unknown): string | null {
  return typeof value === 'string' && value.startsWith('$') ? value.slice(1) : null
}

/** The field(s) a pipeline's (last) $group stage grouped by: either a single field name (scalar
 * _id), or a map of {sub-key -> field name} for a compound _id like {year: "$calendar_year"}. */
function groupedFields(pipeline: Row[]): { scalar: string | null; compound: Record<string, string> } {
  for (let i = pipeline.length - 1; i >= 0; i--) {
    const group = pipeline[i]?.['$group'] as Record<string, unknown> | undefined
    if (!group || !('_id' in group)) continue
    const id = group['_id']
    const scalar = fieldRef(id)
    if (scalar) return { scalar, compound: {} }
    if (id && typeof id === 'object' && !Array.isArray(id)) {
      const compound: Record<string, string> = {}
      for (const [key, val] of Object.entries(id as Record<string, unknown>)) {
        const field = fieldRef(val)
        if (field) compound[key] = field
      }
      return { scalar: null, compound }
    }
    return { scalar: null, compound: {} }
  }
  return { scalar: null, compound: {} }
}

/** A readable header for one results-table column, given the pipeline it came from. Falls back
 * to the raw column name when the field isn't recognised (e.g. a measure like "spend"/"lines"). */
export function columnLabel(column: string, pipeline: Row[], lang: 'en' | 'ar'): string {
  const { scalar, compound } = groupedFields(pipeline)
  const field = column === '_id' ? scalar : compound[column] ?? null
  if (field && FIELD_LABELS[field]) return FIELD_LABELS[field][lang]
  if (column === '_id') return lang === 'ar' ? 'التصنيف' : 'Group'
  return column
}
