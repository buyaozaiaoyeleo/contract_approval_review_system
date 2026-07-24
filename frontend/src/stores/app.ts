import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const collapsed = ref(false)
  const title = ref(import.meta.env.VITE_APP_TITLE || '合同审批审查系统')

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
  }

  function setTitle(newTitle: string) {
    title.value = newTitle
    document.title = newTitle
  }

  return {
    collapsed,
    title,
    toggleCollapsed,
    setTitle,
  }
})