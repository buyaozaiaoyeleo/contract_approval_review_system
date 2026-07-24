<template>
  <div class="dashboard-page">
    <PageHeader title="统计看板" subtitle="合同审查数据概览与趋势分析" />

    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stat-row">
      <a-col :span="6" v-for="card in statCards" :key="card.title">
        <a-card :bordered="false" class="stat-card">
          <a-statistic
            :title="card.title"
            :value="card.value"
            :value-style="{ color: card.color, fontSize: '32px' }"
            :suffix="card.suffix"
          >
            <template #prefix>
              <component :is="card.icon" :style="{ fontSize: '24px', color: card.color }" />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 图表区域 -->
    <a-row :gutter="16">
      <!-- 审查趋势图 -->
      <a-col :span="16">
        <a-card title="近30天审查趋势" :bordered="false" class="chart-card">
          <a-spin :spinning="trendLoading">
            <v-chart :option="trendChartOption" style="height: 360px" autoresize />
          </a-spin>
        </a-card>
      </a-col>

      <!-- 风险等级分布 -->
      <a-col :span="8">
        <a-card title="风险等级分布" :bordered="false" class="chart-card">
          <a-spin :spinning="statsLoading">
            <v-chart :option="riskPieChartOption" style="height: 360px" autoresize />
          </a-spin>
        </a-card>
      </a-col>
    </a-row>

    <!-- 审查成功率 -->
    <a-row :gutter="16">
      <a-col :span="24">
        <a-card title="审查成功率趋势" :bordered="false" class="chart-card">
          <a-spin :spinning="trendLoading">
            <v-chart :option="successRateChartOption" style="height: 300px" autoresize />
          </a-spin>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  CheckCircleOutlined, FileTextOutlined, WarningOutlined, RiseOutlined,
} from '@ant-design/icons-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getDashboardStats, getDashboardTrend } from '@/api/system'
import type { DashboardStats, DashboardTrend } from '@/api/system'

// 注册 ECharts 组件
use([CanvasRenderer, BarChart, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

// 加载状态
const statsLoading = ref(false)
const trendLoading = ref(false)

// API 数据
const stats = ref<DashboardStats | null>(null)
const trend = ref<DashboardTrend | null>(null)

// 统计卡片
const statCards = ref([
  { title: '审批单总数', value: 0, color: '#1677ff', suffix: '单', icon: FileTextOutlined },
  { title: '审查总数', value: 0, color: '#722ed1', suffix: '次', icon: CheckCircleOutlined },
  { title: '发现风险数', value: 0, color: '#fa8c16', suffix: '项', icon: WarningOutlined },
  { title: '审查成功率', value: 0, color: '#52c41a', suffix: '%', icon: RiseOutlined },
])

// 更新统计卡片
function updateStats() {
  if (stats.value) {
    statCards.value[0].value = stats.value.total_orders
    statCards.value[1].value = stats.value.total_reviews
    statCards.value[2].value = stats.value.total_risks
    statCards.value[3].value = stats.value.success_rate
  }
}

// 趋势图配置
const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['审查任务数', '发现风险数'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: trend.value?.dates || [], boundaryGap: false },
  yAxis: { type: 'value' },
  series: [
    {
      name: '审查任务数', type: 'line', smooth: true,
      data: trend.value?.review_counts || [],
      itemStyle: { color: '#1677ff' },
      areaStyle: { color: 'rgba(22, 119, 255, 0.1)' },
    },
    {
      name: '发现风险数', type: 'line', smooth: true,
      data: trend.value?.risk_counts || [],
      itemStyle: { color: '#fa8c16' },
      areaStyle: { color: 'rgba(250, 140, 22, 0.1)' },
    },
  ],
}))

// 风险等级饼图
const riskPieChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: '0%' },
  series: [{
    type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
    data: [
      { value: stats.value?.risk_distribution.high || 0, name: '高风险', itemStyle: { color: '#ff4d4f' } },
      { value: stats.value?.risk_distribution.medium || 0, name: '中风险', itemStyle: { color: '#fa8c16' } },
      { value: stats.value?.risk_distribution.low || 0, name: '低风险', itemStyle: { color: '#52c41a' } },
    ],
    emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.4)' } },
  }],
}))

// 成功率趋势
const successRateChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: trend.value?.dates || [] },
  yAxis: { type: 'value', min: 80, max: 100, axisLabel: { formatter: '{value}%' } },
  series: [{
    name: '成功率', type: 'bar',
    data: (trend.value?.review_counts || []).map((rc, i) => {
      const risks = trend.value?.risk_counts[i] || 0
      return rc > 0 ? Math.round((1 - risks / rc) * 100) : 100
    }),
    itemStyle: {
      color: (params: { dataIndex: number }) => {
        const val = (trend.value?.review_counts || [])[params.dataIndex] || 0
        const risks = (trend.value?.risk_counts || [])[params.dataIndex] || 0
        const rate = val > 0 ? (1 - risks / val) * 100 : 100
        return rate > 95 ? '#52c41a' : rate > 90 ? '#1677ff' : '#fa8c16'
      },
    },
  }],
}))

// 加载数据
async function fetchStats() {
  statsLoading.value = true
  try {
    const res = await getDashboardStats()
    if (res.code === 0) {
      stats.value = res.data
      updateStats()
    }
  } catch {
    // 使用默认值
  } finally {
    statsLoading.value = false
  }
}

async function fetchTrend() {
  trendLoading.value = true
  try {
    const res = await getDashboardTrend(30)
    if (res.code === 0) {
      trend.value = res.data
    }
  } catch {
    // 使用默认值
  } finally {
    trendLoading.value = false
  }
}

onMounted(() => {
  fetchStats()
  fetchTrend()
})
</script>

<style scoped lang="less">
.dashboard-page {
  .stat-row {
    margin-bottom: 16px;

    .stat-card {
      text-align: center;
    }
  }

  .chart-card {
    margin-bottom: 16px;
  }
}
</style>