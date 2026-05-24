-- ============================================================
-- XH-202630 科研文献智能助手 — MySQL 种子数据
-- 数据库：literature_assistant
-- 创建日期：2026-05-24
-- 里程碑：v0.1 M1 基础设施就绪
-- ============================================================
-- 注意：密码使用BCrypt哈希，禁止明文存储
-- BCrypt('password123', strength=10) = $2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
-- ============================================================

USE literature_assistant;

-- -----------------------------------------------------------
-- 1. 测试用户
-- -----------------------------------------------------------
INSERT INTO users (user_id, username, email, password_hash)
VALUES (
    'usr_test_001',
    'test_user',
    'test@example.com',
    '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'
) ON DUPLICATE KEY UPDATE username = VALUES(username);

-- -----------------------------------------------------------
-- 2. 测试用户画像
-- -----------------------------------------------------------
INSERT INTO user_profiles (user_id, education_level, research_field, knowledge_level, preferred_style, profile_data)
VALUES (
    'usr_test_001',
    'master',
    'NLP',
    'intermediate',
    'balanced',
    '{"researchStage": "survey", "interests": ["Multi-Agent", "RAG", "LLM"], "language": "zh-CN"}'
) ON DUPLICATE KEY UPDATE education_level = VALUES(education_level);

-- -----------------------------------------------------------
-- 3. 测试论文
-- -----------------------------------------------------------
INSERT INTO papers (paper_id, title, authors, abstract, year, venue, keywords, citation_count, pdf_url)
VALUES (
    'arxiv_test_001',
    'Multi-Agent Collaborative Decision Making: A Survey on Large Language Model Based Systems',
    '["Wang, Lei", "Chen, Xu", "Zhang, Yu"]',
    'This paper provides a comprehensive survey on multi-agent collaborative decision making systems based on large language models. We systematically review the architecture design, communication protocols, and coordination mechanisms of LLM-based multi-agent systems. We categorize existing approaches into three paradigms: centralized, decentralized, and hybrid orchestration. Our analysis reveals that agent specialization with structured communication significantly improves task completion quality. We also identify key challenges including hallucination propagation, scalability limitations, and evaluation methodology gaps. Finally, we propose future research directions for building more robust and efficient multi-agent systems.',
    2024,
    'AAAI 2024',
    '["multi-agent", "large language model", "collaborative decision making", "LLM orchestration", "agent coordination"]',
    1200,
    'https://arxiv.org/abs/2401.00001'
) ON DUPLICATE KEY UPDATE title = VALUES(title);

-- -----------------------------------------------------------
-- 4. 第二篇测试论文（用于对比分析测试）
-- -----------------------------------------------------------
INSERT INTO papers (paper_id, title, authors, abstract, year, venue, keywords, citation_count, pdf_url)
VALUES (
    'arxiv_test_002',
    'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks',
    '["Lewis, Patrick", "Perez, Ethan", "Piktus, Aleksandra"]',
    'We present Retrieval-Augmented Generation (RAG), a general-purpose fine-tuning approach that combines pre-trained parametric and non-parametric memory for language generation. RAG models retrieve documents from a knowledge base and use them as context for generation, achieving state-of-the-art results on knowledge-intensive benchmarks. We demonstrate that RAG outperforms purely parametric models on open-domain question answering and knowledge-intensive generation tasks, while also providing interpretable provenance for generated content through retrieved documents.',
    2020,
    'NeurIPS 2020',
    '["RAG", "retrieval-augmented generation", "knowledge-intensive NLP", "open-domain QA"]',
    3500,
    'https://arxiv.org/abs/2005.11401'
) ON DUPLICATE KEY UPDATE title = VALUES(title);

-- -----------------------------------------------------------
-- 5. 测试会话
-- -----------------------------------------------------------
INSERT INTO sessions (session_id, user_id, topic, status)
VALUES (
    'ses_test_001',
    'usr_test_001',
    'Multi-Agent协同决策系统研究综述',
    'active'
) ON DUPLICATE KEY UPDATE topic = VALUES(topic);

-- -----------------------------------------------------------
-- 6. 测试分析结果
-- -----------------------------------------------------------
INSERT INTO analysis_results (analysis_id, session_id, type, result, status)
VALUES (
    'anl_test_001',
    'ses_test_001',
    'paper_analysis',
    '{"paper_id": "arxiv_test_001", "research_questions": ["How do LLM-based multi-agent systems coordinate?"], "core_methods": ["Centralized orchestration", "Decentralized communication"], "key_experiments": ["Benchmark on collaborative reasoning tasks"], "core_conclusions": ["Agent specialization improves quality"], "limitations": ["Hallucination propagation", "Scalability"]}',
    'completed'
) ON DUPLICATE KEY UPDATE result = VALUES(result);

-- -----------------------------------------------------------
-- 7. 测试论文收藏
-- -----------------------------------------------------------
INSERT INTO paper_favorites (user_id, paper_id)
VALUES (
    'usr_test_001',
    'arxiv_test_001'
) ON DUPLICATE KEY UPDATE user_id = VALUES(user_id);
