import http from './index'
import type { LoginResponse, UserProfile, ProfileResponse, UserInfo } from '@/types/user'

export const userApi = {
  register: (data: { username: string; email: string; password: string }) =>
    http.post('/users/register', data),

  login: (data: { username: string; password: string }): Promise<LoginResponse> =>
    http.post('/users/login', data),

  getUserInfo: (userId: string): Promise<UserInfo> =>
    http.get(`/users/${userId}`),

  getProfile: (userId: string): Promise<ProfileResponse> =>
    http.get(`/users/${userId}/profile`),

  createProfile: (userId: string, data: UserProfile): Promise<ProfileResponse> =>
    http.post(`/users/${userId}/profile`, data),

  updateProfile: (userId: string, data: UserProfile): Promise<ProfileResponse> =>
    http.put(`/users/${userId}/profile`, data)
}
