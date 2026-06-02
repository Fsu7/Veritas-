# 本次开发关键决策日志

## 决策时间线

### 决策 1:5 篇 vs 200 篇

**触发**: 200 篇导入在 17/200 稳定卡住(2 次复现),根因是 `AsyncOpenAI` 缺 `timeout=...`。

**选项**:
- A. 修代码(加 timeout)+ 重跑 200 篇(预计 30 分钟代码 + 15 分钟重跑)
- B. 接受 5 篇 + 留 AM3 修复(本次收工,后续单独 session 修复)

**决策**: B(用户选择)

**理由**:
- M2 阶段核心目标"单 Agent 可用"已达成(5 篇入库即满足)
- 修复 Embedding Service timeout 涉及 `app/services/embedding_service.py`,属于 AM3 阶段 SSE 推送 + 性能优化的范畴
- 200+ 篇生产数据扩展放到 AM3 阶段更合理

### 决策 2:`--year-start` 参数是否保留在 import_papers.py

**触发**: 我修改脚本加了 `--year-start` 参数(为 200 篇做准备),但本次只跑 5 篇未用到。

**选项**:
- A. 保留(向后兼容,无害)
- B. 回滚(保持代码精简)

**决策**: A(保留)

**理由**:
- 默认值 `None` 不影响现有调用
- 后续 AM3 跑 200+ 篇时可直接 `--year-start 2025`
- 参数命名符合 arXiv 生态习惯(`submittedDate:[...]`)

### 决策 3:临时文件 _temp_show_data.py 是否保留

**触发**: 数据展示时用 Python inline 脚本被 shell 转义破坏,创建了 `scripts/_temp_show_data.py` 临时文件。

**决策**: 删除

**理由**:
- 仅为展示数据快照,临时使用
- `scripts/list_chroma_papers.py` 已有类似功能(更轻量)
- 不污染源码目录

## 待办事项(移交给 AM3 / M3)

### AM3 必做

1. **修复 `app/services/embedding_service.py` 第 89 行**:给 `AsyncOpenAI(...)` 加 `timeout=httpx.Timeout(10.0, connect=5.0)`
2. **跑正式 200 篇**:`python scripts/import_papers.py --count 200 --category cs.AI --year-start 2025 --batch-size 50`
3. **更新 [M2 阶段审阅报告](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/log/阶段审阅报告/ai-service/M2-阶段审阅报告.md)**:增加"环境前置修复记录"章节,记录本次 4 项升级

### M3 启动准备

4. **JM2 联调**: Java 后端打通 `/api/search` 和 `/api/agent/analyze` 的 REST 调用
5. **FM2 前端页面**: Vue3 写登录/注册/论文检索页面
6. **AM3 SSE 推送**: 边分析边推送给前端(`/api/agent/analyze/stream`)

## 关键数字

| 指标 | 值 | 备注 |
|------|-----|------|
| M2 待办项 | 13/13 已完成 | 5 篇论文入库替代 200 篇 |
| ChromaDB 记录 | 12 chunks | 5 篇 × 平均 2.4 chunks |
| 向量维度 | 1024 维 | DashScope text-embedding-v4 |
| 5 篇导入耗时 | 1 分 19 秒 | 含 arXiv 下载 + Embedding + Chroma 写入 |
| 200 篇失败位置 | 17/200 | 稳定复现,根因 timeout 缺失 |
| 修复项数 | 4 项 | feedparser / chromadb / argparse / .env |
| 依赖升级项数 | 2 项 | feedparser 6.0.10→6.0.12, chromadb 0.5.0→0.5.23 |

## 教训(给未来的自己)

1. **大版本 Python 升级前,先扫一遍依赖兼容性**:Python 3.13 的 PEP 594 移除了 19 个 stdlib 模块,影响面广
2. **每次跑新命令,先 dry-run**:本次靠 `--dry-run` 提前发现 feedparser 报错,避免浪费时间
3. **长任务必须用 `command_type=long_running_process`**:前台 `tee | grep | tail` 会导致 SIGPIPE
4. **"卡死"的进程,第一时间 kill -9 不要犹豫**:66818 跑了 5:20 才被发现卡,白白浪费 5 分钟
5. **环境问题写进 README,不要只放在脑子里**:本次 4 项升级如果不写文档,下次还会踩坑
