export interface SessionResponse {
  sessionId: string
  topic: string
  status: string
  createdAt: string
}

export interface SessionDetail {
  sessionId: string
  userId: string
  topic: string
  status: 'active' | 'completed' | 'expired'
  createdAt: string
  updatedAt: string
}
