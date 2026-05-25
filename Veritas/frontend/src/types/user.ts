/**
 * 用户画像4维度
 * JSON字段映射: educationLevel ↔ education_level, knowledgeLevel ↔ knowledge_level,
 * preferredStyle ↔ preferred_style
 */
export interface UserProfile {
  educationLevel: 'undergraduate' | 'master' | 'phd' | 'faculty'
  researchField: string
  knowledgeLevel: 'beginner' | 'intermediate' | 'advanced' | 'expert'
  preferredStyle: 'simple' | 'balanced' | 'technical'
}

/**
 * 登录接口响应
 * JSON字段映射: hasProfile ↔ has_profile
 */
export interface LoginResponse {
  token: string
  userId: string
  username: string
  hasProfile: boolean
}

/**
 * 画像接口响应
 * JSON字段映射: educationLevel ↔ education_level, knowledgeLevel ↔ knowledge_level,
 * preferredStyle ↔ preferred_style
 */
export interface ProfileResponse {
  educationLevel: UserProfile['educationLevel']
  researchField: string
  knowledgeLevel: UserProfile['knowledgeLevel']
  preferredStyle: UserProfile['preferredStyle']
}
