import axios from 'axios'
import type { ApiResponse } from '@/types/common'
import { ElMessage } from 'element-plus'

const AUTH_WHITELIST = ['/users/login', '/users/register']

function isAuthRequest(url: string | undefined): boolean {
  if (!url) return false
  return AUTH_WHITELIST.some(path => url.includes(path))
}

/**
 * 将后端 snake_case 字段递归转换为 camelCase。
 * 后端 application.yml 配置了 property-naming-strategy: SNAKE_CASE，
 * Java DTO (camelCase) 序列化时强制输出 snake_case，前端需要做适配。
 * 示例：{ user_id, has_profile, created_at } → { userId, hasProfile, createdAt }
 */
function snakeToCamel<T = unknown>(input: T): T {
  if (input === null || input === undefined) return input
  if (typeof input !== 'object') return input
  if (input instanceof Date || input instanceof RegExp || input instanceof File) return input
  if (Array.isArray(input)) {
    return input.map((item) => snakeToCamel(item)) as unknown as T
  }
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    const camelKey = key.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase())
    result[camelKey] = snakeToCamel(value)
  }
  return result as T
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

http.interceptors.request.use(
  async (config) => {
    if (isAuthRequest(config.url)) {
      return config
    }
    const { useUserStore } = await import('@/stores/userStore')
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

http.interceptors.response.use(
  (response) => {
    const data = snakeToCamel(response.data) as ApiResponse<unknown>
    if (data.code === 200) {
      return data.data as ReturnType<typeof response.data>
    }
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message))
  },
  async (error) => {
    if (error.response?.status === 401) {
      if (isAuthRequest(error.config?.url)) {
        const message = error.response?.data?.message || '用户名或密码错误'
        ElMessage.error(message)
      } else {
        const { useUserStore } = await import('@/stores/userStore')
        const { default: router } = await import('@/router')
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
      }
    } else if (error.response?.status === 403) {
      ElMessage.error('无权限访问')
    } else if (error.response?.status === 404) {
      ElMessage.error('请求的资源不存在')
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error(error.response?.data?.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

export default http
