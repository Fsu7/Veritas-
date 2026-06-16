# 技术教学文档 — CORS 跨域配置修复

## 开发思路

### 问题排查过程

1. **接收报障**：用户反馈注册时弹出"无权限访问"和"注册失败，请重试"
2. **追踪前端错误源**：`frontend/src/api/index.ts` 拦截器：
   - `error.response?.status === 403` → `ElMessage.error('无权限访问')`
   - `RegisterView.vue` catch 块 → `ElMessage.error('注册失败，请重试')`
   - 确认后端返回 403 HTTP 状态码
3. **排除 Spring Security 授权问题**：`SecurityConfig` 中 `/api/users/register` 已配置 `permitAll()`，且 `JwtAuthFilter` 白名单包含该路径
4. **直接测试后端**：
   - 不带 Origin 头 → 201 成功
   - 带 `Origin: http://localhost:5174` → 403 `Invalid CORS request`
   - 确认是 Spring Security 的 CORS 过滤器拒绝
5. **定位端口差异**：CORS 配置中 `allowedOrigins` 仅包含 `http://localhost:5173`，而前端实际运行在 5174

### 技术选型考虑

`Spring Security` 的 `CorsConfiguration` 提供两种 Origin 匹配方式：
- **`setAllowedOrigins`**：精确字符串匹配，不支持通配符，配合 `setAllowCredentials(true)` 时不能用 `*`
- **`setAllowedOriginPatterns`**：支持 `*` 通配符模式匹配，可灵活匹配多端口

选择 `setAllowedOriginPatterns` 的原因：开发阶段可能涉及多端口（5173/5174/任意），需要一个灵活且安全的方案。

## 实现步骤

1. 打开 `SecurityConfig.java`，定位 `corsConfigurationSource()` 方法
2. 将 `setAllowedOrigins` 调用替换为 `setAllowedOriginPatterns(List.of("http://localhost:*"))`
3. 移除不再需要的 `allowedOrigins` 字段计算逻辑
4. 重启后端服务
5. curl 带 Origin 头测试注册接口，确认 201 返回
6. curl 经 Vite 代理测试全链路，确认 201 返回

## 解决了什么问题

| 维度 | 说明 |
|------|------|
| 核心问题 | CORS Origin 精确匹配导致端口变化时 403 |
| 解决方案对比 | `setAllowedOrigins` 需逐个添加端口 → `setAllowedOriginPatterns` 通配 localhost 所有端口 |
| 最终方案优势 | 一次配置覆盖所有 localhost 端口，无需随端口变化反复修改 |

## 变更内容

### 修改文件
- `backend/src/main/java/com/literatureassistant/config/SecurityConfig.java`
  - 第 67-70 行：CORS origin 配置从精确匹配改为通配模式

### 配置变更
无需配置变更（`application.yml` 中 `cors.allowed-origins` 配置项现在仅作为兜底，实际 CORS 行为由代码中 `setAllowedOriginPatterns` 控制）

## 关键技术点

### CORS 在 Vite 代理下的行为
- 浏览器向 `localhost:5174/api/...` 发起请求，对浏览器而言是**同源请求**
- Vite 的 `http-proxy` 转发到 `localhost:8080`，**会保留浏览器发送的 `Origin` 头**
- `changeOrigin: true` 仅改变 `Host` 头，不影响 `Origin`
- 后端 `CorsFilter` 根据 `Origin` 头判断是否为跨域请求并校验

### `setAllowedOriginPatterns` vs `setAllowedOrigins`
```java
// allowedOrigins: 精确匹配，不支持通配
config.setAllowedOrigins(List.of("http://localhost:5173"));

// allowedOriginPatterns: 支持通配符模式
config.setAllowedOriginPatterns(List.of("http://localhost:*"));
```
两者都可与 `setAllowCredentials(true)` 配合使用，但 `allowedOriginPatterns` 灵活性更高。

### Spring Security 过滤器链顺序
```
CorsFilter → CsrfFilter(disabled) → ... → JwtAuthFilter → AuthorizationFilter
```
CORS 过滤在 JWT 认证之前执行，所以即使路径配置了 `permitAll()`，CORS 过滤器仍会拦截并返回 403。

## 经验总结

### 收获
- CORS 问题是前后端分离项目最常见的"看起来权限有问题但实际是跨域"的案例
- `curl` 测试时加 `-H "Origin: http://..."` 可精确模拟浏览器跨域请求
- `setAllowedOriginPatterns` 是处理多端口开发场景的最佳实践

### 踩过的坑
- 误以为 Vite 代理可以完全绕过 CORS（实际上 `Origin` 头仍会被转发）
- `changeOrigin: true` 只改 `Host` 不改 `Origin`，容易混淆

### 最佳实践
- 开发环境用 `allowedOriginPatterns` 通配本地端口
- 生产环境务必改回 `allowedOrigins` 并明确指定域名
- 排查 CORS 问题时先用 curl 加 Origin 头直连后端，排除代理/前端干扰
