import { get, post, del } from '@/utils/request'
import type { ApiResponse, PageResult } from '@/types/common'
import type { ContractDoc, ContractDocDetail, ContractQueryParams, FieldExtraction } from '@/types/contract'

export function getContractDocs(params: ContractQueryParams): Promise<ApiResponse<PageResult<ContractDoc>>> {
  return get<PageResult<ContractDoc>>('/v1/contracts/', params as unknown as Record<string, unknown>)
}

export function uploadContract(formData: FormData): Promise<ApiResponse<ContractDoc>> {
  return post<ContractDoc>('/v1/contracts/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteContractDoc(id: string): Promise<ApiResponse<{ deleted: boolean }>> {
  return del<{ deleted: boolean }>(`/v1/contracts/${id}`)
}

export function parseContractDoc(id: string): Promise<ApiResponse<{ parse_status: string; doc_id: string }>> {
  return post<{ parse_status: string; doc_id: string }>(`/v1/contracts/${id}/parse`)
}

export function getContractDocDetail(id: string): Promise<ApiResponse<ContractDocDetail>> {
  return get<ContractDocDetail>(`/v1/contracts/${id}`)
}

export function getContractPreviewUrl(id: string): Promise<ApiResponse<{ url: string }>> {
  return get<{ url: string }>(`/v1/contracts/${id}/preview`)
}

export function getContractDownloadUrl(id: string): Promise<ApiResponse<{ download_url: string }>> {
  return get<{ download_url: string }>(`/v1/contracts/${id}/download-url`)
}

export function getContractFields(id: string): Promise<ApiResponse<FieldExtraction[]>> {
  return get<FieldExtraction[]>(`/v1/contracts/${id}/fields`)
}

export function reviewContract(id: string): Promise<ApiResponse<ReviewResult>> {
  return post<ReviewResult>(`/v1/contracts/${id}/review`)
}

export interface ReviewResult {
  task_id: string
  status: string
  risk_count: number
  risk_level: string
  has_risks: boolean
}