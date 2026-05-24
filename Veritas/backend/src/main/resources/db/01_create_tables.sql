-- ============================================================
-- XH-202630 科研文献智能助手 — MySQL DDL
-- 数据库：literature_assistant
-- 字符集：utf8mb4 / utf8mb4_unicode_ci
-- 引擎：InnoDB
-- 创建日期：2026-05-24
-- 里程碑：v0.1 M1 基础设施就绪
-- ============================================================

CREATE DATABASE IF NOT EXISTS literature_assistant
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE literature_assistant;

-- -----------------------------------------------------------
-- 1. 用户表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) UNIQUE NOT NULL COMMENT '用户唯一ID（UUID格式）',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    email VARCHAR(200) COMMENT '邮箱地址',
    password_hash VARCHAR(200) NOT NULL COMMENT 'BCrypt加密密码哈希',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- -----------------------------------------------------------
-- 2. 用户画像表
-- 依赖：users(user_id)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profiles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL COMMENT '关联用户ID',
    education_level ENUM('undergraduate', 'master', 'phd', 'faculty') COMMENT '学历层次',
    research_field VARCHAR(200) COMMENT '研究方向（如NLP/CV/RL）',
    knowledge_level ENUM('beginner', 'intermediate', 'advanced', 'expert') COMMENT '知识水平',
    preferred_style ENUM('simple', 'balanced', 'technical') COMMENT '偏好风格',
    profile_data JSON COMMENT '完整画像扩展数据（JSON格式）',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户画像表';

-- -----------------------------------------------------------
-- 3. 论文元数据表
-- 含FULLTEXT索引（ngram中文分词）
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS papers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    paper_id VARCHAR(100) UNIQUE NOT NULL COMMENT '论文唯一ID（如arxiv_2024_001）',
    title VARCHAR(500) NOT NULL COMMENT '论文标题',
    authors JSON COMMENT '作者列表（JSON数组）',
    abstract TEXT COMMENT '论文摘要',
    year INT COMMENT '发表年份',
    venue VARCHAR(200) COMMENT '发表会议/期刊',
    keywords JSON COMMENT '关键词列表（JSON数组）',
    citation_count INT DEFAULT 0 COMMENT '引用数',
    pdf_url VARCHAR(500) COMMENT 'PDF链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_year (year),
    INDEX idx_venue (venue),
    INDEX idx_citation (citation_count),
    FULLTEXT INDEX ft_title_abstract (title, abstract) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='论文元数据表';

-- -----------------------------------------------------------
-- 4. 分析会话表
-- 依赖：users(user_id)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(100) UNIQUE NOT NULL COMMENT '会话唯一ID',
    user_id VARCHAR(100) NOT NULL COMMENT '关联用户ID',
    topic VARCHAR(500) COMMENT '研究主题',
    status ENUM('active', 'completed', 'expired') DEFAULT 'active' COMMENT '会话状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析会话表';

-- -----------------------------------------------------------
-- 5. 分析结果表
-- 依赖：sessions(session_id)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    analysis_id VARCHAR(100) UNIQUE NOT NULL COMMENT '分析结果唯一ID',
    session_id VARCHAR(100) NOT NULL COMMENT '关联会话ID',
    type ENUM('paper_analysis', 'compare', 'report') NOT NULL COMMENT '分析类型',
    result JSON NOT NULL COMMENT '结构化分析结果（JSON格式）',
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '分析状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_status (status),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析结果表';

-- -----------------------------------------------------------
-- 6. 论文收藏表
-- 依赖：users(user_id) + papers(paper_id)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_favorites (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL COMMENT '关联用户ID',
    paper_id VARCHAR(100) NOT NULL COMMENT '关联论文ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    UNIQUE KEY uk_user_paper (user_id, paper_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='论文收藏表';
