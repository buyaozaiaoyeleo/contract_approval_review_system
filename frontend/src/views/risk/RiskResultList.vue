<template>
  <div class="risk-result-page">
    <PageHeader
      title="风险审查结果"
      subtitle="按审批单ID、原文档名称或任务ID查询风险结果，并支持查看与下载风险报告"
    />

    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" :model="searchForm" @finish="handleSearch">
        <a-form-item label="审批单ID">
          <a-input
            v-model:value="searchForm.approval_order_id"
            placeholder="输入审批单ID"
            allow-clear
            style="width: 220px"
            @pressEnter="handleSearch"
          />
        </a-form-item>
        <a-form-item label="原文档名称">
          <a-input
            v-model:value="searchForm.contract_file_name"
            placeholder="输入原文档名称"
            allow-clear
            style="width: 220px"
            @pressEnter="handleSearch"
          />
        </a-form-item>
        <a-form-item label="任务ID">
          <a-input
            v-model:value="searchForm.task_id"
            placeholder="输入任务ID，例如 TASK_xxx"
            allow-clear
            style="width: 240px"
            @pressEnter="handleSearch"
          />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" :loading="loading" @click="handleSearch">搜索</a-button>
            <a-button type="default" @click="handleViewReport" :disabled="!currentApprovalOrderId">
              <template #icon><FileTextOutlined /></template>
              查看报告
            </a-button>
            <a-button type="primary" :loading="downloadingPdf" :disabled="!currentApprovalOrderId" @click="handleDownloadPdf">
              下载PDF报告
            </a-button>
            <a-button type="dashed" :loading="loading" @click="handleLoadRecent">
              <template #icon><ReloadOutlined /></template>
              加载最近结果
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="list-card">
      <a-table
        :columns="columns"
        :data-source="results"
        :loading="loading"
        :pagination="false"
        row-key="risk_id"
        size="small"
        :scroll="{ x: 1500 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'risk_level'">
            <a-tag :color="getRiskLevelColor(record.risk_level)">
              {{ getRiskLevelText(record.risk_level) }}
            </a-tag>
          </template>

          <template v-else-if="column.key === 'is_valid'">
            <a-tag v-if="record.is_valid === true" color="success">已确认</a-tag>
            <a-tag v-else-if="record.is_valid === false" color="error">已驳回</a-tag>
            <a-tag v-else>待确认</a-tag>
          </template>

          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleValidate(record, true)" :disabled="record.is_valid === true">
                确认
              </a-button>
              <a-button type="link" size="small" danger @click="handleValidate(record, false)" :disabled="record.is_valid === false">
                驳回
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>

      <a-empty
        v-if="!loading && !results.length && searched"
        description="未找到风险审查结果，请确认审批单ID、原文档名称或任务ID是否正确"
      />
      <a-empty
        v-if="!loading && !results.length && !searched"
        description="页面会自动加载最近的风险审查结果"
      />
    </a-card>

    <a-modal v-model:open="reportVisible" title="风险审查报告" width="900px" :footer="null">
      <a-spin :spinning="reportLoading">
        <template v-if="report">
          <a-descriptions :column="3" bordered size="small" class="report-summary">
            <a-descriptions-item label="审批单ID">{{ report.approval_order_id }}</a-descriptions-item>
            <a-descriptions-item label="总体风险等级">
              <a-tag :color="getRiskLevelColor(report.overall_level)">
                {{ getRiskLevelText(report.overall_level) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="风险评分">{{ report.risk_score }}</a-descriptions-item>
          </a-descriptions>

          <a-row :gutter="16" class="report-stats">
            <a-col v-for="stat in statCards" :key="stat.title" :span="6">
              <a-card size="small">
                <a-statistic :title="stat.title" :value="stat.value" :value-style="{ color: stat.color }" />
              </a-card>
            </a-col>
          </a-row>

          <div class="report-toolbar">
            <a-space compact>
              <a-input
                v-model:value="reportSwitchKeyword"
                placeholder="输入审批单ID或原文档名称切换报告"
                allow-clear
                style="width: 320px"
                @pressEnter="handleReportSwitchSearch"
              />
              <a-button @click="handleReportSwitchSearch">搜索</a-button>
            </a-space>

            <a-space compact>
              <a-input
                v-model:value="reportFilterKeyword"
                placeholder="当前报告内筛选：风险ID/合同名/描述"
                allow-clear
                style="width: 320px"
              />
              <a-button type="primary" :loading="downloadingPdf" @click="handleDownloadPdf">下载PDF报告</a-button>
            </a-space>
          </div>

          <a-tabs>
            <a-tab-pane key="high" tab="高风险">
              <RiskItemList :items="filteredHighRisks" />
            </a-tab-pane>
            <a-tab-pane key="medium" tab="中风险">
              <RiskItemList :items="filteredMediumRisks" />
            </a-tab-pane>
            <a-tab-pane key="low" tab="低风险">
              <RiskItemList :items="filteredLowRisks" />
            </a-tab-pane>
          </a-tabs>
        </template>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import type { TableColumnsType } from 'ant-design-vue'

import PageHeader from '@/components/common/PageHeader.vue'
import RiskItemList from '@/components/risk/RiskItemList.vue'
import {
  downloadRiskReportPdf,
  getAllRiskResults,
  getRiskReport,
  getRiskResults,
  getRiskResultsByTask,
  validateRisk,
} from '@/api/risk'
import type { RiskQueryParams, RiskReport, RiskResult } from '@/types/risk'

const route = useRoute()

const searchForm = reactive({
  approval_order_id: '',
  contract_file_name: '',
  task_id: '',
})

const loading = ref(false)
const searched = ref(false)
const downloadingPdf = ref(false)
const results = ref<RiskResult[]>([])
const reportVisible = ref(false)
const reportLoading = ref(false)
const report = ref<RiskReport | null>(null)
const reportSwitchKeyword = ref('')
const reportFilterKeyword = ref('')
const currentApprovalOrderId = ref('')

const columns: TableColumnsType<RiskResult> = [
  { title: '合同名称', dataIndex: 'contract_file_name', key: 'contract_file_name', width: 220, ellipsis: true },
  { title: '审批单ID', dataIndex: 'approval_order_id', key: 'approval_order_id', width: 200 },
  { title: '风险ID', dataIndex: 'risk_id', key: 'risk_id', width: 220, ellipsis: true },
  { title: '规则ID', dataIndex: 'rule_id', key: 'rule_id', width: 140 },
  { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 100 },
  { title: '字段', dataIndex: 'field_name', key: 'field_name', width: 120, ellipsis: true },
  { title: '风险描述', dataIndex: 'risk_description', key: 'risk_description', ellipsis: true },
  { title: '建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
  { title: '状态', dataIndex: 'is_valid', key: 'is_valid', width: 100 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

const statCards = computed(() => {
  if (!report.value) {
    return []
  }
  return [
    { title: '总风险数', value: report.value.statistics.total, color: '#1677ff' },
    { title: '高风险', value: report.value.statistics.high, color: '#ff4d4f' },
    { title: '中风险', value: report.value.statistics.medium, color: '#faad14' },
    { title: '低风险', value: report.value.statistics.low, color: '#52c41a' },
  ]
})

function getRiskLevelColor(level: string): string {
  const map: Record<string, string> = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green', NONE: 'default' }
  return map[level] || 'default'
}

function getRiskLevelText(level: string): string {
  const map: Record<string, string> = { HIGH: '高风险', MEDIUM: '中风险', LOW: '低风险', NONE: '无风险' }
  return map[level] || level
}

function syncCurrentApprovalOrder(items: RiskResult[]) {
  const firstApprovalOrderId = items.find((item) => item.approval_order_id)?.approval_order_id || ''
  currentApprovalOrderId.value = firstApprovalOrderId || searchForm.approval_order_id.trim()
}

function filterRiskItems(items: RiskResult[]): RiskResult[] {
  const keyword = reportFilterKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return items
  }

  return items.filter((item) => {
    return (
      (item.approval_order_id || '').toLowerCase().includes(keyword) ||
      item.risk_id.toLowerCase().includes(keyword) ||
      (item.contract_file_name || '').toLowerCase().includes(keyword) ||
      (item.risk_description || '').toLowerCase().includes(keyword) ||
      (item.source_text || '').toLowerCase().includes(keyword) ||
      (item.field_name || '').toLowerCase().includes(keyword)
    )
  })
}

const filteredHighRisks = computed(() => filterRiskItems(report.value?.high_risks || []))
const filteredMediumRisks = computed(() => filterRiskItems(report.value?.medium_risks || []))
const filteredLowRisks = computed(() => filterRiskItems(report.value?.low_risks || []))

function normalizeRiskListResponse(data: RiskResult[] | { items: RiskResult[] }): RiskResult[] {
  return Array.isArray(data) ? data : data.items || []
}

async function loadRiskResultsByFilters(filters?: RiskQueryParams) {
  const response = await getAllRiskResults(1, 20, filters)
  if (response.code === 0) {
    results.value = normalizeRiskListResponse(response.data)
    syncCurrentApprovalOrder(results.value)
  }
}

async function handleSearch() {
  searched.value = true
  loading.value = true
  try {
    const taskId = searchForm.task_id.trim()
    if (taskId) {
      const response = await getRiskResultsByTask(taskId)
      if (response.code === 0) {
        results.value = response.data
        syncCurrentApprovalOrder(response.data)
      }
      return
    }

    const approvalOrderId = searchForm.approval_order_id.trim()
    const contractFileName = searchForm.contract_file_name.trim()
    if (!approvalOrderId && !contractFileName) {
      message.warning('请输入审批单ID、原文档名称或任务ID')
      results.value = []
      currentApprovalOrderId.value = ''
      return
    }

    if (approvalOrderId && !contractFileName) {
      const response = await getRiskResults(approvalOrderId)
      if (response.code === 0) {
        results.value = response.data
        syncCurrentApprovalOrder(response.data)
      }
      return
    }

    await loadRiskResultsByFilters({
      approval_order_id: approvalOrderId || undefined,
      contract_file_name: contractFileName || undefined,
    })
  } catch {
    message.error('查询风险审查结果失败')
  } finally {
    loading.value = false
  }
}

async function handleLoadRecent() {
  loading.value = true
  searched.value = true
  try {
    await loadRiskResultsByFilters({
      approval_order_id: searchForm.approval_order_id.trim() || undefined,
      contract_file_name: searchForm.contract_file_name.trim() || undefined,
    })
  } catch {
    message.error('加载最近风险结果失败')
  } finally {
    loading.value = false
  }
}

async function handleValidate(record: RiskResult, isValid: boolean) {
  try {
    const response = await validateRisk(record.risk_id, isValid)
    if (response.code === 0) {
      record.is_valid = isValid
      message.success(isValid ? '已确认风险项' : '已驳回风险项')
    }
  } catch {
    message.error('操作失败')
  }
}

async function handleViewReport() {
  if (!currentApprovalOrderId.value) {
    message.warning('请先输入或选择审批单ID')
    return
  }

  reportVisible.value = true
  reportLoading.value = true
  try {
    const response = await getRiskReport(currentApprovalOrderId.value)
    if (response.code === 0) {
      report.value = response.data
      reportSwitchKeyword.value = ''
      reportFilterKeyword.value = ''
    }
  } catch {
    message.error('获取风险报告失败')
  } finally {
    reportLoading.value = false
  }
}

async function handleReportSwitchSearch() {
  const keyword = reportSwitchKeyword.value.trim()
  if (!keyword) {
    return
  }

  reportLoading.value = true
  try {
    let nextApprovalOrderId = ''

    if (/^\d+$/.test(keyword)) {
      const response = await getRiskResults(keyword)
      if (response.code === 0 && response.data.length > 0) {
        nextApprovalOrderId = keyword
      }
    } else {
      const response = await getAllRiskResults(1, 20, { contract_file_name: keyword })
      const rows = response.code === 0 ? normalizeRiskListResponse(response.data) : []
      nextApprovalOrderId = rows[0]?.approval_order_id || ''
    }

    if (!nextApprovalOrderId) {
      message.warning('未找到匹配的审批单ID或原文档名称')
      return
    }

    if (nextApprovalOrderId === currentApprovalOrderId.value) {
      reportFilterKeyword.value = keyword
      return
    }

    currentApprovalOrderId.value = nextApprovalOrderId
    searchForm.approval_order_id = nextApprovalOrderId
    const reportResponse = await getRiskReport(nextApprovalOrderId)
    if (reportResponse.code === 0) {
      report.value = reportResponse.data
      reportSwitchKeyword.value = ''
      reportFilterKeyword.value = ''
    }
  } catch {
    message.error('搜索风险报告失败')
  } finally {
    reportLoading.value = false
  }
}

async function handleDownloadPdf() {
  if (!currentApprovalOrderId.value) {
    message.warning('请先输入或选择审批单ID')
    return
  }

  downloadingPdf.value = true
  try {
    await downloadRiskReportPdf(currentApprovalOrderId.value)
    message.success('风险报告PDF开始下载')
  } catch {
    message.error('下载风险报告PDF失败')
  } finally {
    downloadingPdf.value = false
  }
}

onMounted(() => {
  const routeApprovalOrderId = route.query.approval_order_id
  if (typeof routeApprovalOrderId === 'string' && routeApprovalOrderId.trim()) {
    searchForm.approval_order_id = routeApprovalOrderId.trim()
    currentApprovalOrderId.value = routeApprovalOrderId.trim()
    void handleSearch()
    return
  }
  void handleLoadRecent()
})
</script>

<style scoped lang="less">
.risk-result-page {
  .search-card {
    margin-bottom: 16px;
  }

  .report-summary {
    margin-bottom: 16px;
  }

  .report-stats {
    margin-bottom: 16px;
  }

  .report-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }
}
</style>
