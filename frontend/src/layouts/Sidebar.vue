<template>
  <a-layout-sider
    v-model:collapsed="appStore.collapsed"
    collapsible
    :trigger="null"
    :width="220"
  >
    <div class="logo">
      <img src="@/assets/images/logo.svg" alt="logo" class="logo-img" />
      <span v-if="!appStore.collapsed" class="logo-text">合同审批审查系统</span>
    </div>
    <a-menu
      theme="dark"
      mode="inline"
      :selected-keys="selectedKeys"
      :open-keys="openKeys"
      @click="handleMenuClick"
    >
      <template v-for="item in menuItems" :key="item.resolvedPath">
        <a-sub-menu v-if="item.children && item.children.length" :key="item.resolvedPath">
          <template #title>
            <component :is="item.icon" />
            <span>{{ item.meta?.title }}</span>
          </template>
          <a-menu-item v-for="child in item.children" :key="child.resolvedPath">
            <span>{{ child.meta?.title }}</span>
          </a-menu-item>
        </a-sub-menu>
        <a-menu-item v-else :key="item.resolvedPath">
          <component :is="item.icon" />
          <span>{{ item.meta?.title }}</span>
        </a-menu-item>
      </template>
    </a-menu>
  </a-layout-sider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import {
  DashboardOutlined,
  FileTextOutlined,
  AlertOutlined,
  SafetyCertificateOutlined,
  ApartmentOutlined,
  FilePdfOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const iconMap: Record<string, unknown> = {
  DashboardOutlined,
  FileTextOutlined,
  AlertOutlined,
  SafetyCertificateOutlined,
  ApartmentOutlined,
  FilePdfOutlined,
  SettingOutlined,
}

// 使用路由完整路径作为菜单 key，确保子菜单导航正确
const menuItems = computed<any[]>(() => {
  const routes = router.options.routes.find((r) => r.path === '/')?.children || []
  return routes
    .filter((r) => !r.meta?.hidden)
    .map((r) => {
      const resolvedPath = `/${r.path}`
      const children = r.children
        ?.filter((c) => !c.meta?.hidden)
        .map((c) => ({
          ...c,
          resolvedPath: `${resolvedPath}/${c.path}`,
        }))
      return {
        ...r,
        resolvedPath,
        icon: r.meta?.icon ? iconMap[r.meta.icon as string] : null,
        children: children?.length ? children : undefined,
      }
    })
})

const selectedKeys = computed(() => [route.path])

const openKeys = computed(() => {
  const parent = route.matched.length > 1 ? route.matched[route.matched.length - 2] : null
  if (parent && parent.path !== '/') {
    return [`/${parent.path}`]
  }
  return []
})

function handleMenuClick({ key }: { key: string }) {
  router.push(key)
}
</script>

<style scoped lang="less">
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.logo-img {
  width: 32px;
  height: 32px;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 500;
  margin-left: 10px;
  white-space: nowrap;
}
</style>