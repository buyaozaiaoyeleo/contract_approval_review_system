<template>
  <div class="risk-detail-page">
    <PageHeader :title="`风险详情`" :subtitle="`审批单 #${approvalOrderId}`">
      <template #extra>
        <a-button @click="router.back()">返回列表</a-button>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <!-- 总体概览 -->
      <a-card title="报告概览" :bordered="false" class="overview-card">
        <a-descriptions :column="3" bordered size="small">
          <a-descriptions-item label="审批单ID">
            {{ report?.approval_order_id }}
          </a-descriptions-item>
          <a-descriptions-item label="总体风险等级">
            <a-tag :color="getRiskLevelColor(report?.overall_level)">
              {{ getRiskLevelText(report?.overall_level) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="风险评分">
            {{ report?.risk_score }}
          </a-descriptions-item>
        </a-descriptions>

        <a-row :gutter="16" class="stats-row">
          <a-col :span="6" v-for="stat in statCards" :key="stat.title">
            <a-card size="small" :bordered="false">
              <a-statistic
                :title="stat.title"
                :value="stat.value"
                :value-style="{ color: stat.color, fontSize: '24px' }"
              />
            </a-card>
          </a-col>
        </a-row>

        <a-alert
          v-if="report?.summary"
          :message="report.summary"
          type="info"
          show-icon
          class="summary-alert"
        />
      </a-card>

      <!-- 风险分级 Tab -->
      <a-card :bordered="false" class="detail-card">
        <a-tabs v-model:activeKey="activeTab">
          <a-tab-pane key="high" tab="高风险">
            <RiskItemList :items="report?.high_risks || []" :show-actions="true" @validate="handleValidate" />
          </a-tab-pane>
          <a-tab-pane key="medium" tab="中风险">
            <RiskItemList :items="report?.medium_risks || []" :show-actions="true" @validate="handleValidate" />
          </a-tab-pane>
          <a-tab-pane key="low" tab="低风险">
            <RiskItemList :items="report?.low_risks || []" :show-actions="true" @validate="handleValidate" />
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import RiskItemList from '@/components/risk/RiskItemList.vue'
import { getRiskReport, validateRisk } from '@/api/risk'
import type { RiskReport, RiskResult } from '@/types/risk'

const router = useRouter()
const route = useRoute()
const approvalOrderId = route.params.id as string

const loading = ref(false)
const report = ref<RiskReport | null>(null)
const activeTab = ref('high')

// 统计卡片
const statCards = computed(() => {
  if (!report.value) return []
  return [
    { title: '总风险数', value: report.value.statistics.total, color: '#1677ff' },
    { title: '高风险', value: report.value.statistics.high, color: '#ff4d4f' },
    { title: '中风险', value: report.value.statistics.medium, color: '#faad14' },
    { title: '低风险', value: report.value.statistics.low, color: '#52c41a' },
  ]
})

// 风险等级辅助
function getRiskLevelColor(level?: string): string {
  const map: Record<string, string> = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' }
  return map[level || ''] || 'default'
}
function getRiskLevelText(level?: string): string {
  const map: Record<string, string> = { HIGH: '高风险', MEDIUM: '中风险', LOW: '低风险' }
  return map[level || ''] || (level || '-')
}

// 获取报告
async function fetchReport() {
  loading.value = true
  try {
    const res = await getRiskReport(approvalOrderId)
    if (res.code === 0) {
      report.value = res.data
    }
  } catch {
    message.error('获取风险报告失败')
  } finally {
    loading.value = false
  }
}

// 确认/驳回风险
async function handleValidate(riskId: string, isValid: boolean) {
  try {
    await validateRisk(riskId, isValid)
    message.success(isValid ? '已确认风险' : '已驳回风险')

    if (report.value) {
      const updateItem = (items: RiskResult[]) => {
        const item = items.find((r) => r.risk_id === riskId)
        if (item) item.is_valid = isValid
      }
      updateItem(report.value.high_risks)
      updateItem(report.value.medium_risks)
      updateItem(report.value.low_risks)
    }
  } catch {
    message.error('操作失败')
  }
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped lang="less">
.risk-detail-page {
  .overview-card {
    margin-bottom: 16px;
  }

  .stats-row {
    margin: 16px 0;
  }

  .summary-alert {
    margin-top: 16px;
  }

  .detail-card {
    :deep(.ant-tabs-nav) {
      margin-bottom: 16px;
    }
  }
}
</style>