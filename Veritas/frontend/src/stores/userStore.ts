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

  function logout() {
    token.value = ''
    userId.value = ''
    username.value = ''
    profile.value = null
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_ID_KEY)
    localStorage.removeItem(USERNAME_KEY)
  }

  async function fetchProfile() {
    const res = await userApi.getProfile(userId.value)
    profile.value = {
      educationLevel: res.educationLevel,
      researchField: res.researchField,
      knowledgeLevel: res.knowledgeLevel,
      preferredStyle: res.preferredStyle
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
    isLoggedIn, hasProfile,
    login, logout, fetchProfile, saveProfile, getUserInfo, register
  }
})
