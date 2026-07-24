import { reactive, ref } from 'vue'
import { DEFAULT_PAGE_SIZE } from '@/utils/constants'

export interface PaginationState {
  page: number
  page_size: number
  total: number
}

export function usePagination(defaultPageSize: number = DEFAULT_PAGE_SIZE) {
  const pagination = reactive<PaginationState>({
    page: 1,
    page_size: defaultPageSize,
    total: 0,
  })

  function setTotal(total: number) {
    pagination.total = total
  }

  function reset() {
    pagination.page = 1
  }

  function handlePageChange(page: number, pageSize: number) {
    pagination.page = page
    pagination.page_size = pageSize
  }

  const paginationProps = ref({
    current: pagination.page,
    pageSize: pagination.page_size,
    total: pagination.total,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total: number) => `共 ${total} 条`,
    pageSizeOptions: ['10', '20', '50', '100'],
    onChange: (page: number, pageSize: number) => {
      pagination.page = page
      pagination.page_size = pageSize
    },
  })

  return {
    pagination,
    setTotal,
    reset,
    handlePageChange,
    paginationProps,
  }
}