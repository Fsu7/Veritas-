# 技术教学文档

## 开发思路

### 需求分析
PaperRepository 的 `searchByKeyword` 方法需要实现 MySQL FULLTEXT 全文检索，使用 `MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE)` 语法完成中文分词搜索（ngram parser），同时支持年份/venue 过滤和多维度排序。

### 技术选型考量
最初使用 Spring Data JPA `@Query(nativeQuery=true)` 注解声明原生 SQL，但遇到 ANTLR 解析错误："no viable alternative at input 'SELECT * FROM papers WHERE MATCH('"。

排查过程：
1. 先怀疑是 FULLTEXT 索引不存在 → 查数据库确认 `ft_title_abstract` 索引存在
2. 用原生 SQL 直接在 MySQL 9 上执行 → 语法完全正常，排除 MySQL 版本问题
3. 定位到 Spring Data JPA 3.x 的内部 SQL 解析器在提取 `:keyword` 等命名参数时不识别 `MATCH()` 语法

### 架构设计思路
遵循 Spring Data JPA 官方 Custom Repository 模式：
```
PaperRepository (接口)
  ├── extends JpaRepository<Paper, Long>       ← Spring Data 自动实现 CRUD
  ├── extends JpaSpecificationExecutor<Paper>  ← 动态查询支持
  └── extends PaperRepositoryCustom            ← 自定义复杂查询

PaperRepositoryCustom (接口)  ← 声明自定义方法
        ↓ 实现
PaperRepositoryCustomImpl (类)  ← EntityManager 原生查询
```

Spring Data JPA 会按 "接口名 + Impl" 后缀自动发现实现类，将 `PaperRepositoryCustomImpl` 绑定到 `PaperRepository` 代理中。

## 实现步骤

1. **第一步：创建 Custom 接口**
   - 新建 `PaperRepositoryCustom.java`
   - 声明 `searchByKeyword` 方法签名，与原来 `@Query` 方法保持一致

2. **第二步：创建 CustomImpl 实现类**
   - 新建 `PaperRepositoryCustomImpl.java`
   - 注入 `@PersistenceContext EntityManager`
   - 定义 `DATA_SQL`（数据查询 + ORDER BY + LIMIT/OFFSET）和 `COUNT_SQL`（计数查询）两个常量
   - 使用 `entityManager.createNativeQuery(sql, Paper.class)` 执行数据查询
   - 使用 `entityManager.createNativeQuery(countSql)` 执行计数查询
   - 用 `PageImpl` 组装分页结果

3. **第三步：修改 PaperRepository 接口**
   - 新增 `extends PaperRepositoryCustom`
   - 移除有问题的 `@Query` 方法和不再需要的 import（`@Query`、`@Param`、`Page`、`Pageable`）

4. **第四步：编译验证**
   - `mvn compile` 确认通过

## 解决了什么问题

### 核心问题
Spring Data JPA 3.x / Hibernate 6.x 对 `@Query(nativeQuery=true)` 中的命名参数 (`:keyword`) 进行提取时，使用内部的 ANTLR SQL 解析器。该解析器不支持 MySQL 专有的 `MATCH(column1, column2) AGAINST(...)` 语法，直接抛出解析错误。

### 解决方案对比

| 方案 | 可行性 | 理由 |
|------|--------|------|
| `@Query(nativeQuery=true)` + 命名参数 | ❌ | 解析器不认 MATCH 语法 |
| 改用位置参数 `?1` `?2` 在 @Query 中 | ❌ | 解析器同样需要解析 SQL 来定位参数 |
| JPQL + `FUNCTION('MATCH', ...)` | ❌ | AGAINST 子句无法在 JPQL 中表达 |
| Custom Repository + EntityManager | ✅ | 完全绕过 JPA 解析器，直接交给 JDBC |
| JdbcTemplate | ✅ | 可行但需手写 RowMapper，过度设计 |

