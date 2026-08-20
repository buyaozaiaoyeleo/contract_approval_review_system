<template>
  <div class="preview-page">
    <PageHeader title="文档预览" :subtitle="docId" />

    <a-card :bordered="false">
      <a-spin :spinning="loading">
        <a-descriptions :column="3" bordered size="small" class="doc-info">
          <a-descriptions-item label="文件名称">{{ docInfo.file_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="文件类型">
            <a-tag :color="getFileTypeColor(docInfo.file_type)">
              {{ formatFileType(docInfo.file_type) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="文件大小">{{ formatFileSize(docInfo.file_size) }}</a-descriptions-item>
          <a-descriptions-item label="解析状态">
            <a-tag :color="getParseStatusColor(docInfo.parse_status)">
              {{ getParseStatusText(docInfo.parse_status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="扫描件">
            {{ docInfo.is_scanned ? '是' : '否' }}
          </a-descriptions-item>
          <a-descriptions-item label="MD5">{{ docInfo.file_md5 || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-spin>
    </a-card>

    <a-card title="文件预览" :bordered="false" class="preview-card">
      <div v-if="!previewUrl" class="preview-placeholder">
        <FilePdfOutlined style="font-size: 64px; color: #d9d9d9" />
        <p>当前页面未集成内嵌预览组件，可下载或在新窗口查看文件。</p>
        <a-space>
          <a-button type="primary" @click="handleDownload" :loading="downloadLoading">下载文件查看</a-button>
          <a-button @click="handleOpenInNewTab" :loading="downloadLoading">新窗口打开</a-button>
        </a-space>
      </div>

      <iframe
        v-else-if="docInfo.file_type === 'pdf'"
        :src="previewUrl"
        class="pdf-frame"
        title="PDF 预览"
      />

      <div v-else class="preview-placeholder">
        <FilePdfOutlined style="font-size: 64px; color: #d9d9d9" />
        <p>该文件类型不支持页面内直接预览，请下载后查看。</p>
        <a-space>
          <a-button type="primary" @click="handleDownload" :loading="downloadLoading">下载文件查看</a-button>
          <a-button @click="handleOpenInNewTab" :loading="downloadLoading">新窗口打开</a-button>
        </a-space>
      </div>
    </a-card>

    <a-card title="解析文本" :bordered="false" class="text-card">
      <a-empty v-if="!parsedText" description="文档暂无解析文本" />
      <div v-else class="parsed-text">
        <pre>{{ parsedText }}</pre>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { FilePdfOutlined } from '@ant-design/icons-vue'

import PageHeader from '@/components/common/PageHeader.vue'
import { getContractDocDetail, getContractDownloadUrl } from '@/api/contract'

const route = useRoute()
const docId = String(route.params.id)

const loading = ref(false)
const downloadLoading = ref(false)
const parsedText = ref('')
const previewUrl = ref('')

const docInfo = reactive({
  file_name: '',
  file_type: '',
  file_size: 0,
  file_md5: '',
  parse_status: 'pending',
  is_scanned: false,
})

function getFileTypeColor(type: string): string {
  const map: Record<string, string> = { pdf: 'red', word: 'blue', image: 'green' }
  return map[type] || 'default'
}

function formatFileType(type: string): string {
  const map: Record<string, string> = { pdf: 'PDF', word: 'WORD', image: 'IMAGE' }
  return map[type] || (type || '-')
}

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
    parsed: '已解析',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

async function fetchDocDetail() {
  loading.value = true
  try {
    const res = await getContractDocDetail(docId)
    if (res.code === 0) {
      const data = res.data as unknown as Record<string, unknown>
      docInfo.file_name = String(data.file_name || '')
      docInfo.file_type = String(data.file_type || '')
      docInfo.file_size = Number(data.file_size || 0)
      docInfo.file_md5 = String(data.file_md5 || '')
      docInfo.parse_status = String(data.parse_status || 'pending')
      docInfo.is_scanned = Boolean(data.is_scanned)
      parsedText.value = typeof data.parse_text === 'string' ? data.parse_text : ''
    }
  } catch {
    message.error('获取文档信息失败')
  } finally {
    loading.value = false
  }
}

async function fetchDownloadUrl(): Promise<string | null> {
  downloadLoading.value = true
  try {
    const res = await getContractDownloadUrl(docId)
    if (res.code === 0 && res.data?.download_url) {
      previewUrl.value = res.data.download_url
      return res.data.download_url
    }
    message.error(res.message || '获取下载地址失败')
    return null
  } catch {
    message.error('获取下载地址失败')
    return null
  } finally {
    downloadLoading.value = false
  }
}

async function handleDownload() {
  const url = previewUrl.value || (await fetchDownloadUrl())
  if (!url) {
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function handleOpenInNewTab() {
  await handleDownload()
}

onMounted(() => {
  if (!docId) {
    return
  }
  void fetchDocDetail()
})
</script>

<style scoped lang="less">
.preview-page {
  .doc-info {
    margin-bottom: 0;
  }

  .preview-card {
    margin-top: 16px;
  }

  .preview-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 0;
    gap: 16px;
    color: #999;
  }

  .pdf-frame {
    width: 100%;
    min-height: 720px;
    border: none;
    border-radius: 4px;
    background: #f5f5f5;
  }

  .text-card {
    margin-top: 16px;

    .parsed-text {
      max-height: 500px;
      overflow-y: auto;
      background: #fafafa;
      border-radius: 4px;
      padding: 16px;

      pre {
        white-space: pre-wrap;
        word-break: break-all;
        font-size: 13px;
        line-height: 1.8;
      }
    }
  }
}
</style>
