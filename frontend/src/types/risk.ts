export interface RiskResult {
  risk_id: string
  approval_order_id?: string | null
  contract_file_name?: string | null
  rule_id: number | null
  risk_level: string
  risk_description: string
  suggestion: string | null
  source_text: string | null
  field_name: string | null
  is_valid: boolean
}

export interface RiskReport {
  approval_order_id: string
  overall_level: string
  risk_score: number
  summary: string
  statistics: {
    total: number
    high: number
    medium: number
    low: number
  }
  high_risks: RiskResult[]
  medium_risks: RiskResult[]
  low_risks: RiskResult[]
}

export interface RiskQueryParams {
  approval_order_id?: string
  risk_level?: string
  keyword?: string
  contract_file_name?: string
}
