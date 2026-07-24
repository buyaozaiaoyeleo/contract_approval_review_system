<template>
  <a-layout-header
    :style="{
      background: '#fff',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 1px 4px rgba(0, 0, 0, 0.08)',
      zIndex: 9,
      position: 'sticky',
      top: 0,
    }"
  >
    <div class="header-left">
      <MenuFoldOutlined
        v-if="!appStore.collapsed"
        class="trigger"
        @click="appStore.toggleCollapsed"
      />
      <MenuUnfoldOutlined
        v-else
        class="trigger"
        @click="appStore.toggleCollapsed"
      />
      <a-breadcrumb style="margin-left: 16px">
        <a-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
          {{ item.meta?.title || item.name }}
        </a-breadcrumb-item>
      </a-breadcrumb>
    </div>
    <div class="header-right">
      <a-dropdown>
        <a-space style="cursor: pointer">
          <a-avatar :size="32" icon="user" />
          <span>{{ userStore.userInfo?.display_name || '管理员' }}</span>
          <DownOutlined />
        </a-space>
        <template #overlay>
          <a-menu>
            <a-menu-item key="profile" @click="handleProfile">个人信息</a-menu-item>
            <a-menu-divider />
            <a-menu-item key="logout" @click="handleLogout">退出登录</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </a-layout-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { MenuFoldOutlined, MenuUnfoldOutlined, DownOutlined } from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const breadcrumbs = computed(() => {
  return route.matched.filter((r) => r.meta?.title && r.path !== '/')
})

function handleProfile() {
  router.push('/system')
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped lang="less">
.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.trigger {
  font-size: 18px;
  cursor: pointer;
  transition: color 0.3s;

  &:hover {
    color: #1677ff;
  }
}
</style>