# Task00: 数据库创建与种子数据

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 |
| **功能编号** | F4.1.1, F4.1.2, F4.1.3, F4.1.4 |

## 需求描述

在本机MySQL 9上创建 `literature_assistant` 数据库及6张核心表（users、user_profiles、papers、sessions、analysis_results、paper_favorites），建立所有索引（含FULLTEXT ngram全文索引），并插入种子测试数据。

## 涉及层级

- **data_layer** — MySQL 8.0/9.0

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `backend-java/src/main/resources/db/01_create_tables.sql` | 创建数据库 + 6张表 + 外键约束 |
| 新增 | `backend-java/src/main/resources/db/02_create_indexes.sql` | FULLTEXT索引（papers表title+abstract，WITH PARSER ngram） |
| 新增 | `backend-java/src/main/resources/db/03_insert_seed_data.sql` | 测试用户(BCrypt密码) + 测试画像 + 测试论文种子数据 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | 创建 literature_assistant 数据库，字符集 utf8mb4，排序规则 utf8mb4_unicode_ci |
| FR-002 | P0 | 按依赖顺序创建6张表：users → user_profiles → papers → sessions → analysis_results → paper_favorites，每张表和列必须有COMMENT |
| FR-003 | P0 | 建立外键约束：user_profiles→users, sessions→users, analysis_results→sessions, paper_favorites→users+papers，ON DELETE CASCADE |
| FR-004 | P1 | 创建FULLTEXT索引 ft_title_abstract ON papers(title, abstract) WITH PARSER ngram |
| FR-005 | P0 | 插入种子数据：1个测试用户(usr_test_001, BCrypt密码) + 1条画像(master/NLP/intermediate/balanced) + 1条论文(arxiv_test_001) |

## 约束与禁止事项

- 表名列名 snake_case，索引名 `idx_`/`uk_`/`ft_` 前缀
- 引擎必须 InnoDB，主键 `id BIGINT AUTO_INCREMENT`，业务ID `xxx_id VARCHAR(100) UNIQUE NOT NULL`
- 必须有 `created_at` / `updated_at` 时间戳字段
- **禁止**：省略COMMENT、使用非utf8mb4字符集、使用MyISAM引擎、省略外键约束、明文存储密码
- 种子数据密码必须 BCrypt 哈希

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | literature_assistant 数据库创建成功，字符集utf8mb4 | SQL查询 |
| AC-002 | SHOW TABLES 返回6张表 | SQL查询 |
| AC-003 | 所有字段类型、约束、默认值与数据库设计文档一致 | 代码审查 |
| AC-004 | 所有表和列都有COMMENT | SQL查询 |
| AC-005 | 外键约束正确建立（5条外键关系） | SQL查询 |
| AC-006 | FULLTEXT索引 ft_title_abstract 创建成功，WITH PARSER ngram | SQL查询 |
| AC-007 | 种子数据插入成功：1个测试用户 + 1条画像 + 1条论文 | SQL查询 |
| AC-008 | 种子数据中密码为BCrypt哈希，非明文 | 代码审查 |
| AC-009 | FULLTEXT检索测试通过 | SQL查询 |
| AC-010 | SQL脚本文件编码UTF-8，换行符LF | 代码审查 |

## 验证命令

```bash
# 验证数据库创建
mysql -u root -p'Aa2105268075.' -e "SHOW DATABASES LIKE 'literature_assistant'"

# 验证6张表
mysql -u root -p'Aa2105268075.' literature_assistant -e "SHOW TABLES"

# 验证FULLTEXT索引
mysql -u root -p'Aa2105268075.' literature_assistant -e "SHOW INDEX FROM papers"

# 验证全文检索
mysql -u root -p'Aa2105268075.' literature_assistant -e "SELECT * FROM papers WHERE MATCH(title, abstract) AGAINST('Multi-Agent' IN NATURAL LANGUAGE MODE)"
```
