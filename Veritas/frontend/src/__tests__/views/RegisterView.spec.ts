import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ============ Mock 基础设施 ============

const mocks = vi.hoisted(() => ({
  userStore: {
    register: vi.fn()
  },
  routerPush: vi.fn(),
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

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: {}, query: {} })),
  useRouter: vi.fn(() => ({ push: mocks.routerPush, back: vi.fn() }))
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>
  return {
    ...actual,
    ElMessage: mocks.elMessage,
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') }
  }
})

import RegisterView from '@/views/RegisterView.vue'

// ============ 辅助函数 ============

function mountRegisterView() {
  return mount(RegisterView, {
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

describe('RegisterView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.userStore.register.mockResolvedValue(undefined)
    mocks.mockValidate.mockResolvedValue(true)
  })

  it('渲染注册表单标题', () => {
    const wrapper = mountRegisterView()
    expect(wrapper.find('.register-view__title').text()).toContain('创建新账号')
  })

  it('渲染去登录链接', () => {
    const wrapper = mountRegisterView()
    expect(wrapper.find('.register-view__link').text()).toContain('去登录')
  })

  it('空字段表单验证失败时不调用 register', async () => {
    mocks.mockValidate.mockResolvedValue(false)
    const wrapper = mountRegisterView()
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(mocks.userStore.register).not.toHaveBeenCalled()
    expect(mocks.routerPush).not.toHaveBeenCalled()
  })

  it('注册成功调用 userStore.register 并跳转登录页', async () => {
    const wrapper = mountRegisterView()
    const inputs = wrapper.findAll('.el-input')
    await inputs[0].setValue('newuser')
    await inputs[1].setValue('newuser@example.com')
    await inputs[2].setValue('password123')
    await inputs[3].setValue('password123')
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(mocks.userStore.register).toHaveBeenCalledWith(
      'newuser',
      'newuser@example.com',
      'password123'
    )
    expect(mocks.elMessage.success).toHaveBeenCalledWith('注册成功，请登录')
    expect(mocks.routerPush).toHaveBeenCalledWith('/login')
  })

  it('注册失败时 ElMessage.error 提示且不跳转', async () => {
    mocks.userStore.register.mockRejectedValue(new Error('用户名已存在'))
    const wrapper = mountRegisterView()
    const inputs = wrapper.findAll('.el-input')
    await inputs[0].setValue('existinguser')
    await inputs[1].setValue('user@example.com')
    await inputs[2].setValue('password123')
    await inputs[3].setValue('password123')
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(mocks.elMessage.error).toHaveBeenCalledWith('注册失败，请重试')
    expect(mocks.routerPush).not.toHaveBeenCalled()
  })

  it('注册成功后 loading 状态恢复为 false', async () => {
    const wrapper = mountRegisterView()
    await wrapper.find('.el-button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.el-button').attributes('loading')).toBeUndefined()
  })
})
