import http from './index'
import type { LoginResponse, UserProfile, ProfileResponse, UserInfo } from '@/types/user'

/**
 * 将 camelCase 对象转为 snake_case，与后端 Jackson SNAKE_CASE 策略对齐。
 * 仅用于请求体（响应体由 axios 拦截器统一做 snake→camel 转换）。
 */
function toSnakeCase(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(obj)) {
    const snakeKey = key.replace(/([A-Z])/g, '_$1').toLowerCase()
    result[snakeKey] = value
  }
  return result
}

export const userApi = {
  register: (data: { username: string; email: string; password: string }) =>
    http.post('/users/register', data),

  login: (data: { username: string; password: string }): Promise<LoginResponse> =>
    http.post('/users/login', data),

  /**
   * 退出登录：通知后端将当前 Token 加入黑名单
   * JWT 在请求拦截器中自动注入 Authorization 头
   */
  logout: (): Promise<void> =>
    http.post('/users/logout'),

  getUserInfo: (userId: string): Promise<UserInfo> =>
    http.get(`/users/${userId}`),

  getProfile: (userId: string): Promise<ProfileResponse> =>
    http.get(`/users/${userId}/profile`),

  createProfile: (userId: string, data: UserProfile): Promise<ProfileResponse> =>
    http.post(`/users/${userId}/profile`, toSnakeCase(data as unknown as Record<string, unknown>)),

  updateProfile: (userId: string, data: UserProfile): Promise<ProfileResponse> =>
    http.put(`/users/${userId}/profile`, toSnakeCase(data as unknown as Record<string, unknown>))
}
