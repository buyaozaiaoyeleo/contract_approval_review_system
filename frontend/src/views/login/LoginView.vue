<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>合同审批审查系统</h1>
        <p>企业级合同风险审查管理平台</p>
      </div>
      <a-form
        :model="formState"
        :rules="rules"
        ref="formRef"
        @finish="handleLogin"
        size="large"
      >
        <a-form-item name="username">
          <a-input v-model:value="formState.username" placeholder="用户名" autocomplete="username">
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>
        <a-form-item name="password">
          <a-input-password
            v-model:value="formState.password"
            placeholder="密码"
            autocomplete="current-password"
          >
            <template #prefix><LockOutlined /></template>
          </a-input-password>
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            block
            size="large"
          >
            登 录
          </a-button>
        </a-form-item>
      </a-form>
    </div>
    <div class="login-footer">
      <span>Copyright &copy; {{ new Date().getFullYear() }} 合同审批审查系统</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { login } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)

const formState = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  loading.value = true
  try {
    const res = await login({
      username: formState.username,
      password: formState.password,
    })
    const { access_token, refresh_token } = res.data
    userStore.setToken(access_token, refresh_token)
    await userStore.fetchUserInfo()
    message.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="less">
.login-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;

  h1 {
    font-size: 24px;
    color: #1a1a1a;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: #999;
  }
}

.login-footer {
  position: absolute;
  bottom: 24px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}
</style>