export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  trace_id: string
  timestamp: number
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PageParams {
  page: number
  page_size: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface SelectOption {
  label: string
  value: string | number
}

export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'blocked' | 'cancelled'

export type ApprovalStatus =
  | 'draft'
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'reviewing'
  | 'reviewed'

export type RiskLevel = 'high' | 'medium' | 'low'

export const RISK_LEVEL_MAP: Record<RiskLevel, { label: string; color: string }> = {
  high: { label: '高', color: '#ff4d4f' },
  medium: { label: '中', color: '#faad14' },
  low: { label: '低', color: '#52c41a' },
}

export const TASK_STATUS_MAP: Record<TaskStatus, { label: string; color: string }> = {
  pending: { label: '待执行', color: '#d9d9d9' },
  running: { label: '执行中', color: '#1677ff' },
  success: { label: '已完成', color: '#52c41a' },
  failed: { label: '失败', color: '#ff4d4f' },
  blocked: { label: '阻塞', color: '#faad14' },
  cancelled: { label: '已取消', color: '#d9d9d9' },
}

export const APPROVAL_STATUS_MAP: Record<ApprovalStatus, { label: string; color: string }> = {
  draft: { label: '草稿', color: '#d9d9d9' },
  pending: { label: '审批中', color: '#1677ff' },
  approved: { label: '已通过', color: '#52c41a' },
  rejected: { label: '已驳回', color: '#ff4d4f' },
  reviewing: { label: '审查中', color: '#faad14' },
  reviewed: { label: '已审查', color: '#52c41a' },
}