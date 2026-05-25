# 技术教学文档 — BusinessException异常体系与全局异常处理器

## 开发思路

### 需求分析过程
本次任务需要为Java后端建立统一的异常处理机制。核心需求包括：
1. 定义业务异常基类BusinessException，包含code/message/errorKey三字段
2. 创建3个具体异常子类，分别对应401/404/503场景
3. 实现GlobalExceptionHandler全局异常处理器，统一拦截所有异常并返回ApiResponse格式
4. 安全约束：AI服务异常和兜底异常不能暴露内部细节

### 技术选型考虑
- **继承RuntimeException而非Exception**：业务异常应为unchecked exception，避免在Service层强制try-catch，让异常自然抛出到GlobalExceptionHandler
- **@RestControllerAdvice而非@ExceptionHandler在Controller中**：全局统一处理，避免每个Controller重复编写异常处理代码
- **errorKey字段设计**：为前端国际化提供支持，不同errorKey可映射到不同语言的错误提示
- **Lombok @Getter**：减少样板代码，BusinessException不使用@Data因为字段是final的

### 架构设计思路

异常体系采用继承层次设计：

```
RuntimeException
  └── BusinessException (code, errorKey)
        ├── AuthenticationException (401, AUTHENTICATION_FAILED)
        ├── ResourceNotFoundException (404, RESOURCE_NOT_FOUND)
        └── AIServiceException (503, AI_SERVICE_ERROR)
```

GlobalExceptionHandler异常处理优先级（Spring自动匹配最具体类型）：
1. MethodArgumentNotValidException → 400
2. AuthenticationException → 401
3. ResourceNotFoundException → 404
4. AIServiceException → 503
5. BusinessException → 自定义code
6. Exception → 500（兜底）

### 遇到的问题及解决方案

**问题1：BusinessException的message字段冲突**
- RuntimeException已有message字段（通过super(message)传递）
- 如果BusinessException再声明message字段，会导致字段遮蔽和Lombok生成getter的冲突
- 解决方案：BusinessException不声明message字段，通过`getMessage()`继承自Throwable的方法获取

**问题2：AIServiceException需要4参数构造方法**
- prompt.json FR-001只列出BusinessException的3个构造方法
- 但FR-004要求AIServiceException调用`super(503, message, cause, "AI_SERVICE_ERROR")`
- 这隐含需要第4个构造方法：`BusinessException(int code, String message, Throwable cause, String errorKey)`
- 解决方案：补充第4个构造方法，确保API完整性

**问题3：Java 23与Mockito/Byte Buddy兼容性**
- 测试中mock MethodArgumentNotValidException时，Byte Buddy不支持Java 23
- 错误：`Java 23 (67) is not supported by the current version of Byte Buddy`
- 解决方案：改用真实对象构造（BeanPropertyBindingResult + MethodParameter），避免mock框架兼容性问题

## 实现步骤

1. **创建前置依赖**：先创建ApiResponse和ErrorCode（task04产出），因为GlobalExceptionHandler依赖ApiResponse.error()方法
2. **创建BusinessException**：定义4个构造方法，覆盖有无errorKey、有无cause的所有组合
3. **创建AuthenticationException**：固定code=401, errorKey=AUTHENTICATION_FAILED
4. **创建ResourceNotFoundException**：固定code=404, errorKey=RESOURCE_NOT_FOUND，message格式为`{resource} not found: {id}`
5. **创建AIServiceException**：固定code=503, errorKey=AI_SERVICE_ERROR，保留cause异常链
6. **创建GlobalExceptionHandler**：6个@ExceptionHandler方法，AIServiceException用log.warn，Exception兜底用log.error
7. **编写单元测试**：5个测试类32个测试用例，覆盖所有构造方法、字段赋值、安全约束
8. **修复Mockito兼容性问题**：将mock方式改为真实对象构造
9. **验证**：mvn compile + mvn test 全部通过

## 解决了什么问题

### 核心问题描述
1. Controller层散落大量try-catch代码，难以维护
2. 异常响应格式不统一，前端无法统一处理
3. 内部错误信息（如Python服务堆栈、数据库异常）可能泄露给前端
4. 缺少异常分类，前端无法根据错误类型做差异化处理

### 解决方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| Controller层try-catch | 简单直接 | 代码重复、难以维护、格式不统一 |
| @ExceptionHandler per Controller | 局部统一 | 仍需每个Controller配置 |
| **@RestControllerAdvice全局** | **全项目统一、零侵入、格式一致** | 需要合理设计异常层次 |

