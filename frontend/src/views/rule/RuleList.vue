<template>
  <div class="rule-page">
    <PageHeader title="风险规则管理" subtitle="创建、编辑、启用/禁用风险审查规则">
      <template #extra>
        <a-button type="primary" @click="handleCreate">
          <template #icon><PlusOutlined /></template>
          创建规则
        </a-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <a-card :bordered="false" class="filter-card">
      <a-form layout="inline" :model="filterForm" @finish="handleFilter">
        <a-form-item label="规则分类">
          <a-select
            v-model:value="filterForm.category"
            placeholder="全部分类"
            allow-clear
            style="width: 160px"
          >
            <a-select-option value="amount">金额类</a-select-option>
            <a-select-option value="term">期限类</a-select-option>
            <a-select-option value="clause">条款类</a-select-option>
            <a-select-option value="subject">主体类</a-select-option>
            <a-select-option value="compliance">合规类</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="仅显示启用">
          <a-switch v-model:checked="filterForm.enabled_only" />
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

    <!-- 规则列表 -->
    <a-card :bordered="false" class="list-card">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="false"
        row-key="id"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <!-- 规则分类 -->
          <template v-if="column.key === 'rule_category'">
            <a-tag>{{ getCategoryText(record.rule_category) }}</a-tag>
          </template>

          <!-- 规则类型 -->
          <template v-else-if="column.key === 'rule_type'">
            <a-tag :color="record.rule_type === 'field' ? 'blue' : 'purple'">
              {{ getTypeText(record.rule_type) }}
            </a-tag>
          </template>

          <!-- 风险等级 -->
          <template v-else-if="column.key === 'risk_level'">
            <a-tag :color="getRiskLevelColor(record.risk_level)">
              {{ getRiskLevelText(record.risk_level) }}
            </a-tag>
          </template>

          <!-- 启用状态 -->
          <template v-else-if="column.key === 'is_enabled'">
            <a-switch
              :checked="record.is_enabled"
              size="small"
              @change="(val: boolean) => handleToggle(record, val)"
            />
          </template>

          <!-- 操作 -->
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleEdit(record)">
                编辑
              </a-button>
              <a-popconfirm
                title="确定删除此规则？"
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
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import type { TableColumnsType } from 'ant-design-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getRiskRules, deleteRiskRule, toggleRiskRule } from '@/api/rule'
import type { RiskRule } from '@/types/rule'

const router = useRouter()

// 筛选表单
const filterForm = reactive({
  category: '',
  enabled_only: true,
})

// 列表相关
const loading = ref(false)
const dataSource = ref<RiskRule[]>([])

// 表格列定义
const columns: TableColumnsType = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '规则编码', dataIndex: 'rule_code', key: 'rule_code', width: 120 },
  { title: '规则名称', dataIndex: 'rule_name', key: 'rule_name', ellipsis: true },
  { title: '分类', dataIndex: 'rule_category', key: 'rule_category', width: 80 },
  { title: '类型', dataIndex: 'rule_type', key: 'rule_type', width: 80 },
  { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 90 },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 70 },
  { title: '启用', dataIndex: 'is_enabled', key: 'is_enabled', width: 60 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 140, fixed: 'right' },
]

// 辅助函数
function getCategoryText(category: string): string {
  const map: Record<string, string> = { amount: '金额', term: '期限', clause: '条款', subject: '主体', compliance: '合规' }
  return map[category] || category
}
function getTypeText(type: string): string {
  const map: Record<string, string> = { field: '字段', llm: 'LLM', composite: '组合' }
  return map[type] || type
}
function getRiskLevelColor(level: string): string {
  const map: Record<string, string> = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' }
  return map[level] || 'default'
}
function getRiskLevelText(level: string): string {
  const map: Record<string, string> = { HIGH: '高', MEDIUM: '中', LOW: '低' }
  return map[level] || level
}

// 获取列表
async function fetchList() {
  loading.value = true
  try {
    const res = await getRiskRules({
      category: filterForm.category || undefined,
      enabled_only: filterForm.enabled_only,
    })
    if (res.code === 0) {
      dataSource.value = res.data
    }
  } catch {
    message.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

// 筛选
function handleFilter() {
  fetchList()
}

// 重置
function handleReset() {
  filterForm.category = ''
  filterForm.enabled_only = true
  fetchList()
}

// 创建规则
function handleCreate() {
  router.push('/risk-rules/new')
}

// 编辑规则
function handleEdit(record: RiskRule) {
  router.push(`/risk-rules/${record.id}`)
}

// 启用/禁用
async function handleToggle(record: RiskRule, enabled: boolean) {
  try {
    const res = await toggleRiskRule(record.id, enabled)
    if (res.code === 0) {
      record.is_enabled = enabled
      message.success(enabled ? '已启用' : '已禁用')
    }
  } catch {
    message.error('操作失败')
  }
}

// 删除规则
async function handleDelete(record: RiskRule) {
  try {
    const res = await deleteRiskRule(record.id)
    if (res.code === 0) {
      message.success('删除成功')
      fetchList()
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
.rule-page {
  .filter-card {
    margin-bottom: 16px;
  }
}
</style>