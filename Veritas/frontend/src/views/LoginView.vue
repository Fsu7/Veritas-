<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loginFormRef = ref<FormInstance>()
const loginLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 100, message: '密码长度为8-100个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loginLoading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    ElMessage.error('登录失败，请检查用户名和密码')
  } finally {
    loginLoading.value = false
  }
}
</script>

<template>
  <div class="login-view">
    <div class="login-view__card">
      <div class="login-view__header">
        <h1 class="login-view__title">科研文献智能助手</h1>
        <p class="login-view__subtitle">领域知识个性化生成系统</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        label-position="top"
        class="login-view__form"
        @submit.prevent
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :disabled="loginLoading"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :disabled="loginLoading"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="login-view__submit-btn"
            :loading="loginLoading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-view__footer">
        <span>还没有账号？</span>
        <router-link to="/register" class="login-view__link">去注册</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - var(--header-height));
  padding: var(--spacing-lg);

  &__card {
    width: 100%;
    max-width: 400px;
    padding: var(--spacing-xl);
    background: #fff;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
  }

  &__header {
    text-align: center;
    margin-bottom: var(--spacing-xl);
  }

  &__title {
    font-size: var(--font-size-xxl);
    font-weight: 600;
    color: var(--el-color-primary);
    margin: 0 0 var(--spacing-sm);
  }

  &__subtitle {
    font-size: var(--font-size-base);
    color: var(--el-color-info);
    margin: 0;
  }

  &__form {
    margin-bottom: var(--spacing-md);
  }

  &__submit-btn {
    width: 100%;
  }

  &__footer {
    text-align: center;
    font-size: var(--font-size-base);
    color: var(--el-color-info);
  }

  &__link {
    color: var(--el-color-primary);
    text-decoration: none;
    margin-left: var(--spacing-xs);

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
