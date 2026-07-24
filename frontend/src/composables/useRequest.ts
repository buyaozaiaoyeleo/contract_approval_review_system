import { ref, type UnwrapRef } from 'vue'

interface UseRequestOptions<T> {
  immediate?: boolean
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
}

export function useRequest<T>(
  requestFn: () => Promise<T>,
  options: UseRequestOptions<T> = {},
) {
  const { immediate = false, onSuccess, onError } = options

  const data = ref<T | null>(null) as { value: UnwrapRef<T> | null }
  const loading = ref(false)
  const error = ref<Error | null>(null)

  async function execute() {
    loading.value = true
    error.value = null
    try {
      const result = await requestFn()
      data.value = result as UnwrapRef<T>
      onSuccess?.(result)
      return result
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e))
      error.value = err
      onError?.(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  if (immediate) {
    execute()
  }

  return {
    data,
    loading,
    error,
    execute,
  }
}