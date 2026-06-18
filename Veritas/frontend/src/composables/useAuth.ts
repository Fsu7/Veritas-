import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/userStore'

export function useAuth() {
  const router = useRouter()
  const userStore = useUserStore()

  const isLoggedIn = computed(() => userStore.isLoggedIn)
  const hasProfile = computed(() => userStore.hasProfile)

  function requireAuth(redirectPath?: string): boolean {
    if (!isLoggedIn.value) {
      router.push({
        name: 'Login',
        query: { redirect: redirectPath || router.currentRoute.value.fullPath }
      })
      return false
    }
    return true
  }

  function redirectIfAuthenticated(fallbackPath: string = '/'): void {
    if (isLoggedIn.value) {
      router.push(fallbackPath)
    }
  }

  async function redirectAfterLogin(): Promise<void> {
    const redirect = router.currentRoute.value.query.redirect as string
    if (!userStore.hasProfile) {
      router.push({ name: 'UserCenter', query: { setupProfile: 'true' } })
    } else if (redirect) {
      router.push(redirect)
    } else {
      router.push({ name: 'Home' })
    }
  }

  async function logout(): Promise<void> {
    await userStore.logout()
    router.push({ name: 'Login' })
  }

  return {
    isLoggedIn,
    hasProfile,
    requireAuth,
    redirectIfAuthenticated,
    redirectAfterLogin,
    logout
  }
}
