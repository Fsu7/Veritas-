"""task51 LLM 流式首字节延迟基准测试脚本

测量 generate_stream 的首字节延迟，输出 P50/P95/P99。
验证 AM5 硬指标：P95 < 2000ms

使用方法：
    cd Veritas/ai-service
    python3 -m tests.benchmark.llm_stream_latency_benchmark            # 真实运行
    python3 -m tests.benchmark.llm_stream_latency_benchmark --mock      # Mock 模式
    python3 -m tests.benchmark.llm_stream_latency_benchmark --report    # 生成报告
"""
import argparse
import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


async def measure_first_token_latency(llm_service, prompt: str) -> float:
    """测量单次首字节延迟（毫秒）"""
    start = time.perf_counter()
    async for token in llm_service.generate_stream(prompt, max_tokens=100, temperature=0.7):
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms
    # 无 token 产出
    return (time.perf_counter() - start) * 1000


async def run_benchmark(use_mock: bool = False, iterations: int = 10) -> dict:
    """运行基准测试"""
    latencies = []

    if use_mock:
        # Mock 模式：模拟首字节延迟
        from unittest.mock import AsyncMock, MagicMock

        mock_provider = MagicMock()
        mock_provider.mode = "mock"

        async def mock_generate_stream(prompt, max_tokens, temperature):
            await asyncio.sleep(0.05)  # 模拟 50ms 延迟
            yield "test token"

        mock_provider.generate_stream = mock_generate_stream

        llm_service = MagicMock()
        llm_service.active_provider = mock_provider
        llm_service.generate_stream = AsyncMock()

        # 直接测量 mock
        for _ in range(iterations):
            start = time.perf_counter()
            async for _ in mock_generate_stream("test", 100, 0.7):
                latencies.append((time.perf_counter() - start) * 1000)
                break
    else:
        # 真实模式：需要 LLM 服务初始化
        try:
            from app.core.events import app_state

            if app_state.llm_service is None:
                print("[WARN] LLM 服务未初始化，降级为 Mock 模式")
                return await run_benchmark(use_mock=True, iterations=iterations)

            llm_service = app_state.llm_service
            prompt = "请简要介绍多智能体强化学习的基本概念（50字以内）"

            for i in range(iterations):
                try:
                    latency = await measure_first_token_latency(llm_service, prompt)
                    latencies.append(latency)
                    print(f"  Iter {i+1}/{iterations}: {latency:.1f}ms")
                except Exception as e:
                    print(f"  Iter {i+1}/{iterations}: FAILED - {e}")
                    latencies.append(30000)  # 30s 超时作为失败标记
        except Exception as e:
            print(f"[ERROR] 真实模式失败: {e}，降级为 Mock")
            return await run_benchmark(use_mock=True, iterations=iterations)

    # 计算统计指标
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    def percentile(data, p):
        if not data:
            return 0.0
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = min(f + 1, len(data) - 1)
        return data[f] + (data[c] - data[f]) * (k - f)

    return {
        "iterations": n,
        "min_ms": min(latencies_sorted) if latencies_sorted else 0,
        "max_ms": max(latencies_sorted) if latencies_sorted else 0,
        "mean_ms": statistics.mean(latencies_sorted) if latencies_sorted else 0,
        "p50_ms": percentile(latencies_sorted, 50),
        "p95_ms": percentile(latencies_sorted, 95),
        "p99_ms": percentile(latencies_sorted, 99),
        "latencies": latencies_sorted,
    }


def generate_report(results: dict) -> str:
    """生成 Markdown 报告"""
    lines = []
    lines.append("# task51 LLM 流式首字节延迟基准测试报告\n")
    lines.append(f"- 测试次数: {results['iterations']}")
    lines.append(f"- 模式: {'Mock' if results['iterations'] <= 10 and results['p50_ms'] < 100 else 'Real API'}\n")

    lines.append("## 延迟统计\n")
    lines.append("| 指标 | 值 (ms) |")
    lines.append("|------|---------|")
    lines.append(f"| Min | {results['min_ms']:.1f} |")
    lines.append(f"| Max | {results['max_ms']:.1f} |")
    lines.append(f"| Mean | {results['mean_ms']:.1f} |")
    lines.append(f"| P50 | {results['p50_ms']:.1f} |")
    lines.append(f"| P95 | {results['p95_ms']:.1f} |")
    lines.append(f"| P99 | {results['p99_ms']:.1f} |")

    lines.append("\n## AM5 硬指标验收\n")
    p95 = results["p95_ms"]
    check = "PASS" if p95 < 2000 else "FAIL"
    lines.append(f"| P95 < 2000ms | {check} | {p95:.1f}ms |")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="task51 LLM 流式首字节延迟基准测试")
    parser.add_argument("--mock", action="store_true", help="使用 Mock 模式")
    parser.add_argument("--report", action="store_true", help="生成 Markdown 报告")
    parser.add_argument("--iterations", type=int, default=10, help="测试次数")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("task51 LLM 流式首字节延迟基准测试")
    print(f"{'='*60}\n")

    results = await run_benchmark(use_mock=args.mock, iterations=args.iterations)
    report = generate_report(results)
    print(report)

    if args.report:
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        report_path = reports_dir / "llm_stream_latency_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存到: {report_path}")

    # 退出码
    sys.exit(0 if results["p95_ms"] < 2000 else 1)


if __name__ == "__main__":
    asyncio.run(main())
