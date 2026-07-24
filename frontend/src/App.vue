<template>
  <router-view />
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

watch(
  () => appStore.title,
  (newTitle) => {
    document.title = newTitle
  },
  { immediate: true },
)
</script>