import { get, post } from '@/utils/request'
import type { ApiResponse } from '@/types/common'
import type { WorkflowTask, TaskListResponse, WorkflowQueryParams } from '@/types/workflow'

/** 查询任务列表 */
export function getWorkflowTasks(params?: WorkflowQueryParams): Promise<ApiResponse<TaskListResponse>> {
  return get<TaskListResponse>('/v1/tasks', params as unknown as Record<string, unknown>)
}

/** 查询任务状态 */
export function getWorkflowTaskDetail(taskId: string): Promise<ApiResponse<WorkflowTask>> {
  return get<WorkflowTask>(`/v1/tasks/${taskId}`)
}

/** 创建审查任务 */
export function createReviewTask(approvalOrderId: string | number, asyncMode = false): Promise<ApiResponse<{ task_id: string; status: string; message: string }>> {
  return post<{ task_id: string; status: string; message: string }>('/v1/tasks/review', {
    approval_order_id: approvalOrderId,
    async_mode: asyncMode,
  })
}

/** 重试任务 */
export function retryTask(taskId: string): Promise<ApiResponse<{ task_id: string; status: string; message: string }>> {
  return post<{ task_id: string; status: string; message: string }>(`/v1/tasks/${taskId}/retry`)
}
