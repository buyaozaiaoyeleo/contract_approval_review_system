<template>
  <div class="system-logs-page">
    <PageHeader title="操作日志" subtitle="查看系统运行日志和操作记录" />

    <!-- 筛选栏 -->
    <a-card :bordered="false" class="filter-card">
      <a-form layout="inline" :model="filterForm" @finish="handleFilter">
        <a-form-item label="日志级别">
          <a-select
            v-model:value="filterForm.level"
            placeholder="全部级别"
            allow-clear
            style="width: 120px"
          >
            <a-select-option value="INFO">INFO</a-select-option>
            <a-select-option value="WARNING">WARNING</a-select-option>
            <a-select-option value="ERROR">ERROR</a-select-option>
            <a-select-option value="DEBUG">DEBUG</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模块">
          <a-select
            v-model:value="filterForm.module"
            placeholder="全部模块"
            allow-clear
            style="width: 140px"
          >
            <a-select-option value="risk">风险审查</a-select-option>
            <a-select-option value="workflow">工作流</a-select-option>
            <a-select-option value="contract">合同</a-select-option>
            <a-select-option value="approval">审批</a-select-option>
            <a-select-option value="system">系统</a-select-option>
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

    <!-- 日志列表 -->
    <a-card :bordered="false" class="list-card">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        size="small"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <!-- 日志级别 -->
          <template v-if="column.key === 'level'">
            <a-tag :color="getLevelColor(record.level)">
              {{ record.level }}
            </a-tag>
          </template>

          <!-- 模块 -->
          <template v-else-if="column.key === 'module'">
            <a-tag>{{ getModuleText(record.module) }}</a-tag>
          </template>

          <!-- 消息 -->
          <template v-else-if="column.key === 'message'">
            <span
              :style="{ color: record.level === 'ERROR' ? '#ff4d4f' : 'inherit' }"
              class="log-message"
            >
              {{ record.message }}
            </span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getSystemLogs, type SystemLog } from '@/api/system'

const loading = ref(false)
const dataSource = ref<SystemLog[]>([])
const filterForm = reactive({ level: '', module: '' })
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

// 表格列
const columns: TableColumnsType = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '级别', dataIndex: 'level', key: 'level', width: 80 },
  { title: '模块', dataIndex: 'module', key: 'module', width: 100 },
  { title: '消息', dataIndex: 'message', key: 'message' },
]

function getLevelColor(level: string): string {
  const map: Record<string, string> = { INFO: 'blue', WARNING: 'orange', ERROR: 'red', DEBUG: 'default' }
  return map[level] || 'default'
}
function getModuleText(module: string): string {
  const map: Record<string, string> = {
    risk: '风险审查', workflow: '工作流', contract: '合同', approval: '审批', system: '系统',
  }
  return map[module] || module
}

async function fetchLogs() {
  loading.value = true
  try {
    const res = await getSystemLogs({
      page: pagination.current,
      page_size: pagination.pageSize,
      level: filterForm.level || undefined,
      module: filterForm.module || undefined,
    })
    if (res.code === 0) {
      dataSource.value = res.data.items
      pagination.total = res.data.total
    }
  } catch {
    message.error('获取日志列表失败')
  } finally {
    loading.value = false
  }
}

function handleFilter() {
  pagination.current = 1
  fetchLogs()
}

function handleReset() {
  filterForm.level = ''
  filterForm.module = ''
  pagination.current = 1
  fetchLogs()
}

function handleTableChange(pag: TablePaginationConfig) {
  pagination.current = pag.current || 1
  pagination.pageSize = pag.pageSize || 20
  fetchLogs()
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped lang="less">
.system-logs-page {
  .filter-card {
    margin-bottom: 16px;
  }

  .log-message {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    word-break: break-all;
  }
}
</style>