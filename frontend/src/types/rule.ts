/** 风险规则（与后端 RuleResponse 对齐） */
export interface RiskRule {
  id: number
  rule_code: string
  rule_name: string
  rule_category: string
  rule_type: string
  risk_level: string
  priority: number
  is_enabled: boolean
  description: string | null
}

/** 创建规则请求 */
export interface CreateRuleRequest {
  rule_code: string
  rule_name: string
  rule_category: string
  rule_type: string
  rule_config_json: string | null
  priority: number
  risk_level: string
  description: string | null
}

/** 更新规则请求 */
export interface UpdateRuleRequest {
  rule_name?: string
  rule_category?: string
  rule_type?: string
  rule_config_json?: string | null
  priority?: number
  risk_level?: string
  is_enabled?: boolean
  description?: string | null
}

/** 规则查询参数 */
export interface RuleQueryParams {
  category?: string
  enabled_only?: boolean
}