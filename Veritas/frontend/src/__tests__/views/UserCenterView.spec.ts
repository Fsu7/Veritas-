import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import type { UserProfile, UserInfo } from '@/types/user'
import type { SessionDetail } from '@/types/session'

// ============ Mock 基础设施 ============

const mockProfile: UserProfile = {
  educationLevel: 'master',
  researchField: 'NLP',
  knowledgeLevel: 'intermediate',
  preferredStyle: 'balanced'
}

const mockUserInfo: UserInfo = {
  username: 'testuser',
  email: 'test@example.com',
  createdAt: '2024-01-01T00:00:00Z'
}

const mockSessions: SessionDetail[] = [
  {
    sessionId: 's001',
    userId: 'u001',
    topic: 'Multi-Agent 系统综述',
    status: 'completed',
    createdAt: '2024-06-01T10:00:00Z',
    updatedAt: '2024-06-01T11:00:00Z'
  },
  {
    sessionId: 's002',
    userId: 'u001',
    topic: 'LLM 推理能力分析',
    status: 'completed',
    createdAt: '2024-06-02T10:00:00Z',
    updatedAt: '2024-06-02T11:00:00Z'
  }
]

const mocks = vi.hoisted(() => ({
  // userStore mock
  fetchProfile: vi.fn(),
  getUserInfo: vi.fn(),
  saveProfile: vi.fn(),
  routerPush: vi.fn(),
  routerBack: vi.fn(),
  elMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  // sessionStore mock
  fetchSessions: vi.fn(),
  // paperStore mock
  fetchFavorites: vi.fn(),
  // 响应式状态容器（在 beforeEach 中初始化）
  state: null as null | {
    profile: ReturnType<typeof ref<UserProfile | null>>
    userInfo: ReturnType<typeof ref<UserInfo | null>>
    profileVersion: ReturnType<typeof ref<number>>
    favoritesTotal: ReturnType<typeof ref<number>>
  },
  // 路由 query（setupProfile）
  routeQuery: {} as Record<string, string>
}))

vi.mock('@/stores/userStore', () => ({
  useUserStore: vi.fn(() => ({
    get profile() {
      return mocks.state!.profile.value
    },
    get userInfo() {
      return mocks.state!.userInfo.value
    },
    get profileVersion() {
      return mocks.state!.profileVersion.value
    },
    get isLoggedIn() {
      return true
    },
    get hasProfile() {
      return mocks.state!.profile.value !== null
    },
    fetchProfile: mocks.fetchProfile,
    getUserInfo: mocks.getUserInfo,
    saveProfile: mocks.saveProfile
  }))
}))

vi.mock('@/stores/sessionStore', () => ({
  useSessionStore: vi.fn(() => ({
    fetchSessions: mocks.fetchSessions
  }))
}))

vi.mock('@/stores/paperStore', () => ({
  usePaperStore: vi.fn(() => ({
    get favoritesTotal() {
      return mocks.state!.favoritesTotal.value
    },
    fetchFavorites: mocks.fetchFavorites
  }))
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({
    params: {},
    get query() {
      return mocks.routeQuery
    }
  })),
  useRouter: vi.fn(() => ({ push: mocks.routerPush, back: mocks.routerBack }))
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>
  return {
    ...actual,
    ElMessage: mocks.elMessage,
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') }
  }
})

// 桩掉 UserProfileForm 以便直接触发 saved 事件
vi.mock('@/components/common/UserProfileForm.vue', () => ({
  default: {
    name: 'UserProfileForm',
    props: ['initialData'],
    emits: ['saved'],
    template:
      '<div class="mock-user-profile-form"><button class="save-btn" @click="$emit(\'saved\', mockProfile)">保存画像</button></div>',
    setup() {
      return { mockProfile }
    }
  }
}))

import UserCenterView from '@/views/UserCenterView.vue'

// ============ 辅助函数 ============

function mountUserCenterView() {
  return mount(UserCenterView, {
    global: {
      stubs: {
        'el-card': { name: 'ElCard', template: '<div class="el-card"><slot name="header" /><slot /></div>', props: ['shadow'] },
        'el-descriptions': { name: 'ElDescriptions', template: '<div class="el-descriptions"><slot /></div>', props: ['column', 'border'] },
        'el-descriptions-item': { name: 'ElDescriptionsItem', template: '<div class="el-descriptions-item"><slot /></div>', props: ['label'] },
        'el-tag': { name: 'ElTag', template: '<span class="el-tag"><slot /></span>', props: ['type', 'effect'] },
        'el-alert': { name: 'ElAlert', template: '<div class="el-alert" />', props: ['title', 'description', 'type', 'showIcon', 'closable'] },
        'el-link': { name: 'ElLink', template: '<a class="el-link" @click="$emit(\'click\')"><slot /></a>', props: ['type', 'underline'], emits: ['click'] },
        'el-input': {
          name: 'ElInput',
          template: '<input class="el-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" @blur="$emit(\'blur\')" />',
          props: ['modelValue', 'placeholder', 'clearable', 'prefixIcon'],
          emits: ['update:modelValue', 'input', 'clear', 'blur']
        },
        'el-timeline': { name: 'ElTimeline', template: '<div class="el-timeline"><slot /></div>' },
        'el-timeline-item': {
          name: 'ElTimelineItem',
          template: '<div class="el-timeline-item"><slot /></div>',
          props: ['timestamp', 'placement']
        },
        'el-empty': { name: 'ElEmpty', template: '<div class="el-empty" />', props: ['description'] },
        'el-pagination': {
          name: 'ElPagination',
          template: '<div class="el-pagination" />',
          props: ['currentPage', 'pageSize', 'total', 'layout', 'background'],
          emits: ['update:currentPage', 'currentChange']
        }
      },
      directives: {
        loading: {
          mounted() {},
          updated() {}
        }
      }
    }
  })
}