### 最终方案的优势
1. **Spring 官方推荐模式** — Custom Repository 是 Spring Data 官方文档中处理复杂查询的标准方式
2. **调用方零改动** — Service 层通过 `PaperRepository` 调用，不感知底层实现变化
3. **精确分页** — 数据查询 + COUNT 查询分离，`PageImpl` 返回准确的 `totalElements`
4. **安全** — 使用 `setParameter()` 参数化查询，防止 SQL 注入
5. **可维护** — SQL 抽为常量，参数绑定集中在 `setParameters()` 方法中

## 变更内容

### 新增文件
- `backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustom.java`
  - 作用：声明自定义查询方法接口

- `backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java`
  - 作用：使用 EntityManager 执行 FULLTEXT 原生查询，实现分页

### 修改文件
- `backend/src/main/java/com/literatureassistant/repository/PaperRepository.java`
  - 变更点：移除 `@Query` 方法和相关 import（`@Query`、`@Param`、`Page`、`Pageable`），新增 `extends PaperRepositoryCustom`

### 配置变更
无

## 关键技术点

### 1. Spring Data JPA Custom Repository 自动发现机制
Spring Data JPA 会扫描与 Repository 接口同包下的 `{接口名}Impl` 类。当 `PaperRepository extends PaperRepositoryCustom` 时，框架自动将 `PaperRepositoryCustomImpl` 的方法织入生成的代理中。

命名约定：
- 默认后缀：`Impl`
- 可自定义后缀：`@EnableJpaRepositories(repositoryImplementationPostfix = "CustomImpl")`

### 2. EntityManager 原生查询
```java
// 带实体映射的查询（结果自动映射为 Paper 对象）
Query dataQuery = entityManager.createNativeQuery(DATA_SQL, Paper.class);

// 无映射的查询（用于 COUNT）
Query countQuery = entityManager.createNativeQuery(COUNT_SQL);

// 分页参数
dataQuery.setFirstResult((int) pageable.getOffset());  // 起始行
dataQuery.setMaxResults(pageable.getPageSize());        // 每页条数
```

### 3. PageImpl 组装分页结果
```java
return new PageImpl<>(results, pageable, total);
// results: 当前页数据
// pageable: 分页参数（page, size, sort）
// total: 总记录数（从 COUNT_SQL 获取）
```

### 4. MySQL FULLTEXT 参数绑定注意事项
- 使用位置参数 `?1` ~ `?5` 代替命名参数 `:keyword`
- `MATCH` 在 WHERE 和 ORDER BY 中分别调用，MySQL 仍能利用 FULLTEXT 索引
- 中文分词依赖 `WITH PARSER ngram` 索引定义（在 `01_create_tables.sql` 第 64 行）

## 经验总结

### 开发收获
1. **不要假设框架能处理所有 SQL 方言** — Spring Data JPA 的解析器只覆盖标准 SQL 和常见扩展，MySQL FULLTEXT 这类专有语法需要绕过解析器
2. **先排除基础设施问题** — 先验证 FULLTEXT 索引存在、原生 SQL 在数据库执行通过，再定位框架层问题，避免无效修改
3. **Custom Repository 是复杂查询的安全网** — 任何 `@Query` 搞不定的原生 SQL，都可以用它兜底

### 踩过的坑
- **ANTLR 错误信息不直观**："no viable alternative at input" 不容易直接联想到是参数解析问题
- **EntityManager 需要事务**：即使只读查询，实现类上仍需 `@Transactional(readOnly = true)`，否则可能报 "No EntityManager with actual transaction available"

### 最佳实践建议
1. **简单查询用 @Query，复杂/方言查询用 Custom Repository**
2. **COUNT 查询和数据查询分离**，避免在分页场景下查全量数据
3. **SQL 常量化**：将 SQL 定义为 `private static final String`，方便维护和性能调优
4. **参数绑定集中管理**：抽取 `setParameters()` 私有方法，保证 DATA_SQL 和 COUNT_SQL 参数设置一致性