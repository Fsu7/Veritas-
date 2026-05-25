# Task05: BusinessException异常体系 + GlobalExceptionHandler 实施计划

## 1 任务概述

创建BusinessException异常体系（4个异常类）和GlobalExceptionHandler全局异常处理器（1个类），实现全系统统一的异常处理机制。

## 2 前置依赖问题

⚠️ **task04（ApiResponse/PageResponse/ErrorCode）尚未完成**，但task05的GlobalExceptionHandler依赖`ApiResponse.error()`方法。  
**解决方案**：在执行task05时，先创建task04中的`ApiResponse`和`ErrorCode`（仅创建这两个类，PageResponse暂不创建，避免范围扩大），确保task05可编译通过。

## 3 文件清单

### 3.1 前置依赖文件（来自task04，仅创建必要部分）

| # | 操作 | 文件路径 | 说明 |
|---|------|---------|------|
| 0a | create | `dto/common/ApiResponse.java` | 统一响应包装类，GlobalExceptionHandler依赖其`error()`方法 |
| 0b | create | `dto/common/ErrorCode.java` | 错误码枚举，供后续扩展使用 |

### 3.2 task05核心文件

| # | 操作 | 文件路径 | 说明 |
|---|------|---------|------|
| 1 | create | `exception/BusinessException.java` | 业务异常基类，继承RuntimeException |
| 2 | create | `exception/AuthenticationException.java` | 认证异常(401)，继承BusinessException |
| 3 | create | `exception/ResourceNotFoundException.java` | 资源不存在异常(404)，继承BusinessException |
| 4 | create | `exception/AIServiceException.java` | AI服务调用异常(503)，继承BusinessException |
| 5 | create | `exception/GlobalExceptionHandler.java` | 全局异常处理器，@RestControllerAdvice |

### 3.3 测试文件

| # | 操作 | 文件路径 | 说明 |
|---|------|---------|------|
| 6 | create | `test/.../exception/BusinessExceptionTest.java` | BusinessException单元测试 |
| 7 | create | `test/.../exception/AuthenticationExceptionTest.java` | AuthenticationException单元测试 |
| 8 | create | `test/.../exception/ResourceNotFoundExceptionTest.java` | ResourceNotFoundException单元测试 |
| 9 | create | `test/.../exception/AIServiceExceptionTest.java` | AIServiceException单元测试 |
| 10 | create | `test/.../exception/GlobalExceptionHandlerTest.java` | GlobalExceptionHandler单元测试 |

## 4 详细实现规格

### 4.1 ApiResponse（前置依赖）

```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class ApiResponse<T> {
    private int code;
    private String message;
    @JsonInclude(JsonInclude.Include.NON_NULL)
    private T data;
    private long timestamp;

    public static <T> ApiResponse<T> success(T data) { ... }   // code=200, message="success"
    public static <T> ApiResponse<T> error(int code, String message) { ... }  // data=null
    public static <T> ApiResponse<T> error(ErrorCode errorCode) { ... }
}
```

### 4.2 ErrorCode（前置依赖）

```java
@Getter @AllArgsConstructor
public enum ErrorCode {
    SUCCESS(200, "success"),
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未认证，请先登录"),
    FORBIDDEN(403, "无权限访问"),
    NOT_FOUND(404, "资源不存在"),
    INTERNAL_ERROR(500, "服务器内部错误"),
    SERVICE_UNAVAILABLE(503, "服务暂时不可用");

    private final int code;
    private final String message;
}
```

### 4.3 BusinessException

- 继承 `RuntimeException`（unchecked exception，避免强制try-catch）
- 3个 `final` 字段：`code`(int)、`message`(通过super传给RuntimeException)、`errorKey`(String)
- `@Getter` 注解（Lombok）
- 3个构造方法：
  1. `BusinessException(int code, String message)` — errorKey默认空字符串
  2. `BusinessException(int code, String message, String errorKey)` — 完整构造
  3. `BusinessException(int code, String message, Throwable cause)` — 含cause，errorKey默认空字符串
- **注意**：prompt.json FR-004要求AIServiceException调用`super(503, message, cause, 'AI_SERVICE_ERROR')`，这意味着BusinessException还需要第4个构造方法：
  4. `BusinessException(int code, String message, Throwable cause, String errorKey)` — 含cause和errorKey的完整构造

### 4.4 AuthenticationException

- 继承 `BusinessException`
- 构造方法：`AuthenticationException(String message)` → `super(401, message, "AUTHENTICATION_FAILED")`
- errorKey固定为 `AUTHENTICATION_FAILED`

### 4.5 ResourceNotFoundException

- 继承 `BusinessException`
- 构造方法：`ResourceNotFoundException(String resource, String id)` → `super(404, resource + " not found: " + id, "RESOURCE_NOT_FOUND")`
- errorKey固定为 `RESOURCE_NOT_FOUND`

### 4.6 AIServiceException

- 继承 `BusinessException`
- 构造方法：`AIServiceException(String message, Throwable cause)` → `super(503, message, cause, "AI_SERVICE_ERROR")`
- errorKey固定为 `AI_SERVICE_ERROR`
- 保留原始异常链（cause）

