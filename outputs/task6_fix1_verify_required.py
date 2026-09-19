import contextlib, io, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from scripts.resolve_creator_identities import main
root = Path.cwd()
evidence = root / 'docs/evidence/creator-registry-review-2026-09-19'
scratch = root / 'outputs/task6_fix1_required'
scratch.mkdir(exist_ok=True)
ledger = root / 'data/registry/identity_resolutions.json'
original = ledger.read_bytes()
inputs = {'review-bundle': evidence / 'review_bundle.json', 'baseline': evidence / 'trusted_baseline_1370.json',
          'trusted-registry': Path('C:/Users/Icezaza/Documents/GitHub/ThaiVirtualCreatorRegistry/data/registry.json'),
          'legacy-decisions': evidence / 'legacy_visual_identity_review.json', 'researched': evidence / 'identity_research_linked.json'}
base = [value for flag, path in inputs.items() for value in ('--' + flag, str(path))]
platforms = [value for platform in ('youtube', 'tiktok', 'website', 'instagram', 'facebook', 'ganknow') for value in ('--platform', platform)]
corrections = json.loads((evidence / 'trusted_link_corrections.json').read_text(encoding='utf-8'))
partial = scratch / 'partial_corrections.json'
partial.write_text(json.dumps(dict(corrections, corrections=corrections['corrections'][:-1]), ensure_ascii=False, indent=2), encoding='utf-8')
results = []
for mode in ('fresh', 'filtered_validate', 'full_validate', 'merge'):
    for supplied in ('omitted', 'partial'):
        target = scratch / (mode + '_' + supplied + '.json')
        assert not target.exists()
        args = base + ['--output', str(target)]
        if mode != 'full_validate':
            args += platforms
        if 'validate' in mode:
            args += ['--validate-only']
        elif mode == 'merge':
            args += ['--merge-existing', str(ledger)]
        else:
            args += ['--queue']
        if supplied == 'partial':
            args += ['--trusted-link-corrections', str(partial)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(args)
        error = json.loads(stderr.getvalue())['error']
        assert status == 1 and not stdout.getvalue() and not target.exists()
        assert 'missing required trusted link corrections' in error
        assert ledger.read_bytes() == original
        results.append({'mode': mode, 'supplied': supplied, 'exit_code': status, 'no_output': True, 'error': error})
stdout = io.StringIO()
with contextlib.redirect_stdout(stdout):
    status = main(base + platforms + ['--trusted-link-corrections', str(evidence / 'trusted_link_corrections.json'), '--validate-only'])
assert status == 0
summary = {'fail_closed_cases': results, 'complete_set_validate_exit': status, 'complete_set_counts': json.loads(stdout.getvalue()), 'committed_ledger_unchanged': ledger.read_bytes() == original}
(scratch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary))
