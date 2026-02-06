import os
import shutil
import tempfile
import time

from backend.database.sqlite import SqliteSessionManager, init_sqlite_database
from backend.entrypoints.composition.kb import build_kb_usecase


def main() -> int:
    pdf_path = (os.getenv("BENCH_PDF_PATH") or "").strip()
    if not pdf_path:
        print("Set BENCH_PDF_PATH to a local PDF file path to run this benchmark.")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        base_dir = os.path.join(tmp, "data", "kb")
        db_path = os.path.join(tmp, "kb.sqlite3")
        manager = SqliteSessionManager.from_url(f"sqlite:///{db_path}", echo=False)
        migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "database", "migrations"))
        init_sqlite_database(manager=manager, migrations_dir=migrations_dir)
        kb = build_kb_usecase(manager=manager, base_dir=base_dir)

        kb.create_kb(type("P", (), {"name": "bench", "description": None})())
        name = os.path.basename(pdf_path)
        kb.save_upload("1", name, None)
        uploads_dir = os.path.join(base_dir, "1", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        shutil.copyfile(pdf_path, os.path.join(uploads_dir, name))

        t0 = time.perf_counter()
        kb.ingest_uploaded_file("1", name)
        dt = time.perf_counter() - t0
        print(f"ingest_uploaded_file wall time: {dt:.3f}s")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
