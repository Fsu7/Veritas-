<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const router = useRouter()
const userStore = useUserStore()

const registerFormRef = ref<FormInstance>()
const registerLoading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void
) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 100, message: '密码长度为8-100个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

watch(
  () => registerForm.password,
  () => {
    if (registerForm.confirmPassword) {
      registerFormRef.value?.validateField('confirmPassword')
    }
  }
)

async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return

  registerLoading.value = true
  try {
    await userStore.register(registerForm.username, registerForm.email, registerForm.password)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {
    ElMessage.error('注册失败，请重试')
  } finally {
    registerLoading.value = false
  }
}
</script>

<template>
  <div class="register-view">
    <div class="register-view__card">
      <div class="register-view__header">
        <h1 class="register-view__title">创建新账号</h1>
      </div>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="rules"
        label-position="top"
        class="register-view__form"
        @submit.prevent
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            :disabled="registerLoading"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱"
            :disabled="registerLoading"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :disabled="registerLoading"
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入密码"
            :disabled="registerLoading"
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="register-view__submit-btn"
            :loading="registerLoading"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-view__footer">
        <span>已有账号？</span>
        <router-link to="/login" class="register-view__link">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.register-view {
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
