import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .operations import apply_change, discover_candidate, import_legacy, preview_change, twitch_discover
from .reports import export_bundle, write_report
from .review import QUEUE_KINDS, QUEUE_STATUSES, RECORD_TABLES, inspect_record, review_queue
from .store import PLATFORMS, ROOT, edit, load, validate


def main(argv=None):
    parser = argparse.ArgumentParser(description='ThaiVirtualCreatorRegistry — evidence-backed cross-platform catalog')
    parser.add_argument('--data', type=Path, default=ROOT / 'data/registry.json')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('validate')
    legacy = commands.add_parser('import-legacy')
    legacy.add_argument('--csv', type=Path, required=True)
    legacy.add_argument('--source-commit', required=True)
    candidate = commands.add_parser('candidate')
    candidate.add_argument('--platform', choices=PLATFORMS, required=True)
    candidate.add_argument('--url', required=True)
    candidate.add_argument('--name', required=True)
    candidate.add_argument('--source-url', required=True)
    candidate.add_argument('--method', choices=['manual_search', 'official_crosslink', 'self_submission'], default='manual_search')
    candidate.add_argument('--query', default='')
    candidate.add_argument('--observed-at')
    candidate.add_argument('--platform-id')
    candidate.add_argument('--id-namespace')
    review = commands.add_parser('apply')
    review.add_argument('--file', type=Path, required=True)
    review.add_argument('--dry-run', action='store_true', help='Validate and show field changes without saving')
    queue = commands.add_parser('queue', help='List candidates and account review issues')
    queue.add_argument('--platform', choices=PLATFORMS)
    queue.add_argument('--kind', choices=QUEUE_KINDS)
    queue.add_argument('--status', choices=QUEUE_STATUSES, default='pending')
    queue.add_argument('--priority', default=None, help='Filter by priority (1=identity blockers, 2=stable-ID, 3=lifecycle, 4=coverage)')
    queue.add_argument('--query', default='')
    queue.add_argument('--limit', type=int, default=50)
    queue.add_argument('--offset', type=int, default=0)
    inspect = commands.add_parser('inspect', help='Read a record and its stored evidence and relationships')
    inspect.add_argument('kind', choices=RECORD_TABLES)
    inspect.add_argument('id')
    twitch = commands.add_parser('twitch-discover')
    twitch.add_argument('--max-pages', type=int, default=3)
    twitch.add_argument('--language', default='th')
    discover_all = commands.add_parser('discover-all', help='Multi-platform browser-driven discovery via Playwright')
    discover_all.add_argument('--headless', action='store_true', help='Run Chromium in headless mode')
    discover_all.add_argument('--platform', action='append', dest='platforms', help='Target platform (repeatable)')
    discover_all.add_argument('--query', action='append', dest='queries', help='Search query (repeatable)')
    discover_all.add_argument('--expand-registry', action='store_true', help='Seed discovery from existing registry accounts/personas without auto-linking')
    discover_all.add_argument('--max-results', type=int, default=20, help='Maximum results per platform/query')
    discover_all.add_argument('--max-pages', type=int, default=3, help='Maximum pages per platform/query')
    discover_all.add_argument('--max-seeds', type=int, default=250, help='Maximum expansion seeds from registry')
    discover_all.add_argument('--mode', choices=['broad', 'registry-expansion', 'intake', 'missing-platforms'], default='broad', help='Discovery mode')
    discover_all.add_argument('--include-intake', action='store_true', help='Ingest un-ingested directory & owner crosslink queues from intake/ directory')
    discover_all.add_argument('--output', type=Path, default=None, help='Output path for discovered candidate observations JSON')
    discover_all.add_argument('--timeout', type=float, default=30.0, help='Navigation timeout in seconds')
    discover_all.add_argument('--profile-dir', type=Path, default=None, help='Persistent local browser profile directory')
    discover_all.add_argument('--incremental', action='store_true', help='Skip queries that were recently completed within freshness window')
    discover_all.add_argument('--freshness-days', type=int, default=7, help='Freshness window in days for incremental discovery (default 7)')
    cov_cmd = commands.add_parser('coverage', help='Display cross-platform catalog coverage statistics')
    cov_cmd.add_argument('--format', choices=['table', 'json'], default='table')
    mat_cmd = commands.add_parser('missing-matrix', help='Display persona missing-platform matrix')
    mat_cmd.add_argument('--limit', type=int, default=50)
    mat_cmd.add_argument('--format', choices=['table', 'json'], default='table')
    quality = commands.add_parser('quality', help='Generate data-quality and evidence freshness audit report')
    quality.add_argument('--as-of', default=datetime.now(timezone.utc).date().isoformat())
    quality.add_argument('--output', type=Path, default=ROOT / 'reports/current')
    for name in ('report', 'export'):
        sub = commands.add_parser(name)
        sub.add_argument('--as-of', default=datetime.now(timezone.utc).date().isoformat())
        sub.add_argument('--output', type=Path, default=ROOT / ('reports' if name == 'report' else 'dist/snapshot'))
        if name == 'report':
            sub.add_argument('--active-days', type=int, default=90)
    map_cmd = commands.add_parser('map-creators', help='Run the creator-link pipeline (YT → X → hub → platforms)')
    map_cmd.add_argument('--stage',
        choices=['youtube-to-x', 'x-to-hub', 'hub-to-platforms', 'build-review', 'all'],
        default='all', help='Pipeline stage to run')
    map_cmd.add_argument('--limit', type=int, default=None, help='Max accounts to process')
    map_cmd.add_argument('--offset', type=int, default=0, help='Skip first N accounts (for batching)')
    map_cmd.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    map_cmd.add_argument('--profile-dir', type=Path, default=None, help='Persistent browser profile (for logged-in X)')
    map_cmd.add_argument('--model', default='grok-4.3', help='Grok model for X Search')
    map_cmd.add_argument('--delay', type=float, default=0.5, help='Seconds between Grok API calls')
    map_cmd.add_argument('--output', type=Path, default=None, help='Output directory (default: intake/consolidated/)')
    map_cmd.add_argument('--no-existing-evidence', action='store_true',
        help='Skip scanning existing intake files (forces all accounts through Grok)')
    args = parser.parse_args(argv)
    try:
        dry_run = args.command == 'apply' and args.dry_run
        if args.command in {'import-legacy', 'candidate', 'apply', 'twitch-discover', 'discover-all', 'map-creators'} and not dry_run:
            if args.command == 'map-creators':
                from .pipeline.runner import (
                    load_youtube_seeds, run_youtube_to_x, run_x_to_hub,
                    run_hub_to_platforms, run_build_review,
                )
                import os
                from datetime import date as _date
                out_dir = args.output or (ROOT / 'intake/consolidated')
                out_dir.mkdir(parents=True, exist_ok=True)
                review_dir = ROOT / 'reviews/pending'
                review_dir.mkdir(parents=True, exist_ok=True)
                today = _date.today().isoformat()
                seeds = load_youtube_seeds(args.data)
                stage = args.stage
                result = {'stage': stage, 'seeds': len(seeds)}

                def _latest_jsonl(prefix: str):
                    files = [
                        p for p in out_dir.glob(f'{prefix}-*.jsonl')
                        if 'pass1' not in p.name and 'remaining' not in p.name
                    ]
                    if not files:
                        files = list(out_dir.glob(f'{prefix}-*.jsonl'))
                    if not files:
                        raise FileNotFoundError(
                            f'No {prefix}-*.jsonl in {out_dir}; run the previous stage first'
                        )
                    return max(files, key=lambda p: p.stat().st_mtime)

                if stage in ('youtube-to-x', 'all'):
                    try:
                        yt_x_path = _latest_jsonl('youtube-to-x')
                    except FileNotFoundError:
                        yt_x_path = out_dir / f'youtube-to-x-{today}.jsonl'
                    r = run_youtube_to_x(
                        seeds, yt_x_path,
                        limit=args.limit, offset=args.offset,
                        model=args.model, delay=args.delay,
                        use_existing_evidence=not args.no_existing_evidence,
                    )
                    result['youtube-to-x'] = r
                if stage in ('x-to-hub', 'all'):
                    yt_x_path = _latest_jsonl('youtube-to-x')
                    x_hub_path = out_dir / f'x-profile-links-{today}.jsonl'
                    r = run_x_to_hub(
                        yt_x_path, x_hub_path,
                        profile_dir=args.profile_dir,
                        headless=args.headless,
                        limit=args.limit,
                    )
                    result['x-to-hub'] = r
                if stage in ('hub-to-platforms', 'all'):
                    x_hub_path = _latest_jsonl('x-profile-links')
                    plat_path = out_dir / f'creator-platform-links-{today}.jsonl'
                    r = run_hub_to_platforms(x_hub_path, plat_path, limit=args.limit)
                    result['hub-to-platforms'] = r
                if stage in ('build-review', 'all'):
                    plat_path = _latest_jsonl('creator-platform-links')
                    review_path = review_dir / f'creator-link-map-{today}.json'
                    r = run_build_review(plat_path, review_path, args.data)
                    result['build-review'] = r
            elif args.command == 'discover-all':
                from .discovery import PlaywrightNotInstalledError, run_discovery
                try:
                    with edit(args.data) as db:
                        result = run_discovery(
                            db,
                            headless=args.headless,
                            platforms=args.platforms,
                            queries=args.queries,
                            expand_registry=args.expand_registry,
                            max_seeds=args.max_seeds,
                            mode=args.mode,
                            include_intake=args.include_intake,
                            output=args.output,
                            max_results=args.max_results,
                            max_pages=args.max_pages,
                            timeout=args.timeout,
                            profile_dir=args.profile_dir,
                            incremental=args.incremental,
                            freshness_days=args.freshness_days,
                        )
                except PlaywrightNotInstalledError as exc:
                    parser.exit(1, f'{exc}\n')
            else:
                with edit(args.data) as db:
                    if args.command == 'import-legacy':
                        result = import_legacy(db, args.csv, args.source_commit)
                    elif args.command == 'candidate':
                        fields = vars(args).copy()
                        for field in ('data', 'command'):
                            fields.pop(field)
                        result = {'candidate_or_account_id': discover_candidate(db, **fields)}
                    elif args.command == 'apply':
                        apply_change(db, json.loads(args.file.read_text(encoding='utf-8')))
                        result = {'applied': str(args.file)}
                    else:
                        result = twitch_discover(db, args.max_pages, args.language)
        else:
            if not args.data.is_file():
                raise ValueError('Registry does not exist; import a baseline or apply a reviewed change first')
            db = load(args.data)
            try:
                if args.command == 'validate':
                    validate(db)
                    result = {'valid': True}
                elif args.command == 'coverage':
                    from .discovery.coverage import format_coverage_table, get_platform_coverage
                    cov = get_platform_coverage(db)
                    if args.format == 'table':
                        print(format_coverage_table(cov))
                        return 0
                    result = {'coverage': cov}
                elif args.command == 'missing-matrix':
                    from .discovery.coverage import format_matrix_table, get_missing_platform_matrix
                    mat = get_missing_platform_matrix(db, limit=args.limit)
                    if args.format == 'table':
                        print(format_matrix_table(mat))
                        return 0
                    result = {'matrix': mat}
                elif args.command == 'queue':
                    priority = int(args.priority) if args.priority and args.priority.isdigit() else args.priority
                    result = review_queue(db, platform=args.platform, kind=args.kind, status=args.status,
                                          priority=priority, query=args.query, limit=args.limit, offset=args.offset)
                elif args.command == 'inspect':
                    result = inspect_record(db, args.kind, args.id)
                elif dry_run:
                    result = preview_change(db, json.loads(args.file.read_text(encoding='utf-8')))
                elif args.command == 'quality':
                    from .quality import write_data_quality_report
                    result = write_data_quality_report(db, args.output, args.as_of)
                elif args.command == 'report':
                    summary = write_report(db, args.output, args.as_of, args.active_days)
                    result = {'output': str(args.output), 'inventory': summary['inventory']}
                else:
                    result = export_bundle(db, args.output, args.as_of)
            finally:
                db.close()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1 if result.get('stop_reason') == 'http_error' else 0
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
        parser.exit(1, f'Registry error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
