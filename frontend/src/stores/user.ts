import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCurrentUser, type UserInfo } from '@/api/auth'
import { getStorage, setStorage, removeStorage } from '@/utils/storage'
import { TOKEN_KEY, REFRESH_TOKEN_KEY, USER_INFO_KEY } from '@/utils/constants'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(getStorage(TOKEN_KEY) || '')
  const refreshToken = ref<string>(getStorage(REFRESH_TOKEN_KEY) || '')
  const userInfo = ref<UserInfo | null>(null)
  const permissions = ref<string[]>([])

  const isLoggedIn = () => !!token.value

  function setToken(accessToken: string, refreshTokenValue: string) {
    token.value = accessToken
    refreshToken.value = refreshTokenValue
    setStorage(TOKEN_KEY, accessToken)
    setStorage(REFRESH_TOKEN_KEY, refreshTokenValue)
  }

  async function fetchUserInfo() {
    try {
      const res = await getCurrentUser()
      userInfo.value = res.data
      permissions.value = res.data.permissions || []
      setStorage(USER_INFO_KEY, JSON.stringify(res.data))
    } catch {
      logout()
    }
  }

  function hasPermission(perm: string): boolean {
    if (permissions.value.includes('*')) return true
    return permissions.value.includes(perm)
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    permissions.value = []
    removeStorage(TOKEN_KEY)
    removeStorage(REFRESH_TOKEN_KEY)
    removeStorage(USER_INFO_KEY)
  }

  return {
    token,
    refreshToken,
    userInfo,
    permissions,
    isLoggedIn,
    setToken,
    fetchUserInfo,
    hasPermission,
    logout,
  }
})