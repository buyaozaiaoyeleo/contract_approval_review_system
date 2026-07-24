export interface ApprovalOrder {
  approval_order_id: string
  title: string
  applicant: string | null
  status: string
  risk_level: string | null
  risk_count: number
  created_at: string | null
  updated_at: string | null
}

export interface ApprovalOrderDetail {
  approval: ApprovalOrder
  documents: ContractDocItem[]
  comments: CommentItem[]
}

export interface ContractDocItem {
  doc_id: string
  file_name: string
  file_type: string
  parse_status: string
  is_scanned: boolean
}

export interface CommentItem {
  comment_id: string
  content: string
  created_at: string | null
}

export interface ApprovalQueryParams {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
}
