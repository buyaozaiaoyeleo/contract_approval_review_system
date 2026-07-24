import { ref } from 'vue'

export function useTable<T>() {
  const selectedRowKeys = ref<string[]>([])
  const selectedRows = ref<T[]>([])

  const rowSelection = {
    selectedRowKeys: selectedRowKeys.value,
    onChange: (keys: string[], rows: T[]) => {
      selectedRowKeys.value = keys
      selectedRows.value = rows
    },
  }

  function clearSelection() {
    selectedRowKeys.value = []
    selectedRows.value = []
  }

  return {
    selectedRowKeys,
    selectedRows,
    rowSelection,
    clearSelection,
  }
}