# 07 — 编码规范与安全

> 加载时机：编写任何代码前必读，确保代码风格一致、安全合规。
> 关联文件：[02-tech-stack.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/02-tech-stack.md)

---

## 1 命名规范

| 对象 | Java | Python | TypeScript |
|------|------|--------|------------|
| 类名 | PascalCase | PascalCase | PascalCase |
| 方法/函数 | camelCase | snake_case | camelCase |
| 变量 | camelCase | snake_case | camelCase |
| 常量 | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE |
| 文件名 | PascalCase.java | snake_case.py | PascalCase.vue |
| 枚举值 | UPPER_SNAKE_CASE | lower_case | PascalCase |
| 配置键 | kebab-case | UPPER_SNAKE_CASE | camelCase |
| 数据库表/列 | snake_case | — | — |

**跨系统字段转换**: Java camelCase ↔ Python/JSON snake_case（通过@JsonProperty / Pydantic field alias）

---

## 2 Java后端规范

- **分层架构**: Controller → Service → Repository → Client，禁止跨层调用
- **Entity与DTO分离**: 禁止直接返回Entity给前端
- **异常处理**: 全局@RestControllerAdvice + BusinessException体系
- **缓存**: @Cacheable/@CacheEvict + Cache-Aside
- **事务**: @Transactional，方法粒度，避免大事务
- **Entity注解**: @Data @NoArgsConstructor @Builder + @PrePersist

---

## 3 Python AI服务规范

- **FastAPI**: 路由在api/endpoints/，逻辑在services/，模型在models/schemas.py
- **Agent统一接口**: execute(state) → state，超时30s，异常不阻塞后续Agent
- **Prompt管理**: 模板存prompts/目录，使用string.Template变量替换
- **配置**: pydantic-settings BaseSettings + .env
- **异步**: I/O用async/await，CPU密集用run_in_executor

---

## 4 前端规范

- **组件**: `<script setup lang="ts">` + Composition API + scoped样式
- **状态管理**: Pinia setup store风格，按业务域划分
- **API调用**: Axios实例统一配置，请求拦截器注入JWT，响应拦截器统一错误处理
- **SSE**: useSSE composable封装，自动重连(3s间隔，最多5次)
- **路由**: 懒加载 + meta.requiresAuth + 全局前置守卫
- **命名**: 页面{Name}View.vue，组件{Name}.vue，Store{domain}Store.ts，组合函数use{Name}.ts

---

## 5 Git规范

- **分支**: main → develop → feature/xxx | fix/xxx | refactor/xxx
- **Commit**: `<type>(<scope>): <subject>` — feat/fix/docs/style/refactor/perf/test/chore
- **.gitignore**: .env, node_modules/, target/, __pycache__/, models/, data/vector_db/

---

## 6 安全规范

| 安全项 | 措施 |
|--------|------|
| 密码存储 | BCrypt哈希，盐值随机 |
| 认证 | JWT Token (24h有效期) + Redis黑名单 |
| 传输加密 | 生产环境HTTPS |
| SQL注入防护 | JPA参数化查询，禁止SQL拼接 |
| XSS防护 | 前端输入转义 |
| 数据隔离 | 用户只能访问自己的会话和分析结果（WHERE user_id = currentUserId） |
| 敏感配置 | .env环境变量注入，不硬编码 |
| AI内容标注 | 生成内容标注"AI生成，仅供参考" |
