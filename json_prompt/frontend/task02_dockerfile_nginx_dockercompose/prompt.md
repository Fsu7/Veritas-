# Task 02: Dockerfile + nginx.conf + docker-compose.yml frontend服务

## 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

## 版本与里程碑
- 版本：v0.1
- 里程碑：M1 / FM1：项目骨架与基础设施就绪

## 需求描述
创建前端Dockerfile（多阶段构建：Node.js构建+Nginx运行）、nginx.conf（SPA路由try_files+API反向代理+SSE proxy_buffering off+静态资源缓存）、更新docker-compose.yml添加frontend服务（nginx:alpine镜像，端口80，挂载dist和nginx.conf，依赖java-backend）。

## 涉及层级
前端（frontend）+ 基础设施（infra）

## 前置任务
- task00_vue3_vite_project（项目骨架已创建）
- task01_vite_tsconfig_env_config（构建配置已完成）
- backend/task03_dockerfile_dockercompose（docker-compose.yml已存在）

## 修改范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | Veritas/frontend/Dockerfile | 多阶段Docker构建 |
| 新增 | Veritas/frontend/.dockerignore | Docker构建忽略文件 |
| 新增 | Veritas/nginx.conf | Nginx反向代理配置 |
| 修改 | Veritas/docker-compose.yml | 添加frontend服务 |

## 关键实现要求

### Dockerfile
1. 多阶段构建：Stage1 node:18-alpine构建dist/，Stage2 nginx:alpine运行
2. 非root用户运行Nginx
3. 健康检查配置

### nginx.conf
1. SPA路由：`try_files $uri $uri/ /index.html`
2. API代理：`/api/` → `http://java-backend:8080/api/`
3. SSE支持：`proxy_buffering off; proxy_cache off; proxy_read_timeout 300s;`
4. 静态资源缓存：`expires 1d; add_header Cache-Control "public, immutable";`
5. 安全：`server_tokens off;` + 安全响应头
6. Gzip压缩

### docker-compose.yml
1. 仅添加frontend服务，不修改已有服务
2. image: nginx:alpine, ports: 80:80
3. 挂载dist/和nginx.conf
4. depends_on: java-backend
5. networks: app-network

## 禁止行为
- ❌ 删除docker-compose.yml中已有服务
- ❌ Docker容器以root用户运行
- ❌ 忽略SSE proxy_buffering off配置
- ❌ 使用latest标签的Docker基础镜像
- ❌ Nginx配置中硬编码API Key

## 验收标准
- [ ] Dockerfile多阶段构建成功
- [ ] SPA路由直接访问/search返回index.html
- [ ] API代理/api/到java-backend:8080
- [ ] SSE proxy_buffering off配置
- [ ] 静态资源缓存1天+immutable
- [ ] docker-compose.yml包含frontend服务
- [ ] 非root用户运行
- [ ] 安全响应头配置
- [ ] docker-compose up前端服务正常