### 4.7 GlobalExceptionHandler

- `@RestControllerAdvice` 注解
- 注入SLF4J Logger：`private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class)`
- 6个异常处理方法：

| 方法 | 异常类型 | 返回code | 返回message | 日志级别 |
|------|---------|---------|------------|---------|
| `handleValidation` | MethodArgumentNotValidException | 400 | 拼接所有字段错误（`field: defaultMessage`，分号分隔） | — |
| `handleAuth` | AuthenticationException | e.getCode() | e.getMessage() | — |
| `handleNotFound` | ResourceNotFoundException | e.getCode() | e.getMessage() | — |
| `handleAIService` | AIServiceException | e.getCode() | "AI服务暂时不可用，请稍后重试" | **WARN** |
| `handleBusiness` | BusinessException | e.getCode() | e.getMessage() | — |
| `handleGeneral` | Exception | 500 | "服务器内部错误" | **ERROR** |

**安全约束**：
- AIServiceException：不暴露Python服务内部错误细节，返回固定友好消息
- Exception兜底：不暴露异常类名和堆栈信息，返回固定友好消息

**日志约束**：
- AIServiceException用`log.warn`（预期内降级场景）
- Exception兜底用`log.error("Unexpected error", e)`（记录完整异常栈）

## 5 测试计划

### 5.1 BusinessExceptionTest

- 测试3个构造方法的字段赋值
- 测试默认errorKey为空字符串
- 测试含cause构造方法的异常链保留
- 测试含errorKey构造方法的errorKey赋值

### 5.2 AuthenticationExceptionTest

- 测试code=401
- 测试errorKey="AUTHENTICATION_FAILED"
- 测试message正确传递

### 5.3 ResourceNotFoundExceptionTest

- 测试code=404
- 测试errorKey="RESOURCE_NOT_FOUND"
- 测试message格式为`{resource} not found: {id}`

### 5.4 AIServiceExceptionTest

- 测试code=503
- 测试errorKey="AI_SERVICE_ERROR"
- 测试cause保留（原始IOException等）

### 5.5 GlobalExceptionHandlerTest

- 测试6种异常处理方法，验证返回的ApiResponse的code和message
- 参数校验异常：模拟MethodArgumentNotValidException，验证message拼接格式
- AIServiceException：验证返回固定友好消息，不暴露内部细节
- Exception兜底：验证返回"服务器内部错误"，不暴露异常类名

## 6 执行步骤

```
Step 1: 创建前置依赖 ApiResponse.java + ErrorCode.java
Step 2: 创建 BusinessException.java
Step 3: 创建 AuthenticationException.java
Step 4: 创建 ResourceNotFoundException.java
Step 5: 创建 AIServiceException.java
Step 6: 创建 GlobalExceptionHandler.java
Step 7: 创建5个单元测试文件
Step 8: mvn compile 验证编译通过
Step 9: mvn test 执行所有单元测试
Step 10: 修复可能出现的编译/测试问题
```

## 7 验收标准对照

| AC# | 验收标准 | 验证方式 |
|-----|---------|---------|
| AC-001 | BusinessException包含code/message/errorKey三个字段，继承RuntimeException | 自动化测试 |
| AC-002 | AuthenticationException的code=401, errorKey=AUTHENTICATION_FAILED | 自动化测试 |
| AC-003 | ResourceNotFoundException的message格式为'{resource} not found: {id}', code=404 | 自动化测试 |
| AC-004 | AIServiceException的code=503，保留cause异常链 | 自动化测试 |
| AC-005 | GlobalExceptionHandler处理6种异常类型，全部返回ApiResponse<Void>格式 | 自动化测试 |
| AC-006 | 参数校验异常message拼接所有字段错误（field: defaultMessage，分号分隔） | 自动化测试 |
| AC-007 | AIServiceException处理返回'AI服务暂时不可用，请稍后重试'，不暴露内部细节 | 自动化测试 |
| AC-008 | Exception兜底处理返回'服务器内部错误'，不暴露堆栈信息 | 自动化测试 |
| AC-009 | AIServiceException日志级别为WARN，Exception兜底日志级别为ERROR | 代码审查 |
| AC-010 | 单元测试全部通过 | 自动化测试 |

## 8 风险与注意事项

1. **BusinessException的message字段**：RuntimeException已有message字段（通过super(message)传递），BusinessException不应再声明message字段，应通过`getMessage()`获取。prompt.json中提到3个字段code/message/errorKey，但message实际继承自RuntimeException。
2. **AIServiceException构造方法**：需要调用`super(503, message, cause, "AI_SERVICE_ERROR")`，这要求BusinessException提供4参数构造方法（含cause和errorKey），prompt.json FR-001只列了3个构造方法，但FR-004隐含需要第4个。
3. **GlobalExceptionHandler中BusinessException的处理顺序**：`handleBusiness`方法必须放在具体子类（AuthenticationException等）之后，因为@ExceptionHandler匹配最具体的类型。但由于Spring的异常处理机制会自动匹配最具体的类型，顺序不影响功能。
