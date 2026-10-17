from scripts.publish import build_plan, has_changes, load_canonical_state


def empty_state():
    return {"concepts": [], "predicates": [], "statements": [], "definitions": []}


def test_plan_reports_add_update_and_remove():
    repository = empty_state()
    database = empty_state()

    repository["concepts"] = [
        {"id": "11111111-1111-4111-8111-111111111111", "slug": "array", "label": "Array"},
        {"id": "22222222-2222-4222-8222-222222222222", "slug": "queue", "label": "Queue"},
    ]
    database["concepts"] = [
        {"id": "22222222-2222-4222-8222-222222222222", "slug": "queue", "label": "Old Queue"},
        {"id": "33333333-3333-4333-8333-333333333333", "slug": "stack", "label": "Stack"},
    ]

    plan = build_plan(repository, database)

    assert plan["concepts"]["add"] == 1
    assert plan["concepts"]["update"] == 1
    assert plan["concepts"]["remove"] == 1
    assert has_changes(plan)


def test_current_canonical_repository_loads_as_v2():
    state = load_canonical_state()

    assert state["concepts"]
    assert state["predicates"]
    assert state["statements"]
    assert all("description" not in concept for concept in state["concepts"])
    assert len({concept["id"] for concept in state["concepts"]}) == len(state["concepts"])
