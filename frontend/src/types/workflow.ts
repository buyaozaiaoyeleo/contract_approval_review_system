import type { TaskStatus } from './common'

/** 工作流任务（与后端 TaskStatusResponse 对齐） */
export interface WorkflowTask {
  task_id: string
  task_status: string
  current_node: string | null
  retry_count: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  node_statuses: Record<string, string> | null
  failed_node: string | null
  file_name: string | null  // 原文档名称
}

/** 任务列表响应（与后端 TaskListResponse 对齐） */
export interface TaskListResponse {
  total: number
  items: WorkflowTask[]
}

/** 任务查询参数 */
export interface WorkflowQueryParams {
  page?: number
  page_size?: number
  status?: string
}