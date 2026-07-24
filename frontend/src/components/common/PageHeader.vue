<template>
  <div class="page-header">
    <div class="page-header-title">
      <h2>{{ title }}</h2>
      <span v-if="subtitle" class="page-header-subtitle">{{ subtitle }}</span>
    </div>
    <div v-if="$slots.extra" class="page-header-extra">
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped lang="less">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 24px;
  background: #fff;
  border-radius: 4px;
}

.page-header-title {
  h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 500;
    color: #1a1a1a;
  }
}

.page-header-subtitle {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
  display: block;
}

.page-header-extra {
  display: flex;
  gap: 8px;
}
</style>