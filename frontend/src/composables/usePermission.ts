import { useUserStore } from '@/stores/user'

export function usePermission() {
  const userStore = useUserStore()

  function has(perm: string): boolean {
    return userStore.hasPermission(perm)
  }

  function hasAny(perms: string[]): boolean {
    return perms.some((p) => userStore.hasPermission(p))
  }

  function hasAll(perms: string[]): boolean {
    return perms.every((p) => userStore.hasPermission(p))
  }

  return {
    has,
    hasAny,
    hasAll,
  }
}