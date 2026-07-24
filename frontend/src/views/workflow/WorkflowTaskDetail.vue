<template>
  <div class="workflow-detail-page">
    <PageHeader :title="`任务详情`" :subtitle="taskId">
      <template #extra>
        <a-space>
          <a-button @click="router.back()">返回列表</a-button>
          <a-button
            v-if="task?.task_status === 'failed' || task?.task_status === 'blocked'"
            type="primary"
            @click="handleRetry"
            :loading="retrying"
          >
            重试任务
          </a-button>
        </a-space>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <!-- 基本信息 -->
      <a-card title="任务信息" :bordered="false" class="info-card">
        <a-descriptions :column="3" bordered size="small">
          <a-descriptions-item label="任务ID">
            {{ task?.task_id }}
          </a-descriptions-item>
          <a-descriptions-item label="原文档">
            {{ task?.file_name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-badge :status="getStatusBadge(task?.task_status)" />
            <a-tag :color="getStatusColor(task?.task_status)" style="margin-left: 4px">
              {{ getStatusText(task?.task_status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="当前节点">
            {{ getNodeText(task?.current_node) || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="重试次数">
            {{ task?.retry_count ?? 0 }}
          </a-descriptions-item>
          <a-descriptions-item label="开始时间">
            {{ task?.started_at || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="完成时间">
            {{ task?.completed_at || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="耗时">
            {{ formatDuration(task?.duration_ms) }}
          </a-descriptions-item>
          <a-descriptions-item label="错误信息" :span="3" v-if="task?.error_message">
            <a-alert
              :message="task.error_message"
              type="error"
              show-icon
              style="margin-top: 0"
            />
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <!-- 工作流节点 -->
      <a-card title="工作流节点" :bordered="false" class="nodes-card">
        <a-steps
          direction="horizontal"
          size="small"
        >
          <a-step
            v-for="node in workflowNodes"
            :key="node.key"
            :title="node.label"
            :description="node.description"
            :status="getNodeStepStatus(node.key)"
          />
        </a-steps>
      </a-card>

      <!-- 错误信息 -->
      <a-card
        v-if="task?.error_message"
        title="错误详情"
        :bordered="false"
        class="error-card"
      >
        <a-alert
          :message="task.error_message"
          type="error"
          show-icon
        />
      </a-card>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getWorkflowTaskDetail, retryTask } from '@/api/workflow'
import type { WorkflowTask } from '@/types/workflow'

const router = useRouter()
const route = useRoute()
const taskId = route.params.id as string

const loading = ref(false)
const retrying = ref(false)
const task = ref<WorkflowTask | null>(null)

// 轮询定时器
const POLL_INTERVAL_MS = 2000
let pollTimer: ReturnType<typeof setInterval> | null = null
const terminalStatuses = new Set(['success', 'failed', 'blocked'])

// 工作流节点定义（状态由 a-steps 根据 :current 和 :status 自动计算）
const workflowNodes = [
  { key: 'fetch_approval', label: '拉取审批单', description: '从OA同步' },
  { key: 'download_contract', label: '下载合同', description: '下载附件' },
  { key: 'parse_document', label: '解析文档', description: 'MinerU/OCR' },
  { key: 'extract_fields', label: '提取字段', description: 'LLM提取' },
  { key: 'risk_review', label: '风险审查', description: '规则匹配' },
  { key: 'write_comment', label: '回写评论', description: 'OA回写' },
]

const NODE_ORDER = ['fetch_approval', 'download_contract', 'parse_document', 'extract_fields', 'risk_review', 'write_comment']

// 获取每个节点的步骤状态
function getNodeStepStatus(nodeKey: string): 'error' | 'process' | 'finish' | 'wait' {
  if (!task.value) return 'wait'

  const statuses = task.value.node_statuses || {}
  const nodeStatus = statuses[nodeKey]
  const failedNode = task.value.failed_node

  // 节点明确标记为 completed → 绿色对勾
  if (nodeStatus === 'completed') return 'finish'

  // 节点明确标记为 failed → 红色叉号
  if (nodeStatus === 'failed' || failedNode === nodeKey) return 'error'

  // 当前正在执行的节点 → 转圈
  if (task.value.current_node === nodeKey && task.value.task_status === 'running') return 'process'

  // 判断是否已到达此节点
  const nodeIdx = NODE_ORDER.indexOf(nodeKey)
  const currentIdx = task.value.current_node ? NODE_ORDER.indexOf(task.value.current_node) : -1

  // 如果任务已完成，所有节点视为完成
  if (task.value.task_status === 'success') return 'finish'

  // 如果在当前节点之前（已通过）→ 绿色对勾
  if (currentIdx >= 0 && nodeIdx < currentIdx) return 'finish'

  // 如果在当前节点之后或就是当前节点但不在运行 → 等待
  return 'wait'
}

// 状态辅助
function getStatusBadge(status?: string): 'success' | 'processing' | 'error' | 'warning' | 'default' {
  const map: Record<string, 'success' | 'processing' | 'error' | 'warning' | 'default'> = {
    pending: 'default', running: 'processing', success: 'success', failed: 'error', blocked: 'warning',
  }
  return map[status || ''] || 'default'
}
function getStatusColor(status?: string): string {
  const map: Record<string, string> = {
    pending: 'default', running: 'processing', success: 'success', failed: 'error', blocked: 'warning',
  }
  return map[status || ''] || 'default'
}
function getStatusText(status?: string): string {
  const map: Record<string, string> = {
    pending: '待执行', running: '执行中', success: '已完成', failed: '失败', blocked: '阻塞',
  }
  return map[status || ''] || (status || '-')
}
function getNodeText(node?: string | null): string {
  const map: Record<string, string> = {
    fetch_approval: '拉取审批单', download_contract: '下载合同', parse_document: '解析文档',
    extract_fields: '提取字段', risk_review: '风险审查', write_comment: '回写评论',
  }
  return map[node || ''] || (node || '')
}
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

// 获取详情（不显示全局 loading，避免闪烁）
async function fetchDetail() {
  try {
    const res = await getWorkflowTaskDetail(taskId)
    if (res.code === 0) {
      task.value = res.data
    }
  } catch {
    // 轮询静默失败，避免刷屏
  }
}

// 初始加载（显示 loading）
async function initialLoad() {
  loading.value = true
  try {
    const res = await getWorkflowTaskDetail(taskId)
    if (res.code === 0) {
      task.value = res.data
    }
  } catch {
    message.error('获取任务详情失败')
  } finally {
    loading.value = false
  }
}

// 启动轮询
function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    fetchDetail()
  }, POLL_INTERVAL_MS)
}

// 停止轮询
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 根据任务状态决定是否轮询
function updatePolling() {
  const status = task.value?.task_status
  if (status && terminalStatuses.has(status)) {
    stopPolling()
  } else if (!pollTimer) {
    startPolling()
  }
}

// 监听任务状态变化，自动启停轮询
watch(() => task.value?.task_status, () => {
  updatePolling()
})

// 重试
async function handleRetry() {
  retrying.value = true
  try {
    const res = await retryTask(taskId)
    if (res.code === 0) {
      message.success('任务已重新提交')
      await initialLoad()
      // 重试后重新启动轮询
      updatePolling()
    }
  } catch {
    message.error('重试失败')
  } finally {
    retrying.value = false
  }
}

onMounted(async () => {
  await initialLoad()
  // 初始加载后，如果任务不是终态则启动轮询
  updatePolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="less">
.workflow-detail-page {
  .info-card {
    margin-bottom: 16px;
  }

  .nodes-card {
    margin-bottom: 16px;

    :deep(.ant-steps) {
      overflow-x: auto;
    }
  }

  .error-card {
    margin-bottom: 16px;
  }
}
</style>