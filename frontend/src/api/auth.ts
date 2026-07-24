import { get, post } from '@/utils/request'
import type { ApiResponse } from '@/types/common'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  refresh_token: string
  expires_in: number
}

export interface UserInfo {
  id: string
  username: string
  display_name: string
  avatar: string | null
  roles: string[]
  permissions: string[]
}

export function login(data: LoginParams): Promise<ApiResponse<LoginResult>> {
  return post<LoginResult>('/v1/auth/login', data)
}

export function refreshToken(refreshToken: string): Promise<ApiResponse<LoginResult>> {
  return post<LoginResult>('/v1/auth/refresh', { refresh_token: refreshToken })
}

export function getCurrentUser(): Promise<ApiResponse<UserInfo>> {
  return get<UserInfo>('/v1/auth/me')
}