"""Shared scope and canonical-series contracts for public research artifacts."""
from pathlib import Path
import pandas as pd
import re

def is_ratio_key(key):
    return bool(re.search(r"(?:^|_)(?:pct|ratio|rate|share|gini|density|percent|percentage)(?:_|$)", key.lower()))

ROOT = Path(__file__).resolve().parents[1]
COHORT = 'FROZEN_COHORT_193'

def reactivation_series():
    frame = pd.read_parquet(ROOT / 'data/industry/audience_behavior_yearly.parquet')
    return [{'year': int(r.year), 'accounts': int(r.reactivated_accounts), 'partial_window': int(r.year) == 2026} for r in frame.sort_values('year').itertuples() if int(r.year) >= 2022]

def validate_scope(claim):
    assert claim.get('numerator_scope') and claim.get('denominator_scope'), 'Missing denominator scope'
    assert claim['numerator_scope'] == claim['denominator_scope'] or claim.get('scope_caveat'), 'Incompatible denominator scopes'

def annotate_scopes(value, path=''):
    # Declares the sampling universe, not that different measures share a counting unit.
    if isinstance(value, list):
        for child in value: annotate_scopes(child, path)
    elif isinstance(value, dict):
        for key, child in list(value.items()): annotate_scopes(child, path + '/' + key)
        keys = list(value)
        if any(is_ratio_key(key) for key in keys) or is_ratio_key(str(value.get('metric', ''))):
            scope = 'ILLUSTRATIVE_MARKET_SCENARIO' if path.startswith('/market') else COHORT
            value['numerator_scope'] = scope
            value['denominator_scope'] = scope

def integrity_payload():
    return {'supply_saturation': {'status': 'INSUFFICIENT_EVIDENCE', 'claim_class': 'HYPOTHESIS', 'numerator_scope': 'FULL_REGISTRY', 'denominator_scope': COHORT, 'scope_caveat': 'Audience coverage exists only for the frozen cohort. No registry-to-cohort competition ratio is valid.'}, 'reactivation_series': reactivation_series()}


def validate_scopes(value):
    """Check every declared or ratio-bearing object in the public payload."""
    if isinstance(value, list):
        for child in value:
            validate_scopes(child)
    elif isinstance(value, dict):
        if any(is_ratio_key(k) for k in value) or is_ratio_key(str(value.get('metric', ''))) or 'numerator_scope' in value:
            validate_scope(value)
        for child in value.values():
            validate_scopes(child)
