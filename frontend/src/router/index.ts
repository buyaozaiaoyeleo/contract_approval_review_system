import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { setupRouterGuards } from './guards'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', layout: 'blank' },
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '统计看板', icon: 'DashboardOutlined' },
      },
      {
        path: 'approval-orders',
        name: 'ApprovalOrders',
        component: () => import('@/views/approval/ApprovalList.vue'),
        meta: { title: '审批单管理', icon: 'FileTextOutlined' },
      },
      {
        path: 'approval-orders/:id',
        name: 'ApprovalDetail',
        component: () => import('@/views/approval/ApprovalDetail.vue'),
        meta: { title: '审批单详情', hidden: true },
      },
      {
        path: 'risk-results',
        name: 'RiskResults',
        component: () => import('@/views/risk/RiskResultList.vue'),
        meta: { title: '风险审查结果', icon: 'AlertOutlined' },
      },
      {
        path: 'risk-results/:id',
        name: 'RiskResultDetail',
        component: () => import('@/views/risk/RiskResultDetail.vue'),
        meta: { title: '风险详情', hidden: true },
      },
      {
        path: 'risk-rules',
        name: 'RiskRules',
        component: () => import('@/views/rule/RuleList.vue'),
        meta: { title: '风险规则管理', icon: 'SafetyCertificateOutlined' },
      },
      {
        path: 'risk-rules/:id',
        name: 'RuleEdit',
        component: () => import('@/views/rule/RuleEdit.vue'),
        meta: { title: '规则编辑', hidden: true },
      },
      {
        path: 'workflow-tasks',
        name: 'WorkflowTasks',
        component: () => import('@/views/workflow/WorkflowTaskList.vue'),
        meta: { title: '工作流任务', icon: 'ApartmentOutlined' },
      },
      {
        path: 'workflow-tasks/:id',
        name: 'WorkflowTaskDetail',
        component: () => import('@/views/workflow/WorkflowTaskDetail.vue'),
        meta: { title: '任务详情', hidden: true },
      },
      {
        path: 'contract-docs',
        name: 'ContractDocs',
        component: () => import('@/views/contract/ContractDocList.vue'),
        meta: { title: '合同文档管理', icon: 'FilePdfOutlined' },
      },
      {
        path: 'contract-docs/:id',
        name: 'ContractDocPreview',
        component: () => import('@/views/contract/ContractDocPreview.vue'),
        meta: { title: '文档预览', hidden: true },
      },
      {
        path: 'system',
        name: 'System',
        redirect: '/system/config',
        meta: { title: '系统管理', icon: 'SettingOutlined' },
        children: [
          {
            path: 'config',
            name: 'SystemConfig',
            component: () => import('@/views/system/SystemConfig.vue'),
            meta: { title: '系统配置' },
          },
          {
            path: 'logs',
            name: 'SystemLogs',
            component: () => import('@/views/system/SystemLogs.vue'),
            meta: { title: '操作日志' },
          },
        ],
      },
    ],
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404', layout: 'blank' },
  },
  {
    path: '/500',
    name: 'ServerError',
    component: () => import('@/views/error/500.vue'),
    meta: { title: '500', layout: 'blank' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

setupRouterGuards(router)

export default router