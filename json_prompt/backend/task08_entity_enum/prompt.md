# Task08: 6个Entity类 + 6个枚举类

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F4.1 |

## 需求描述

创建6个JPA Entity类（User、UserProfile、Paper、Session、AnalysisResult、PaperFavorite）和6个枚举类（EducationLevel、KnowledgeLevel、PreferredStyle、SessionStatus、AnalysisType、AnalysisStatus）。Entity类严格对应数据库DDL定义，使用Lombok注解，枚举字段使用`@Enumerated(EnumType.STRING)`，JSON字段使用`columnDefinition='JSON'`，时间字段使用`@PrePersist`/`@PreUpdate`自动填充。

## 涉及层级

- **java_backend** — com.literatureassistant.entity / com.literatureassistant.enums
- **data_layer** — MySQL 6张表

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `entity/User.java` | 用户实体，对应users表 |
| 新增 | `entity/UserProfile.java` | 用户画像实体，对应user_profiles表 |
| 新增 | `entity/Paper.java` | 论文实体，对应papers表 |
| 新增 | `entity/Session.java` | 会话实体，对应sessions表 |
| 新增 | `entity/AnalysisResult.java` | 分析结果实体，对应analysis_results表 |
| 新增 | `entity/PaperFavorite.java` | 论文收藏实体，对应paper_favorites表 |
| 新增 | `enums/EducationLevel.java` | 学历层次枚举：UNDERGRADUATE/MASTER/PHD/FACULTY |
| 新增 | `enums/KnowledgeLevel.java` | 知识水平枚举：BEGINNER/INTERMEDIATE/ADVANCED/EXPERT |
| 新增 | `enums/PreferredStyle.java` | 偏好风格枚举：SIMPLE/BALANCED/TECHNICAL |
| 新增 | `enums/SessionStatus.java` | 会话状态枚举：ACTIVE/COMPLETED/EXPIRED |
| 新增 | `enums/AnalysisType.java` | 分析类型枚举：PAPER_ANALYSIS/COMPARE/REPORT |
| 新增 | `enums/AnalysisStatus.java` | 分析状态枚举：PENDING/PROCESSING/COMPLETED/FAILED |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | User实体：id/userId/username/email/passwordHash/createdAt，@PrePersist自动填充createdAt |
| FR-002 | P0 | UserProfile实体：枚举字段educationLevel/knowledgeLevel/preferredStyle，JSON字段profileData，@PrePersist/@PreUpdate填充updatedAt |
| FR-003 | P0 | Paper实体：abstractText映射abstract列，JSON字段authors/keywords，@PrePersist/@PreUpdate填充时间 |
| FR-004 | P0 | Session实体：SessionStatus枚举字段，@PrePersist填充createdAt |
| FR-005 | P0 | AnalysisResult实体：AnalysisType/AnalysisStatus双枚举字段，JSON result字段 |
| FR-006 | P0 | PaperFavorite实体：userId/paperId/createdAt |
| FR-007 | P0 | EducationLevel枚举：含code/label字段和fromCode静态方法 |
| FR-008 | P0 | KnowledgeLevel枚举：含code/label字段和fromCode静态方法 |
| FR-009 | P0 | PreferredStyle枚举：含code/label字段和fromCode静态方法 |
| FR-010 | P0 | SessionStatus枚举：ACTIVE/COMPLETED/EXPIRED纯枚举值 |
| FR-011 | P0 | AnalysisType枚举：PAPER_ANALYSIS/COMPARE/REPORT纯枚举值 |
| FR-012 | P0 | AnalysisStatus枚举：PENDING/PROCESSING/COMPLETED/FAILED纯枚举值 |

## 跨系统一致性

- Java枚举值UPPER_SNAKE_CASE ↔ Python/JSON lower_case（通过code字段映射）
- 关键字段映射：educationLevel↔education_level, knowledgeLevel↔knowledge_level, preferredStyle↔preferred_style
- Paper.abstractText ↔ 数据库abstract列 ↔ JSON abstract字段

## 关键约束

- **禁止**Entity字段与DDL定义不一致
- **禁止**枚举字段不使用`@Enumerated(EnumType.STRING)`
- **禁止**使用abstract作为Java字段名（使用abstractText）
- **禁止**省略`@Column(name=...)`属性
- **禁止**在toString()中输出passwordHash

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | 6个Entity类编译通过，@Table/@Column与DDL一致 | 自动化测试 |
| AC-002 | 6个枚举类编译通过，枚举值完整 | 自动化测试 |
| AC-003 | 所有Entity使用Lombok注解 | 代码审查 |
| AC-004 | 枚举字段@Enumerated(STRING)，JSON字段columnDefinition='JSON' | 代码审查 |
| AC-005 | Paper.abstractText正确映射到abstract列 | 自动化测试 |
| AC-006 | EducationLevel/KnowledgeLevel/PreferredStyle的fromCode方法正确 | 自动化测试 |
| AC-007 | @PrePersist/@PreUpdate自动填充时间字段 | 自动化测试 |
| AC-008 | Spring Boot启动自动创建6张表 | 手动测试 |
| AC-009 | User.passwordHash不在toString()中输出 | 代码审查 |
| AC-010 | 单元测试全部通过 | 自动化测试 |

## 验证命令

```bash
cd Veritas/backend && mvn compile
cd Veritas/backend && mvn test -Dtest=UserEntityTest,UserProfileEntityTest,PaperEntityTest,EnumTest
cd Veritas/backend && mvn spring-boot:run
```
