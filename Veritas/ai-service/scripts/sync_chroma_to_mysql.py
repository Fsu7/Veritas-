# 将 ChromaDB 向量库中的论文元数据同步到 MySQL papers 表
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymysql
from loguru import logger

from app.core.config import Settings
from app.services.vector_store_service import VectorStoreService


MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "Aa2105268075.",
    "database": "literature_assistant",
    "charset": "utf8mb4",
}


def get_chroma_metadata(collection) -> dict:
    """从 ChromaDB collection 获取所有论文的完整元数据，按 paper_id 去重。"""
    raw = collection.get()
    metadatas = raw.get("metadatas", [])
    documents = raw.get("documents", [])

    papers = {}
    for meta, doc in zip(metadatas, documents):
        pid = meta["paper_id"]
        if pid not in papers:
            papers[pid] = {
                "paper_id": pid,
                "title": meta.get("title", ""),
                "year": meta.get("year"),
                "venue": meta.get("venue", ""),
                "abstract": "",  # 从 document 中提取（拼接所有 chunks）
                "_chunks": [],
            }
        papers[pid]["_chunks"].append(doc)

    # 拼接 abstract
    for pid, p in papers.items():
        full = " ".join(p["_chunks"])
        # 去掉 title 前缀
        title = p["title"]
        if full.startswith(title):
            full = full[len(title):].strip(". ")
        p["abstract"] = full[:5000]  # 限制长度
        del p["_chunks"]

    return papers


def get_mysql_paper_ids(cursor) -> set:
    """获取 MySQL 中已有的 paper_id。"""
    cursor.execute("SELECT paper_id FROM papers")
    return {row[0] for row in cursor.fetchall()}


def insert_paper(cursor, paper: dict):
    """插入一篇论文到 MySQL（幂等）。"""
    sql = """
        INSERT INTO papers (paper_id, title, authors, abstract, year, venue, keywords, citation_count, pdf_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            abstract = VALUES(abstract),
            year = VALUES(year),
            venue = VALUES(venue)
    """
    cursor.execute(sql, (
        paper["paper_id"],
        paper["title"],
        "[]",  # authors 未知，用空 JSON 数组
        paper["abstract"],
        paper["year"],
        paper["venue"],
        "[]",  # keywords 未知
        0,     # citation_count 未知
        f"https://arxiv.org/abs/{paper['paper_id'].replace('arxiv_', '')}",
    ))


async def main():
    settings = Settings()

    # 1. 连接 ChromaDB
    vs = VectorStoreService(settings)
    await vs.initialize()
    chroma_papers = get_chroma_metadata(vs.collection)
    logger.info(f"ChromaDB 论文数: {len(chroma_papers)}")

    # 2. 连接 MySQL
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    try:
        existing = get_mysql_paper_ids(cursor)
        logger.info(f"MySQL 已有论文数: {len(existing)}")

        new_count = 0
        skip_count = 0

        for pid, paper in chroma_papers.items():
            if pid in existing:
                skip_count += 1
                logger.debug(f"跳过已存在: {pid}")
                continue

            insert_paper(cursor, paper)
            new_count += 1
            logger.info(f"[+{new_count}] 写入 MySQL: {pid} — {paper['title'][:60]}")

        conn.commit()
        logger.info(f"同步完成: 新增 {new_count} 篇, 跳过 {skip_count} 篇")

    finally:
        cursor.close()
        conn.close()
        await vs.close()


if __name__ == "__main__":
    asyncio.run(main())
