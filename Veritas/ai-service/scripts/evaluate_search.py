import argparse
import asyncio
import json
import math
import os
import sys
from datetime import datetime
from itertools import product
from typing import Dict
from typing import List
from typing import Set

from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService
from app.services.reranker import Reranker
from app.services.search_service import SearchService
from app.services.vector_store_service import VectorStoreService


def calc_mrr(results: List[dict], relevant_ids: Set[str]) -> float:
    if not results or not relevant_ids:
        return 0.0
    for i, item in enumerate(results):
        pid = item.get("paper_id") or item.get("paperId", "")
        if pid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def calc_ndcg(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float:
    if not results or not relevant_ids:
        return 0.0
    top_k = results[:k]
    dcg = 0.0
    for i, item in enumerate(top_k):
        pid = item.get("paper_id") or item.get("paperId", "")
        rel = 1 if pid in relevant_ids else 0
        dcg += (2 ** rel - 1) / math.log2(i + 2)
    ideal_rels = sorted(
        [1] * min(len(relevant_ids), k) + [0] * max(0, k - len(relevant_ids)),
        reverse=True,
    )
    idcg = 0.0
    for i, rel in enumerate(ideal_rels):
        idcg += (2 ** rel - 1) / math.log2(i + 2)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def calc_precision(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float:
    if not results or not relevant_ids:
        return 0.0
    top_k = results[:k]
    relevant_count = sum(
        1
        for item in top_k
        if (item.get("paper_id") or item.get("paperId", "")) in relevant_ids
    )
    return relevant_count / k


def calc_recall(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float:
    if not results or not relevant_ids:
        return 0.0
    top_k = results[:k]
    relevant_count = sum(
        1
        for item in top_k
        if (item.get("paper_id") or item.get("paperId", "")) in relevant_ids
    )
    return relevant_count / len(relevant_ids)


def load_queries(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def evaluate_single_query(
    search_service: SearchService,
    reranker: Reranker,
    query_item: dict,
    top_k: int,
    use_hybrid: bool = True,
    use_reranker: bool = True,
    user_profile: Dict = None,
) -> Dict:
    query = query_item["query"]
    relevant_ids = set(query_item["relevant_paper_ids"])

    if use_hybrid:
        results = await search_service.hybrid_search(query, top_k=top_k)
    else:
        results = await search_service.search(query, top_k=top_k)

    if use_reranker and reranker is not None:
        results = await reranker.rerank(query, results, user_profile=user_profile)

    mrr = calc_mrr(results, relevant_ids)
    ndcg = calc_ndcg(results, relevant_ids, k=top_k)
    precision = calc_precision(results, relevant_ids, k=top_k)
    recall = calc_recall(results, relevant_ids, k=top_k)

    retrieved_ids = [
        r.get("paper_id") or r.get("paperId", "") for r in results[:top_k]
    ]

    return {
        "query": query,
        "query_id": query_item.get("query_id", ""),
        "relevant_ids": list(relevant_ids),
        "retrieved_ids": retrieved_ids,
        "metrics": {
            "mrr": round(mrr, 4),
            "ndcg_at_10": round(ndcg, 4),
            "precision_at_10": round(precision, 4),
            "recall_at_10": round(recall, 4),
        },
    }


async def run_evaluation(
    queries: List[dict],
    search_service: SearchService,
    reranker: Reranker,
    top_k: int,
    rrf_k: int,
    reranker_weights: List[float],
    user_profile: Dict = None,
) -> Dict:
    original_rrf_k = SearchService.RRF_K
    SearchService.RRF_K = rrf_k

    if reranker is not None and len(reranker_weights) == 3:
        reranker.WEIGHT_RRF = reranker_weights[0]
        reranker.WEIGHT_FIELD = reranker_weights[1]
        reranker.WEIGHT_POPULARITY = reranker_weights[2]

    per_query_details = []
    for q in queries:
        detail = await evaluate_single_query(
            search_service=search_service,
            reranker=reranker,
            query_item=q,
            top_k=top_k,
            use_hybrid=True,
            use_reranker=True,
            user_profile=user_profile,
        )
        per_query_details.append(detail)

    avg_mrr = sum(d["metrics"]["mrr"] for d in per_query_details) / len(per_query_details)
    avg_ndcg = sum(d["metrics"]["ndcg_at_10"] for d in per_query_details) / len(per_query_details)
    avg_precision = sum(d["metrics"]["precision_at_10"] for d in per_query_details) / len(per_query_details)
    avg_recall = sum(d["metrics"]["recall_at_10"] for d in per_query_details) / len(per_query_details)

    SearchService.RRF_K = original_rrf_k
    if reranker is not None:
        reranker.WEIGHT_RRF = 0.5
        reranker.WEIGHT_FIELD = 0.3
        reranker.WEIGHT_POPULARITY = 0.2

    return {
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "top_k": top_k,
            "rrf_k": rrf_k,
            "reranker_weights": reranker_weights,
        },
        "metrics": {
            "mrr": round(avg_mrr, 4),
            "ndcg_at_10": round(avg_ndcg, 4),
            "precision_at_10": round(avg_precision, 4),
            "recall_at_10": round(avg_recall, 4),
        },
        "per_query_details": per_query_details,
    }


async def main(args: argparse.Namespace):
    queries = load_queries(args.queries)
    logger.info("Loaded {} test queries from {}", len(queries), args.queries)

    settings = Settings()
    embedding_service = EmbeddingService(settings)
    await embedding_service.load_model()
    logger.info("EmbeddingService loaded: status={}", embedding_service.status)

    vector_store_service = VectorStoreService(settings)
    await vector_store_service.initialize()
    logger.info("VectorStoreService initialized")

    search_service = SearchService(vector_store_service, embedding_service)
    reranker = Reranker()
    search_service.reranker = reranker
    logger.info("SearchService + Reranker initialized")

    top_k_values = args.top_k
    rrf_k_values = args.rrf_k
    weight_strs = args.reranker_weights

    all_reports = []
    total_combos = len(top_k_values) * len(rrf_k_values) * len(weight_strs)
    combo_idx = 0

    for top_k, rrf_k, weight_str in product(top_k_values, rrf_k_values, weight_strs):
        reranker_weights = [float(w) for w in weight_str.split(",")]
        combo_idx += 1
        logger.info(
            "Evaluating [{}/{}]: top_k={}, rrf_k={}, weights={}",
            combo_idx,
            total_combos,
            top_k,
            rrf_k,
            reranker_weights,
        )

        report = await run_evaluation(
            queries=queries,
            search_service=search_service,
            reranker=reranker,
            top_k=top_k,
            rrf_k=rrf_k,
            reranker_weights=reranker_weights,
        )
        all_reports.append(report)

        logger.info(
            "  MRR={:.4f}, NDCG@10={:.4f}, P@10={:.4f}, R@10={:.4f}",
            report["metrics"]["mrr"],
            report["metrics"]["ndcg_at_10"],
            report["metrics"]["precision_at_10"],
            report["metrics"]["recall_at_10"],
        )

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)
    logger.info("Evaluation report saved to {}", output_path)

    await vector_store_service.close()
    logger.info("VectorStoreService closed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search evaluation script with parameter grid search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/evaluate_search.py --top-k 10 --rrf-k 60 --output data/search_eval_report.json\n"
            "  python scripts/evaluate_search.py --top-k 5 10 20 --rrf-k 30 60 120\n"
            "  python scripts/evaluate_search.py --reranker-weights 0.5,0.3,0.2 0.4,0.4,0.2\n"
        ),
    )
    parser.add_argument(
        "--top-k",
        nargs="+",
        type=int,
        default=[5, 10, 20],
        help="Top-K candidate values for retrieval (default: 5 10 20)",
    )
    parser.add_argument(
        "--rrf-k",
        nargs="+",
        type=int,
        default=[30, 60, 120],
        help="RRF k parameter values (default: 30 60 120)",
    )
    parser.add_argument(
        "--reranker-weights",
        nargs="+",
        type=str,
        default=["0.5,0.3,0.2"],
        help="Reranker weight combinations as comma-separated strings (default: 0.5,0.3,0.2)",
    )
    parser.add_argument(
        "--queries",
        type=str,
        default="tests/test_data/search_queries.json",
        help="Path to test queries JSON file (default: tests/test_data/search_queries.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/search_eval_report.json",
        help="Output path for evaluation report JSON (default: data/search_eval_report.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
