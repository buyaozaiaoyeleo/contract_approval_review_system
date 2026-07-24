import { get, post } from '@/utils/request'
import type { ApiResponse } from '@/types/common'
import type { ApprovalOrder, ApprovalOrderDetail, ApprovalQueryParams } from '@/types/approval'

export function getApprovalOrders(params: ApprovalQueryParams): Promise<ApiResponse<{ items: ApprovalOrder[]; total: number; page: number; page_size: number }>> {
  return get<{ items: ApprovalOrder[]; total: number; page: number; page_size: number }>('/v1/approvals', params as unknown as Record<string, unknown>)
}

export function getApprovalOrderDetail(id: string): Promise<ApiResponse<ApprovalOrderDetail>> {
  return get<ApprovalOrderDetail>(`/v1/approvals/${id}`)
}

export function syncApproval(
  id: string,
  autoReview = true,
  asyncMode = true,
): Promise<ApiResponse<{
  status: string
  title: string | null
  approval_order_id: string
  auto_review: boolean
  task_id?: string
  review_status?: string
  review_message?: string
  reused_task?: boolean
  risk_count?: number
  risk_level?: string
  has_risks?: boolean
}>> {
  return post(`/v1/approvals/${id}/sync`, {
    auto_review: autoReview,
    async_mode: asyncMode,
  })
}

export function reviewApproval(
  id: string,
  asyncMode = true,
): Promise<ApiResponse<{ task_id: string; status: string; risk_count?: number; risk_level?: string; has_risks?: boolean }>> {
  return post<{ task_id: string; status: string; risk_count?: number; risk_level?: string; has_risks?: boolean }>(`/v1/approvals/${id}/review`, {
    async_mode: asyncMode,
  })
}
