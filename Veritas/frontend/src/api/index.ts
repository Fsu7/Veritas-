import axios from 'axios'
import type { ApiResponse } from '@/types/common'
import { ElMessage } from 'element-plus'

const AUTH_WHITELIST = ['/users/login', '/users/register', '/users/logout']

function isAuthRequest(url: string | undefined): boolean {
  if (!url) return false
  return AUTH_WHITELIST.some(path => url.includes(path))
}

/** 并发 401 防抖标志：防止多个并发请求同时触发 logout + 重复提示 */
let isRefreshing = false

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
    // Blob / ArrayBuffer 响应：跳过 JSON 转换和 code 校验，直接返回原始数据
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response.data
    }
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
        // 登录/注册/退出接口的 401：显示具体错误，不触发全局跳转
        const message = error.response?.data?.message || '用户名或密码错误'
        ElMessage.error(message)
      } else if (!isRefreshing) {
        // 并发 401 防抖：仅首个请求执行 logout + 跳转，后续并发请求直接 reject
        isRefreshing = true
        const { useUserStore } = await import('@/stores/userStore')
        const userStore = useUserStore()
        // 区分主动退出与 Token 过期
        if (userStore.isManualLogout) {
          // 主动退出触发的 401：不显示"登录过期"提示，不重复跳转
          // logout 流程已处理本地清理和跳转
        } else {
          // Token 过期：清理本地状态并跳转登录页
          // 不调用后端 logout API（Token 已失效），仅清理本地
          userStore.isManualLogout = true
          // 直接清理本地状态，避免再次调用已失效的 API
          await userStore.logout()
          const { default: router } = await import('@/router')
          router.push('/login')
          ElMessage.error('登录已过期，请重新登录')
        }
        isRefreshing = false
      }
    } else if (error.response?.status === 403) {
      ElMessage.error('无权限访问')
    } else if (error.response?.status === 404) {
      // 画像查询 404 = 用户尚未设置画像，属于正常状态，不显示错误提示
      const url = error.config?.url || ''
      if (!url.includes('/profile')) {
        ElMessage.error('请求的资源不存在')
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error(error.response?.data?.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

export default http
