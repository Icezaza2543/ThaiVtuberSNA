"""Orchestrator for multi-platform Playwright discovery."""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from uuid import uuid4

from ..operations import discover_candidate
from ..store import put, rows, uid, validate
from .adapters import get_adapter, list_available_platforms
from .browser import BrowserSession, check_playwright
from .coverage import get_missing_platform_search_targets
from .dedupe import deduplicate_leads
from .enrich import StableIdResolver, enrich_lead
from .incremental import should_skip_discovery
from .intake_loader import load_intake_batches
from .models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .normalize import normalize_url
from .queries import get_registry_expansion_seeds, resolve_queries


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_discovery_score(lead: DiscoveryLead, is_known_handle: bool = False, source_count: int = 1) -> int:
    """Calculate deterministic relevance/priority score for review ordering."""
    score = 0
    text = f"{lead.name} {lead.handle or ''} {lead.query} {lead.url}".lower()
    if lead.method in ("official_crosslink", "crosslink_crawl"):
        score += 4
    if any(k in text for k in ("vtuber", "vstreamer", "pngtuber", "vsinger", "วีทูป", "วีทูบ", "virtual")):
        score += 3
    if any("\u0e00" <= c <= "\u0e7f" for c in f"{lead.name} {lead.query}"):
        score += 3
    if is_known_handle:
        score += 2
    if source_count > 1:
        score += 2
    if "ganknow" in (lead.source_url or "").lower():
        score += 2
    if lead.name and lead.name != lead.url:
        score += 1
    return score


