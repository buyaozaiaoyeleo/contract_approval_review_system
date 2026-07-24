<template>
  <div class="system-config-page">
    <PageHeader title="系统配置" subtitle="管理系统运行参数和配置项" />

    <a-card :bordered="false" class="config-card">
      <a-spin :spinning="loading">
        <a-table
          :columns="columns"
          :data-source="dataSource"
          :pagination="false"
          row-key="key"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <!-- 配置值 -->
            <template v-if="column.key === 'value'">
              <template v-if="editingKey === record.key">
                <a-input
                  v-model:value="editValue"
                  :placeholder="record.value"
                  style="width: 300px"
                  @press-enter="handleSave(record)"
                />
              </template>
              <template v-else>
                <a-tag v-if="record.key === 'debug_mode'" :color="record.value === 'true' ? 'green' : 'default'">
                  {{ record.value === 'true' ? '开启' : '关闭' }}
                </a-tag>
                <span v-else-if="record.key.includes('secret') || record.key.includes('password')" class="secret-value">
                  ********
                </span>
                <span v-else>{{ record.value }}</span>
              </template>
            </template>

            <!-- 更新时间 -->
            <template v-else-if="column.key === 'updated_at'">
              {{ record.updated_at || '-' }}
            </template>

            <!-- 操作 -->
            <template v-else-if="column.key === 'action'">
              <template v-if="editingKey === record.key">
                <a-space>
                  <a-button type="link" size="small" :loading="saving" @click="handleSave(record)">
                    保存
                  </a-button>
                  <a-button type="link" size="small" @click="handleCancelEdit">
                    取消
                  </a-button>
                </a-space>
              </template>
              <template v-else>
                <a-button
                  type="link"
                  size="small"
                  @click="handleEdit(record)"
                  :disabled="editingKey !== ''"
                >
                  编辑
                </a-button>
              </template>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getSystemConfigs, updateSystemConfig, type SystemConfig } from '@/api/system'

const loading = ref(false)
const saving = ref(false)
const dataSource = ref<SystemConfig[]>([])
const editingKey = ref('')
const editValue = ref('')

// 表格列
const columns: TableColumnsType = [
  { title: '配置键', dataIndex: 'key', key: 'key', width: 220 },
  { title: '配置值', dataIndex: 'value', key: 'value', width: 400 },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170 },
  { title: '操作', key: 'action', width: 120 },
]

// 加载配置
async function fetchConfigs() {
  loading.value = true
  try {
    const res = await getSystemConfigs()
    if (res.code === 0) {
      dataSource.value = res.data
    }
  } catch {
    message.error('获取配置列表失败')
  } finally {
    loading.value = false
  }
}

// 编辑
function handleEdit(record: SystemConfig) {
  editingKey.value = record.key
  editValue.value = record.value
}

// 取消编辑
function handleCancelEdit() {
  editingKey.value = ''
  editValue.value = ''
}

// 保存
async function handleSave(record: SystemConfig) {
  if (!editValue.value.trim()) {
    message.warning('配置值不能为空')
    return
  }
  saving.value = true
  try {
    const res = await updateSystemConfig(record.key, editValue.value.trim())
    if (res.code === 0) {
      record.value = res.data.value
      record.updated_at = res.data.updated_at
      message.success('配置已更新')
      editingKey.value = ''
      editValue.value = ''
    }
  } catch {
    message.error('更新配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped lang="less">
.system-config-page {
  .config-card {
    .secret-value {
      color: rgba(0, 0, 0, 0.45);
      font-family: monospace;
      font-size: 13px;
    }
  }
}
</style>