# Cacheable注解修复与DDL模式调整

## 功能描述
- 修复了 `@Cacheable(sync=true)` 与 `unless` 属性不兼容导致的所有缓存方法 500 错误
- 修复了 JPA `ddl-auto=validate` 模式下表结构不匹配导致后端启动失败
- 修复了前端 `ProfileUpdateRequest` camelCase 字段无法被后端 Jackson SNAKE_CASE 策略反序列化的问题
- 修复了新用户无画像时 `getProfile` 返回 404 导致前端"请求的资源不存在"错误

## 实现逻辑
- 移除 4 处 `@Cacheable` 注解中的 `unless="#result==null"`（保留 `sync=true` 防缓存击穿）
- 将 `application.yml` 中 `ddl-auto` 从 `validate` 改为 `update`
- 前端 `userApi` 添加 `toSnakeCase` 转换函数，发送画像请求前将 camelCase 转 snake_case
- 前端 `fetchProfile` 捕获 404 时不抛异常，设置 `profile=null` 表示用户尚未设置画像
- 前端 axios 拦截器对 `/profile` 路径的 404 不显示错误提示

## 接口变更
### Request
```json
// PUT /api/users/{userId}/profile
// 修改前（camelCase，后端无法反序列化）
{
  "educationLevel": "master",
  "researchField": "NLP",
  "knowledgeLevel": "intermediate",
  "preferredStyle": "balanced"
}
// 修改后（snake_case，与后端 Jackson 策略对齐）
{
  "education_level": "master",
  "research_field": "NLP",
  "knowledge_level": "intermediate",
  "preferred_style": "balanced"
}
```

### Response
```json
// GET /api/users/{userId}/profile（有画像）
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "usr_test_001",
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced"
  }
}
// GET /api/users/{userId}/profile（无画像，404）
{
  "code": 404,
  "message": "UserProfile not found: usr_xxx"
}
```

## 测试结果
- 测试场景1：登录 test_user 后访问"我的收藏"→ 200 正常返回收藏列表
- 测试场景2：登录 test_user 后访问"用户中心"→ 200 正常返回用户信息和画像
- 测试场景3：新注册用户（无画像）访问"用户中心"→ 页面正常展示"尚未设置画像"提示
- 测试场景4：编辑画像保存→ 200 成功保存
- 是否通过：是

## 相关文件
- `backend/src/main/java/com/literatureassistant/service/UserService.java`
- `backend/src/main/java/com/literatureassistant/service/FavoriteService.java`
- `backend/src/main/java/com/literatureassistant/service/AnalysisService.java`
- `backend/src/main/java/com/literatureassistant/service/SessionService.java`
- `backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`
- `backend/src/main/resources/application.yml`
- `frontend/src/api/user.ts`
- `frontend/src/api/index.ts`
- `frontend/src/stores/userStore.ts`
