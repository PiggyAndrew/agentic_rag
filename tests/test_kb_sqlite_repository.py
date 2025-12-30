import os
import tempfile
import unittest

from backend.database.sqlite import SqliteSessionManager, init_sqlite_database
from backend.kb.knowledge_repository import SqlAlchemyKnowledgeRepository


class TestSqliteKnowledgeRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        db_path = os.path.join(self._tmp.name, "kb.sqlite3")
        self._manager = SqliteSessionManager.from_url(f"sqlite:///{db_path}", echo=False)
        migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "database", "migrations"))
        init_sqlite_database(manager=self._manager, migrations_dir=migrations_dir)
        self._repo = SqlAlchemyKnowledgeRepository(manager=self._manager)

    def tearDown(self):
        self._manager.engine.dispose()
        self._tmp.cleanup()

    def test_kb_crud(self):
        ts = 1700000000000
        created = self._repo.create_kb(
            {"kb_id": 1, "name": "kb1", "description": None, "created_at_ms": ts, "updated_at_ms": ts}
        )
        self.assertEqual(created["kb_id"], 1)
        self.assertEqual(created["name"], "kb1")

        got = self._repo.get_kb(1)
        self.assertIsNotNone(got)
        self.assertEqual(got["kb_id"], 1)

        updated = self._repo.update_kb(1, {"name": "kb1-new", "updated_at_ms": ts + 1})
        self.assertEqual(updated["name"], "kb1-new")

        all_kbs = self._repo.list_kbs()
        self.assertEqual(len(all_kbs), 1)

        self._repo.delete_kb(1)
        self.assertIsNone(self._repo.get_kb(1))

    def test_file_and_chunks(self):
        ts = 1700000000000
        self._repo.create_kb({"kb_id": 1, "name": "kb1", "description": None, "created_at_ms": ts, "updated_at_ms": ts})
        f = self._repo.create_file(
            1,
            {
                "file_id": 10,
                "name": "a.pdf",
                "mime_type": "application/pdf",
                "created_at_ms": ts,
                "updated_at_ms": ts,
                "chunk_count": 0,
                "status": "uploaded",
                "source_path": None,
            },
        )
        self.assertEqual(f["file_id"], 10)
        self.assertEqual(f["status"], "uploaded")

        chunks = [
            {"chunk_index": 0, "content": "hello", "metadata": {"p": 1}, "created_at_ms": ts, "updated_at_ms": ts},
            {"chunk_index": 1, "content": "world", "metadata": None, "created_at_ms": ts, "updated_at_ms": ts},
        ]
        self._repo.upsert_chunks(1, 10, chunks)
        got_chunks = self._repo.list_chunks(1, 10)
        self.assertEqual(len(got_chunks), 2)
        self.assertEqual(got_chunks[0]["chunk_index"], 0)
        self.assertEqual(got_chunks[0]["metadata"], {"p": 1})

        file_after = self._repo.get_file(1, 10)
        self.assertIsNotNone(file_after)
        self.assertEqual(file_after["chunk_count"], 2)

        self._repo.delete_file(1, 10)
        self.assertIsNone(self._repo.get_file(1, 10))
        self.assertEqual(self._repo.list_chunks(1, 10), [])


if __name__ == "__main__":
    unittest.main()
