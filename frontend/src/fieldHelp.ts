/** Per-field Arabic descriptions and ready-made example questions, shown in the sidebar. */

export interface FieldHelp {
  /** Arabic translation of the field's English `notes`, shown when the UI language is Arabic. */
  descriptionAr: string
  /** 2-3 example questions about this field, in each language. */
  examples: { en: string[]; ar: string[] }
}

export const FIELD_HELP: Record<string, FieldHelp> = {
  creation_date: {
    descriptionAr: 'تاريخ إدخال النظام 2012-07-02..2015-06-30؛ استخدم هذا الحقل لتصفية التواريخ',
    examples: {
      en: ['How many orders were created in March 2014?', 'Show the number of orders per month in calendar year 2013'],
      ar: ['كم عدد الطلبات اللي انعملت في مارس 2014؟', 'وريني عدد الطلبات شهريًا في سنة 2013'],
    },
  },
  purchase_date: {
    descriptionAr: 'تاريخ أدخله المستخدم، قد يكون بتاريخ سابق؛ لا تستخدمه لتصفية التواريخ',
    examples: {
      en: ['How many purchase dates are missing or invalid?'],
      ar: ['كم عدد تواريخ الشراء المفقودة أو غير الصحيحة؟'],
    },
  },
  calendar_year: {
    descriptionAr: 'السنة التقويمية، من 2012 إلى 2015',
    examples: {
      en: ['Total spend per calendar year', 'How many orders were created in calendar year 2014?'],
      ar: ['إجمالي الإنفاق لكل سنة تقويمية', 'كم عدد الطلبات في سنة 2014 التقويمية؟'],
    },
  },
  calendar_month: {
    descriptionAr: 'الشهر التقويمي، من 1 إلى 12',
    examples: {
      en: ['Show the number of orders per month in calendar year 2013'],
      ar: ['وريني عدد الطلبات شهريًا في سنة 2013'],
    },
  },
  calendar_quarter: {
    descriptionAr: 'الربع التقويمي، من 1 إلى 4 (يناير-مارس = 1)',
    examples: {
      en: ['Which calendar quarter had the highest spending?', 'How many orders were created in Q2 of calendar year 2014?'],
      ar: ['ما هو الربع التقويمي الأعلى إنفاقاً؟', 'كم عدد الطلبات في الربع الثاني التقويمي لسنة 2014؟'],
    },
  },
  year_month: {
    descriptionAr: 'نص بصيغة "2014-03" يمثل السنة والشهر',
    examples: {
      en: ['How many orders were created in March 2014?'],
      ar: ['كم عدد الطلبات اللي انعملت في مارس 2014؟'],
    },
  },
  fiscal_year: {
    descriptionAr: 'السنة المالية، نص مثل "2012-2013" أو "2013-2014" أو "2014-2015"',
    examples: {
      en: ['Total spend per fiscal year?', 'Who are the top 3 suppliers by spend in fiscal year 2014-2015?'],
      ar: ['إجمالي الإنفاق لكل سنة مالية؟', 'من هم أكبر 3 موردين من حيث الإنفاق في السنة المالية 2014-2015؟'],
    },
  },
  fiscal_year_start: {
    descriptionAr: 'سنة بداية السنة المالية: 2012 أو 2013 أو 2014',
    examples: {
      en: ['How many purchase orders were created in fiscal year 2013-2014?'],
      ar: ['كم عدد أوامر الشراء التي أُنشئت في السنة المالية 2013-2014؟'],
    },
  },
  fiscal_quarter: {
    descriptionAr: 'الربع المالي، من 1 إلى 4 (يوليو-سبتمبر = 1، أكتوبر-ديسمبر = 2، يناير-مارس = 3، أبريل-يونيو = 4)',
    examples: {
      en: ['Which fiscal quarter had the highest total spending?'],
      ar: ['ما هو الربع المالي الأعلى إنفاقاً؟'],
    },
  },
  fiscal_quarter_label: {
    descriptionAr: 'نص يجمع السنة والربع المالي، مثل "FY13-14 Q3"',
    examples: {
      en: ['Which fiscal quarter had the highest total spending?'],
      ar: ['ما هو الربع المالي الأعلى إنفاقاً؟'],
    },
  },
  lpa_number: {
    descriptionAr: 'رقم العقد؛ فارغ في 73% من السطور',
    examples: {
      en: ['What share of spending was contract spend (has an LPA number)?'],
      ar: ['ما هي نسبة إنفاق العقود (التي لها رقم LPA)؟'],
    },
  },
  is_contract_spend: {
    descriptionAr: 'صحيح إذا كان للسطر رقم عقد (lpa_number)',
    examples: {
      en: ['What share of spending was contract spend (has an LPA number)?'],
      ar: ['ما هي نسبة إنفاق العقود؟'],
    },
  },
  purchase_order_number: {
    descriptionAr: 'رقم أمر الشراء؛ غير فريد بين الجهات الحكومية المختلفة',
    examples: {
      en: ['How many orders were created in March 2014?'],
      ar: ['كم عدد الطلبات اللي انعملت في مارس 2014؟'],
    },
  },
  requisition_number: {
    descriptionAr: 'رقم طلب الشراء الداخلي؛ فارغ في 96% من السطور',
    examples: {
      en: ['How many lines have a requisition number?'],
      ar: ['كم عدد السطور التي لها رقم طلب شراء؟'],
    },
  },
  department_name: {
    descriptionAr: 'اسم الجهة الحكومية، 111 قيمة مختلفة، مثل "Corrections and Rehabilitation, Department of"',
    examples: {
      en: ['Top 5 departments by spending', 'How much did the Department of Corrections spend in fiscal year 2014-2015?'],
      ar: ['أكبر 5 جهات حكومية من حيث الإنفاق', 'كم صرفت وزارة الإصلاحيات في السنة المالية 2014-2015؟'],
    },
  },
  po_key: {
    descriptionAr: 'معرف فريد للطلب = اسم الجهة + رقم أمر الشراء',
    examples: {
      en: ['Average order value (sum of line totals per order) in fiscal year 2012-2013?'],
      ar: ['متوسط قيمة الطلب في السنة المالية 2012-2013؟'],
    },
  },
  acquisition_type: {
    descriptionAr: 'نوع الشراء: سلع/خدمات تقنية أو غير تقنية أو اتصالات',
    examples: {
      en: ['How is spending split across acquisition types?'],
      ar: ['كيف يتوزع الإنفاق على أنواع الشراء؟'],
    },
  },
  sub_acquisition_type: {
    descriptionAr: 'نوع فرعي للشراء، مثل خدمات شخصية أو عقد طارئ',
    examples: {
      en: ['How much was spent on Emergency Contract purchases?'],
      ar: ['كم تم إنفاقه على عقود الطوارئ؟'],
    },
  },
  acquisition_method: {
    descriptionAr: 'طريقة الشراء، 20 قيمة مثل منافسة غير رسمية أو عقد على مستوى الولاية',
    examples: {
      en: ['How much spend went through CMAS contracts?'],
      ar: ['كم تم الإنفاق عبر عقود CMAS؟'],
    },
  },
  sub_acquisition_method: {
    descriptionAr: 'طريقة شراء فرعية، مثل الأسطول (Fleet)',
    examples: {
      en: ['How much was spent through the Fleet sub-method?'],
      ar: ['كم تم إنفاقه عبر طريقة الأسطول (Fleet)؟'],
    },
  },
  supplier_code: {
    descriptionAr: 'الرقم التعريفي للمورد',
    examples: {
      en: ['Who are the top 3 suppliers by spend in fiscal year 2014-2015?'],
      ar: ['من هم أكبر 3 موردين من حيث الإنفاق في السنة المالية 2014-2015؟'],
    },
  },
  supplier_name: {
    descriptionAr: 'اسم المورد، حوالي 24.7 ألف قيمة مختلفة؛ "Unknown" قيمة بديلة لمورد غير معروف',
    examples: {
      en: ['Who are the top 3 suppliers by spend in fiscal year 2014-2015?'],
      ar: ['من هم أكبر 3 موردين من حيث الإنفاق في السنة المالية 2014-2015؟'],
    },
  },
  supplier_qualifications: {
    descriptionAr: 'مؤهلات المورد، مثل ["CA-MB","CA-SB"]',
    examples: {
      en: ['How much was spent with small businesses in each fiscal year?'],
      ar: ['كم تم الإنفاق مع المنشآت الصغيرة في كل سنة مالية؟'],
    },
  },
  is_small_business: {
    descriptionAr: 'صحيح إذا كان المورد منشأة صغيرة (CA-SB / SB / CA-SBE)',
    examples: {
      en: ['How much was spent with small businesses in each fiscal year?'],
      ar: ['كم تم الإنفاق مع المنشآت الصغيرة في كل سنة مالية؟'],
    },
  },
  is_micro_business: {
    descriptionAr: 'صحيح إذا كان المورد منشأة صغرى (CA-MB)',
    examples: {
      en: ['How much was spent with micro businesses?'],
      ar: ['كم تم الإنفاق مع المنشآت الصغرى؟'],
    },
  },
  is_dvbe: {
    descriptionAr: 'صحيح إذا كان المورد منشأة لأصحاب الهمم من قدامى المحاربين (DVBE)',
    examples: {
      en: ['How much was spent with disabled veteran business enterprises (DVBE) in fiscal year 2014-2015?'],
      ar: ['كم تم الإنفاق مع منشآت قدامى المحاربين من أصحاب الهمم في السنة المالية 2014-2015؟'],
    },
  },
  is_nonprofit: {
    descriptionAr: 'صحيح إذا كان المورد منظمة غير ربحية (CA-NP)',
    examples: {
      en: ['How much was spent with nonprofit suppliers?'],
      ar: ['كم تم الإنفاق مع الموردين غير الربحيين؟'],
    },
  },
  supplier_zip: {
    descriptionAr: 'الرمز البريدي للمورد، 5 أرقام',
    examples: {
      en: ['Which supplier ZIP codes appear most often?'],
      ar: ['ما هي الرموز البريدية الأكثر تكرارًا للموردين؟'],
    },
  },
  supplier_lat: {
    descriptionAr: 'خط عرض موقع المورد',
    examples: { en: ['How many suppliers have location data?'], ar: ['كم عدد الموردين الذين لديهم بيانات موقع؟'] },
  },
  supplier_lon: {
    descriptionAr: 'خط طول موقع المورد',
    examples: { en: ['How many suppliers have location data?'], ar: ['كم عدد الموردين الذين لديهم بيانات موقع؟'] },
  },
  calcard: {
    descriptionAr: 'صحيح إذا تم الدفع ببطاقة الولاية الائتمانية (CalCard)',
    examples: {
      en: ['How much was spent using CalCard, and how many line items?', 'How much did the state spend using CalCard in each fiscal year?'],
      ar: ['كم صرفت الولاية باستخدام بطاقة CalCard في كل سنة مالية؟', 'كم عدد السطور المدفوعة ببطاقة CalCard؟'],
    },
  },
  item_name: {
    descriptionAr: 'اسم الصنف كما هو مكتوب (نص خام)',
    examples: {
      en: ['What are the 5 most frequently ordered line items?'],
      ar: ['ما هي أكثر 5 أصناف تم طلبها؟'],
    },
  },
  item_name_normalized: {
    descriptionAr: 'اسم الصنف بعد التوحيد (حروف صغيرة وبلا علامات ترقيم)؛ استخدمه للتجميع',
    examples: {
      en: ['What are the 5 most frequently ordered line items?'],
      ar: ['ما هي أكثر 5 أصناف تم طلبها؟'],
    },
  },
  item_description: {
    descriptionAr: 'وصف الصنف (نص خام)',
    examples: {
      en: ['How much was spent on toner?'],
      ar: ['كم تم الإنفاق على الحبر (toner)؟'],
    },
  },
  quantity: {
    descriptionAr: 'الكمية المطلوبة',
    examples: {
      en: ['What is the average quantity per line item?'],
      ar: ['ما هو متوسط الكمية لكل سطر؟'],
    },
  },
  unit_price: {
    descriptionAr: 'سعر الوحدة بالدولار الأمريكي',
    examples: {
      en: ['Which lines have the highest unit price?'],
      ar: ['ما هي السطور ذات أعلى سعر وحدة؟'],
    },
  },
  total_price: {
    descriptionAr: 'إجمالي السطر بالدولار، قد يكون سالبًا؛ الإنفاق = مجموع هذا الحقل',
    examples: {
      en: ['Total spend per fiscal year?', 'Which quarter had the highest spending?'],
      ar: ['إجمالي الإنفاق لكل سنة مالية؟', 'ما هو الربع الأعلى إنفاقاً؟'],
    },
  },
  is_negative_amount: {
    descriptionAr: 'صحيح لسطور التسوية/الائتمان (مبلغ سالب)',
    examples: {
      en: ['How much spend comes from negative adjustment lines?'],
      ar: ['كم يبلغ الإنفاق من سطور التسوية السالبة؟'],
    },
  },
  price_mismatch: {
    descriptionAr: 'صحيح إذا كانت الكمية × سعر الوحدة لا يساوي الإجمالي',
    examples: {
      en: ['How many lines have a price mismatch?'],
      ar: ['كم عدد السطور التي فيها تعارض في السعر؟'],
    },
  },
  is_duplicate_row: {
    descriptionAr: 'صحيح إذا كان السطر تكرارًا مطابقًا لسطر آخر؛ يُستبعد من مجاميع الإنفاق وعدد السطور',
    examples: {
      en: ['How many duplicate rows are in the dataset?'],
      ar: ['كم عدد السطور المكررة في البيانات؟'],
    },
  },
  classification_codes: {
    descriptionAr: 'جميع رموز UNSPSC المرتبطة بالسطر',
    examples: {
      en: ['Which UNSPSC segment had the highest spend?'],
      ar: ['ما هو قطاع UNSPSC الأعلى إنفاقاً؟'],
    },
  },
  normalized_unspsc: {
    descriptionAr: 'رمز UNSPSC المكون من 8 أرقام',
    examples: {
      en: ['Which UNSPSC segment had the highest spend, and what was its top supplier?'],
      ar: ['ما هو قطاع UNSPSC الأعلى إنفاقاً، ومن هو أكبر مورد فيه؟'],
    },
  },
  commodity_title: {
    descriptionAr: 'أدق مستوى في تصنيف UNSPSC',
    examples: {
      en: ['What are the top commodities by spend?'],
      ar: ['ما هي أكبر السلع من حيث الإنفاق؟'],
    },
  },
  class_title: {
    descriptionAr: 'مستوى "الفئة" في تصنيف UNSPSC',
    examples: {
      en: ['What are the top UNSPSC classes by spend?'],
      ar: ['ما هي أكبر فئات UNSPSC من حيث الإنفاق؟'],
    },
  },
  family_title: {
    descriptionAr: 'مستوى "العائلة" في تصنيف UNSPSC',
    examples: {
      en: ['What are the top UNSPSC families by spend?'],
      ar: ['ما هي أكبر عائلات UNSPSC من حيث الإنفاق؟'],
    },
  },
  segment_title: {
    descriptionAr: 'أوسع مستوى في تصنيف UNSPSC، 57 قيمة، مثل "Healthcare Services"',
    examples: {
      en: ['Which UNSPSC segment had the highest spend, and what was its top supplier?'],
      ar: ['ما هو قطاع UNSPSC الأعلى إنفاقاً، ومن هو أكبر مورد فيه؟'],
    },
  },
}
