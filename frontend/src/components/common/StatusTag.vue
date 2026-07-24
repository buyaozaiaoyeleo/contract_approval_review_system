<template>
  <a-tag :color="statusInfo.color">{{ statusInfo.label }}</a-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatus, ApprovalStatus, RiskLevel } from '@/types/common'
import { TASK_STATUS_MAP, APPROVAL_STATUS_MAP, RISK_LEVEL_MAP } from '@/types/common'

const props = defineProps<{
  status: TaskStatus | ApprovalStatus | RiskLevel
  type: 'task' | 'approval' | 'risk'
}>()

const statusInfo = computed(() => {
  switch (props.type) {
    case 'task':
      return TASK_STATUS_MAP[props.status as TaskStatus] || { label: props.status, color: '#d9d9d9' }
    case 'approval':
      return APPROVAL_STATUS_MAP[props.status as ApprovalStatus] || { label: props.status, color: '#d9d9d9' }
    case 'risk':
      return RISK_LEVEL_MAP[props.status as RiskLevel] || { label: props.status, color: '#d9d9d9' }
    default:
      return { label: props.status, color: '#d9d9d9' }
  }
})
</script>