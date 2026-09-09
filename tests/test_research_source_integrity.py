from copy import deepcopy
import pytest
from scripts.build_creator_lifecycle_evidence import VERIFIED_CREATOR_INTEL
from scripts.audit_creator_identity_mapping import audit_identity
from analytics.research_integrity import validate_scope
from scripts.audit_research_source_integrity import audit_source_integrity

@pytest.mark.parametrize('wrong,right', [('UC_nmh9XycGlquouvai2UC6g','UCuZ1ajvlGFUMCHZAPdetKHw'),('UCpGtwNmbOtgmcKIY81MIX_w','UCNTEr2_96vJnXNazr5MwNLA')])
def test_wrong_channel_subject_rejected(wrong,right):
    assert wrong not in VERIFIED_CREATOR_INTEL
    events=deepcopy(VERIFIED_CREATOR_INTEL[right])
    for e in events: e['subject_channel_id']=wrong
    with pytest.raises(AssertionError): audit_identity({wrong:events})

@pytest.mark.parametrize('field,value',[('subject_channel_id','invalid'),('subject_name','Unrelated Creator'),('source_subject','Schneider'),('source_reference','https://virtualyoutuber.fandom.com/wiki/Schneider')])
def test_subject_metadata_tampering(field,value):
    cid='UCuZ1ajvlGFUMCHZAPdetKHw'; events=deepcopy(VERIFIED_CREATOR_INTEL[cid]);events[0][field]=value
    with pytest.raises(AssertionError): audit_identity({cid:events})

def test_denominator_scope_required():
    for claim in ({}, {'numerator_scope':'FULL_REGISTRY','denominator_scope':'FROZEN_COHORT_193'}):
        with pytest.raises(AssertionError): validate_scope(claim)
    validate_scope({'numerator_scope':'FULL_REGISTRY','denominator_scope':'FROZEN_COHORT_193','scope_caveat':'Not comparable; ratio withheld'})

def test_canonical_source_integrity():
    audit_identity()
    audit_source_integrity()


def test_agency_source_cannot_bypass_independent_guard():
    cid = 'UCt8vlwt6qi6P1mz5uuStJCA'
    events = deepcopy(VERIFIED_CREATOR_INTEL[cid])
    events[0]['source_reference'] = 'https://x.com/ARP_Vtuber/status/123'
    with pytest.raises(AssertionError): audit_identity({cid: events})
