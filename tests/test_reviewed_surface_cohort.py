from scripts.build_reviewed_surface_cohort import classify_channel

def identity(**changes):
    row=dict(review_status="SUPPORTED",event_type="identity_start",source_title="Debut",evidence_summary="",review_reason="",persona_label="Synthetic creator");row.update(changes);return row

def test_explicit_virtual_identity_is_strict():
    assert classify_channel(identity(review_reason="Owner explicitly identifies as a VTuber persona"))[0]=="STRICT_VIRTUAL"

def test_verified_debut_without_virtual_medium_is_provisional_not_rejected():
    assert classify_channel(identity(review_status="VERIFIED",review_reason="First stream and self introduction"))[0]=="PROVISIONAL_VIRTUAL"

def test_reviewed_virtual_role_can_confirm_channel():
    assert classify_channel(identity(review_status="AMBIGUOUS",event_type="unknown"),dict(review_status="SUPPORTED",entity_type="virtual_creator"))[0]=="STRICT_VIRTUAL"

def test_project_account_hosting_someone_else_is_excluded():
    row=identity(review_status="AMBIGUOUS",event_type="unknown",persona_label="Synthetic Project",review_reason="Project channel hosts A debut; cannot assign A identity start to the project entity.")
    assert classify_channel(row)[0]=="EXCLUDE_NON_PERSONA_ACCOUNT"

def test_rejected_event_does_not_make_channel_non_vtuber():
    assert classify_channel(identity(review_status="REJECTED_AS_IDENTITY_EVENT",event_type="not_identity_event"))[0]=="HOLD_NEEDS_CHANNEL_REVIEW"

def test_conflicting_positive_and_nonpersona_evidence_holds():
    row=identity(review_reason="Project channel hosts A debut; cannot assign A identity start to the project entity. VTuber")
    assert classify_channel(row)[0]=="HOLD_CONFLICTING_ELIGIBILITY"