async def run_discovery_async(
    db: Any,
    *,
    headless: bool = True,
    platforms: Optional[List[str]] = None,
    queries: Optional[List[str]] = None,
    expand_registry: bool = False,
    max_seeds: int = 250,
    mode: str = "broad",
    include_intake: bool = False,
    output: Optional[Path] = None,
    max_results: int = 20,
    max_pages: int = 3,
    timeout: float = 30.0,
    profile_dir: Optional[Path] = None,
    browser_context: Optional[Any] = None,
    custom_resolver: Optional[Callable[[str, str], Optional[Tuple[str, str]]]] = None,
    incremental: bool = False,
    freshness_days: int = 7,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute discovery across selected platforms and queries using Playwright.
    Persists results into db through registry candidate/evidence/run flow.
    """
    validate(db)

    # 1. Resolve platforms and queries
    target_platforms = platforms or list_available_platforms()
    for p in target_platforms:
        if p not in list_available_platforms():
            raise ValueError(f"Unknown discovery platform: {p}")

    additional_queries = None
    if expand_registry or mode == "registry-expansion":
        additional_queries = get_registry_expansion_seeds(db, max_seeds=max_seeds)

    limits = DiscoveryLimits(max_results=max_results, max_pages=max_pages, timeout=timeout)

    all_batches: List[DiscoveryBatch] = []
    platform_summaries: Dict[str, Dict[str, Any]] = {}
    skipped_queries: List[Dict[str, Any]] = []

    # Load intake queues if requested
    if mode == "intake" or include_intake:
        intake_batches = load_intake_batches(platforms=platforms, max_records=max_results if mode == "intake" else 1500)
        all_batches.extend(intake_batches)

    # Helper to execute an adapter query and expand execution sub-batches
    async def _run_adapter_query(adapter, page, q):
        try:
            batch = await adapter.discover(page, q, limits)
            if hasattr(batch, "sub_batches") and batch.sub_batches:
                batches = batch.sub_batches
            elif isinstance(batch, list):
                batches = batch
            else:
                batches = [batch]
            for b in batches:
                if not b.query:
                    b.query = q
                if not b.method:
                    b.method = "playwright_search"
            return batches
        except Exception as exc:
            msg = str(exc)
            status = "timeout" if "timeout" in msg.lower() else "partial"
            return [
                adapter.create_batch(
                    query=q,
                    method="playwright_search",
                    status=status,
                    error_message=msg,
                )
            ]

    # Helper to execute discovery across target platforms
    async def _execute_platforms(page):
        for plat in target_platforms:
            adapter = get_adapter(plat)
            platform_queries = resolve_queries(
                queries,
                additional_queries=additional_queries,
                platform=plat,
            )
            plat_batches = []
            plat_skipped = []
            for q in platform_queries:
                if incremental:
                    skip, skip_reason, last_run = should_skip_discovery(
                        db,
                        platform=adapter.platform,
                        query=q,
                        method="playwright_search",
                        as_of=as_of,
                        freshness_days=freshness_days,
                    )
                    if skip:
                        plat_skipped.append({
                            "platform": adapter.platform,
                            "query": q,
                            "method": "playwright_search",
                            "reason": skip_reason,
                            "last_run": last_run,
                        })
                        continue
                batches = await _run_adapter_query(adapter, page, q)
                plat_batches.extend(batches)
            all_batches.extend(plat_batches)
            skipped_queries.extend(plat_skipped)
            search_batches = [b for b in plat_batches if b.method == "playwright_search"]
            if not plat_batches and plat_skipped:
                platform_summaries[plat] = {
                    "status": "skipped_fresh",
                    "skip_reason": plat_skipped[0]["reason"],
                    "hits": 0,
                    "skipped_queries": len(plat_skipped),
                }
            else:
                final_status = "completed"
                for b in (search_batches or plat_batches):
                    if b.status != "completed":
                        final_status = b.status
                        break
                total_hits = sum(len(b.leads) for b in plat_batches)
                plat_summary = {"status": final_status, "hits": total_hits}
                if plat_skipped:
                    plat_summary["skipped_queries"] = len(plat_skipped)
                platform_summaries[plat] = plat_summary

    # 2. Run adapters within browser session (or supplied mock context)
    if mode != "intake":
        if browser_context is not None:
            page = getattr(browser_context, "page", None)
            if page is None and hasattr(browser_context, "new_page"):
                page = await browser_context.new_page()
            await _execute_platforms(page)
        else:
            check_playwright()
            async with BrowserSession(headless=headless, profile_dir=profile_dir, timeout=timeout) as context:
                page = await context.new_page()
                await _execute_platforms(page)
    else:
        for b in all_batches:
            if b.platform not in platform_summaries:
                platform_summaries[b.platform] = {"status": "completed", "hits": 0}
            platform_summaries[b.platform]["hits"] += len(b.leads)

    # 3. Provenance-preserving persistence
    observed_at = _now_iso()
    runs_by_key: Dict[Tuple[str, str, str, str], str] = {}
    resolver = StableIdResolver(custom_resolver=custom_resolver)

    existing_candidates = {r["id"] for r in rows(db, "candidates")}
    existing_accounts = {r["id"] for r in rows(db, "accounts")}
    known_handles = {
        r["handle"].lower().lstrip("@") for r in rows(db, "accounts") if r.get("handle")
    }

    discovered_candidates: Set[str] = set()
    discovered_known_accounts: Set[str] = set()
    raw_hits = sum(len(b.leads) for b in all_batches)
    unique_entities: Set[str] = set()

    query_yield: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"raw_hits": 0, "new_candidates": 0, "known_accounts": 0}))
    source_yield: Dict[str, Dict[str, int]] = defaultdict(lambda: {"profiles_crawled": 0, "links_inspected": 0, "new_candidates": 0, "stable_ids_resolved": 0})
    sample_new_candidates: List[Dict[str, Any]] = []

    for b in all_batches:
        run_key = (
            b.platform,
            b.query,
            b.method,
            b.source_url if b.method == "crosslink_crawl" else "",
        )
        if run_key not in runs_by_key:
            run_id = uid("run", f"{b.platform}:{b.query}:{b.method}:{run_key[3]}:{observed_at}:{uuid4().hex[:8]}")
            runs_by_key[run_key] = run_id
            put(
                db,
                "discovery_runs",
                dict(
                    id=run_id,
                    platform=b.platform,
                    method=b.method,
                    query=b.query or "",
                    observed_at=observed_at,
                    stop_reason=b.status if b.status in {
                        "completed", "partial", "login_required", "captcha",
                        "rate_limited", "selector_changed", "timeout", "blocked"
                    } else "completed",
                    pages=b.pages_seen,
                    records_seen=b.records_seen if b.records_seen is not None else len(b.leads),
                ),
            )

        if b.source_url:
            source_yield[b.source_url]["links_inspected"] += len(b.leads)

        # Deduplicate leads within this single batch execution
        batch_leads = deduplicate_leads(b.leads)
        if batch_leads:
            batch_leads = list(await asyncio.gather(*(resolver.enrich_lead_async(lead) for lead in batch_leads)))
        for lead in batch_leads:
            # Calculate discovery score
            lead_h = (lead.handle or "").lower().lstrip("@")
            is_known = lead_h in known_handles if lead_h else False
            score = compute_discovery_score(lead, is_known_handle=is_known)
            lead.metadata["discovery_score"] = score

            # Determine target run_id
            method = lead.method or b.method or "playwright_search"
            raw_source = lead.source_url or b.source_url or lead.url
            if raw_source and raw_source.startswith("https://"):
                try:
                    parsed_s = urlparse(raw_source)
                    lead_source = raw_source if (parsed_s.hostname and "." in parsed_s.hostname) else lead.url
                except Exception:
                    lead_source = lead.url
            else:
                lead_source = lead.url

            lead_key = (
                lead.platform,
                lead.query or b.query,
                method,
                lead_source if method == "crosslink_crawl" else "",
            )
            if lead_key not in runs_by_key:
                lead_run_id = uid(
                    "run", f"{lead.platform}:{lead_key[1]}:{lead_key[2]}:{lead_key[3]}:{observed_at}:{uuid4().hex[:8]}"
                )
                runs_by_key[lead_key] = lead_run_id
                put(
                    db,
                    "discovery_runs",
                    dict(
                        id=lead_run_id,
                        platform=lead.platform,
                        method=lead_key[2],
                        query=lead_key[1],
                        observed_at=lead.observed_at or observed_at,
                        stop_reason="completed",
                        pages=1,
                        records_seen=1,
                    ),
                )
            target_run_id = runs_by_key[lead_key]

            result_id = discover_candidate(
                db,
                platform=lead.platform,
                url=lead.url,
                name=lead.name or lead.handle or lead.url,
                source_url=lead_source,
                method=method,
                query=lead.query or b.query or "",
                observed_at=lead.observed_at or observed_at,
                platform_id=lead.platform_id,
                id_namespace=lead.id_namespace,
                run_id=target_run_id,
                source_kind=lead.source_kind or "platform_observation",
            )

            unique_entities.add(result_id)
            query_yield[lead.platform][lead.query or b.query]["raw_hits"] += 1
            if result_id in existing_accounts:
                discovered_known_accounts.add(result_id)
                query_yield[lead.platform][lead.query or b.query]["known_accounts"] += 1
            elif result_id not in existing_candidates:
                discovered_candidates.add(result_id)
                query_yield[lead.platform][lead.query or b.query]["new_candidates"] += 1
                if lead_source:
                    source_yield[lead_source]["new_candidates"] += 1
                    if lead.platform_id:
                        source_yield[lead_source]["stable_ids_resolved"] += 1
                sample_new_candidates.append({
                    "id": result_id,
                    "platform": lead.platform,
                    "name": lead.name or lead.handle or "",
                    "handle": lead.handle,
                    "url": lead.url,
                    "platform_id": lead.platform_id,
                    "id_namespace": lead.id_namespace,
                    "source_url": lead_source,
                    "query": lead.query or b.query,
                    "discovery_score": score,
                })

    # Optional export of observations to file
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": {
                    "raw_hits": raw_hits,
                    "new_candidates": len(discovered_candidates),
                    "known_accounts": len(discovered_known_accounts),
                },
                "candidates": sample_new_candidates,
            }, f, indent=2, ensure_ascii=False)

    # 4. Revalidate db
    validate(db)

    # Format yields for summary
    formatted_query_yield = {p: dict(qmap) for p, qmap in query_yield.items()}
    formatted_source_yield = {s: dict(stats) for s, stats in source_yield.items() if stats["new_candidates"] > 0 or stats["links_inspected"] > 0}

    return {
        "platforms": platform_summaries,
        "raw_hits": raw_hits,
        "deduplicated_leads": len(unique_entities),
        "new_candidates": len(discovered_candidates),
        "known_accounts": len(discovered_known_accounts),
        "enrichment": resolver.stats,
        "query_yield": formatted_query_yield,
        "source_yield": formatted_source_yield,
        "sample_candidates": sorted(sample_new_candidates, key=lambda c: c["discovery_score"], reverse=True)[:50],
        "skipped_queries": skipped_queries,
    }


def run_discovery(db: Any, **kwargs) -> Dict[str, Any]:
    """Synchronous entry point for discovery orchestration."""
    return asyncio.run(run_discovery_async(db, **kwargs))
