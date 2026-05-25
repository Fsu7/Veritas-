# Task04: ApiResponse + PageResponse + 统一响应DTO

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

创建统一响应DTO体系，包含 `ApiResponse<T>`（统一响应包装，含code/message/data/timestamp字段）、`PageResponse<T>`（分页响应，含items/total/page/size/totalPages字段）、`ErrorCode`（业务错误码枚举）。所有DTO使用Lombok注解，JSON字段统一使用snake_case。ApiResponse为全系统所有Controller的统一返回类型。

## 涉及层级

- **java_backend** — com.literatureassistant.dto.common

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java` | 统一响应包装类，泛型T |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/common/PageResponse.java` | 分页响应DTO |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ErrorCode.java` | 业务错误码枚举 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | ApiResponse<T>包含code/message/data/timestamp，提供success(T data)和error(int code, String message)静态工厂方法 |
| FR-002 | P0 | PageResponse<T>包含items/total/page/size/totalPages，提供fromPage(Page<T>)和fromPage(Page<T>, List<R>)静态工厂方法，page从0-based转为1-based |
| FR-003 | P0 | ErrorCode枚举定义7个标准错误码：SUCCESS(200)/BAD_REQUEST(400)/UNAUTHORIZED(401)/FORBIDDEN(403)/NOT_FOUND(404)/INTERNAL_ERROR(500)/SERVICE_UNAVAILABLE(503) |
| FR-004 | P1 | ApiResponse的data字段为null时JSON不输出（@JsonInclude(NON_NULL)），totalPages等字段使用@JsonProperty注解确保snake_case |
| FR-005 | P0 | PageResponse.fromPage()中page从Spring Data的0-based转为1-based |

## 跨系统一致性

- JSON字段命名：totalPages → total_pages（@JsonProperty注解）
- 所有API响应统一格式：`{code, message, data, timestamp}`
- 分页接口返回：`ApiResponse<PageResponse<XxxResponse>>`

## 关键约束

- **禁止**在DTO中添加业务逻辑方法
- **禁止**PageResponse中page使用0-based索引（必须1-based）
- **禁止**省略@JsonProperty注解（camelCase字段需映射为snake_case）

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | ApiResponse包含code/message/data/timestamp四个字段 | 单元测试 |
| AC-002 | ApiResponse.success(data)返回code=200 | 单元测试 |
| AC-003 | ApiResponse.error(code, message)返回data=null | 单元测试 |
| AC-004 | PageResponse包含items/total/page/size/totalPages五个字段 | 单元测试 |
| AC-005 | PageResponse.fromPage()正确转换，page从0-based转为1-based | 单元测试 |
| AC-006 | ErrorCode枚举7个标准错误码正确 | 单元测试 |
| AC-007 | 所有DTO使用Lombok注解 | 代码审查 |
| AC-008 | JSON序列化totalPages输出为total_pages | 单元测试 |
| AC-009 | error响应JSON中data为null时不输出 | 单元测试 |
| AC-010 | 单元测试全部通过 | 自动化测试 |

## 验证命令

```bash
cd Veritas/backend && mvn test -Dtest=ApiResponseTest,PageResponseTest,ErrorCodeTest
cd Veritas/backend && mvn compile
```
