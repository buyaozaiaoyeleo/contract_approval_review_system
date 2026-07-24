<template>
  <div class="workflow-page">
    <PageHeader title="工作流任务" subtitle="查看合同审查任务的执行状态，重试失败任务" />

    <!-- 筛选栏 -->
    <a-card :bordered="false" class="filter-card">
      <a-form layout="inline" :model="filterForm" @finish="handleFilter">
        <a-form-item label="任务状态">
          <a-select
            v-model:value="filterForm.status"
            placeholder="全部状态"
            allow-clear
            style="width: 140px"
          >
            <a-select-option value="pending">待执行</a-select-option>
            <a-select-option value="running">执行中</a-select-option>
            <a-select-option value="success">已完成</a-select-option>
            <a-select-option value="failed">失败</a-select-option>
            <a-select-option value="blocked">阻塞</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit">
              <template #icon><SearchOutlined /></template>
              筛选
            </a-button>
            <a-button @click="handleReset">
              <template #icon><ReloadOutlined /></template>
              重置
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 任务列表 -->
    <a-card :bordered="false" class="list-card">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="pagination"
        row-key="task_id"
        size="small"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <!-- 任务状态 -->
          <template v-if="column.key === 'task_status'">
            <a-badge :status="getStatusBadge(record.task_status)" />
            <a-tag :color="getStatusColor(record.task_status)" style="margin-left: 4px">
              {{ getStatusText(record.task_status) }}
            </a-tag>
          </template>

          <!-- 当前节点 -->
          <template v-else-if="column.key === 'current_node'">
            <a-tag v-if="record.current_node" color="blue">
              {{ getNodeText(record.current_node) }}
            </a-tag>
            <span v-else>-</span>
          </template>

          <!-- 耗时 -->
          <template v-else-if="column.key === 'duration'">
            {{ formatDuration(record.duration_ms) }}
          </template>

          <!-- 操作 -->
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="handleViewDetail(record)"
              >
                详情
              </a-button>
              <a-button
                v-if="record.task_status === 'failed' || record.task_status === 'blocked'"
                type="link"
                size="small"
                @click="handleRetry(record)"
                :loading="retryingIds.has(record.task_id)"
              >
                重试
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getWorkflowTasks, retryTask } from '@/api/workflow'
import type { WorkflowTask } from '@/types/workflow'

const router = useRouter()

// 筛选表单
const filterForm = reactive({
  status: '',
})

// 列表相关
const loading = ref(false)
const dataSource = ref<WorkflowTask[]>([])
const retryingIds = ref(new Set<string>())
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

// 表格列定义
const columns: TableColumnsType = [
  { title: '任务ID', dataIndex: 'task_id', key: 'task_id', width: 150, ellipsis: true },
  { title: '原文档', dataIndex: 'file_name', key: 'file_name', width: 200, ellipsis: true },
  { title: '状态', dataIndex: 'task_status', key: 'task_status', width: 100 },
  { title: '当前节点', dataIndex: 'current_node', key: 'current_node', width: 120 },
  { title: '重试次数', dataIndex: 'retry_count', key: 'retry_count', width: 80 },
  { title: '耗时', key: 'duration', width: 100 },
  { title: '创建时间', dataIndex: 'started_at', key: 'started_at', width: 170 },
  { title: '操作', key: 'action', width: 130, fixed: 'right' },
]

// 状态辅助函数
function getStatusBadge(status: string): 'success' | 'processing' | 'error' | 'warning' | 'default' {
  const map: Record<string, 'success' | 'processing' | 'error' | 'warning' | 'default'> = {
    pending: 'default', running: 'processing', success: 'success', failed: 'error', blocked: 'warning',
  }
  return map[status] || 'default'
}
function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    pending: 'default', running: 'processing', success: 'success', failed: 'error', blocked: 'warning',
  }
  return map[status] || 'default'
}
function getStatusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待执行', running: '执行中', success: '已完成', failed: '失败', blocked: '阻塞',
  }
  return map[status] || status
}
function getNodeText(node: string): string {
  const map: Record<string, string> = {
    fetch_approval: '拉取审批单', download_contract: '下载合同', parse_document: '解析文档',
    extract_fields: '提取字段', risk_review: '风险审查', write_comment: '回写评论',
  }
  return map[node] || node
}
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

// 获取列表
async function fetchList() {
  loading.value = true
  try {
    const res = await getWorkflowTasks({
      page: pagination.current,
      page_size: pagination.pageSize,
      status: filterForm.status || undefined,
    })
    if (res.code === 0) {
      dataSource.value = res.data.items
      pagination.total = res.data.total
    }
  } catch {
    message.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// 筛选
function handleFilter() {
  pagination.current = 1
  fetchList()
}

// 重置
function handleReset() {
  filterForm.status = ''
  pagination.current = 1
  fetchList()
}

// 分页变化
function handleTableChange(pag: TablePaginationConfig) {
  pagination.current = pag.current || 1
  pagination.pageSize = pag.pageSize || 20
  fetchList()
}

// 查看详情
function handleViewDetail(record: WorkflowTask) {
  router.push(`/workflow-tasks/${record.task_id}`)
}

// 重试任务
async function handleRetry(record: WorkflowTask) {
  retryingIds.value.add(record.task_id)
  try {
    const res = await retryTask(record.task_id)
    if (res.code === 0) {
      message.success('任务已重新提交')
      fetchList()
    }
  } catch {
    message.error('重试失败')
  } finally {
    retryingIds.value.delete(record.task_id)
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped lang="less">
.workflow-page {
  .filter-card {
    margin-bottom: 16px;
  }
}
</style>