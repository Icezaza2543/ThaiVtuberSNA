"""Deterministic deduplication of discovery leads within a run."""

from typing import Dict, List, Tuple

from .models import DiscoveryLead
from .normalize import normalize_url


def deduplicate_leads(leads: List[DiscoveryLead]) -> List[DiscoveryLead]:
    """
    Deduplicate a list of leads within a discovery run.
    Key preference:
    1. (platform, id_namespace, platform_id) when stable ID exists
    2. (platform, canonical_url)
    """
    deduped_by_id: Dict[Tuple[str, str, str], DiscoveryLead] = {}
    deduped_by_url: Dict[Tuple[str, str], DiscoveryLead] = {}
    result: List[DiscoveryLead] = []

    for lead in leads:
        try:
            canonical_url = normalize_url(lead.platform, lead.url)
            lead.url = canonical_url
        except ValueError:
            # If canonicalization fails, skip lead
            continue

        url_key = (lead.platform, lead.url)
        id_key = (
            (lead.platform, lead.id_namespace, lead.platform_id)
            if (lead.id_namespace and lead.platform_id)
            else None
        )

        existing = None
        if id_key and id_key in deduped_by_id:
            existing = deduped_by_id[id_key]
        elif url_key in deduped_by_url:
            existing = deduped_by_url[url_key]

        if existing:
            # Enrich existing lead
            if not existing.platform_id and lead.platform_id:
                existing.platform_id = lead.platform_id
                existing.id_namespace = lead.id_namespace
                if id_key:
                    deduped_by_id[id_key] = existing
            if not existing.handle and lead.handle:
                existing.handle = lead.handle
            if (not existing.name or existing.name == existing.handle) and lead.name:
                existing.name = lead.name
            if lead.metadata:
                existing.metadata.update(lead.metadata)
            continue

        # Register new unique lead
        result.append(lead)
        deduped_by_url[url_key] = lead
        if id_key:
            deduped_by_id[id_key] = lead

    return result
