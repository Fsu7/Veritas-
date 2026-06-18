import http from './index'
import type { LoginResponse, UserProfile, ProfileResponse, UserInfo } from '@/types/user'

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
    http.post(`/users/${userId}/profile`, data),

  updateProfile: (userId: string, data: UserProfile): Promise<ProfileResponse> =>
    http.put(`/users/${userId}/profile`, data)
}
