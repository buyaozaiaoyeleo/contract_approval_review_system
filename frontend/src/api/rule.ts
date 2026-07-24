import { get, post, put, del } from '@/utils/request'
import type { ApiResponse } from '@/types/common'
import type { RiskRule, CreateRuleRequest, UpdateRuleRequest, RuleQueryParams } from '@/types/rule'

/** 查询规则列表 */
export function getRiskRules(params?: RuleQueryParams): Promise<ApiResponse<RiskRule[]>> {
  return get<RiskRule[]>('/v1/risks/rules', params as unknown as Record<string, unknown>)
}

/** 创建规则 */
export function createRiskRule(data: CreateRuleRequest): Promise<ApiResponse<RiskRule>> {
  return post<RiskRule>('/v1/risks/rules', data)
}

/** 更新规则 */
export function updateRiskRule(id: number, data: UpdateRuleRequest): Promise<ApiResponse<RiskRule>> {
  return put<RiskRule>(`/v1/risks/rules/${id}`, data)
}

/** 删除规则 */
export function deleteRiskRule(id: number): Promise<ApiResponse<{ status: string; rule_id: number }>> {
  return del<{ status: string; rule_id: number }>(`/v1/risks/rules/${id}`)
}

/** 启用/禁用规则 */
export function toggleRiskRule(id: number, enabled: boolean): Promise<ApiResponse<RiskRule>> {
  return post<RiskRule>(`/v1/risks/rules/${id}/toggle?enabled=${enabled}`)
}