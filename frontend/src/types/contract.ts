/** 合同文档列表项（与后端 DocumentResponse 对齐） */
export interface ContractDoc {
  doc_id: string
  file_name: string
  file_type: string
  file_md5: string | null
  file_size: number | null
  parse_status: string
  is_scanned: boolean
  created_at: string | null
}

/** 合同文档详情（与后端 DocumentResponse 对齐） */
export interface ContractDocDetail extends ContractDoc {
  is_duplicate: boolean
  preview_url: string | null
  parsed_text: string | null
  extracted_fields: Record<string, unknown> | null
  parse_error: string | null
}

export interface FieldExtraction {
  field_name: string
  field_label: string
  value: string | number | null
  confidence: number
  source: string
}

export interface ContractQueryParams {
  page: number
  page_size: number
  approval_order_id?: string
  parse_status?: string
  keyword?: string
}