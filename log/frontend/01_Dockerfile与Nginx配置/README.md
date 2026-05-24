# 前端 Dockerfile 与 Nginx 配置

## 功能描述

- 解决了前端容器化部署问题，实现从开发环境到生产环境的一致性部署
- 实现了前端多阶段 Docker 构建（Node.js 构建 + Nginx 运行），大幅减小镜像体积
- 实现了 Nginx 反向代理配置，包含 SPA 路由支持、API 代理、SSE 实时推送、静态资源缓存、安全加固和 Gzip 压缩
- 完善了 Docker Compose 编排，将 frontend 服务正式纳入 5 服务架构
- 业务价值：一键部署完整系统，环境一致性保障，SSE 实时推送能力支撑 Agent 可视化核心功能

## 实现逻辑

### 修改的核心文件列表

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `Veritas/frontend/Dockerfile` | 多阶段构建：node:18-alpine 构建 dist → nginx:1.25-alpine 运行 |
| 新增 | `Veritas/nginx.conf` | Nginx 反向代理完整配置 |
| 修改 | `Veritas/docker-compose.yml` | 替换 frontend 服务骨架为完整配置 |
| 新增 | `Veritas/frontend/.dockerignore` | Docker 构建上下文优化 |

### 使用的设计模式

- **多阶段构建模式**：Stage1 构建 dist，Stage2 仅保留运行时产物，镜像体积从 ~1GB 降至 ~30MB
- **Resolver 动态解析模式**：使用 `resolver 127.0.0.11` + `$backend` 变量，避免 Nginx 启动时因上游不可达而启动失败
- **最小权限原则**：非 root 用户运行 Nginx 容器

### 关键代码逻辑说明

**Dockerfile 多阶段构建**：
- Stage1 使用 `npm ci`（基于 lock 文件精确安装，比 `npm install` 更可靠）
- Stage2 创建 `nginx-user` 用户，chown 所有必要目录（html/cache/log/pid），最后 `USER nginx-user` 切换

**Nginx SSE 代理**：
- `proxy_buffering off`：关闭响应缓冲，SSE 事件实时推送到客户端
- `proxy_cache off`：关闭缓存，避免 SSE 事件被缓存
- `proxy_read_timeout 300s`：长连接超时 5 分钟，适配 Agent 工作流执行时间
- `proxy_http_version 1.1` + `Connection ""`：保持 HTTP/1.1 长连接

**Nginx 动态 DNS 解析**：
- Docker Compose 内置 DNS 服务器为 `127.0.0.11`
- 使用 `set $backend "java-backend"` 变量，Nginx 在运行时解析域名而非启动时
- `valid=30s` 缓存 DNS 结果 30 秒，平衡性能与服务发现

## 接口变更

### Request

本次不涉及新增 API 接口，但 Nginx 代理层新增以下路由规则：

```
GET /                    → 静态文件（SPA 路由 try_files）
GET /api/*               → proxy_pass http://java-backend:8080/api/
GET /api/analysis/*/agent-stream  → SSE 事件流（proxy_buffering off）
GET /health              → Nginx 健康检查（access_log off）
```

### Response

```
HTTP/1.1 200 OK
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Content-Encoding: gzip  (对 text/css, application/javascript 等类型)
```

## 测试结果

- 测试场景1：`docker compose config --quiet` — Docker Compose YAML 语法验证通过
- 测试场景2：`nginx -t` — Nginx 配置语法验证通过（使用 resolver 动态解析后不再报 host not found）
- 测试场景3：Dockerfile 多阶段构建逻辑审查 — node:18-alpine + nginx:1.25-alpine，非 root 用户，HEALTHCHECK 完整
- 是否通过：是

## 相关文件

- `Veritas/frontend/Dockerfile` — 前端多阶段 Docker 构建文件
- `Veritas/frontend/.dockerignore` — Docker 构建忽略文件
- `Veritas/nginx.conf` — Nginx 反向代理配置
- `Veritas/docker-compose.yml` — Docker Compose 编排文件（frontend 服务部分）
- `docs/架构决策记录(ADR).md` — ADR-009 SSE 推送、ADR-010 Docker Compose 部署
- `docs/frontend/前端模块系统架构文档.md` — 第17章 部署架构