### 最终方案的优势
1. Service层直接throw异常，Controller无需try-catch，代码简洁
2. 所有异常统一返回ApiResponse<Void>格式，前端Axios拦截器统一处理
3. errorKey支持前端国际化映射
4. 安全约束内置：AI服务异常和兜底异常自动脱敏

## 变更内容

### 新增文件
- `dto/common/ApiResponse.java` — 统一响应包装类，泛型T，含success/error静态工厂方法
- `dto/common/ErrorCode.java` — 7个标准错误码枚举（200/400/401/403/404/500/503）
- `exception/BusinessException.java` — 业务异常基类，4个构造方法
- `exception/AuthenticationException.java` — 401认证异常
- `exception/ResourceNotFoundException.java` — 404资源不存在异常
- `exception/AIServiceException.java` — 503 AI服务调用异常
- `exception/GlobalExceptionHandler.java` — 全局异常处理器，6个@ExceptionHandler方法
- `test/.../exception/BusinessExceptionTest.java` — 6个测试用例
- `test/.../exception/AuthenticationExceptionTest.java` — 5个测试用例
- `test/.../exception/ResourceNotFoundExceptionTest.java` — 5个测试用例
- `test/.../exception/AIServiceExceptionTest.java` — 6个测试用例
- `test/.../exception/GlobalExceptionHandlerTest.java` — 10个测试用例

### 修改文件
- 无修改已有文件

### 配置变更
- 无配置变更

## 关键技术点

### 1. RuntimeException vs Exception的选择
- BusinessException继承RuntimeException（unchecked exception）
- 好处：Service层无需在方法签名上声明throws，也不强制调用方try-catch
- 异常自然向上抛出到GlobalExceptionHandler统一处理
- 如果继承Exception（checked exception），每个Service方法都要声明throws，Controller也要try-catch，违背全局统一处理的初衷

### 2. @RestControllerAdvice的工作原理
- Spring MVC在Controller方法抛出异常后，会查找匹配的@ExceptionHandler方法
- 匹配规则：最具体的异常类型优先（如AuthenticationException优先于BusinessException）
- 返回值直接序列化为JSON响应（因为是@RestControllerAdvice而非@ControllerAdvice）

### 3. 参数校验异常的message拼接
```java
e.getBindingResult().getFieldErrors().stream()
    .map(f -> f.getField() + ": " + f.getDefaultMessage())
    .collect(Collectors.joining("; "));
```
- getFieldErrors()获取所有字段校验错误
- 拼接格式：`field1: message1; field2: message2`
- 分号分隔，便于前端解析和展示

### 4. 安全约束实现
- AIServiceException：返回固定消息"AI服务暂时不可用，请稍后重试"，不暴露Python服务内部错误
- Exception兜底：返回固定消息"服务器内部错误"，不暴露异常类名和堆栈
- 内部错误信息仅通过日志记录（log.error记录完整异常栈），不返回给前端

### 5. 日志级别区分
- AIServiceException用log.warn：AI服务不可用是预期内的降级场景，不是系统Bug
- Exception兜底用log.error：未知异常可能是系统Bug，需要告警和排查

## 经验总结

### 开发过程中的收获
1. 异常体系设计需要提前考虑所有子类的构造方法需求，AIServiceException需要cause+errorKey的组合，这要求基类提供对应的构造方法
2. RuntimeException的message字段通过super()传递，子类不应重复声明message字段
3. 全局异常处理器的@ExceptionHandler匹配是自动按最具体类型匹配的，方法声明顺序不影响

### 踩过的坑及如何避免
1. **Java 23与Mockito兼容性问题**：Byte Buddy在Java 23上无法mock某些类（如MethodArgumentNotValidException）
   - 避免方法：优先使用真实对象构造而非mock，特别是对于Spring框架内置类
   - 替代方案：使用BeanPropertyBindingResult + MethodParameter构造真实的MethodArgumentNotValidException
2. **BusinessException构造方法遗漏**：初始只按FR-001列了3个构造方法，但AIServiceException需要4参数版本
   - 避免方法：先分析所有子类的构造方法调用，反推基类需要的构造方法集合

### 最佳实践建议
1. 异常体系设计时，先列出所有具体异常子类的构造需求，再设计基类API
2. 全局异常处理器必须包含Exception兜底处理，防止未捕获异常导致500空白响应
3. 安全敏感的异常（如外部服务调用失败、数据库异常）必须返回脱敏消息
4. 日志级别要与异常严重程度匹配：预期内降级用WARN，未知异常用ERROR
5. 测试中优先使用真实对象而非mock，避免框架兼容性问题
