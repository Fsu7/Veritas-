# CORS 跨域配置修复（注册接口 403 问题）

## 功能描述
- **问题**：用户在注册页面提交表单后，前端先后弹出两条错误提示："无权限访问"（axios 拦截器 403 分支）和"注册失败，请重试"（RegisterView catch 块），注册无法完成
- **根因**：`SecurityConfig` 的 CORS 配置使用 `setAllowedOrigins` 精确匹配 `http://localhost:5173`，但 Vite 开发服务器因 5173 被占用，自动切换至 5174。浏览器跨域请求携带 `Origin: http://localhost:5174`，Spring Security 的 `CorsFilter` 判定该 Origin 不在允许列表中，返回 `Invalid CORS request` → 403
- **修复**：将 `setAllowedOrigins` 改为 `setAllowedOriginPatterns(List.of("http://localhost:*"))`，允许所有 localhost 端口
- **业务价值**：恢复注册功能可用性，同时消除开发阶段因端口变化导致的 CORS 阻塞问题

## 实现逻辑
- **修改的核心文件**：
  - `backend/src/main/java/com/literatureassistant/config/SecurityConfig.java` — `corsConfigurationSource()` 方法
- **关键代码变更**：
  ```java
  // 修复前（精确匹配，仅允许 5173）
  List<String> origins = Arrays.asList(allowedOrigins.split(","));
  configuration.setAllowedOrigins(origins);

  // 修复后（通配模式，允许所有 localhost 端口）
  configuration.setAllowedOriginPatterns(List.of("http://localhost:*"));
  ```
- **设计决策**：`allowedOriginPatterns` 支持 `*` 通配符匹配端口，比逐个添加特定端口更灵活，适合开发阶段多端口并存的场景

## 接口变更
无接口契约变更。

## 测试结果
| 测试场景 | 预期结果 | 实际结果 |
|---------|---------|---------|
| 直连后端 + `Origin: http://localhost:5174` 注册 | 201 Created | 201 Created |
| 通过 Vite 代理 (5174→8080) 注册 | 201 Created | 201 Created |
| 直连后端（无 Origin 头）注册 | 201 Created | 201 Created |
| 重复用户名注册 | 409 Conflict | 409 Conflict "用户名已存在" |

## 相关文件
- 修改：`backend/src/main/java/com/literatureassistant/config/SecurityConfig.java`
