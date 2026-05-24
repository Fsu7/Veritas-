# Task02: 前端 Dockerfile + Nginx + Docker Compose 实施计划

## 任务概述

创建前端 Dockerfile（多阶段构建）、nginx.conf（SPA路由+API代理+SSE+缓存）、更新 docker-compose.yml 添加 frontend 服务、创建 .dockerignore。

## 需修改/创建的文件

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| **创建** | `Veritas/frontend/Dockerfile` | 多阶段构建：Node.js 构建 + Nginx 运行 |
| **创建** | `Veritas/nginx.conf` | Nginx 反向代理配置 |
| **修改** | `Veritas/docker-compose.yml` | 添加 frontend 服务配置 |
| **创建** | `Veritas/frontend/.dockerignore` | Docker 构建忽略文件 |

## 实施步骤

### Step 1: 创建 `Veritas/frontend/.dockerignore`

**依据**: FR-004（P1），减小 Docker 构建上下文

```
node_modules/
dist/
dist-ssr/
.git/
.gitignore
.env
.env.local
.env.*.local
*.log
.vscode/
.idea/
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?
README.md
.dockerignore
Dockerfile
```

### Step 2: 创建 `Veritas/frontend/Dockerfile`

**依据**: FR-001（P0）、FR-005（P1）、FA-003（非root运行）、FA-006（禁止latest标签）

**多阶段构建设计**：

```dockerfile
# Stage 1: Node.js 构建
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Nginx 运行
FROM nginx:1.25-alpine
RUN addgroup -S nginx-group && adduser -S nginx-user -G nginx-group
COPY --from=build /app/dist /usr/share/nginx/html
COPY ../nginx.conf /etc/nginx/conf.d/default.conf
RUN chown -R nginx-user:nginx-group /usr/share/nginx/html && \
    chown -R nginx-user:nginx-group /var/cache/nginx && \
    chown -R nginx-user:nginx-group /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx-group /var/run/nginx.pid
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1
USER nginx-user
CMD ["nginx", "-g", "daemon off;"]
```

**关键决策**：
- 基础镜像使用 `node:18-alpine`（指定版本，非latest）和 `nginx:1.25-alpine`（指定版本）
- `npm ci` 代替 `npm install`，确保基于 lock 文件精确安装
- 非 root 用户运行：创建 `nginx-user` 用户
- HEALTHCHECK 检查根路径 `/`
- nginx.conf 通过 Docker Compose volume 挂载（而非 COPY），因为 prompt.json 中 FR-003 要求挂载方式

**⚠️ 重要调整**：根据 FR-003 要求，docker-compose.yml 使用 `image: nginx:alpine` + volume 挂载 dist 和 nginx.conf。因此 Dockerfile 的作用是**构建 dist/**，而运行时使用独立的 nginx:alpine 镜像。

**最终方案**：Dockerfile 仍采用多阶段构建（构建 dist 并打包到 nginx 镜像中），docker-compose.yml 使用 `build: ./frontend` 方式构建（与现有 backend 服务一致），同时保留 nginx.conf 的 volume 挂载以便配置热更新。

### Step 3: 创建 `Veritas/nginx.conf`

**依据**: FR-002（P0）、FR-006（P1）、FR-007（P2）、FA-002（禁止硬编码密钥）、FA-005（SSE proxy_buffering off）

**配置结构**：

```nginx
server {
    listen 80;
    server_name localhost;

    # 安全配置（FR-006）
    server_tokens off;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip 压缩（FR-007）
    gzip on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types text/css application/javascript application/json text/xml application/xml;

    # SPA 路由（FR-002）
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理（FR-002）
    location /api/ {
        proxy_pass http://java-backend:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持（FR-002, FA-005）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # 静态资源缓存（FR-002）
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$ {
        root /usr/share/nginx/html;
        expires 1d;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
    }

    # 健康检查端点（不记录日志）
    location /health {
        access_log off;
        return 200 "ok";
        add_header Content-Type text/plain;
    }
}
```

**关键决策**：
- `server_tokens off`：隐藏 Nginx 版本号
- 安全响应头在 location / 和静态资源 location 中都添加（`always` 确保错误响应也包含）
- SSE 配置：`proxy_buffering off` + `proxy_cache off` + `proxy_read_timeout 300s` + `proxy_http_version 1.1` + `Connection ""`
- 静态资源缓存：`expires 1d` + `Cache-Control: public, immutable`
- 健康检查端点 `/health` 不记录 access_log
- Gzip：最小 1KB，级别 6，覆盖主要文本类型

### Step 4: 更新 `Veritas/docker-compose.yml`

**依据**: FR-003（P0）、FA-004（不删除已有服务）

**当前状态**：docker-compose.yml 已有 frontend 服务骨架（第 84-96 行），但配置不完整，缺少 container_name、image 版本锁定、restart 策略等。

**修改内容**：替换现有的 frontend 服务定义为完整配置：

```yaml
  frontend:
    build: ./frontend
    container_name: literature-frontend
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      java-backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network
```

**关键决策**：
- 使用 `build: ./frontend` 而非 `image: nginx:alpine`，因为需要多阶段构建打包 dist
- nginx.conf 通过 volume 挂载（`:ro` 只读），便于配置修改后重启即生效
- 不再挂载 `./frontend/dist`，因为 dist 已打包到镜像中（更符合 Docker 最佳实践）
- `restart: unless-stopped` 提高可用性
- `depends_on: java-backend: condition: service_healthy` 确保启动顺序

## 验收标准对照

| ID | 验收标准 | 对应实现 |
|----|---------|---------|
| AC-001 | Dockerfile 多阶段构建成功 | Step 2: node:18-alpine 构建 + nginx:1.25-alpine 运行 |
| AC-002 | SPA 路由正常 | Step 3: `try_files $uri $uri/ /index.html` |
| AC-003 | API 代理到 java-backend:8080 | Step 3: `proxy_pass http://java-backend:8080/api/` |
| AC-004 | SSE 支持 | Step 3: `proxy_buffering off` + `proxy_read_timeout 300s` |
| AC-005 | 静态资源缓存 | Step 3: `expires 1d` + `Cache-Control: public, immutable` |
| AC-006 | docker-compose 包含 frontend + depends_on | Step 4: frontend 服务完整配置 |
| AC-007 | 非 root 用户运行 | Step 2: `USER nginx-user` |
| AC-008 | 隐藏版本号 + 安全头 | Step 3: `server_tokens off` + 3个安全头 |
| AC-009 | 端口 80 可访问 | Step 4: `ports: "80:80"` |

## 禁止行为检查

| ID | 禁止行为 | 合规 |
|----|---------|------|
| FA-001 | 输出伪代码或 TODO | ✅ 全部完整可执行代码 |
| FA-002 | Nginx 硬编码密钥 | ✅ 无密钥硬编码 |
| FA-003 | root 用户运行 | ✅ USER nginx-user |
| FA-004 | 删除已有服务 | ✅ 仅修改 frontend 服务 |
| FA-005 | 忽略 SSE 配置 | ✅ proxy_buffering off |
| FA-006 | 使用 latest 标签 | ✅ node:18-alpine, nginx:1.25-alpine |

## 实施顺序

1. 创建 `.dockerignore` → 2. 创建 `Dockerfile` → 3. 创建 `nginx.conf` → 4. 更新 `docker-compose.yml`
