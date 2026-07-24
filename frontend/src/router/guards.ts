import type { Router } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getStorage } from '@/utils/storage'
import { TOKEN_KEY } from '@/utils/constants'

const WHITE_LIST = ['/login', '/404', '/500']

export function setupRouterGuards(router: Router) {
  router.beforeEach(async (to, _from, next) => {
    const token = getStorage(TOKEN_KEY)

    if (WHITE_LIST.includes(to.path)) {
      if (token && to.path === '/login') {
        next({ path: '/dashboard' })
      } else {
        next()
      }
      return
    }

    if (!token) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    const userStore = useUserStore()
    if (!userStore.userInfo) {
      try {
        await userStore.fetchUserInfo()
      } catch {
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
    }

    next()
  })
}