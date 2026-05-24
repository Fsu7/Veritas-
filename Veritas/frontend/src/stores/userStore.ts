import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserProfile, LoginResponse } from '@/types/user'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userId = ref<string>(localStorage.getItem('userId') || '')
  const username = ref<string>(localStorage.getItem('username') || '')
  const profile = ref<UserProfile | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const hasProfile = computed(() => !!profile.value)

  function setLoginData(data: LoginResponse) {
    token.value = data.token
    userId.value = data.userId
    username.value = data.username
    localStorage.setItem('token', data.token)
    localStorage.setItem('userId', data.userId)
    localStorage.setItem('username', data.username)
  }

  function logout() {
    token.value = ''
    userId.value = ''
    username.value = ''
    profile.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    localStorage.removeItem('username')
  }

  async function fetchProfile() {
    // TODO: 调用API获取用户画像
  }

  async function saveProfile(_data: UserProfile) {
    // TODO: 调用API保存用户画像
  }

  return {
    token, userId, username, profile,
    isLoggedIn, hasProfile,
    setLoginData, logout, fetchProfile, saveProfile
  }
})
