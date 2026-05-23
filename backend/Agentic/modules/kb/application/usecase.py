from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from backend.shared.ids import parse_document_id, parse_kb_id
from backend.shared.utils.time_utils import now_ms
from backend.modules.kb.application.services.document_ingestion import DocumentIngestionService
from backend.modules.kb.application.usecase_search import KnowledgeSearchUseCase
from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.errors import KnowledgeConflictError, KnowledgeNotFoundError
from backend.modules.kb.domain.document_models import Document
from backend.modules.kb.domain.enums import DocumentStatus
from backend.modules.kb.domain.kb_models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBasePatch
from backend.modules.kb.domain.ports import KbDocumentStoragePort, KnowledgeBaseControllerPort, KnowledgeRepositoryPort, SearchPort
from backend.modules.kb.domain.ports import VectorStorePort


@dataclass(frozen=True, slots=True)
class KnowledgeBaseUseCase:
    controller: KnowledgeBaseControllerPort
    repo: KnowledgeRepositoryPort
    ingestion: DocumentIngestionService
    storage: KbDocumentStoragePort
    search_usecase: Optional[KnowledgeSearchUseCase] = None
    vstore: Optional[VectorStorePort] = None

    def list_kbs(self) -> List[KnowledgeBase]:
        rows = list(self.repo.list_kbs())
        rows.sort(key=lambda m: int(getattr(m, "created_at_ms", 0)), reverse=True)
        return rows

    def create_kb(self, payload: Any) -> KnowledgeBase:
        existing_ids = [int(r.kb_id) for r in self.repo.list_kbs()]
        start_id = (max(existing_ids) + 1) if existing_ids else 1
        ts = now_ms()
        name = str(getattr(payload, "name", "") or "").strip()
        desc = (str(getattr(payload, "description", "") or "").strip() or None)
        for candidate in range(start_id, start_id + 50):
            try:
                self.controller.createKnowledgeBase(candidate, reset_sqlite=False)
                self.repo.create_kb(
                    KnowledgeBaseCreate(
                        kb_id=candidate,
                        name=name,
                        description=desc,
                        created_at_ms=ts,
                        updated_at_ms=ts,
                    )
                )
                created = self.repo.get_kb(int(candidate))
                if created is None:
                    raise RuntimeError("创建知识库失败：持久化后未找到记录")
                return created
            except KnowledgeConflictError:
                continue
        raise KnowledgeConflictError("创建知识库失败：KB ID 已被占用")

    def update_kb(self, kb_id: str, payload: Any) -> KnowledgeBase:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        ts = now_ms()
        patch = KnowledgeBasePatch(
            name=str(getattr(payload, "name", "")).strip() if (getattr(payload, "name", None) is not None) else None,
            description=(str(getattr(payload, "description", "")).strip() or None) if (getattr(payload, "description", None) is not None) else None,
            updated_at_ms=ts,
        )
        try:
            row = self.repo.update_kb(kb_int, patch)
        except KnowledgeNotFoundError:
            created_at = self._disk_kb_created_at(kb_int)
            self.repo.create_kb(
                KnowledgeBaseCreate(
                    kb_id=kb_int,
                    name=patch.name or f"知识库 {kb_int}",
                    description=patch.description,
                    created_at_ms=created_at,
                    updated_at_ms=ts,
                )
            )
            row = self.repo.get_kb(kb_int)
            if row is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
        return row

    def delete_kb(self, kb_id: str) -> None:
        kb_int = parse_kb_id(kb_id)
        try:
            self.repo.delete_kb(kb_int)
        except KnowledgeNotFoundError:
            pass
        self.controller.deleteKnowledgeBase(kb_int)
        if self.vstore is not None:
            try:
                self.vstore.clear(int(kb_int))
            except Exception:
                pass

    def list_documents(self, kb_id: str) -> List[Document]:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        return list(self.repo.list_documents(kb_int))
#上传文档
    def save_uploaded_document(self, kb_id: str, name: str, content_b64: Optional[str]) -> Document:
        if not name or not name.strip():
            raise ValueError("文件名不能为空")
        if len(name) > 255:
            raise ValueError("文件名长度不能超过 255 个字符")
        if not name.split("/")[-1].split("\\")[-1]:
            raise ValueError("文件名格式无效")
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        lower = name.lower()
        self.storage.ensure_uploads_dir(kb_int)
        saved_path = self.storage.upload_path(kb_int, name)
        if content_b64:
            import base64

            try:
                decoded = base64.b64decode(content_b64)
                if len(decoded) > 100 * 1024 * 1024:
                    raise ValueError("文件大小不能超过 100MB")
                self.storage.write_bytes(saved_path, decoded)
            except Exception as e:
                raise ValueError(f"文件解码失败: {e}")

        ts = now_ms()
        rows = self.repo.list_documents(kb_int)
        existing_row = None
        for r in rows:
            if str(r.filename or "") == name:
                existing_row = r
                break

        if existing_row is not None:
            fid = int(existing_row.document_id)
        else:
            used_ids = [int(r.document_id) for r in rows]
            start_id = (max(used_ids) + 1) if used_ids else 1
            fid = start_id
            for candidate in range(start_id, start_id + 50):
                try:
                    self.repo.create_document(
                        kb_int,
                        Document(
                            kb_id=kb_int,
                            document_id=candidate,
                            filename=name,
                            mime_type="application/octet-stream",
                            created_at_ms=ts,
                            updated_at_ms=ts,
                            chunk_count=0,
                            status=DocumentStatus.uploaded,
                            source_path=saved_path,
                        ),
                    )
                    fid = candidate
                    break
                except KnowledgeConflictError:
                    continue

        mime = (
            "application/pdf"
            if lower.endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if lower.endswith(".xlsx")
            else "application/octet-stream"
        )
        self._upsert_document_row(
            kb_int,
            fid,
            name=name,
            mime_type=mime,
            created_at_ms=ts,
            updated_at_ms=ts,
            chunk_count=0,
            status=str(DocumentStatus.uploaded.value),
            source_path=saved_path,
        )
        row = self.repo.get_document(int(kb_int), int(fid))
        if row is None:
            raise RuntimeError("上传文档登记失败：持久化后未找到文档记录")
        return row
