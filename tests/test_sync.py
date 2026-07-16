import pytest

from scripts import sync


def use_temp_data(monkeypatch, tmp_path):
    concepts = tmp_path / "concepts.jsonl"
    relations = tmp_path / "relations.jsonl"
    monkeypatch.setattr(sync, "CONCEPTS", concepts)
    monkeypatch.setattr(sync, "RELATIONS", relations)
    return concepts, relations


def concept(slug, label=None):
    return {
        "slug": slug,
        "label": label or slug.title(),
        "description": "",
        "metadata": {},
    }


def relation(source, target, relation_type):
    return {
        "source": source,
        "target": target,
        "type": relation_type,
        "metadata": {},
    }


def test_check_accepts_extensible_relation_types(monkeypatch, tmp_path):
    concepts_path, relations_path = use_temp_data(monkeypatch, tmp_path)
    sync.write_jsonl(concepts_path, [concept("algorithm"), concept("queue")])
    sync.write_jsonl(
        relations_path,
        [relation("queue", "algorithm", "implemented_by")],
    )

    concepts, relations = sync.check(format_check=True, quiet=True)

    assert len(concepts) == 2
    assert relations[0]["type"] == "implemented_by"


def test_check_rejects_dangling_relations(monkeypatch, tmp_path):
    concepts_path, relations_path = use_temp_data(monkeypatch, tmp_path)
    sync.write_jsonl(concepts_path, [concept("queue")])
    sync.write_jsonl(
        relations_path,
        [relation("queue", "missing", "related_to")],
    )

    with pytest.raises(SystemExit, match="missing concepts"):
        sync.check(quiet=True)


def test_format_data_is_deterministic(monkeypatch, tmp_path):
    concepts_path, relations_path = use_temp_data(monkeypatch, tmp_path)
    concepts_path.write_text(
        '\n'.join(
            [
                '{"slug":"queue","label":"Queue","description":"","metadata":{}}',
                '{"slug":"array","label":"Array","description":"","metadata":{}}',
            ]
        )
        + '\n',
        encoding="utf-8",
    )
    relations_path.write_text("", encoding="utf-8")

    sync.format_data()

    assert concepts_path.read_text(encoding="utf-8").splitlines()[0].endswith(
        '"slug":"array"}'
    )
    sync.check(format_check=True, quiet=True)


def test_build_plan_reports_add_update_and_remove():
    repository_concepts = [concept("array", "Array"), concept("queue", "Queue")]
    database_concepts = [concept("queue", "Old Queue"), concept("stack", "Stack")]
    repository_relations = [relation("array", "queue", "related_to")]
    database_relations = [relation("stack", "queue", "related_to")]

    plan = sync.build_plan(
        repository_concepts,
        repository_relations,
        database_concepts,
        database_relations,
    )

    assert plan["concepts"]["add"] == 1
    assert plan["concepts"]["update"] == 1
    assert plan["concepts"]["remove_if_pruned"] == 1
    assert plan["relations"]["add"] == 1
    assert plan["relations"]["remove_if_pruned"] == 1


def test_prune_requires_explicit_confirmation(monkeypatch, tmp_path):
    concepts_path, relations_path = use_temp_data(monkeypatch, tmp_path)
    sync.write_jsonl(concepts_path, [concept("queue")])
    sync.write_jsonl(relations_path, [])

    with pytest.raises(SystemExit, match="confirm-prune"):
        sync.push(apply=True, prune=True, confirm_prune="")
