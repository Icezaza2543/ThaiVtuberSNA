from copy import deepcopy
import pytest
from tests.test_expanded_backfill import setup_interactions, Comments, next_claim


def test_replay_compares_events_not_only_state(tmp_path):
    engine, job, journal, jid, book = setup_interactions(tmp_path, Comments())
    captured = []
    original = engine.batches.commit
    def capture(*args):
        captured.append(deepcopy(args))
        return original(*args)
    engine.batches.commit = capture
    engine.step(job=job, journal=journal, claim=next_claim(journal, jid))
    before = deepcopy(book.tabs[0].cells)
    writes = book.tabs[0].writes
    assert original(*captured[0])['reconciled'] is True
    assert book.tabs[0].cells == before and book.tabs[0].writes == writes
    changed = deepcopy(captured[0])
    changed[2][0]['viewer_hash'] = 'synthetic-conflicting-participant'
    with pytest.raises(RuntimeError, match='Conflicting replay content'):
        original(*changed)
    assert book.tabs[0].cells == before and book.tabs[0].writes == writes
