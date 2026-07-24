import axios, { type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'
import type { ApiResponse } from '@/types/common'
import { getStorage, setStorage, removeStorage } from './storage'
import { TOKEN_KEY, REFRESH_TOKEN_KEY } from './constants'
import { message } from 'ant-design-vue'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

const instance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Mock 数据生成器
const MOCK_AUTH_URLS = ['/v1/auth/login', '/v1/auth/me', '/v1/auth/refresh']

function getMockUserInfo() {
  return {
    id: '1',
    username: 'admin',
    display_name: '系统管理员',
    avatar: null,
    roles: ['admin'],
    permissions: ['*'],
  }
}

function getMockLoginResult() {
  return {
    access_token: 'mock_token_dev_environment',
    refresh_token: 'mock_refresh_token_dev',
    expires_in: 86400,
  }
}

function buildMockData(url: string | undefined): unknown {
  if (!url) return null

  // Auth 端点
  if (url === '/v1/auth/login' || url === '/v1/auth/refresh') {
    return getMockLoginResult()
  }
  if (url === '/v1/auth/me') {
    return getMockUserInfo()
  }

  // Dashboard 统计看板
  if (url.includes('/dashboard/stats')) {
    return {
      total_orders: 326,
      total_reviews: 258,
      total_risks: 365,
      risk_distribution: { high: 45, medium: 120, low: 200 },
      avg_duration: 12.5,
      success_rate: 94.6,
    }
  }
  if (url.includes('/dashboard/trend')) {
    const dates: string[] = []
    const reviewCounts: number[] = []
    const riskCounts: number[] = []
    const now = new Date()
    for (let i = 29; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      dates.push(d.toISOString().slice(0, 10))
      reviewCounts.push(Math.floor(Math.random() * 15) + 3)
      riskCounts.push(Math.floor(Math.random() * 8) + 1)
    }
    return { dates, review_counts: reviewCounts, risk_counts: riskCounts }
  }
  if (url.includes('/dashboard/risk-distribution')) {
    return { high: 45, medium: 120, low: 200 }
  }

  // 审批单列表
  if (url.includes('/approval-orders') || url.includes('/orders')) {
    return {
      items: [
        { id: '1', order_no: 'AP202607001', title: '2024年度采购合同审批', status: 'pending', applicant: '张三', created_at: '2026-07-20 10:00:00' },
        { id: '2', order_no: 'AP202607002', title: 'IT服务外包合同审批', status: 'approved', applicant: '李四', created_at: '2026-07-19 14:30:00' },
        { id: '3', order_no: 'AP202607003', title: '办公室租赁合同续签', status: 'reviewing', applicant: '王五', created_at: '2026-07-18 09:15:00' },
      ],
      total: 3,
    }
  }

  // 风险审查结果
  if (url.includes('/risks/results')) {
    return {
      items: [
        { id: '1', approval_order_id: 'AP202607001', risk_level: 'HIGH', risk_score: 85, risk_type: '合同条款', title: '违约责任条款不明确', status: 'pending', created_at: '2026-07-20 10:30:00' },
        { id: '2', approval_order_id: 'AP202607001', risk_level: 'MEDIUM', risk_score: 60, risk_type: '付款条件', title: '付款周期过长', status: 'confirmed', created_at: '2026-07-20 10:35:00' },
        { id: '3', approval_order_id: 'AP202607002', risk_level: 'LOW', risk_score: 25, risk_type: '文本格式', title: '合同编号格式不一致', status: 'rejected', created_at: '2026-07-19 15:00:00' },
      ],
      total: 3,
    }
  }

  // 风险规则
  if (url.includes('/risks/rules')) {
    return {
      items: [
        { id: '1', name: '违约责任条款检查', rule_type: 'contract_clause', risk_level: 'HIGH', enabled: true, description: '检查合同中是否包含明确的违约责任条款', created_at: '2026-07-15 08:00:00' },
        { id: '2', name: '付款条件检查', rule_type: 'payment_terms', risk_level: 'MEDIUM', enabled: true, description: '检查付款条件是否合理', created_at: '2026-07-15 09:00:00' },
        { id: '3', name: '保密条款检查', rule_type: 'confidentiality', risk_level: 'HIGH', enabled: false, description: '检查保密条款是否完备', created_at: '2026-07-15 10:00:00' },
      ],
      total: 3,
    }
  }

  // 工作流任务
  if (url.includes('/tasks')) {
    return {
      items: [
        { id: '1', task_type: 'contract_review', status: 'success', approval_order_id: 'AP202607001', progress: 100, duration_ms: 12500, created_at: '2026-07-20 10:00:00' },
        { id: '2', task_type: 'contract_review', status: 'running', approval_order_id: 'AP202607002', progress: 60, duration_ms: null, created_at: '2026-07-19 14:30:00' },
        { id: '3', task_type: 'contract_review', status: 'failed', approval_order_id: 'AP202607003', progress: 30, duration_ms: 5000, error_message: 'PDF解析失败', created_at: '2026-07-18 09:15:00' },
      ],
      total: 3,
    }
  }

  // 合同文档
  if (url.includes('/contracts') || url.includes('/documents')) {
    return {
      items: [
        { id: '1', file_name: '2024年度采购合同.pdf', file_size: 2048576, file_type: 'application/pdf', approval_order_id: 'AP202607001', upload_status: 'success', created_at: '2026-07-20 10:00:00' },
        { id: '2', file_name: 'IT服务外包合同.docx', file_size: 1048576, file_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', approval_order_id: 'AP202607002', upload_status: 'success', created_at: '2026-07-19 14:30:00' },
      ],
      total: 2,
    }
  }

  // 系统配置
  if (url.includes('/system/configs')) {
    return [
      { key: 'review.auto_confirm', value: 'false', description: '是否自动确认风险', updated_at: '2026-07-20 08:00:00' },
      { key: 'review.max_retry', value: '3', description: '最大重试次数', updated_at: '2026-07-19 10:00:00' },
      { key: 'review.timeout', value: '300', description: '审查超时时间(秒)', updated_at: '2026-07-18 14:00:00' },
      { key: 'ocr.engine', value: 'paddleocr', description: 'OCR引擎选择', updated_at: '2026-07-15 09:00:00' },
      { key: 'llm.model', value: 'qwen-max', description: '大模型选择', updated_at: '2026-07-15 09:00:00' },
    ]
  }

  // 系统日志
  if (url.includes('/system/logs')) {
    return {
      items: [
        { id: '1', level: 'INFO', module: 'system', message: '系统启动成功', detail: null, created_at: '2026-07-23 08:00:00' },
        { id: '2', level: 'INFO', module: 'workflow', message: '工作流任务创建成功', detail: '{"task_id":"1"}', created_at: '2026-07-23 08:05:00' },
        { id: '3', level: 'WARNING', module: 'risk', message: '风险审查超时', detail: '{"order_id":"AP202607003"}', created_at: '2026-07-23 08:10:00' },
        { id: '4', level: 'ERROR', module: 'contract', message: 'PDF解析失败', detail: '{"file":"test.pdf"}', created_at: '2026-07-23 08:15:00' },
        { id: '5', level: 'INFO', module: 'approval', message: '审批评论回写成功', detail: '{"order_id":"AP202607001"}', created_at: '2026-07-23 08:20:00' },
      ],
      total: 5,
    }
  }

  // 默认返回
  return null
}

function buildMockResponse(url: string | undefined): ApiResponse {
  return {
    code: 0,
    message: 'success',
    data: buildMockData(url),
    trace_id: 'mock',
    timestamp: Date.now(),
  }
}

instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getStorage(TOKEN_KEY)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

instance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const { data } = response
    if (data.code === undefined && data.message === undefined) {
      response.data = {
        code: 0,
        message: 'success',
        data: data as unknown as ApiResponse['data'],
        trace_id: '',
        timestamp: Date.now(),
      }
      return response
    }
    if (data.code === 0) {
      return response
    }
    if (data.code === 401) {
      removeStorage(TOKEN_KEY)
      removeStorage(REFRESH_TOKEN_KEY)
      window.location.href = '/login'
      return Promise.reject(new Error(data.message || '认证失败'))
    }
    message.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message || '请求失败'))
  },
  async (error) => {
    // 开发模式 Mock：当后端不可达时，拦截 auth 请求返回模拟数据
    if (USE_MOCK && error.config && MOCK_AUTH_URLS.includes(error.config.url || '')) {
      const mockData = buildMockResponse(error.config.url)
      return Promise.resolve({
        data: mockData,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: error.config,
      } as AxiosResponse<ApiResponse>)
    }

    if (error.response?.status === 401) {
      // 防止无限重试：已经重试过的请求不再刷新 token
      const retryCount = (error.config as InternalAxiosRequestConfig & { _retryCount?: number })._retryCount || 0
      if (retryCount > 0) {
        // 已经重试过但仍然 401，说明不是 token 过期问题，直接跳转登录
        removeStorage(TOKEN_KEY)
        removeStorage(REFRESH_TOKEN_KEY)
        window.location.replace('/login')
        return Promise.reject(error)
      }

      const refreshToken = getStorage(REFRESH_TOKEN_KEY)
      if (refreshToken && !isRefreshing) {
        isRefreshing = true
        try {
          const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
          const newToken = res.data.data.access_token
          setStorage(TOKEN_KEY, newToken)
          isRefreshing = false
          onRefreshed(newToken)
          if (error.config.headers) {
            error.config.headers.Authorization = `Bearer ${newToken}`
          }
          // 标记已重试，下次不再刷新
          ;(error.config as InternalAxiosRequestConfig & { _retryCount?: number })._retryCount = retryCount + 1
          return instance(error.config)
        } catch {
          isRefreshing = false
          removeStorage(TOKEN_KEY)
          removeStorage(REFRESH_TOKEN_KEY)
          window.location.replace('/login')
          return Promise.reject(error)
        }
      }
      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((token: string) => {
            if (error.config.headers) {
              error.config.headers.Authorization = `Bearer ${token}`
            }
            resolve(instance(error.config))
          })
        })
      }
      removeStorage(TOKEN_KEY)
      removeStorage(REFRESH_TOKEN_KEY)
      window.location.replace('/login')
    }

    // 开发模式 Mock：其他请求后端不可达时静默处理，返回合理的默认数据
    if (USE_MOCK && !error.response) {
      console.warn(`[Mock] 后端不可达，请求被拦截: ${error.config?.url}`)
      const mockData = buildMockResponse(error.config?.url)
      return Promise.resolve({
        data: mockData,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: error.config,
      } as AxiosResponse<ApiResponse>)
    }

    message.error(error.message || '网络错误')
    return Promise.reject(error)
  },
)

export async function get<T = unknown>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await instance.get<ApiResponse<T>>(url, { params, ...config })
  return response.data
}

export async function post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await instance.post<ApiResponse<T>>(url, data, config)
  return response.data
}

export async function put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await instance.put<ApiResponse<T>>(url, data, config)
  return response.data
}

export async function del<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await instance.delete<ApiResponse<T>>(url, config)
  return response.data
}