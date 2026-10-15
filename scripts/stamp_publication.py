"""Record a verified canonical Git publication in a non-production or approved DB."""
import argparse
import subprocess

from scripts.publish import build_plan, connect, fetch_database_state, has_changes, load_canonical_state, require_target_schema


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url")
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "STAMP-VERIFIED-PUBLICATION":
        raise SystemExit("explicit publication confirmation required")
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--", "knowledge", "migration/legacy-v1"], text=True)
    if dirty:
        raise SystemExit("canonical knowledge or identity ledger is uncommitted")
    canonical = load_canonical_state()
    with connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", ("curricula-live-data-publish",))
            require_target_schema(cursor)
            cursor.execute("select to_regclass('knowledge.publication')")
            if cursor.fetchone()[0] is None:
                raise SystemExit("publication migration 0004 is required")
            if has_changes(build_plan(canonical, fetch_database_state(cursor))):
                raise SystemExit("database differs from canonical Git; publish and verify first")
            cursor.execute("""insert into knowledge.publication(singleton, git_commit)
                           values (true, %s) on conflict(singleton) do update
                           set git_commit=excluded.git_commit, published_at=now()""", (commit,))
    print(f"verified publication recorded at {commit}")


if __name__ == "__main__":
    main()