#按文件后缀，解析文档
    def ingest_uploaded_document(self, kb_id: str, filename: str) -> Document:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        lower = filename.lower()
        src_path = self.storage.upload_path(kb_int, filename)
        if not self.storage.exists(src_path):
            raise FileNotFoundError("文档不存在，请先上传")

        if lower.endswith(".pdf"):
            info = self.ingestion.ingest_pdf(kb_id=kb_int, pdf_path=src_path)
            mime = "application/pdf"
        elif lower.endswith(".xlsx"):
            info = self.ingestion.ingest_excel(kb_id=kb_int, excel_path=src_path)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise ValueError("仅支持 PDF 或 Excel(xlsx)")

        ts = now_ms()
        self._upsert_document_row(
            kb_int,
            int(info.document_id),
            name=info.filename,
            mime_type=info.mime_type or mime,
            created_at_ms=ts,
            updated_at_ms=ts,
            chunk_count=int(info.chunk_count),
            status=str(info.status),
            source_path=src_path,
        )
        row = self.repo.get_document(int(kb_int), int(info.document_id))
        if row is None:
            raise RuntimeError("文档 ingestion 持久化失败：未找到文档记录")
        return row

    def read_document_chunks(self, kb_id: str, document_id: str) -> List[DocumentChunk]:
        kb_int = parse_kb_id(kb_id)
        fid = parse_document_id(document_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        return list(self.repo.list_document_chunks(kb_int, fid))

    def delete_document_global(self, document_id: str) -> None:
        fid = parse_document_id(document_id)
        for kb_int in self.storage.list_kb_ids(self.controller.base_dir):
            if self.controller.deleteDocument(kb_int, fid):
                try:
                    self.repo.delete_document(kb_int, fid)
                except KnowledgeNotFoundError:
                    pass
                if self.vstore is not None:
                    try:
                        self.vstore.delete_by_filter(int(kb_int), {"document_id": int(fid)})
                    except Exception:
                        pass
                return
        raise FileNotFoundError("文档不存在")

    def search(self, kb_id: int, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库
        
        Args:
            kb_id: 知识库 ID
            query: 搜索查询
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        if self.search_usecase is None:
            return []
        return self.search_usecase.search(kb_id, query, top_k)

    def get_documents_meta(self, kb_id: int, document_ids: List[int]) -> List[Dict[str, Any]]:
        """获取文档元数据
        
        Args:
            kb_id: 知识库 ID
            document_ids: 文档 ID 列表
            
        Returns:
            文档元数据列表
        """
        if self.search_usecase is None:
            return []
        return self.search_usecase.get_documents_meta(kb_id, document_ids)

    def read_document_chunks_dict(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Dict[str, Any]]:
        """读取文档块
        
        Args:
            kb_id: 知识库 ID
            chunks: 文档块列表，格式为 [{"documentId": int, "chunkIndex": int}, ...]
            
        Returns:
            文档块内容列表
        """
        if self.search_usecase is None:
            return []
        return self.search_usecase.read_document_chunks(kb_id, chunks)

    def list_documents_paginated(self, kb_id: int, page: int, page_size: int) -> List[Dict[str, Any]]:
        """分页列出文档
        
        Args:
            kb_id: 知识库 ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            文档列表
        """
        if self.search_usecase is None:
            return []
        return self.search_usecase.list_documents_paginated(kb_id, page, page_size)

    def _disk_kb_created_at(self, kb_int: int) -> int:
        return int(self.storage.kb_created_at_ms(self.controller.kb_dir(kb_int)) or now_ms())

    def _ensure_kb_row(self, kb_int: int) -> None:
        row = self.repo.get_kb(kb_int)
        if row is not None:
            return
        created_at = self._disk_kb_created_at(kb_int)
        self.repo.create_kb(
            KnowledgeBaseCreate(
                kb_id=kb_int,
                name=f"知识库 {kb_int}",
                description=None,
                created_at_ms=created_at,
                updated_at_ms=created_at,
            )
        )

    def _upsert_document_row(
        self,
        kb_int: int,
        document_id: int,
        *,
        name: str,
        mime_type: str,
        created_at_ms: int,
        updated_at_ms: int,
        chunk_count: int,
        status: str,
        source_path: Optional[str],
    ) -> None:
        existing = self.repo.get_document(kb_int, document_id)
        document = Document(
            kb_id=int(kb_int),
            document_id=int(document_id),
            filename=name,
            mime_type=mime_type,
            created_at_ms=int(created_at_ms if existing is None else existing.created_at_ms),
            updated_at_ms=int(updated_at_ms),
            chunk_count=int(chunk_count),
            status=DocumentStatus.coerce(status),
            source_path=source_path,
            summary=None if existing is None else existing.summary,
            details=None if existing is None else existing.details,
        )
        if existing is None:
            self.repo.create_document(kb_int, document)
        else:
            self.repo.update_document(kb_int, document_id, document)
