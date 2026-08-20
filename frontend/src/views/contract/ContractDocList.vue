<template>
  <div class="contract-doc-page">
    <PageHeader title="合同文档管理" subtitle="上传合同文件，管理文档解析与字段提取" />

    <!-- 上传区域 -->
    <a-card :bordered="false" class="upload-card">
      <a-upload-dragger
        name="file"
        :multiple="true"
        :accept="acceptTypes"
        :before-upload="beforeUpload"
        :custom-request="handleUpload"
        :show-upload-list="false"
        :disabled="uploading"
      >
        <p class="upload-icon">
          <InboxOutlined style="font-size: 48px; color: #1677ff" />
        </p>
        <p class="upload-text">点击或拖拽合同文件到此区域上传</p>
        <p class="upload-hint">
          支持 PDF、Word（.doc/.docx）、图片（.jpg/.png/.tiff），单文件最大 50MB
        </p>
      </a-upload-dragger>

      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-progress">
        <a-progress :percent="uploadProgress" :status="uploadStatus" />
        <span class="upload-status-text">{{ uploadStatusText }}</span>
      </div>
    </a-card>

    <!-- 文档列表 -->
    <a-card :bordered="false" class="list-card">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="pagination"
        row-key="doc_id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <!-- 文件类型图标 -->
          <!-- 【修复】兼容后端返回 review_report 的旧数据，强制展示为 PDF -->
          <template v-if="column.key === 'file_type'">
            <a-tag :color="getFileTypeColor(normalizeFileType(record.file_type))">
              <FilePdfOutlined v-if="normalizeFileType(record.file_type) === 'pdf'" />
              <FileWordOutlined v-else-if="normalizeFileType(record.file_type) === 'word'" />
              <FileImageOutlined v-else-if="normalizeFileType(record.file_type) === 'image'" />
              <FileOutlined v-else />
              {{ getFileTypeLabel(record.file_type) }}
            </a-tag>
          </template>

          <!-- 文件大小 -->
          <template v-else-if="column.key === 'file_size'">
            {{ formatFileSize(record.file_size) }}
          </template>

          <!-- 解析状态 -->
          <template v-else-if="column.key === 'parse_status'">
            <a-tag :color="getParseStatusColor(record.parse_status)">
              {{ getParseStatusText(record.parse_status) }}
            </a-tag>
          </template>

          <!-- 操作 -->
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="handleParse(record)"
                :disabled="record.parse_status === 'parsing'"
              >
                解析
              </a-button>
              <a-button
                v-if="record.parse_status === 'parsed'"
                type="link"
                size="small"
                @click="handleReview(record)"
                :loading="reviewingId === record.doc_id"
              >
                审查
              </a-button>
              <a-button type="link" size="small" @click="handleDownload(record)">
                下载
              </a-button>
              <a-popconfirm
                title="确定删除此文档？"
                @confirm="handleDelete(record)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  InboxOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileImageOutlined,
  FileOutlined,
} from '@ant-design/icons-vue'
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue'
import type { UploadChangeParam } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import type { ContractDoc } from '@/types/contract'
import { getContractDocs, uploadContract, deleteContractDoc, parseContractDoc, reviewContract, getContractDownloadUrl } from '@/api/contract'

// 上传相关
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref<'active' | 'success' | 'exception' | 'normal'>('normal')
const uploadStatusText = ref('')
const acceptTypes = '.pdf,.doc,.docx,.jpg,.jpeg,.png,.tiff'

// 审查相关
const reviewingId = ref<string | null>(null)

// 列表相关
const loading = ref(false)
const dataSource = ref<ContractDoc[]>([])
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
  { title: '文件名称', dataIndex: 'file_name', key: 'file_name', ellipsis: true },
  { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 100 },
  { title: '大小', dataIndex: 'file_size', key: 'file_size', width: 100 },
  { title: '解析状态', dataIndex: 'parse_status', key: 'parse_status', width: 120 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 200 },
]

// 文件类型颜色映射
function getFileTypeColor(type: string): string {
  const map: Record<string, string> = { pdf: 'red', word: 'blue', image: 'green' }
  return map[type] || 'default'
}

// 【修复】兼容后端旧数据：review_report 视为 pdf 类型
function normalizeFileType(type: string): string {
  if (type === 'review_report') return 'pdf'
  return type
}

// 【修复】文件类型展示文本：review_report 显示为 PDF
function getFileTypeLabel(type: string): string {
  if (type === 'review_report') return 'PDF'
  return type?.toUpperCase() || '-'
}

