# Task05: BusinessException体系 + GlobalExceptionHandler

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

创建BusinessException异常体系（含AuthenticationException/ResourceNotFoundException/AIServiceException子类）+ GlobalExceptionHandler全局异常处理器。所有异常包含code/message/errorKey三个字段，GlobalExceptionHandler统一处理6种异常类型，全部返回 `ApiResponse<Void>` 统一格式。

## 涉及层级

- **java_backend** — com.literatureassistant.exception
- **java_backend** — com.literatureassistant.dto.common（依赖ApiResponse/ErrorCode）

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/exception/BusinessException.java` | 业务异常基类，code/message/errorKey |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/exception/AuthenticationException.java` | 认证异常（401） |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/exception/ResourceNotFoundException.java` | 资源不存在异常（404） |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/exception/AIServiceException.java` | AI服务调用异常（503） |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java` | 全局异常处理器，@RestControllerAdvice |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | BusinessException继承RuntimeException，包含code/message/errorKey，提供3个构造方法 |
| FR-002 | P0 | AuthenticationException(code=401, errorKey=AUTHENTICATION_FAILED) |
| FR-003 | P0 | ResourceNotFoundException(code=404, message='{resource} not found: {id}', errorKey=RESOURCE_NOT_FOUND) |
| FR-004 | P0 | AIServiceException(code=503, errorKey=AI_SERVICE_ERROR)，保留cause异常链 |
| FR-005 | P0 | GlobalExceptionHandler处理6种异常：参数校验(400)、认证(401)、资源不存在(404)、AI服务(503)、业务异常(自定义code)、兜底(500) |
| FR-006 | P1 | AIServiceException日志级别WARN，Exception兜底日志级别ERROR |

## 安全要求

- AIServiceException处理时返回通用消息"AI服务暂时不可用，请稍后重试"，**不暴露**Python服务内部错误细节
- Exception兜底处理返回"服务器内部错误"，**不暴露**异常类名和堆栈信息

## 关键约束

- **禁止**Controller直接try-catch返回错误，异常统一由GlobalExceptionHandler处理
- **禁止**AIServiceException处理时暴露Python服务内部错误细节
- **禁止**Exception兜底处理返回异常类名或堆栈信息给前端
- **禁止**BusinessException使用checked exception（必须继承RuntimeException）

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | BusinessException包含code/message/errorKey三个字段 | 单元测试 |
| AC-002 | AuthenticationException的code=401, errorKey=AUTHENTICATION_FAILED | 单元测试 |
| AC-003 | ResourceNotFoundException的message格式正确, code=404 | 单元测试 |
| AC-004 | AIServiceException的code=503，保留cause异常链 | 单元测试 |
| AC-005 | GlobalExceptionHandler处理6种异常类型，全部返回ApiResponse<Void> | 单元测试 |
| AC-006 | 参数校验异常message拼接所有字段错误 | 单元测试 |
| AC-007 | AIServiceException处理返回通用消息，不暴露内部细节 | 单元测试 |
| AC-008 | Exception兜底处理返回'服务器内部错误' | 单元测试 |
| AC-009 | AIServiceException日志WARN，Exception兜底日志ERROR | 代码审查 |
| AC-010 | 单元测试全部通过 | 自动化测试 |

## 验证命令

```bash
cd Veritas/backend && mvn test -Dtest=BusinessExceptionTest,AuthenticationExceptionTest,ResourceNotFoundExceptionTest,AIServiceExceptionTest,GlobalExceptionHandlerTest
cd Veritas/backend && mvn compile
```
