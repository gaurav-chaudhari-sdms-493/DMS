"""T97 — performance pass at realistic corpus volume.

Not a synthetic micro-benchmark against internal functions: this drives
the real running stack (real HTTP API, real Celery ingestion pipeline,
real Postgres/pgvector, real embedding provider) exactly the way a user
or the frontend would, and reports real numbers. No load-testing
artifact existed before this — this is a starting baseline, not a claim
that this IS "real corpus volumes" at production scale (that needs a
real corpus, same class of gap as A1).

Uses plain-text documents deliberately: this benchmark measures the
parts of the pipeline that scale with corpus SIZE (chunking, embedding,
DB writes, vector/keyword/trigram search) rather than the parts that
scale with per-document AI-call cost (VLM extraction, LLM summary
generation) — those are a separate, already-measured cost (see
COSTING_AND_ESTIMATION.md), and hammering external LLM/VLM APIs at
volume here would mostly benchmark rate limits, not the system.

Usage (inside the backend container):
    python3 scripts/perf_benchmark.py --email <email> --password <password> --count 50
"""
import argparse
import asyncio
import io
import random
import statistics
import time

import httpx

WORDS = (
    "district survey property valuation wakf register serial mutation "
    "boundary tenant grant deed institution masjid dargah graveyard "
    "trust mosque endowment religious khuldabad aurangabad taluka "
    "mango tamarind neem tree area guntha hectare assessment revenue"
).split()


def make_document(index: int, run_nonce: int) -> bytes:
    # run_nonce makes content different across script invocations — without
    # it, a re-run generates byte-identical content to a prior run and the
    # real hash-based dedup check (correctly!) skips every "upload" as a
    # duplicate, silently uploading zero new documents (found live: a
    # second run reported "0/30 indexed" not because of a bug, but because
    # all 30 really were exact repeats of the first run's real uploads).
    rng = random.Random(run_nonce * 100000 + index)
    lines = [f"Synthetic benchmark document {index} (run {run_nonce})."]
    for _ in range(40):
        lines.append(" ".join(rng.choices(WORDS, k=12)))
    # A guaranteed-unique, findable term so search queries have a real target.
    lines.append(f"UNIQUEMARKER{run_nonce}{index:05d} appears only in this document.")
    return "\n".join(lines).encode("utf-8")


async def sign_up_or_login(client: httpx.AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/sign-up", json={"full_name": "Perf Bench", "email": email, "password": password})
    if resp.status_code not in (201, 409, 400):
        resp.raise_for_status()
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


async def upload_all(client: httpx.AsyncClient, token: str, count: int, run_nonce: int) -> tuple[float, list[str]]:
    headers = {"Authorization": f"Bearer {token}"}
    doc_ids = []
    t0 = time.monotonic()
    for i in range(count):
        content = make_document(i, run_nonce)
        files = {"files": (f"bench_{run_nonce}_{i:04d}.txt", io.BytesIO(content), "text/plain")}
        resp = await client.post("/api/v1/documents/bulk", headers=headers, files=files)
        resp.raise_for_status()
        body = resp.json()
        if not body["documents"]:
            print(f"    WARNING: upload {i} returned no document (dedup skip?): {body}")
        for doc in body["documents"]:
            doc_ids.append(doc["document_id"])
    upload_elapsed = time.monotonic() - t0
    return upload_elapsed, doc_ids


async def wait_for_indexing(client: httpx.AsyncClient, token: str, doc_ids: list[str], timeout_s: float) -> tuple[float, int, int]:
    headers = {"Authorization": f"Bearer {token}"}
    remaining = set(doc_ids)
    failed = 0
    t0 = time.monotonic()
    while remaining and (time.monotonic() - t0) < timeout_s:
        resp = await client.get("/api/v1/documents", headers=headers, params={"limit": len(doc_ids) + 10})
        resp.raise_for_status()
        by_id = {d["id"]: d["status"] for d in resp.json()}
        for doc_id in list(remaining):
            status = by_id.get(doc_id)
            if status == "indexed":
                remaining.discard(doc_id)
            elif status == "failed":
                remaining.discard(doc_id)
                failed += 1
        if remaining:
            await asyncio.sleep(2)
    elapsed = time.monotonic() - t0
    indexed = len(doc_ids) - len(remaining) - failed
    return elapsed, indexed, failed


async def run_searches(client: httpx.AsyncClient, token: str, count: int, num_queries: int, run_nonce: int) -> list[float]:
    headers = {"Authorization": f"Bearer {token}"}
    latencies = []
    rng = random.Random(42)
    for _ in range(num_queries):
        i = rng.randrange(count)
        query = rng.choice([f"UNIQUEMARKER{run_nonce}{i:05d}", rng.choice(WORDS)])
        t0 = time.monotonic()
        resp = await client.post(
            "/api/v1/search/", headers=headers,
            json={"query": query, "limit": 10, "generate_summary": False},
        )
        resp.raise_for_status()
        latencies.append((time.monotonic() - t0) * 1000)
    return latencies


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(int(len(s) * p), len(s) - 1)
    return s[idx]


async def main():
    parser = argparse.ArgumentParser(description="T97 performance baseline against the real running stack")
    parser.add_argument("--email", default="perfbench@test.com")
    parser.add_argument("--password", default="PerfBench123!")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=50, help="number of documents to ingest")
    parser.add_argument("--queries", type=int, default=30, help="number of search queries to run")
    parser.add_argument("--index-timeout", type=float, default=180.0)
    args = parser.parse_args()

    run_nonce = int(time.time()) % 100000

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0) as client:
        token = await sign_up_or_login(client, args.email, args.password)

        print("=" * 70)
        print(f"T97 — Performance baseline: {args.count} documents, {args.queries} search queries (run {run_nonce})")
        print("=" * 70)

        upload_elapsed, doc_ids = await upload_all(client, token, args.count, run_nonce)
        print(f"\n[1] Upload (bulk API, {args.count} docs): {upload_elapsed:.1f}s total, {upload_elapsed / args.count * 1000:.0f}ms/doc avg")

        index_elapsed, indexed, failed = await wait_for_indexing(client, token, doc_ids, args.index_timeout)
        rate = indexed / index_elapsed if index_elapsed > 0 else 0
        print(f"\n[2] Indexing (async Celery pipeline): {index_elapsed:.1f}s wall time")
        print(f"    {indexed}/{args.count} indexed, {failed} failed, {len(doc_ids) - indexed - failed} still pending at timeout")
        print(f"    Throughput: {rate:.2f} docs/sec ({rate * 60:.0f} docs/min)")

        latencies = await run_searches(client, token, args.count, args.queries, run_nonce)
        print(f"\n[3] Search latency ({args.queries} queries, generate_summary=False, real hybrid retrieval):")
        print(f"    min={min(latencies):.0f}ms  p50={percentile(latencies, 0.5):.0f}ms  "
              f"p95={percentile(latencies, 0.95):.0f}ms  max={max(latencies):.0f}ms  "
              f"mean={statistics.mean(latencies):.0f}ms")

        print("\n" + "=" * 70)
        print("This is a starting baseline against synthetic text documents, not the")
        print("official real-corpus performance number (needs a real corpus, blocked")
        print("on A1 same as T25/T31/T32). Re-run with a larger --count as the corpus grows.")
        print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
