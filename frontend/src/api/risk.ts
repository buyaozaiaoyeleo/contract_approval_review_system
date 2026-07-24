import { get, post } from '@/utils/request'
import { getStorage } from '@/utils/storage'
import { TOKEN_KEY } from '@/utils/constants'
import type { ApiResponse } from '@/types/common'
import type { RiskQueryParams, RiskReport, RiskResult } from '@/types/risk'

export function getRiskResults(approvalOrderId: string): Promise<ApiResponse<RiskResult[]>> {
  return get<RiskResult[]>(`/v1/risks/results/${approvalOrderId}`)
}

export function getRiskReport(approvalOrderId: string): Promise<ApiResponse<RiskReport>> {
  return get<RiskReport>(`/v1/risks/report/${approvalOrderId}`)
}

export function getRiskResultsByTask(taskId: string): Promise<ApiResponse<RiskResult[]>> {
  return get<RiskResult[]>(`/v1/risks/results/by-task/${taskId}`)
}

export function getAllRiskResults(
  page = 1,
  pageSize = 20,
  filters?: RiskQueryParams,
): Promise<ApiResponse<{ items: RiskResult[]; total: number; page: number; page_size: number }>> {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (filters?.approval_order_id) params['approval_order_id'] = filters.approval_order_id
  if (filters?.risk_level) params['risk_level'] = filters.risk_level
  if (filters?.keyword) params['keyword'] = filters.keyword
  if (filters?.contract_file_name) params['contract_file_name'] = filters.contract_file_name
  return get<{ items: RiskResult[]; total: number; page: number; page_size: number }>(
    '/v1/risks/results',
    params,
  )
}

export function validateRisk(riskId: string, isValid: boolean): Promise<ApiResponse<{ status: string; risk_id: string; is_valid: boolean }>> {
  return post<{ status: string; risk_id: string; is_valid: boolean }>(`/v1/risks/results/${riskId}/validate?is_valid=${isValid}`)
}

export async function downloadRiskReportPdf(approvalOrderId: string): Promise<void> {
  const token = getStorage(TOKEN_KEY)
  const response = await fetch(`/api/v1/risks/report/${approvalOrderId}/download`, {
    method: 'GET',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })

  if (!response.ok) {
    throw new Error('下载风险报告失败')
  }

  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const disposition = response.headers.get('Content-Disposition') || ''
  const utf8NameMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const fallbackNameMatch = disposition.match(/filename="?([^\"]+)"?/i)
  const fileName = utf8NameMatch?.[1]
    ? decodeURIComponent(utf8NameMatch[1])
    : fallbackNameMatch?.[1] || `risk-report-${approvalOrderId}.pdf`

  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}
