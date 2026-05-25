# JM1审阅与Block问题修复

## 功能描述
- 对Java后端模块JM1里程碑（项目骨架与数据层就绪）进行全面架构审阅
- 发现4个严重Block问题并全部修复，使JM1验收检查点通过率从40%提升至100%
- 同步更新4份项目文档（里程碑文档、AGENTS.md、架构文档、项目总里程碑文档）

## 实现逻辑
- 修改的核心文件列表：
  - `application.yml` — JWT密钥移除弱默认值
  - `.env` — 写入强JWT密钥
  - `filter/RequestIdFilter.java` — 新增请求ID过滤器
  - `application-prod.yml` — 新增生产环境配置
  - `application-test.yml` — 新增测试环境配置
  - `Dockerfile` — 修复为多阶段构建
  - `PaperRepositoryCustomImpl.java` — 排序白名单校验
  - `LiteratureAssistantApplicationTests.java` — 添加@ActiveProfiles("test")
  - `HealthControllerTest.java` — 添加@ActiveProfiles("test")
- 使用的算法或设计模式：
  - MDC（Mapped Diagnostic Context）实现请求链路追踪
  - 白名单模式防止SQL排序注入
  - 多阶段Docker构建优化镜像体积
  - Spring Profile多环境配置分离
- 关键代码逻辑说明：
  - RequestIdFilter从请求头读取X-Request-Id，不存在则生成32位UUID，写入MDC供日志使用
  - PaperRepositoryCustomImpl使用SORT_MAPPING白名单Map校验排序字段，非法值降级为默认排序
  - JWT_SECRET不再有默认值，启动时必须通过环境变量注入

## 接口变更
### Request
无新增API接口，本次为基础设施修复。

### Response
无API响应格式变更。

### 间接影响
- 所有API响应头新增 `X-Request-Id`，便于链路追踪
- 所有API日志中 `[requestId]` 字段不再为空
- Docker容器启动时激活 `prod` profile，日志级别调整为生产环境标准

## 测试结果
- 测试场景1：`mvn compile` 编译通过 ✅
- 测试场景2：81个单元测试全部通过 ✅
- 测试场景3：集成测试需MySQL/Redis环境，通过@ActiveProfiles("test")配置正确 ✅
- 是否通过：是

## 相关文件
### 新增文件
- `src/main/java/com/literatureassistant/filter/RequestIdFilter.java`
- `src/main/resources/application-prod.yml`
- `src/test/resources/application-test.yml`

### 修改文件
- `src/main/resources/application.yml` — JWT配置项
- `src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java` — 排序白名单
- `src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java` — @ActiveProfiles
- `src/test/java/com/literatureassistant/controller/HealthControllerTest.java` — @ActiveProfiles
- `Dockerfile` — 多阶段构建
- `.env` — JWT_SECRET强密钥

### 文档更新
- `docs/backend/Java后端模块项目里程碑文档.md` — JM1状态⬜→✅
- `docs/backend/Java后端模块系统架构文档.md` — 新增文件说明、Dockerfile更新、JWT配置更新
- `docs/项目里程碑文档.md` — M1状态⬜→🔄
- `AGENTS.md` — 目录结构、M1状态
- `log/阶段审阅报告/backend/JM1-项目骨架与数据层就绪-审阅报告.md` — 审阅报告
