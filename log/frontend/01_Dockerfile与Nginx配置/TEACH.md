# 技术教学文档 — 前端 Dockerfile 与 Nginx 配置

## 开发思路

### 需求分析过程

本次任务的核心需求是将前端 Vue3 应用容器化部署，并配置 Nginx 作为反向代理。需求拆解为：

1. **Dockerfile**：需要将 Vue3 源码构建为静态文件，然后打包到 Nginx 镜像中运行
2. **nginx.conf**：需要同时满足 SPA 路由、API 代理、SSE 实时推送、静态资源缓存、安全加固 5 个维度的需求
3. **docker-compose.yml**：需要将 frontend 服务集成到已有的 4 服务编排中
4. **.dockerignore**：优化构建上下文，避免无关文件进入 Docker 构建过程

### 技术选型考虑

| 决策点 | 选项 | 最终选择 | 理由 |
|--------|------|---------|------|
| 构建基础镜像 | node:18 / node:18-alpine | node:18-alpine | 体积小（~50MB vs ~300MB），功能足够 |
| 运行基础镜像 | nginx:latest / nginx:alpine / nginx:1.25-alpine | nginx:1.25-alpine | 指定版本确保可复现，alpine 体积小 |
| npm 安装方式 | npm install / npm ci | npm ci | 基于 lock 文件精确安装，CI/CD 环境更可靠 |
| 配置挂载方式 | COPY 到镜像 / Volume 挂载 | Volume 挂载（:ro） | 便于配置热更新，重启即生效 |
| dist 分发方式 | Volume 挂载 / 打包到镜像 | 打包到镜像 | 更符合 Docker 最佳实践，镜像自包含 |

### 架构设计思路

```
用户浏览器 → Nginx:80
                ├── /           → 静态文件（SPA try_files）
                ├── /api/*      → java-backend:8080（反向代理）
                │   └── /api/analysis/*/agent-stream → SSE 流（proxy_buffering off）
                ├── /health     → 健康检查
                └── 静态资源     → 缓存 1d + immutable
```

### 遇到的问题及解决方案

**问题1：Nginx 启动时 `host not found in upstream "java-backend"`**

- 原因：Nginx 在启动时尝试解析 `proxy_pass` 中的域名，但 Docker Compose 的 DNS 在 Nginx 容器启动时可能尚未就绪
- 解决方案：使用 `resolver 127.0.0.11 valid=30s` + `set $backend "java-backend"` 变量方式，让 Nginx 在运行时动态解析域名
- `127.0.0.11` 是 Docker 内置 DNS 服务器地址，所有 Docker Compose 服务共享

**问题2：非 root 用户运行 Nginx 需要额外权限配置**

- 原因：Nginx 默认需要写入 `/var/cache/nginx`、`/var/log/nginx`、`/var/run/nginx.pid` 等目录
- 解决方案：在 Dockerfile 中预先 chown 这些目录给 nginx-user

## 实现步骤

1. **创建 .dockerignore**：排除 node_modules、dist、.git 等无关文件，减小构建上下文
2. **创建 Dockerfile**：多阶段构建，Stage1 用 Node.js 构建 dist，Stage2 用 Nginx 运行
3. **创建 nginx.conf**：配置 SPA 路由、API 代理（含 SSE）、静态资源缓存、安全头、Gzip 压缩
4. **更新 docker-compose.yml**：替换 frontend 服务骨架为完整配置（build + volume + depends_on + restart）
5. **验证**：`docker compose config --quiet` 和 `nginx -t` 双重验证

## 解决了什么问题

### 核心问题描述

前端 Vue3 SPA 应用需要容器化部署，面临以下挑战：
- SPA 路由在 Nginx 直接访问子路径时返回 404
- API 请求需要反向代理到 Java 后端
- SSE 事件流需要关闭 Nginx 缓冲才能实时推送
- Docker 容器安全要求非 root 用户运行
- Nginx 启动时上游服务可能尚未就绪

### 解决方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|---------|
| 直接 proxy_pass 硬编码域名 | 简单 | 启动时上游不可达则 Nginx 启动失败 | ❌ |
| resolver + 变量动态解析 | 启动不依赖上游，运行时解析 | 配置稍复杂 | ✅ |
| 挂载 dist 目录到 nginx 镜像 | 灵活 | 需要本地先构建 dist，镜像不自包含 | ❌ |
| 多阶段构建打包 dist 到镜像 | 镜像自包含，一键部署 | 配置变更需重新构建 | ✅ |

### 最终方案的优势

- **镜像自包含**：dist 打包在镜像中，不依赖宿主机文件
- **配置热更新**：nginx.conf 通过 volume 挂载，修改后重启即生效
- **启动健壮性**：resolver 动态解析，不依赖上游服务启动顺序
- **安全合规**：非 root 用户运行，隐藏版本号，安全响应头

## 变更内容

### 新增文件

- `Veritas/frontend/Dockerfile` — 前端多阶段 Docker 构建文件（21 行）
- `Veritas/nginx.conf` — Nginx 反向代理配置（51 行）
- `Veritas/frontend/.dockerignore` — Docker 构建忽略文件（20 行）

### 修改文件

