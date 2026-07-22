"""Representative load test — see docs/performance-and-reliability.md
#load-test-results.

Self-contained (httpx + asyncio, both already dependencies) rather than
adding k6/locust for one script. Hits a representative read-heavy mix
(the traffic pattern this app actually expects — browsing/search, not
writes) against a running local API instance and reports p50/p95/p99
latency and error rate per endpoint.

Usage: .venv/Scripts/python scripts/load_test.py [--base-url URL]
       [--concurrency N] [--requests-per-endpoint N]
Requires the API running locally (`uvicorn app.main:app`) with the local
Postgres/Redis containers up (see docker-compose.yml).
"""

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field

import httpx

ENDPOINTS = [
    ("GET /health", "/health"),
    ("GET /api/v1/designs/published", "/api/v1/designs/published?limit=20"),
    ("GET /api/v1/categories", "/api/v1/categories"),
]


@dataclass
class EndpointResult:
    label: str
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0

    def summary(self) -> str:
        if not self.latencies_ms:
            return f"{self.label}: no successful requests ({self.errors} errors)"
        sorted_latencies = sorted(self.latencies_ms)
        p50 = statistics.median(sorted_latencies)
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95) - 1]
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99) - 1]
        total = len(self.latencies_ms) + self.errors
        error_rate = self.errors / total * 100
        return (
            f"{self.label}: n={total} p50={p50:.1f}ms p95={p95:.1f}ms "
            f"p99={p99:.1f}ms errors={self.errors} ({error_rate:.1f}%)"
        )


async def _hit(client: httpx.AsyncClient, path: str, result: EndpointResult) -> None:
    start = time.perf_counter()
    try:
        response = await client.get(path)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if response.status_code >= 500:
            result.errors += 1
        else:
            result.latencies_ms.append(elapsed_ms)
    except httpx.HTTPError:
        result.errors += 1


async def _run_endpoint(
    client: httpx.AsyncClient, label: str, path: str, *, concurrency: int, requests: int
) -> EndpointResult:
    result = EndpointResult(label=label)
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded() -> None:
        async with semaphore:
            await _hit(client, path, result)

    await asyncio.gather(*(_bounded() for _ in range(requests)))
    return result


async def main(base_url: str, concurrency: int, requests_per_endpoint: int) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for label, path in ENDPOINTS:
            wall_start = time.perf_counter()
            result = await _run_endpoint(
                client, label, path, concurrency=concurrency, requests=requests_per_endpoint
            )
            wall_elapsed = time.perf_counter() - wall_start
            throughput = requests_per_endpoint / wall_elapsed
            print(f"{result.summary()} | throughput={throughput:.1f} req/s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests-per-endpoint", type=int, default=200)
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.concurrency, args.requests_per_endpoint))
