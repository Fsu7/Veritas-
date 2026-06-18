import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ============ Mock 基础设施（vi.hoisted 保证在 vi.mock 工厂前可用） ============

const mocks = vi.hoisted(() => ({
  userStore: {
    login: vi.fn(),
    isLoggedIn: false,
    hasProfile: false,
    profile: null as unknown
  },
  redirectAfterLogin: vi.fn(),
  mockValidate: vi.fn(() => Promise.resolve(true)),
  elMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  }
}))

vi.mock('@/stores/userStore', () => ({
  useUserStore: vi.fn(() => mocks.userStore)
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: vi.fn(() => ({
    redirectAfterLogin: mocks.redirectAfterLogin,
    isLoggedIn: { value: mocks.userStore.isLoggedIn },
    hasProfile: { value: false },
    requireAuth: vi.fn(),
    redirectIfAuthenticated: vi.fn(),
    logout: vi.fn()
  }))
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: {}, query: {} })),
  useRouter: vi.fn(() => ({ push: vi.fn(), back: vi.fn() }))
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>
  return {
    ...actual,
    ElMessage: mocks.elMessage,
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') }
  }
})

import LoginView from '@/views/LoginView.vue'

// ============ 辅助函数 ============

function mountLoginView() {
  return mount(LoginView, {
    global: {
      stubs: {
        'el-form': {
          name: 'ElForm',
          template: '<form class="el-form"><slot /></form>',
          methods: {
            validate: mocks.mockValidate
          }
        },
        'el-form-item': { name: 'ElFormItem', template: '<div class="el-form-item"><slot /></div>' },
        'el-input': {
          name: 'ElInput',
          template:
            '<input class="el-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          props: ['modelValue', 'type', 'placeholder', 'disabled', 'showPassword']
        },
        'el-button': {
          name: 'ElButton',
          template:
            '<button class="el-button" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'loading', 'disabled']
        },
        'router-link': { template: '<a class="router-link"><slot /></a>', props: ['to'] }
      }
    }
  })
}

// ============ 测试 ============

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.userStore.login.mockResolvedValue(undefined)
    mocks.mockValidate.mockResolvedValue(true)
  })

  it('渲染登录表单标题和副标题', () => {
    const wrapper = mountLoginView()
    expect(wrapper.find('.login-view__title').text()).toContain('科研文献智能助手')
    expect(wrapper.find('.login-view__subtitle').text()).toContain('领域知识个性化生成系统')
  })

  it('渲染去注册链接', () => {
    const wrapper = mountLoginView()
    expect(wrapper.find('.login-view__link').text()).toContain('去注册')
  })

  it('空用户名/密码表单验证失败时不调用 login', async () => {
    mocks.mockValidate.mockResolvedValue(false)
    const wrapper = mountLoginView()
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(mocks.userStore.login).not.toHaveBeenCalled()
    expect(mocks.redirectAfterLogin).not.toHaveBeenCalled()
  })

  it('登录成功调用 userStore.login 和 redirectAfterLogin', async () => {
    const wrapper = mountLoginView()
    const inputs = wrapper.findAll('.el-input')
    await inputs[0].setValue('testuser')
    await inputs[1].setValue('password123')
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(mocks.userStore.login).toHaveBeenCalledWith('testuser', 'password123')
    expect(mocks.elMessage.success).toHaveBeenCalledWith('登录成功')
    expect(mocks.redirectAfterLogin).toHaveBeenCalled()
  })

  it('登录失败时 ElMessage.error 提示且不跳转', async () => {
    mocks.userStore.login.mockRejectedValue(new Error('登录失败'))
    const wrapper = mountLoginView()
    const inputs = wrapper.findAll('.el-input')
    await inputs[0].setValue('testuser')
    await inputs[1].setValue('wrongpassword')
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(mocks.elMessage.error).toHaveBeenCalledWith('登录失败，请检查用户名和密码')
    expect(mocks.redirectAfterLogin).not.toHaveBeenCalled()
  })
})
