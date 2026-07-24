<template>
  <div class="approval-page">
    <PageHeader title="审批单管理" subtitle="查看、搜索、同步审批单，并自动衔接合同审查" />

    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" :model="searchForm" @finish="handleSearch">
        <a-form-item label="关键字">
          <a-input
            v-model:value="searchForm.keyword"
            placeholder="搜索标题或申请人"
            allow-clear
            style="width: 220px"
          />
        </a-form-item>
        <a-form-item label="状态">
          <a-select
            v-model:value="searchForm.status"
            placeholder="全部状态"
            allow-clear
            style="width: 160px"
          >
            <a-select-option value="pending">待审批</a-select-option>
            <a-select-option value="approved">已通过</a-select-option>
            <a-select-option value="rejected">已驳回</a-select-option>
            <a-select-option value="reviewing">审查中</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit">
              <template #icon><SearchOutlined /></template>
              搜索
            </a-button>
            <a-button @click="handleReset">
              <template #icon><ReloadOutlined /></template>
              重置
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="list-card">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="pagination"
        row-key="approval_order_id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>

          <template v-else-if="column.key === 'risk_level'">
            <a-tag v-if="record.risk_level" :color="getRiskLevelColor(record.risk_level)">
              {{ getRiskLevelText(record.risk_level) }}
            </a-tag>
            <span v-else class="text-muted">-</span>
          </template>

          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleViewDetail(record)">详情</a-button>
              <a-button
                type="link"
                size="small"
                @click="handleSync(record)"
                :loading="syncingIds.has(record.approval_order_id)"
              >
                同步
              </a-button>
              <a-popconfirm
                title="确认发起合同审查吗？"
                ok-text="确认"
                cancel-text="取消"
                @confirm="handleTriggerReview(record)"
              >
                <a-button
                  type="link"
                  size="small"
                  :loading="reviewingIds.has(record.approval_order_id)"
                >
                  审查
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue'

import PageHeader from '@/components/common/PageHeader.vue'
import { getApprovalOrders, reviewApproval, syncApproval } from '@/api/approval'
import type { ApprovalOrder } from '@/types/approval'

const router = useRouter()

const searchForm = reactive({
  keyword: '',
  status: '',
})

const loading = ref(false)
const dataSource = ref<ApprovalOrder[]>([])
const syncingIds = ref(new Set<string>())
const reviewingIds = ref(new Set<string>())
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const columns: TableColumnsType = [
  { title: '审批单ID', dataIndex: 'approval_order_id', key: 'approval_order_id', width: 180 },
  { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '申请人', dataIndex: 'applicant', key: 'applicant', width: 120 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '合同风险', dataIndex: 'risk_level', key: 'risk_level', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: '操作', key: 'action', width: 220, fixed: 'right' },
]

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    pending: 'processing',
    approved: 'success',
    rejected: 'error',
    reviewing: 'warning',
    reviewed: 'success',
  }
  return map[status] || 'default'
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已驳回',
    reviewing: '审查中',
    reviewed: '已审查',
  }
  return map[status] || status
}

function getRiskLevelColor(level: string): string {
  const map: Record<string, string> = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' }
  return map[level] || 'default'
}

function getRiskLevelText(level: string): string {
  const map: Record<string, string> = { HIGH: '高风险', MEDIUM: '中风险', LOW: '低风险' }
  return map[level] || level
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getApprovalOrders({
      page: pagination.current,
      page_size: pagination.pageSize,
      status: searchForm.status || undefined,
      keyword: searchForm.keyword || undefined,
    })

    if (res.code === 0) {
      dataSource.value = res.data?.items || []
      pagination.total = res.data?.total || 0
    }
  } catch {
    message.error('获取审批单列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  void fetchList()
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.status = ''
  pagination.current = 1
  void fetchList()
}

function handleTableChange(pag: TablePaginationConfig) {
  pagination.current = pag.current || 1
  pagination.pageSize = pag.pageSize || 20
  void fetchList()
}

function handleViewDetail(record: ApprovalOrder) {
  router.push(`/approval-orders/${record.approval_order_id}`)
}

async function handleSync(record: ApprovalOrder) {
  syncingIds.value.add(record.approval_order_id)
  try {
    const res = await syncApproval(record.approval_order_id, true, true)
    if (res.code === 0) {
      if (res.data.auto_review && res.data.task_id) {
        message.success(`同步成功，并已自动发起审查。任务ID：${res.data.task_id}`)
      } else if (res.data.review_message) {
        message.success(res.data.review_message)
      } else {
        message.success(`审批单 ${record.approval_order_id} 同步成功`)
      }
      await fetchList()
    }
  } catch (error) {
    const err = error as Error
    message.error(`同步失败：${err.message}`)
  } finally {
    syncingIds.value.delete(record.approval_order_id)
  }
}

async function handleTriggerReview(record: ApprovalOrder) {
  reviewingIds.value.add(record.approval_order_id)
  try {
    const res = await reviewApproval(record.approval_order_id, true)
    if (res.code === 0) {
      message.success(`审查任务已启动，任务ID：${res.data.task_id}`)
      router.push(`/workflow-tasks/${res.data.task_id}`)
    } else {
      message.error(res.message || '启动审查失败')
    }
  } catch (error) {
    const err = error as Error
    message.error(`启动审查失败：${err.message}`)
  } finally {
    reviewingIds.value.delete(record.approval_order_id)
  }
}

onMounted(() => {
  void fetchList()
})
</script>

<style scoped lang="less">
.approval-page {
  .search-card {
    margin-bottom: 16px;
  }

  .text-muted {
    color: rgba(0, 0, 0, 0.35);
  }
}
</style>
