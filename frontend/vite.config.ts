import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const USE_MOCK = false

// ============================================================
//  状态化 Mock 数据存储（所有 CRUD 操作都会修改这些数据）
// ============================================================

// -- 合同文档 --
const mockDocs = [
  { doc_id: 'doc-001', file_name: '2024年度采购合同.pdf', file_type: 'pdf', file_md5: 'a1b2c3', file_size: 2048576, parse_status: 'completed', is_scanned: false, created_at: '2026-07-20 10:00:00' },
  { doc_id: 'doc-002', file_name: 'IT服务外包合同.docx', file_type: 'word', file_md5: 'd4e5f6', file_size: 1048576, parse_status: 'pending', is_scanned: false, created_at: '2026-07-19 14:30:00' },
  { doc_id: 'doc-003', file_name: '办公室租赁合同.pdf', file_type: 'pdf', file_md5: 'g7h8i9', file_size: 3096576, parse_status: 'failed', is_scanned: true, created_at: '2026-07-18 09:15:00' },
]
let docIdCounter = 4

// -- 风险规则 --
const mockRules = [
  { id: 1, rule_code: 'R001', rule_name: '违约责任条款检查', rule_category: 'clause', rule_type: 'llm', risk_level: 'HIGH', priority: 1, is_enabled: true, description: '检查合同中是否包含明确的违约责任条款和违约金标准' },
  { id: 2, rule_code: 'R002', rule_name: '付款条件检查', rule_category: 'amount', rule_type: 'field', risk_level: 'MEDIUM', priority: 2, is_enabled: true, description: '检查付款周期是否超过行业惯例60天，超过则触发风险' },
  { id: 3, rule_code: 'R003', rule_name: '保密条款检查', rule_category: 'clause', rule_type: 'llm', risk_level: 'HIGH', priority: 3, is_enabled: false, description: '检查保密条款是否覆盖知识产权、数据安全等内容' },
  { id: 4, rule_code: 'R004', rule_name: '合同期限检查', rule_category: 'term', rule_type: 'field', risk_level: 'MEDIUM', priority: 4, is_enabled: true, description: '检查合同期限是否超过5年，长期合同需额外审批' },
  { id: 5, rule_code: 'R005', rule_name: '签约主体资质检查', rule_category: 'subject', rule_type: 'composite', risk_level: 'HIGH', priority: 5, is_enabled: true, description: '检查签约方是否在工商登记系统中可查，是否存在经营异常' },
  { id: 6, rule_code: 'R006', rule_name: '合规性检查', rule_category: 'compliance', rule_type: 'llm', risk_level: 'LOW', priority: 6, is_enabled: true, description: '检查合同条款是否符合最新法律法规要求' },
]
let ruleIdCounter = 7

// -- 风险审查结果 --
const mockResults = [
  { risk_id: 'r1', rule_id: 1, risk_level: 'HIGH', risk_description: '违约责任条款缺失，未明确违约赔偿标准', suggestion: '建议在第8条增加具体违约金比例', source_text: '如一方违约，应承担相应责任', field_name: '违约责任', is_valid: false },
  { risk_id: 'r2', rule_id: 2, risk_level: 'HIGH', risk_description: '保密条款未覆盖知识产权保护内容', suggestion: '建议增加知识产权归属和保护条款', source_text: '双方应对商业秘密保密', field_name: '保密条款', is_valid: false },
  { risk_id: 'r3', rule_id: 3, risk_level: 'MEDIUM', risk_description: '付款周期为90天，超出行业惯例', suggestion: '建议将付款周期缩短至60天以内', source_text: '甲方应在收到发票后90日内付款', field_name: '付款条件', is_valid: false },
  { risk_id: 'r4', rule_id: 4, risk_level: 'MEDIUM', risk_description: '争议解决条款未明确管辖法院', suggestion: '建议补充约定管辖法院为乙方所在地', source_text: '双方协商不成的，可提起诉讼', field_name: '争议解决', is_valid: false },
  { risk_id: 'r5', rule_id: 5, risk_level: 'MEDIUM', risk_description: '合同生效条件存在歧义，可能影响执行', suggestion: '建议明确写明合同自双方签字盖章之日起生效', source_text: '合同自审批通过后生效', field_name: '合同生效', is_valid: false },
  { risk_id: 'r6', rule_id: 6, risk_level: 'LOW', risk_description: '合同编号格式不统一，建议规范化', suggestion: '建议统一使用公司标准合同编号规则', source_text: '合同编号：HT-2026-001', field_name: '合同编号', is_valid: false },
]

// -- 系统配置 --
const mockConfigs = [
  { key: 'review.auto_confirm', value: 'false', description: '是否自动确认风险', updated_at: '2026-07-20 08:00:00' },
  { key: 'review.max_retry', value: '3', description: '最大重试次数', updated_at: '2026-07-19 10:00:00' },
  { key: 'review.timeout', value: '300', description: '审查超时时间(秒)', updated_at: '2026-07-18 14:00:00' },
]

