import os
import tempfile
import unittest

from backend.api.models import KnowledgeBaseCreate
from backend.database.sqlite import SqliteSessionManager, init_sqlite_database
from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.kb.knowledge_repository import SqlAlchemyKnowledgeRepository
from backend.kb.knowledge_service import KnowledgeService


class TestSqliteKnowledgeService(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._base_dir = os.path.join(self._tmp.name, "data", "kb")
        db_path = os.path.join(self._tmp.name, "kb.sqlite3")
        self._manager = SqliteSessionManager.from_url(f"sqlite:///{db_path}", echo=False)
        migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "database", "migrations"))
        init_sqlite_database(manager=self._manager, migrations_dir=migrations_dir)
        self._ctrl = PersistentKnowledgeBaseController(base_dir=self._base_dir, manager=self._manager)
        self._repo = SqlAlchemyKnowledgeRepository(manager=self._manager)
        self._svc = KnowledgeService(controller=self._ctrl, repo=self._repo)

    def tearDown(self):
        try:
            self._ctrl.close()
        except Exception:
            pass
        self._manager.engine.dispose()
        self._tmp.cleanup()

    def test_create_kb_and_list(self):
        kb = self._svc.create_kb(KnowledgeBaseCreate(name="kb1", description="d"))
        self.assertEqual(kb.kb_id, 1)
        self.assertEqual(kb.name, "kb1")
        self.assertTrue(os.path.exists(os.path.join(self._base_dir, "1")))
        all_kbs = self._svc.list_kbs()
        self.assertEqual(len(all_kbs), 1)

    def test_upload_and_sync_chunks(self):
        kb = self._svc.create_kb(KnowledgeBaseCreate(name="kb1", description=None))
        info = self._svc.save_upload(f"kb-{kb.kb_id}", "a.pdf", None)
        self.assertEqual(str(info.status), "uploaded")
        fid = int(info.file_id)

        self._ctrl.save_chunks(
            1,
            file_id=fid,
            chunks=[
                {"content": "c1", "metadata": {"k": 1}},
                {"content": "c2", "metadata": None},
            ],
        )

        chunks = self._svc.read_file_chunks("kb-1", f"f-{fid}")
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(getattr(chunks[0].metadata, "data", None), {"k": 1})

        files = self._svc.list_files("kb-1")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].chunk_count, 2)


if __name__ == "__main__":
    unittest.main()
