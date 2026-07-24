<template>
  <div class="approval-detail-page">
    <PageHeader
      :title="`审批单详情 #${approvalId}`"
      :subtitle="detail?.approval?.title || '查看审批单、关联合同和审批评论'"
    >
      <template #extra>
        <a-space>
          <a-button @click="router.back()">返回列表</a-button>
          <a-button type="default" @click="goToRiskResults" :disabled="!detail">查看风险结果</a-button>
          <a-button
            type="primary"
            @click="handleTriggerReview"
            :loading="reviewing"
            :disabled="!canTriggerReview"
          >
            触发审查
          </a-button>
        </a-space>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <a-card title="基本信息" :bordered="false" class="info-card">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="审批单ID">
            {{ detail?.approval?.approval_order_id || approvalId }}
          </a-descriptions-item>
          <a-descriptions-item label="标题">
            {{ detail?.approval?.title || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="申请人">
            {{ detail?.approval?.applicant || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="getStatusColor(detail?.approval?.status)">
              {{ getStatusText(detail?.approval?.status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="合同数量">
            {{ detail?.documents?.length || 0 }}
          </a-descriptions-item>
          <a-descriptions-item label="评论数量">
            {{ detail?.comments?.length || 0 }}
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">
            {{ detail?.approval?.created_at || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="更新时间">
            {{ detail?.approval?.updated_at || '-' }}
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <a-row :gutter="16" class="summary-row">
        <a-col :xs="24" :md="8">
          <a-card size="small">
            <a-statistic title="原始合同" :value="originalDocumentCount" />
          </a-card>
        </a-col>
        <a-col :xs="24" :md="8">
          <a-card size="small">
            <a-statistic title="风险报告" :value="reportDocumentCount" />
          </a-card>
        </a-col>
        <a-col :xs="24" :md="8">
          <a-card size="small">
            <a-statistic title="已解析文档" :value="parsedDocumentCount" />
          </a-card>
        </a-col>
      </a-row>

      <a-card :bordered="false" class="tab-card">
        <a-tabs v-model:activeKey="activeTab">
          <a-tab-pane key="documents" tab="关联合同">
            <a-table
              :columns="docColumns"
              :data-source="detail?.documents || []"
              :pagination="false"
              row-key="doc_id"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'file_type'">
                  <a-tag :color="getFileTypeColor(record.file_type)">
                    {{ formatFileType(record.file_type) }}
                  </a-tag>
                </template>

                <template v-else-if="column.key === 'document_kind'">
                  <a-tag :color="isReportDocument(record.file_name) ? 'orange' : 'blue'">
                    {{ isReportDocument(record.file_name) ? '风险报告' : '原始合同' }}
                  </a-tag>
                </template>

                <template v-else-if="column.key === 'parse_status'">
                  <a-tag :color="getParseStatusColor(record.parse_status)">
                    {{ getParseStatusText(record.parse_status) }}
                  </a-tag>
                </template>

                <template v-else-if="column.key === 'is_scanned'">
                  {{ record.is_scanned ? '是' : '否' }}
                </template>

                <template v-else-if="column.key === 'doc_action'">
                  <a-space>
                    <a-button type="link" size="small" @click="handlePreviewDoc(record)">预览</a-button>
                    <a-button
                      v-if="!isReportDocument(record.file_name)"
                      type="link"
                      size="small"
                      @click="goToContractDoc(record.doc_id)"
                    >
                      打开文档
                    </a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
            <a-empty v-if="!detail?.documents?.length" description="暂无关联合同文档" />
          </a-tab-pane>

          <a-tab-pane key="comments" tab="审批评论">
            <a-timeline v-if="detail?.comments?.length">
              <a-timeline-item v-for="comment in detail.comments" :key="comment.comment_id">
                <div class="comment-content">{{ comment.content }}</div>
                <div class="comment-time">{{ comment.created_at || '-' }}</div>
              </a-timeline-item>
            </a-timeline>
            <a-empty v-else description="暂无审批评论" />
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'

import PageHeader from '@/components/common/PageHeader.vue'
import { getApprovalOrderDetail, reviewApproval } from '@/api/approval'
import type { ApprovalOrderDetail, ContractDocItem } from '@/types/approval'

const router = useRouter()
const route = useRoute()
const approvalId = String(route.params.id)

const loading = ref(false)
const reviewing = ref(false)
const detail = ref<ApprovalOrderDetail | null>(null)
const activeTab = ref('documents')

const docColumns: TableColumnsType = [
  { title: '文件名', dataIndex: 'file_name', key: 'file_name', ellipsis: true },
  { title: '文档类型', key: 'document_kind', width: 110 },
  { title: '文件格式', dataIndex: 'file_type', key: 'file_type', width: 100 },
  { title: '解析状态', dataIndex: 'parse_status', key: 'parse_status', width: 110 },
  { title: '扫描件', dataIndex: 'is_scanned', key: 'is_scanned', width: 90 },
  { title: '操作', key: 'doc_action', width: 180 },
]

const canTriggerReview = computed(() => (detail.value?.documents?.length || 0) > 0)

const originalDocumentCount = computed(
  () => detail.value?.documents?.filter((item) => !isReportDocument(item.file_name)).length || 0,
)

const reportDocumentCount = computed(
  () => detail.value?.documents?.filter((item) => isReportDocument(item.file_name)).length || 0,
)

const parsedDocumentCount = computed(
  () => detail.value?.documents?.filter((item) => item.parse_status === 'parsed' || item.parse_status === 'completed').length || 0,
)

function isReportDocument(fileName: string | null | undefined): boolean {
  if (!fileName) {
    return false
  }
  const upperName = fileName.toUpperCase()
  return upperName.startsWith('HIGH_') || upperName.startsWith('MEDIUM_') || upperName.startsWith('LOW_')
}

function getStatusColor(status?: string): string {
  const map: Record<string, string> = {
    pending: 'processing',
    approved: 'success',
    rejected: 'error',
    reviewing: 'warning',
    reviewed: 'success',
  }
  return map[status || ''] || 'default'
}

function getStatusText(status?: string): string {
  const map: Record<string, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已驳回',
    reviewing: '审查中',
    reviewed: '已审查',
  }
  return map[status || ''] || (status || '-')
}

function getFileTypeColor(type?: string): string {
  const map: Record<string, string> = { pdf: 'red', word: 'blue', image: 'green' }
  return map[type || ''] || 'default'
}

function formatFileType(type?: string): string {
  const map: Record<string, string> = { pdf: 'PDF', word: 'WORD', image: 'IMAGE' }
  return map[type || ''] || (type || '-')
}

function getParseStatusColor(status?: string): string {
  const map: Record<string, string> = {
    pending: 'default',
    parsing: 'processing',
    parsed: 'success',
    completed: 'success',
    failed: 'error',
  }
  return map[status || ''] || 'default'
}

function getParseStatusText(status?: string): string {
  const map: Record<string, string> = {
    pending: '待解析',
    parsing: '解析中',
    parsed: '已解析',
    completed: '已完成',
    failed: '失败',
  }
  return map[status || ''] || (status || '-')
}

async function fetchDetail() {
  loading.value = true
  try {
    const res = await getApprovalOrderDetail(approvalId)
    if (res.code === 0) {
      detail.value = res.data
    } else {
      message.error(res.message || '获取审批单详情失败')
    }
  } catch {
    message.error('获取审批单详情失败')
  } finally {
    loading.value = false
  }
}

function handlePreviewDoc(record: ContractDocItem) {
  router.push(`/contract-docs/${record.doc_id}`)
}

function goToContractDoc(docId: string) {
  router.push(`/contract-docs/${docId}`)
}

function goToRiskResults() {
  router.push(`/risk-results?approval_order_id=${approvalId}`)
}

async function handleTriggerReview() {
  reviewing.value = true
  try {
    const res = await reviewApproval(approvalId, true)
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
    reviewing.value = false
  }
}

onMounted(() => {
  void fetchDetail()
})
</script>

<style scoped lang="less">
.approval-detail-page {
  .info-card {
    margin-bottom: 16px;
  }

  .summary-row {
    margin-bottom: 16px;
  }

  .tab-card {
    :deep(.ant-tabs-nav) {
      margin-bottom: 16px;
    }
  }

  .comment-content {
    margin-bottom: 4px;
    color: rgba(0, 0, 0, 0.88);
    white-space: pre-wrap;
  }

  .comment-time {
    font-size: 12px;
    color: rgba(0, 0, 0, 0.45);
  }
}
</style>