// ============ 测试 ============

describe('UserCenterView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.state = {
      profile: ref<UserProfile | null>(mockProfile),
      userInfo: ref<UserInfo | null>(mockUserInfo),
      profileVersion: ref<number>(0),
      favoritesTotal: ref<number>(0)
    }
    mocks.routeQuery = {}
    mocks.fetchProfile.mockResolvedValue(undefined)
    mocks.getUserInfo.mockResolvedValue(undefined)
    mocks.fetchSessions.mockResolvedValue({ items: [], total: 0, page: 1, size: 10, totalPages: 0 })
    mocks.fetchFavorites.mockResolvedValue(undefined)
    mocks.saveProfile.mockResolvedValue(undefined)
  })

  it('挂载时调用 getUserInfo / fetchProfile / fetchSessions / fetchFavorites', async () => {
    mocks.fetchSessions.mockResolvedValue({ items: mockSessions, total: 2, page: 1, size: 10, totalPages: 1 })
    mountUserCenterView()
    await flushPromises()

    expect(mocks.getUserInfo).toHaveBeenCalled()
    expect(mocks.fetchProfile).toHaveBeenCalled()
    expect(mocks.fetchSessions).toHaveBeenCalledWith({ page: 1, size: 10 })
    expect(mocks.fetchFavorites).toHaveBeenCalledWith(1, 1)
  })

  it('画像保存后调用 fetchProfile 刷新并显示成功提示', async () => {
    const wrapper = mountUserCenterView()
    await flushPromises()

    mocks.fetchProfile.mockClear()
    await wrapper.find('.mock-user-profile-form .save-btn').trigger('click')
    await flushPromises()

    expect(mocks.fetchProfile).toHaveBeenCalled()
    expect(mocks.elMessage.success).toHaveBeenCalledWith('画像保存成功')
  })

  it('历史记录点击跳转 /search?sessionId=xxx', async () => {
    mocks.fetchSessions.mockResolvedValue({ items: mockSessions, total: 2, page: 1, size: 10, totalPages: 1 })
    const wrapper = mountUserCenterView()
    await flushPromises()

    const sessionItems = wrapper.findAll('.user-center-view__session-item')
    expect(sessionItems.length).toBeGreaterThan(0)
    await sessionItems[0].trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith('/search?sessionId=s002')
  })

  it('setupProfile=true 模式保存后跳转 Home', async () => {
    mocks.routeQuery = { setupProfile: 'true' }
    const wrapper = mountUserCenterView()
    await flushPromises()

    await wrapper.find('.mock-user-profile-form .save-btn').trigger('click')
    await flushPromises()

    expect(mocks.routerPush).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('setupProfile=false 模式保存后不跳转 Home', async () => {
    mocks.routeQuery = {}
    const wrapper = mountUserCenterView()
    await flushPromises()

    mocks.routerPush.mockClear()
    await wrapper.find('.mock-user-profile-form .save-btn').trigger('click')
    await flushPromises()

    expect(mocks.routerPush).not.toHaveBeenCalledWith({ name: 'Home' })
  })

  it('空历史记录状态显示 el-empty', async () => {
    mocks.fetchSessions.mockResolvedValue({ items: [], total: 0, page: 1, size: 10, totalPages: 0 })
    const wrapper = mountUserCenterView()
    await flushPromises()

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.find('.el-timeline').exists()).toBe(false)
  })

  it('有历史记录时渲染 el-timeline', async () => {
    mocks.fetchSessions.mockResolvedValue({ items: mockSessions, total: 2, page: 1, size: 10, totalPages: 1 })
    const wrapper = mountUserCenterView()
    await flushPromises()

    expect(wrapper.find('.el-timeline').exists()).toBe(true)
    expect(wrapper.findAll('.el-timeline-item').length).toBe(2)
  })

  it('已设置画像时渲染画像标签', async () => {
    mocks.state!.profile.value = mockProfile
    const wrapper = mountUserCenterView()
    await flushPromises()

    expect(wrapper.find('.user-center-view__profile-tags').exists()).toBe(true)
    const tags = wrapper.findAll('.user-center-view__profile-tag')
    expect(tags.length).toBe(4)
  })

  it('未设置画像时显示"尚未设置画像"提示', async () => {
    mocks.state!.profile.value = null
    const wrapper = mountUserCenterView()
    await flushPromises()

    expect(wrapper.find('.user-center-view__setup-hint').exists()).toBe(true)
    expect(wrapper.find('.user-center-view__profile-tags').exists()).toBe(false)
  })

  it('setupProfile=true 时显示欢迎提示 alert', async () => {
    mocks.routeQuery = { setupProfile: 'true' }
    const wrapper = mountUserCenterView()
    await flushPromises()

    // 编辑画像卡片中应包含欢迎 alert（setup-hint 类）
    const alerts = wrapper.findAll('.user-center-view__setup-hint')
    expect(alerts.length).toBeGreaterThanOrEqual(1)
  })

  it('历史记录加载失败时 ElMessage.error 提示', async () => {
    mocks.fetchSessions.mockRejectedValue(new Error('网络错误'))
    mountUserCenterView()
    await flushPromises()

    expect(mocks.elMessage.error).toHaveBeenCalledWith('历史记录加载失败')
  })
})
