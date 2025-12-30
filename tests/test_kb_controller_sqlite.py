import os
import tempfile
import unittest

from backend.database.sqlite import SqliteSessionManager, init_sqlite_database
from backend.kb.knowledge_base import PersistentKnowledgeBaseController


class TestPersistentKnowledgeBaseControllerSqlite(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._base_dir = os.path.join(self._tmp.name, "data", "kb")
        db_path = os.path.join(self._tmp.name, "kb.sqlite3")
        self._manager = SqliteSessionManager.from_url(f"sqlite:///{db_path}", echo=False)
        migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "database", "migrations"))
        init_sqlite_database(manager=self._manager, migrations_dir=migrations_dir)
        self._kb = PersistentKnowledgeBaseController(base_dir=self._base_dir, manager=self._manager)

    def tearDown(self):
        self._manager.engine.dispose()
        self._tmp.cleanup()

    def test_no_json_storage_for_files_and_chunks(self):
        self._kb.createKnowledgeBase(1)
        info = self._kb.add_file(1, "a.pdf", chunk_count=0, status="uploaded")
        self._kb.save_chunks(1, info.id, [{"content": "hello", "metadata": {"p": 1}}])

        self.assertFalse(os.path.exists(os.path.join(self._base_dir, "1", "files.json")))
        self.assertFalse(os.path.exists(os.path.join(self._base_dir, "1", "chunks", f"{info.id}.json")))

        files = self._kb._repo.list_files(1)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].file_id, info.id)
        chunks = self._kb._load_file_chunks(1, info.id)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, "hello")


if __name__ == "__main__":
    unittest.main()
