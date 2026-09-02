#!/usr/bin/env python3
"""Entity graph (T56-T59) health check.

Exercises the real, running HTTP API end-to-end — auth, node/edge
creation, tier auto-verify vs. held behavior, confirm/revert, and all
guard rails — then deletes its own test nodes/edges directly from the
DB (no delete API exists for graph data, by design, matching the
audit-log-style permanence of everything else in this module).

Entities are NOT created automatically from document processing today
(create_node/create_edge are only ever called from the API router and
tests) — this script populates its own throwaway test data rather than
depending on anything already in your account.

Usage:
    docker compose exec backend python3 scripts/check_entity_graph.py \\
        --email you@example.com --password '...' [--base-url http://localhost:8000]

    Or set ENTITY_CHECK_EMAIL / ENTITY_CHECK_PASSWORD env vars instead of --email/--password.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from app.database import AsyncSessionLocal
from app.models.entity_edge import EntityEdge
from app.models.entity_node import EntityNode
from sqlalchemy import delete

PASS = "PASS"
FAIL = "FAIL"

results = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    results.append((label, status, detail))
    print(f"[{status}] {label}" + (f" — {detail}" if detail and status == FAIL else ""))
    return condition


async def run(base_url: str, email: str, password: str) -> bool:
    node1_id = node2_id = edge1_id = edge2_id = None
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        try:
            print("=== Entity Graph Health Check ===\n")

            # 1. Auth
            resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
            if not check("Login", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"):
                return False
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Create two nodes
            r1 = await client.post("/api/v1/entities", headers=headers, json={
                "entity_type": "person", "label": "_healthcheck_person",
            })
            check("Create node 1", r1.status_code == 201, f"HTTP {r1.status_code}: {r1.text}")
            node1_id = r1.json().get("id") if r1.status_code == 201 else None

            r2 = await client.post("/api/v1/entities", headers=headers, json={
                "entity_type": "property", "label": "_healthcheck_property",
            })
            check("Create node 2", r2.status_code == 201, f"HTTP {r2.status_code}: {r2.text}")
            node2_id = r2.json().get("id") if r2.status_code == 201 else None

            if not (node1_id and node2_id):
                print("\nCannot continue without both nodes.")
                return False

            # 3. Tier-1 edge must auto-verify as "machine"
            e1 = await client.post("/api/v1/entities/edges", headers=headers, json={
                "edge_type": "manages", "tier": 1, "source_node_id": node1_id,
                "target_type": "entity", "target_node_id": node2_id, "confidence": 0.95,
            })
            edge1_id = e1.json().get("id") if e1.status_code == 201 else None
            check("Tier-1 edge auto-verifies as 'machine'",
                  e1.status_code == 201 and e1.json().get("status") == "machine",
                  f"HTTP {e1.status_code}: {e1.text}")

            # 4. Tier-4 edge must stay "held" even at high confidence
            e2 = await client.post("/api/v1/entities/edges", headers=headers, json={
                "edge_type": "legal_owner_of", "tier": 4, "source_node_id": node1_id,
                "target_type": "entity", "target_node_id": node2_id, "confidence": 0.99,
            })
            edge2_id = e2.json().get("id") if e2.status_code == 201 else None
            check("Tier-4 (legal) edge stays 'held' despite 0.99 confidence",
                  e2.status_code == 201 and e2.json().get("status") == "held",
                  f"HTTP {e2.status_code}: {e2.text}")

            if not (edge1_id and edge2_id):
                print("\nCannot continue without both edges.")
                return False

            # 5. Entity 360 view shows both edges
            v = await client.get(f"/api/v1/entities/{node1_id}/360", headers=headers)
            linked_ids = {e["edge_id"] for e in v.json().get("linked_entities", [])} if v.status_code == 200 else set()
            check("Entity 360 view shows both linked edges",
                  v.status_code == 200 and {edge1_id, edge2_id} <= linked_ids,
                  f"HTTP {v.status_code}: {v.text}")

            # 6. Confirm the held tier-4 edge
            c = await client.post(f"/api/v1/entities/edges/{edge2_id}/confirm", headers=headers)
            check("Confirm held (tier-4) edge succeeds",
                  c.status_code == 200 and c.json().get("status") == "verified",
                  f"HTTP {c.status_code}: {c.text}")

            # 7. Guard rails
            g1 = await client.post(f"/api/v1/entities/edges/{edge1_id}/confirm", headers=headers)
            check("Guard rail: confirming a machine edge is blocked (409)", g1.status_code == 409, f"HTTP {g1.status_code}: {g1.text}")

            g2 = await client.post(f"/api/v1/entities/edges/{edge1_id}/revert", headers=headers)
            check("Guard rail: reverting a machine edge is blocked (409)", g2.status_code == 409, f"HTTP {g2.status_code}: {g2.text}")

            g3 = await client.post(f"/api/v1/entities/edges/{edge2_id}/confirm", headers=headers)
            check("Guard rail: double-confirming a verified edge is blocked (409)", g3.status_code == 409, f"HTTP {g3.status_code}: {g3.text}")

            # 8. Revert the verified edge back to held
            rv = await client.post(f"/api/v1/entities/edges/{edge2_id}/revert", headers=headers)
            check("Revert verified edge returns it to 'held'",
                  rv.status_code == 200 and rv.json().get("status") == "held",
                  f"HTTP {rv.status_code}: {rv.text}")

            return True
        finally:
            # Cleanup — no delete API exists for graph data by design, so go direct to the DB.
            async with AsyncSessionLocal() as db:
                if edge1_id or edge2_id:
                    ids = [i for i in (edge1_id, edge2_id) if i]
                    await db.execute(delete(EntityEdge).where(EntityEdge.id.in_(ids)))
                if node1_id or node2_id:
                    ids = [i for i in (node1_id, node2_id) if i]
                    await db.execute(delete(EntityNode).where(EntityNode.id.in_(ids)))
                await db.commit()
            print("\n(Test nodes/edges cleaned up from the database.)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default=os.environ.get("ENTITY_CHECK_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("ENTITY_CHECK_PASSWORD"))
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error("--email/--password required (or set ENTITY_CHECK_EMAIL / ENTITY_CHECK_PASSWORD)")

    asyncio.run(run(args.base_url, args.email, args.password))

    print("\n=== Summary ===")
    passed = sum(1 for _, s, _ in results if s == PASS)
    total = len(results)
    print(f"{passed}/{total} checks passed")
    if passed < total:
        print("\nFailed checks:")
        for label, status, detail in results:
            if status == FAIL:
                print(f"  - {label}: {detail}")
        sys.exit(1)
    print("Entity graph is healthy.")
    sys.exit(0)


if __name__ == "__main__":
    main()
