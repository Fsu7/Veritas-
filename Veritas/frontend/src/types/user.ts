export interface UserProfile {
  educationLevel: 'undergraduate' | 'master' | 'phd' | 'faculty'
  researchField: string
  knowledgeLevel: 'beginner' | 'intermediate' | 'advanced' | 'expert'
  preferredStyle: 'simple' | 'balanced' | 'technical'
}

export interface LoginResponse {
  token: string
  userId: string
  username: string
  hasProfile: boolean
}

export interface ProfileResponse {
  educationLevel: string
  researchField: string
  knowledgeLevel: string
  preferredStyle: string
}
