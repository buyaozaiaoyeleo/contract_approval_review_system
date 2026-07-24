<template>
  <div class="risk-item-list">
    <a-empty v-if="!items.length" description="暂无此类风险项" />
    <div v-else class="risk-items">
      <a-card
        v-for="item in items"
        :key="item.risk_id"
        size="small"
        :bordered="true"
        class="risk-item-card"
      >
        <div class="risk-item-header">
          <a-space>
            <a-tag :color="getRiskLevelColor(item.risk_level)">
              {{ getRiskLevelText(item.risk_level) }}
            </a-tag>
            <span class="risk-id">{{ item.risk_id }}</span>
            <a-tag v-if="item.is_valid === true" color="success">已确认</a-tag>
            <a-tag v-else-if="item.is_valid === false" color="error">已驳回</a-tag>
            <a-tag v-else>待确认</a-tag>
          </a-space>
        </div>

        <a-descriptions :column="2" size="small" class="risk-detail">
          <a-descriptions-item label="原文档名称">
            {{ item.contract_file_name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="规则ID">
            {{ item.rule_id || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="风险描述" :span="2">
            {{ item.risk_description }}
          </a-descriptions-item>
          <a-descriptions-item label="原文片段" :span="2" v-if="item.source_text">
            <span class="source-text">{{ item.source_text }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="建议" :span="2" v-if="item.suggestion">
            <span class="suggestion-text">{{ item.suggestion }}</span>
          </a-descriptions-item>
        </a-descriptions>

        <div class="risk-item-actions" v-if="showActions">
          <a-space>
            <a-button
              size="small"
              type="primary"
              ghost
              @click="emit('validate', item.risk_id, true)"
              :disabled="item.is_valid === true"
            >
              确认
            </a-button>
            <a-button
              size="small"
              danger
              ghost
              @click="emit('validate', item.risk_id, false)"
              :disabled="item.is_valid === false"
            >
              驳回
            </a-button>
          </a-space>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RiskResult } from '@/types/risk'

defineProps<{
  items: RiskResult[]
  showActions?: boolean
}>()

const emit = defineEmits<{
  validate: [riskId: string, isValid: boolean]
}>()

function getRiskLevelColor(level: string): string {
  const map: Record<string, string> = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' }
  return map[level] || 'default'
}

function getRiskLevelText(level: string): string {
  const map: Record<string, string> = { HIGH: '高风险', MEDIUM: '中风险', LOW: '低风险' }
  return map[level] || level
}
</script>

<style scoped lang="less">
.risk-item-list {
  .risk-items {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .risk-item-card {
    border-left: 3px solid #1677ff;

    .risk-item-header {
      margin-bottom: 8px;

      .risk-id {
        font-size: 12px;
        color: rgba(0, 0, 0, 0.45);
        font-family: monospace;
      }
    }

    .risk-detail {
      .source-text {
        color: rgba(0, 0, 0, 0.65);
        font-style: italic;
        background: #fffbe6;
        padding: 2px 6px;
        border-radius: 3px;
      }

      .suggestion-text {
        color: #1677ff;
      }
    }

    .risk-item-actions {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #f0f0f0;
    }
  }
}
</style>
