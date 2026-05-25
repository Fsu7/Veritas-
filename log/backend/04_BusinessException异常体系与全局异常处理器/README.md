# BusinessException异常体系与全局异常处理器

## 功能描述
- 解决了什么问题：统一了Java后端所有业务异常的定义和处理方式，消除了Controller层散落的try-catch代码，确保所有API错误响应格式一致
- 实现了什么功能：
  - BusinessException业务异常基类，包含code/message/errorKey三字段，继承RuntimeException
  - AuthenticationException（401认证异常）、ResourceNotFoundException（404资源不存在异常）、AIServiceException（503 AI服务调用异常）三个子类
  - GlobalExceptionHandler全局异常处理器，使用@RestControllerAdvice统一处理6种异常类型
  - 所有异常统一返回ApiResponse<Void>格式
- 业务价值：前端可根据code字段统一判断错误类型并做对应处理；errorKey支持前端国际化；AIServiceException和Exception兜底不暴露内部细节，保障安全性

## 实现逻辑
- 修改的核心文件列表：
  - `dto/common/ApiResponse.java` — 统一响应包装类（前置依赖，来自task04）
  - `dto/common/ErrorCode.java` — 错误码枚举（前置依赖，来自task04）
  - `exception/BusinessException.java` — 业务异常基类
  - `exception/AuthenticationException.java` — 认证异常
  - `exception/ResourceNotFoundException.java` — 资源不存在异常
  - `exception/AIServiceException.java` — AI服务调用异常
  - `exception/GlobalExceptionHandler.java` — 全局异常处理器
- 使用的设计模式：
  - 异常继承体系（BusinessException继承链）
  - 模板方法模式（子类固定code和errorKey）
  - 全局拦截器模式（@RestControllerAdvice）
- 关键代码逻辑说明：
  - BusinessException提供4个构造方法，支持有无errorKey、有无cause的组合
  - 子类构造方法中固定code和errorKey，调用super()传递
  - GlobalExceptionHandler中AIServiceException返回固定友好消息，不暴露Python服务内部错误
  - Exception兜底返回"服务器内部错误"，不暴露异常类名和堆栈
  - AIServiceException用log.warn（预期内降级），Exception兜底用log.error（未知异常）

## 接口变更

### Request
本任务不新增API接口，但影响所有API的错误响应格式。

### Response — 参数校验异常（400）
```json
{
  "code": 400,
  "message": "username: 用户名不能为空; email: 邮箱格式不正确",
  "timestamp": 1716451200000
}
```

### Response — 认证异常（401）
```json
{
  "code": 401,
  "message": "Token已过期",
  "timestamp": 1716451200000
}
```

### Response — 资源不存在异常（404）
```json
{
  "code": 404,
  "message": "User not found: usr_001",
  "timestamp": 1716451200000
}
```

### Response — AI服务异常（503）
```json
{
  "code": 503,
  "message": "AI服务暂时不可用，请稍后重试",
  "timestamp": 1716451200000
}
```

### Response — 通用业务异常
```json
{
  "code": 409,
  "message": "用户名已存在",
  "timestamp": 1716451200000
}
```

### Response — 兜底异常（500）
```json
{
  "code": 500,
  "message": "服务器内部错误",
  "timestamp": 1716451200000
}
```

## 测试结果
- BusinessException构造方法测试（4个构造方法+继承验证+默认errorKey）：6个测试全部通过 ✅
- AuthenticationException测试（code=401, errorKey=AUTHENTICATION_FAILED, message传递）：5个测试全部通过 ✅
- ResourceNotFoundException测试（code=404, errorKey=RESOURCE_NOT_FOUND, message格式）：5个测试全部通过 ✅
- AIServiceException测试（code=503, errorKey=AI_SERVICE_ERROR, cause保留）：6个测试全部通过 ✅
- GlobalExceptionHandler测试（6种异常处理+安全约束验证）：10个测试全部通过 ✅
- 是否通过：**是**（32/32测试通过）

## 相关文件
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ErrorCode.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/BusinessException.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/AuthenticationException.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/ResourceNotFoundException.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/AIServiceException.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`
- `Veritas/backend/src/test/java/com/literatureassistant/exception/BusinessExceptionTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/exception/AuthenticationExceptionTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/exception/ResourceNotFoundExceptionTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/exception/AIServiceExceptionTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/exception/GlobalExceptionHandlerTest.java`