// 解析状态辅助函数
function getParseStatusColor(status: string): string {
  const map: Record<string, string> = {
    pending: 'default',
    parsing: 'processing',
    parsed: 'success',
    completed: 'success',
    failed: 'error',
  }
  return map[status] || 'default'
}

function getParseStatusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待解析',
    parsing: '解析中',
    parsed: '已完成',
    completed: '已完成',
    failed: '解析失败',
  }
  return map[status] || status
}

// 文件大小格式化
function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

// 上传前校验
function beforeUpload(file: File): boolean {
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    message.error(`文件 ${file.name} 超过 50MB 限制`)
    return false
  }
  return true
}

// 上传处理
async function handleUpload(options: { file: File; onSuccess: () => void; onError: (err: Error) => void }) {
  const { file, onSuccess, onError } = options

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = 'active'
  uploadStatusText.value = `正在上传 ${file.name}...`

  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await uploadContract(formData)

    if (res.code === 0) {
      uploadStatus.value = 'success'
      uploadProgress.value = 100
      if (res.data.is_duplicate) {
        uploadStatusText.value = `${file.name} 已存在，跳过上传`
      } else {
        uploadStatusText.value = `${file.name} 上传成功`
      }
      message.success(`${file.name} 上传成功`)
      fetchList()
      onSuccess()
    } else {
      throw new Error(res.message || '上传失败')
    }
  } catch (err: unknown) {
    const error = err as Error
    uploadStatus.value = 'exception'
    uploadStatusText.value = `${file.name} 上传失败: ${error.message}`
    message.error(`${file.name} 上传失败: ${error.message}`)
    onError(error)
  } finally {
    setTimeout(() => {
      uploading.value = false
    }, 2000)
  }
}

// 获取文档列表
async function fetchList() {
  loading.value = true
  try {
    const res = await getContractDocs({
      page: pagination.current,
      page_size: pagination.pageSize,
    })
    if (res.code === 0) {
      dataSource.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (err: unknown) {
    message.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

// 表格分页变化
function handleTableChange(pag: TablePaginationConfig) {
  pagination.current = pag.current || 1
  pagination.pageSize = pag.pageSize || 20
  fetchList()
}

// 文档解析
async function handleParse(record: Record<string, unknown>) {
  try {
    const res = await parseContractDoc(record.doc_id as string)
    if (res.code === 0) {
      message.success(`解析完成: ${record.file_name}`)
      fetchList()
    }
  } catch {
    message.error('解析失败')
  }
}

// 发起审查
async function handleReview(record: Record<string, unknown>) {
  reviewingId.value = record.doc_id as string
  try {
    const res = await reviewContract(record.doc_id as string)
    if (res.code === 0) {
      message.success(
        `审查完成 | 风险数: ${res.data.risk_count} | 等级: ${res.data.risk_level}`,
        5,
      )
    } else {
      message.error(res.message || '审查失败')
    }
  } catch (err: unknown) {
    const error = err as Error
    message.error(`审查失败: ${error.message}`)
  } finally {
    reviewingId.value = null
  }
}

// 文档下载
async function handleDownload(record: Record<string, unknown>) {
  try {
    const res = await getContractDownloadUrl(record.doc_id as string)
    if (res.code === 0 && res.data.download_url) {
      // 通过预签名 URL 触发浏览器下载
      const a = document.createElement('a')
      a.href = res.data.download_url
      a.download = record.file_name as string
      a.target = '_blank'
      a.click()
      message.success(`开始下载: ${record.file_name}`)
    } else {
      message.error('获取下载链接失败')
    }
  } catch {
    message.error('下载失败')
  }
}

// 文档删除
async function handleDelete(record: Record<string, unknown>) {
  try {
    const res = await deleteContractDoc(record.doc_id as string)
    if (res.code === 0) {
      message.success(`已删除: ${record.file_name}`)
      fetchList()
    } else {
      message.error(res.message || '删除失败')
    }
  } catch {
    message.error('删除失败')
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped lang="less">
.contract-doc-page {
  .upload-card {
    margin-bottom: 16px;

    .upload-icon {
      margin-bottom: 8px;
    }

    .upload-text {
      font-size: 16px;
      color: rgba(0, 0, 0, 0.85);
    }

    .upload-hint {
      font-size: 13px;
      color: rgba(0, 0, 0, 0.45);
    }

    .upload-progress {
      margin-top: 16px;
      display: flex;
      align-items: center;
      gap: 12px;

      .upload-status-text {
        font-size: 13px;
        color: rgba(0, 0, 0, 0.65);
        white-space: nowrap;
      }
    }
  }

  .list-card {
    :deep(.ant-table) {
      .ant-table-cell {
        white-space: nowrap;
      }
    }
  }
}
</style>