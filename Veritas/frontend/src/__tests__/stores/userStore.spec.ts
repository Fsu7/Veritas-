import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// 隔离外部依赖：mock @/api/user 模块
vi.mock('@/api/user', () => ({
  userApi: {
    login: vi.fn(),
    logout: vi.fn(),
    getProfile: vi.fn(),
    createProfile: vi.fn(),
    updateProfile: vi.fn(),
    getUserInfo: vi.fn(),
    register: vi.fn()
  }
}))

import { useUserStore } from '@/stores/userStore'
import { userApi } from '@/api/user'
import type { UserProfile, ProfileResponse, UserInfo, LoginResponse } from '@/types/user'

const mockProfile: UserProfile = {
  educationLevel: 'master',
  researchField: 'NLP',
  knowledgeLevel: 'intermediate',
  preferredStyle: 'balanced'
}

const mockProfileResponse: ProfileResponse = {
  educationLevel: 'master',
  researchField: 'NLP',
  knowledgeLevel: 'intermediate',
  preferredStyle: 'balanced'
}

const mockUserInfo: UserInfo = {
  username: 'alice',
  email: 'alice@example.com',
  createdAt: '2024-01-01T00:00:00Z'
}

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('login 成功后 token/userId/username 持久化到 localStorage，且 hasProfile=true 时调用 fetchProfile', async () => {
      const loginRes: LoginResponse = {
        token: 'jwt-token-123',
        userId: 'u_001',
        username: 'alice',
        hasProfile: true
      }
      ;(userApi.login as ReturnType<typeof vi.fn>).mockResolvedValue(loginRes)
      ;(userApi.getProfile as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfileResponse)

      const store = useUserStore()
      await store.login('alice', 'pwd123')

      // 状态正确
      expect(store.token).toBe('jwt-token-123')
      expect(store.userId).toBe('u_001')
      expect(store.username).toBe('alice')

      // localStorage 持久化
      expect(localStorage.getItem('token')).toBe('jwt-token-123')
      expect(localStorage.getItem('userId')).toBe('u_001')
      expect(localStorage.getItem('username')).toBe('alice')

      // 调用 fetchProfile → getProfile(userId)
      expect(userApi.getProfile).toHaveBeenCalledWith('u_001')
      // profile 已更新
      expect(store.profile).toEqual(mockProfile)
    })

    it('login 成功后 hasProfile=false 不调用 fetchProfile', async () => {
      const loginRes: LoginResponse = {
        token: 'jwt-token-456',
        userId: 'u_002',
        username: 'bob',
        hasProfile: false
      }
      ;(userApi.login as ReturnType<typeof vi.fn>).mockResolvedValue(loginRes)

      const store = useUserStore()
      await store.login('bob', 'pwd456')

      // 状态与持久化仍然生效
      expect(store.token).toBe('jwt-token-456')
      expect(localStorage.getItem('token')).toBe('jwt-token-456')

      // 不应调用 getProfile
      expect(userApi.getProfile).not.toHaveBeenCalled()
      // profile 仍为 null
      expect(store.profile).toBeNull()
    })
  })

  describe('logout', () => {
    it('logout 成功后清除状态 + localStorage + 设置 isManualLogout=true', async () => {
      // 先准备已登录状态
      localStorage.setItem('token', 'old-token')
      localStorage.setItem('userId', 'u_001')
      localStorage.setItem('username', 'alice')
      ;(userApi.logout as ReturnType<typeof vi.fn>).mockResolvedValue(undefined)

      const store = useUserStore()
      // 模拟已登录
      store.token = 'old-token'
      store.userId = 'u_001'
      store.username = 'alice'
      store.profile = mockProfile
      store.userInfo = mockUserInfo

      await store.logout()

      // 状态清空
      expect(store.token).toBe('')
      expect(store.userId).toBe('')
      expect(store.username).toBe('')
      expect(store.profile).toBeNull()
      expect(store.userInfo).toBeNull()

      // localStorage 清空
      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('userId')).toBeNull()
      expect(localStorage.getItem('username')).toBeNull()

      // 主动退出标志
      expect(store.isManualLogout).toBe(true)

      // 调用了 logout API
      expect(userApi.logout).toHaveBeenCalled()
    })

    it('logout API 失败也清理本地状态', async () => {
      ;(userApi.logout as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network error'))

      const store = useUserStore()
      store.token = 'old-token'
      store.userId = 'u_001'
      store.username = 'alice'
      store.profile = mockProfile
      store.userInfo = mockUserInfo
      localStorage.setItem('token', 'old-token')

      // 不应抛出
      await expect(store.logout()).resolves.toBeUndefined()

      // 状态仍被清理
      expect(store.token).toBe('')
      expect(store.userId).toBe('')
      expect(store.username).toBe('')
      expect(store.profile).toBeNull()
      expect(store.userInfo).toBeNull()

      // localStorage 仍被清理
      expect(localStorage.getItem('token')).toBeNull()

      // 主动退出标志仍设置
      expect(store.isManualLogout).toBe(true)
    })
  })

  describe('fetchProfile', () => {
    it('fetchProfile 成功更新 profile', async () => {
      ;(userApi.getProfile as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfileResponse)

      const store = useUserStore()
      store.userId = 'u_001'

      await store.fetchProfile()

      expect(userApi.getProfile).toHaveBeenCalledWith('u_001')
      expect(store.profile).toEqual({
        educationLevel: 'master',
        researchField: 'NLP',
        knowledgeLevel: 'intermediate',
        preferredStyle: 'balanced'
      })
    })
  })

  describe('saveProfile', () => {
    it('已有 profile 时调用 updateProfile + profileVersion 自增', async () => {
      ;(userApi.updateProfile as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfileResponse)

      const store = useUserStore()
      store.userId = 'u_001'
      // 预置已有 profile，使 hasProfile=true
      store.profile = {
        educationLevel: 'undergraduate',
        researchField: 'CV',
        knowledgeLevel: 'beginner',
        preferredStyle: 'simple'
      }
      const beforeVersion = store.profileVersion

      await store.saveProfile(mockProfile)

      // 调用 updateProfile 而非 createProfile
      expect(userApi.updateProfile).toHaveBeenCalledWith('u_001', mockProfile)
      expect(userApi.createProfile).not.toHaveBeenCalled()

      // profile 更新为接口返回值
      expect(store.profile).toEqual(mockProfile)

      // 版本号自增
      expect(store.profileVersion).toBe(beforeVersion + 1)
    })

    it('无 profile 时调用 createProfile + profileVersion 自增', async () => {
      ;(userApi.createProfile as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfileResponse)

      const store = useUserStore()
      store.userId = 'u_001'
      // profile 为 null，使 hasProfile=false
      store.profile = null
      const beforeVersion = store.profileVersion

      await store.saveProfile(mockProfile)

      // 调用 createProfile 而非 updateProfile
      expect(userApi.createProfile).toHaveBeenCalledWith('u_001', mockProfile)
      expect(userApi.updateProfile).not.toHaveBeenCalled()

      // profile 更新为接口返回值
      expect(store.profile).toEqual(mockProfile)

      // 版本号自增
      expect(store.profileVersion).toBe(beforeVersion + 1)
    })
  })

  describe('计算属性', () => {
    it('isLoggedIn 在有/无 token 时正确返回', () => {
      const store = useUserStore()
      // 初始无 token
      store.token = ''
      expect(store.isLoggedIn).toBe(false)

      store.token = 'some-token'
      expect(store.isLoggedIn).toBe(true)
    })

    it('hasProfile 在有/无 profile 时正确返回', () => {
      const store = useUserStore()
      // 初始无 profile
      store.profile = null
      expect(store.hasProfile).toBe(false)

      store.profile = mockProfile
      expect(store.hasProfile).toBe(true)
    })
  })
})
