import { get, put } from '@/utils/request'
import type { ApiResponse, PageResult } from '@/types/common'

export interface SystemConfig {
  key: string
  value: string
  description: string
  updated_at: string
}

export interface DashboardStats {
  total_orders: number
  total_reviews: number
  total_risks: number
  risk_distribution: { high: number; medium: number; low: number }
  avg_duration: number
  success_rate: number
}

export interface DashboardTrend {
  dates: string[]
  review_counts: number[]
  risk_counts: number[]
}

export interface SystemLog {
  id: string
  level: string
  module: string
  message: string
  created_at: string
}

export function getSystemConfigs(): Promise<ApiResponse<SystemConfig[]>> {
  return get<SystemConfig[]>('/v1/system/configs')
}

export function updateSystemConfig(key: string, value: string): Promise<ApiResponse<SystemConfig>> {
  return put<SystemConfig>(`/v1/system/configs/${key}`, { value })
}

export function getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
  return get<DashboardStats>('/v1/dashboard/stats')
}

export function getDashboardTrend(days: number = 30): Promise<ApiResponse<DashboardTrend>> {
  return get<DashboardTrend>('/v1/dashboard/trend', { days })
}

export function getRiskDistribution(): Promise<ApiResponse<DashboardStats['risk_distribution']>> {
  return get<DashboardStats['risk_distribution']>('/v1/dashboard/risk-distribution')
}

export function getSystemLogs(params: { page: number; page_size: number; level?: string }): Promise<ApiResponse<PageResult<SystemLog>>> {
  return get<PageResult<SystemLog>>('/v1/system/logs', params as unknown as Record<string, unknown>)
}