- `Veritas/docker-compose.yml` — 替换 frontend 服务定义：
  - 移除 `# TODO: 待后续任务完善` 注释
  - 添加 `:ro` 只读标记到 nginx.conf 挂载
  - 添加 `restart: unless-stopped` 重启策略

### 配置变更

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Nginx listen | 80 | 前端服务端口 |
| proxy_pass target | java-backend:8080 | API 代理目标 |
| proxy_buffering | off | SSE 实时推送 |
| proxy_read_timeout | 300s | SSE 长连接超时 |
| 静态资源缓存 | 1d + immutable | 减少重复请求 |
| gzip_comp_level | 6 | 压缩级别（1-9） |
| gzip_min_length | 1024 | 最小压缩阈值 1KB |

## 关键技术点

### 1. Docker 多阶段构建

```dockerfile
FROM node:18-alpine AS build    # Stage 1: 构建
# ... npm ci + npm run build

FROM nginx:1.25-alpine          # Stage 2: 运行
COPY --from=build /app/dist ... # 仅复制构建产物
```

核心思想：构建阶段的依赖（node_modules、TypeScript 编译器等）不会进入最终镜像，大幅减小镜像体积。

### 2. Nginx Resolver 动态 DNS 解析

```nginx
resolver 127.0.0.11 valid=30s;          # Docker 内置 DNS
set $backend "java-backend";             # 变量赋值
proxy_pass http://$backend:8080/api/;    # 运行时解析
```

- 直接写 `proxy_pass http://java-backend:8080/` 时，Nginx 启动时就会解析域名
- 使用变量后，Nginx 延迟到请求时才解析，避免启动失败
- `valid=30s` 缓存 DNS 结果 30 秒

### 3. SSE 代理配置

```nginx
proxy_buffering off;      # 关闭响应缓冲 — SSE 事件实时推送
proxy_cache off;          # 关闭缓存 — 不缓存 SSE 事件
proxy_read_timeout 300s;  # 长连接超时 — 适配 Agent 工作流
proxy_http_version 1.1;   # HTTP/1.1 — 支持长连接
proxy_set_header Connection "";  # 清除 Connection 头
```

SSE（Server-Sent Events）是基于 HTTP 长连接的服务端推送协议。如果 Nginx 开启 `proxy_buffering`，会缓冲上游响应直到缓冲区满才发送，导致 SSE 事件延迟。

### 4. 非 root 用户运行 Nginx

```dockerfile
RUN addgroup -S nginx-group && adduser -S nginx-user -G nginx-group
RUN chown -R nginx-user:nginx-group /usr/share/nginx/html \
    /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx-group /var/run/nginx.pid
USER nginx-user
```

关键点：Nginx 需要写入 4 个目录/文件，必须预先 chown：
- `/usr/share/nginx/html` — 静态文件目录
- `/var/cache/nginx` — 代理缓存目录
- `/var/log/nginx` — 日志目录
- `/var/run/nginx.pid` — PID 文件

### 5. 安全响应头

```nginx
server_tokens off;                              # 隐藏 Nginx 版本号
add_header X-Content-Type-Options "nosniff" always;    # 防止 MIME 嗅探
add_header X-Frame-Options "SAMEORIGIN" always;        # 防止点击劫持
add_header X-XSS-Protection "1; mode=block" always;    # XSS 过滤
```

`always` 关键字确保即使响应为错误状态码（如 404、500）也包含安全头。

## 经验总结

### 开发过程中的收获

1. **Docker Compose 中 Nginx 代理上游服务的正确姿势**：使用 resolver + 变量而非直接 proxy_pass 硬编码域名，这是 Docker 环境下 Nginx 配置的最佳实践
2. **多阶段构建的价值**：前端项目 node_modules 通常 200MB+，多阶段构建让最终镜像仅包含 dist/ 和 Nginx，体积从 GB 级降到 ~30MB
3. **SSE 与 WebSocket 的选择**：SSE 是单向推送（服务端→客户端），比 WebSocket 轻量，适合 Agent 状态推送场景；但 Nginx 必须关闭 proxy_buffering

### 踩过的坑及如何避免

1. **Nginx 启动失败 `host not found in upstream`**：在 Docker Compose 外部用 `nginx -t` 测试时必然报错，因为上游服务不在同一网络。解决方案是使用 resolver 动态解析
2. **非 root 用户运行 Nginx 权限不足**：忘记 chown `/var/run/nginx.pid` 会导致 Nginx 无法启动。需要逐一检查 Nginx 需要写入的所有路径
3. **静态资源 location 覆盖了安全头**：Nginx 的 `add_header` 在子 location 中会覆盖父级的同名指令，因此每个 location 都需要重新声明安全头

### 最佳实践建议

1. **Docker 基础镜像必须指定版本号**：禁止使用 `latest` 标签，确保构建可复现
2. **nginx.conf 通过 volume 挂载而非 COPY 到镜像**：便于配置修改后只需 `docker compose restart frontend` 即可生效
3. **健康检查端点不记录 access_log**：`location /health { access_log off; }` 避免健康检查请求污染日志
4. **SSE 代理必须设置 `proxy_http_version 1.1`**：HTTP/1.0 不支持长连接，SSE 会断开
5. **docker-compose.yml 中 volume 挂载配置文件加 `:ro`**：只读挂载防止容器内进程意外修改宿主机配置文件
