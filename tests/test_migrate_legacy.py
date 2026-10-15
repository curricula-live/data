from scripts.migrate_legacy import CONCEPT_NAMESPACE, concept_id, humanize


def test_legacy_concept_uuid_is_deterministic():
    assert str(CONCEPT_NAMESPACE) == "645d16b7-688a-5ffc-aa3d-8b6626ba1383"
    assert concept_id("queue") == "de9bf887-66f9-582c-ab57-4fd19be68e3d"


def test_humanize_handles_common_acronyms():
    assert humanize("api") == "API"
    assert humanize("fifo") == "FIFO"
