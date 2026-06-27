import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { userApi } from '@/api/user'
import type { UserProfile, LoginResponse, UserInfo } from '@/types/user'

const TOKEN_KEY = 'token'
const USER_ID_KEY = 'userId'
const USERNAME_KEY = 'username'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const userId = ref<string>(localStorage.getItem(USER_ID_KEY) || '')
  const username = ref<string>(localStorage.getItem(USERNAME_KEY) || '')
  const profile = ref<UserProfile | null>(null)
  const userInfo = ref<UserInfo | null>(null)
  // 画像版本号：每次保存画像后自增，用于触发依赖画像的视图刷新
  const profileVersion = ref(0)
  // 主动退出标志：用于区分 401 是主动退出还是 Token 过期
  const isManualLogout = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const hasProfile = computed(() => !!profile.value)

  function persistLoginData(data: LoginResponse) {
    token.value = data.token
    userId.value = data.userId
    username.value = data.username
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_ID_KEY, data.userId)
    localStorage.setItem(USERNAME_KEY, data.username)
  }

  async function login(user: string, password: string) {
    const res = await userApi.login({ username: user, password })
    persistLoginData(res)
    if (res.hasProfile) {
      await fetchProfile()
    }
  }

  /**
   * 退出登录（异步）
   * - 标记 isManualLogout 用于 401 拦截器区分主动退出与 Token 过期
   * - 调用后端 logout API 将 Token 加入黑名单
   * - 即使 API 失败也清理本地状态，确保用户能退出
   */
  async function logout() {
    isManualLogout.value = true
    try {
      await userApi.logout()
    } catch (e: unknown) {
      // 后端 logout 失败不阻塞本地清理，仅记录警告
      console.warn('logout API failed:', e)
    } finally {
      token.value = ''
      userId.value = ''
      username.value = ''
      profile.value = null
      userInfo.value = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_ID_KEY)
      localStorage.removeItem(USERNAME_KEY)
    }
  }

  async function fetchProfile() {
    try {
      const res = await userApi.getProfile(userId.value)
      profile.value = {
        educationLevel: res.educationLevel,
        researchField: res.researchField,
        knowledgeLevel: res.knowledgeLevel,
        preferredStyle: res.preferredStyle
      }
    } catch (e: unknown) {
      // 404 = 用户尚未设置画像，属于正常状态，静默处理不抛出异常
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        profile.value = null
        return
      }
      throw e
    }
  }

  async function saveProfile(data: UserProfile) {
    if (hasProfile.value) {
      const res = await userApi.updateProfile(userId.value, data)
      profile.value = {
        educationLevel: res.educationLevel,
        researchField: res.researchField,
        knowledgeLevel: res.knowledgeLevel,
        preferredStyle: res.preferredStyle
      }
    } else {
      const res = await userApi.createProfile(userId.value, data)
      profile.value = {
        educationLevel: res.educationLevel,
        researchField: res.researchField,
        knowledgeLevel: res.knowledgeLevel,
        preferredStyle: res.preferredStyle
      }
    }
    // 画像保存成功后自增版本号，触发依赖画像的视图刷新
    profileVersion.value++
  }

  async function getUserInfo() {
    const res = await userApi.getUserInfo(userId.value)
    userInfo.value = res
  }

  async function register(user: string, email: string, password: string) {
    await userApi.register({ username: user, email, password })
  }

  return {
    token, userId, username, profile, userInfo,
    profileVersion, isManualLogout,
    isLoggedIn, hasProfile,
    login, logout, fetchProfile, saveProfile, getUserInfo, register
  }
})