// -- 系统日志 --
const mockLogs = [
  { id: '1', level: 'INFO', module: 'system', message: '系统启动成功', created_at: '2026-07-23 08:00:00' },
  { id: '2', level: 'INFO', module: 'workflow', message: '工作流任务创建', created_at: '2026-07-23 08:05:00' },
  { id: '3', level: 'WARNING', module: 'risk', message: '风险审查超时', created_at: '2026-07-23 08:10:00' },
  { id: '4', level: 'ERROR', module: 'contract', message: 'PDF解析失败', created_at: '2026-07-23 08:15:00' },
]

// ============================================================
//  Mock 数据路由（根据 URL + method 返回响应）
// ============================================================
function buildMockData(url: string, method: string): unknown {
  // -- Auth --
  if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
    return { access_token: 'mock_token_dev', refresh_token: 'mock_refresh_dev', expires_in: 86400 }
  }
  if (url.includes('/auth/me')) {
    return { id: '1', username: 'admin', display_name: '系统管理员', avatar: null, roles: ['admin'], permissions: ['*'] }
  }

  // -- Dashboard --
  if (url.includes('/dashboard/stats')) {
    return { total_orders: 326, total_reviews: 258, total_risks: mockResults.length, risk_distribution: { high: 45, medium: 120, low: 200 }, avg_duration: 12.5, success_rate: 94.6 }
  }
  if (url.includes('/dashboard/trend')) {
    const dates: string[] = []; const rc: number[] = []; const risk: number[] = []
    for (let i = 29; i >= 0; i--) {
      const d = new Date(); d.setDate(d.getDate() - i)
      dates.push(d.toISOString().slice(0, 10))
      rc.push(Math.floor(Math.random() * 15) + 3)
      risk.push(Math.floor(Math.random() * 8) + 1)
    }
    return { dates, review_counts: rc, risk_counts: risk }
  }
  if (url.includes('/dashboard/risk-distribution')) {
    return { high: 45, medium: 120, low: 200 }
  }

  // -- 审批单列表 --
  if (url.includes('/approvals')) {
    return [
      { approval_order_id: 1, title: '2024年度采购合同审批', applicant: '张三', status: 'pending', created_at: '2026-07-20 10:00:00', updated_at: '2026-07-20 10:00:00' },
      { approval_order_id: 2, title: 'IT服务外包合同审批', applicant: '李四', status: 'approved', created_at: '2026-07-19 14:30:00', updated_at: '2026-07-19 16:00:00' },
      { approval_order_id: 3, title: '办公室租赁合同续签', applicant: '王五', status: 'pending', created_at: '2026-07-18 09:15:00', updated_at: '2026-07-18 09:15:00' },
      { approval_order_id: 4, title: '设备采购合同', applicant: '赵六', status: 'rejected', created_at: '2026-07-17 11:00:00', updated_at: '2026-07-17 15:30:00' },
      { approval_order_id: 5, title: '广告投放合同', applicant: '张三', status: 'approved', created_at: '2026-07-16 08:45:00', updated_at: '2026-07-16 09:00:00' },
    ]
  }

  // -- 风险审查报告（按审批单ID） --
  if (url.includes('/risks/report/')) {
    return {
      approval_order_id: 1,
      overall_level: 'MEDIUM',
      risk_score: 65,
      summary: '该合同存在中等风险，主要集中在违约责任条款和付款条件方面，建议重点关注。',
      statistics: { total: mockResults.length, high: 2, medium: 3, low: 1 },
      high_risks: mockResults.filter((r) => r.risk_level === 'HIGH'),
      medium_risks: mockResults.filter((r) => r.risk_level === 'MEDIUM'),
      low_risks: mockResults.filter((r) => r.risk_level === 'LOW'),
    }
  }

  // -- 风险结果确认/驳回（POST /v1/risks/results/{risk_id}/validate） --
  if (url.includes('/risks/results/') && url.includes('/validate')) {
    const riskId = url.split('/').filter((s) => s === 'validate' ? false : true).pop()?.split('?')[0] || ''
    const risk = mockResults.find((r) => r.risk_id === riskId)
    if (risk) {
      risk.is_valid = !risk.is_valid
    }
    return { risk_id: riskId, is_valid: risk?.is_valid ?? false }
  }

  // -- 风险结果列表（GET /v1/risks/results?approval_order_id=1） --
  if (url.includes('/risks/results') && !url.includes('/validate')) {
    return mockResults
  }

  // -- 风险规则：启用/禁用（POST /v1/risks/rules/{id}/toggle） --
  if (url.includes('/risks/rules/') && url.includes('/toggle')) {
    const ruleId = parseInt(url.split('/').filter(Boolean).pop()?.split('?')[0] || '0', 10)
    const rule = mockRules.find((r) => r.id === ruleId)
    if (rule) {
      rule.is_enabled = !rule.is_enabled
    }
    return rule || null
  }

  // -- 风险规则：删除（DELETE /v1/risks/rules/{id}） --
  if (method === 'DELETE' && url.includes('/risks/rules/')) {
    const ruleId = parseInt(url.split('/').filter(Boolean).pop()?.split('?')[0] || '0', 10)
    const idx = mockRules.findIndex((r) => r.id === ruleId)
    if (idx !== -1) {
      mockRules.splice(idx, 1)
    }
    return { deleted: true }
  }

  // -- 风险规则：更新/创建（PUT or POST /v1/risks/rules） --
  if ((method === 'PUT' || method === 'POST') && url.includes('/risks/rules') && !url.includes('/toggle')) {
    return { id: ruleIdCounter++, rule_code: 'R007', rule_name: '新规则', rule_category: 'clause', rule_type: 'llm', risk_level: 'MEDIUM', priority: 7, is_enabled: true, description: '新创建的规则' }
  }

  // -- 风险规则详情（GET /v1/risks/rules/{id}） --
  if (url.includes('/risks/rules/') && !url.includes('/toggle')) {
    const ruleId = parseInt(url.split('/').filter(Boolean).pop()?.split('?')[0] || '0', 10)
    return mockRules.find((r) => r.id === ruleId) || mockRules[0]
  }

  // -- 风险规则列表 --
  if (url.includes('/risks/rules')) {
    return mockRules
  }

  // -- 工作流任务列表（公用数据源） --
  const taskItems = [
    { task_id: 'task-001', task_status: 'success', current_node: 'write_comment', retry_count: 0, error_message: null, started_at: '2026-07-20 10:00:00', completed_at: '2026-07-20 10:00:15', duration_ms: 15200 },
    { task_id: 'task-002', task_status: 'running', current_node: 'risk_review', retry_count: 0, error_message: null, started_at: '2026-07-20 10:01:00', completed_at: null, duration_ms: null },
    { task_id: 'task-003', task_status: 'failed', current_node: 'parse_document', retry_count: 2, error_message: 'PDF解析失败：文件格式不支持', started_at: '2026-07-20 09:45:00', completed_at: '2026-07-20 09:45:05', duration_ms: 5000 },
    { task_id: 'task-004', task_status: 'blocked', current_node: 'download_contract', retry_count: 3, error_message: '合同文件下载失败：MinIO连接超时', started_at: '2026-07-20 09:30:00', completed_at: null, duration_ms: null },
    { task_id: 'task-005', task_status: 'pending', current_node: null, retry_count: 0, error_message: null, started_at: null, completed_at: null, duration_ms: null },
  ]

  // -- 工作流任务详情 --
  if (url.includes('/tasks/') && !url.includes('/tasks/review') && !url.includes('/retry')) {
    const taskId = url.split('/').pop()?.split('?')[0]
    return taskItems.find((t) => t.task_id === taskId) || taskItems[0]
  }

  // -- 工作流任务列表 --
  if (url.includes('/tasks')) {
    return { total: taskItems.length, items: taskItems }
  }

  // -- 合同文档：上传（POST /v1/contracts/upload） --
  if ((method === 'POST') && url.includes('/contracts/upload')) {
    const newDoc = {
      doc_id: `doc-${String(docIdCounter++).padStart(3, '0')}`,
      file_name: `新合同${docIdCounter - 1}.pdf`,
      file_type: 'pdf',
      file_md5: 'new_md5_' + Date.now(),
      file_size: Math.floor(Math.random() * 5000000) + 500000,
      parse_status: 'pending',
      is_scanned: false,
      created_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
    }
    mockDocs.push(newDoc)
    return newDoc
  }

  // -- 合同文档：删除（DELETE /v1/contracts/{doc_id}） --
  if (method === 'DELETE' && url.includes('/contracts/')) {
    const docId = url.split('/').filter(Boolean).pop()?.split('?')[0]
    const idx = mockDocs.findIndex((d) => d.doc_id === docId)
    if (idx !== -1) {
      mockDocs.splice(idx, 1)
    }
    return { deleted: true }
  }

  // -- 合同文档：解析（POST /v1/contracts/{doc_id}/parse） --
  if (method === 'POST' && url.includes('/contracts/') && url.includes('/parse')) {
    const docId = url.split('/').filter(Boolean).slice(-2, -1)[0]
    const doc = mockDocs.find((d) => d.doc_id === docId)
    if (doc) {
      doc.parse_status = 'completed'
    }
    return { parse_status: 'completed', doc_id: docId }
  }

  // -- 合同文档列表 --
  if (url.includes('/contracts')) {
    return { items: [...mockDocs], total: mockDocs.length }
  }

  // -- 系统配置 --
  if (url.includes('/system/configs')) {
    return mockConfigs
  }

  // -- 系统日志 --
  if (url.includes('/system/logs')) {
    return { items: mockLogs, total: mockLogs.length }
  }
  return null
}

function mockApiPlugin(): Plugin {
  return {
    name: 'mock-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url?.startsWith('/api/')) {
          const method = req.method || 'GET'
          const mockData = buildMockData(req.url, method)
          const response = { code: 0, message: 'success', data: mockData, trace_id: 'mock', timestamp: Date.now() }
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify(response))
          return
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), ...(USE_MOCK ? [mockApiPlugin()] : [])],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  css: {
    preprocessorOptions: {
      less: {
        javascriptEnabled: true,
        modifyVars: {
          'primary-color': '#1677ff',
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})