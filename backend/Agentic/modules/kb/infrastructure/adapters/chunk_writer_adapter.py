from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.chunk_serialization import document_chunk_to_metadata
from backend.modules.kb.domain.document_models import Document
from backend.modules.kb.domain.enums import DocumentStatus
from backend.modules.kb.domain.ports import (
    EmbeddingPort,
    KnowledgeChunkWriterPort,
    VectorStorePort,
)

logger = logging.getLogger(__name__)


class ChunkWriterAdapter(KnowledgeChunkWriterPort):
    def __init__(
        self,
        repo: Any,
        vstore: VectorStorePort,
        embedder: EmbeddingPort,
    ):
        self._repo = repo
        self._vstore = vstore
        self._embedder = embedder

    def save_document_chunks(self, kb_id: int, document_id: int, chunks: List[DocumentChunk]) -> bool:
        if not chunks:
            raise RuntimeError("chunk 保存失败：未生成可持久化的 chunk")
        now_ms = int(time.time() * 1000)
        texts: List[str] = []
        vitems: List[Dict[str, Any]] = []
        non_empty_indices: List[int] = []

        for i, documentChunk in enumerate(chunks):
            content = documentChunk.ai_text()
            texts.append(content)
            if content.strip():
                non_empty_indices.append(i)
            inline_text = documentChunk.inline_text() or content
            storage_document_id = int(document_id)
            vitems.append(
                {
                    "document_id": storage_document_id,
                    "chunk_index": int(documentChunk.chunk_index),
                    "content": content,
                    "metadata": document_chunk_to_metadata(documentChunk),
                    "preview": (inline_text[:200] + "...") if len(inline_text) > 200 else inline_text,
                }
            )

        if non_empty_indices:
            to_embed = [texts[i] for i in non_empty_indices]
            try:
                embs = self._embedder.embed_texts(to_embed)
                if len(embs) != len(to_embed):
                    raise RuntimeError(
                        f"向量化失败：期望 {len(to_embed)} 个 embedding，实际得到 {len(embs)} 个"
                    )
                for k, i in enumerate(non_empty_indices):
                    vitems[i]["embedding"] = embs[k].tolist() if hasattr(embs[k], "tolist") else embs[k]
            except Exception as e:
                logger.error("Failed to embed chunks: %s", e)
                raise RuntimeError("chunk 保存失败：向量化未完成") from e
        else:
            raise RuntimeError("chunk 保存失败：没有可向量化的有效文本内容")

        db_update_success = False
        try:
            self._repo.upsert_document_chunks(int(kb_id), int(document_id), chunks)
            db_update_success = True
        except Exception as e:
            logger.error("Failed to upsert chunks to database: %s", e)
            raise

        vitems_embedded = [item for item in vitems if "embedding" in item]
        if vitems_embedded:
            try:
                self._delete_vector_items(int(kb_id), int(document_id))
                self._add_vector_items(int(kb_id), vitems_embedded)
            except Exception as e:
                logger.error("Failed to update vector store: %s", e)
                if db_update_success:
                    try:
                        self._update_document_status(
                            kb_id=int(kb_id),
                            document_id=int(document_id),
                            chunk_count=len(chunks),
                            status=DocumentStatus.chunked,
                            updated_at_ms=now_ms,
                        )
                    except Exception as rollback_error:
                        logger.error("Failed to rollback database update: %s", rollback_error)
                raise RuntimeError("chunk 保存失败：向量写入失败") from e

            self._update_document_status(
                kb_id=int(kb_id),
                document_id=int(document_id),
                chunk_count=len(chunks),
                status=DocumentStatus.indexed,
                updated_at_ms=now_ms,
            )
            return True

        raise RuntimeError("chunk 保存失败：向量化未完成")



    def _delete_vector_items(self, kb_id: int, document_id: int) -> None:
        if hasattr(self._vstore, "delete_by_filter"):
            self._vstore.delete_by_filter(int(kb_id), {"document_id": int(document_id)})
            return
        self._vstore.delete_items(int(kb_id), {"document_id": int(document_id)})

    def _add_vector_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        if hasattr(self._vstore, "add"):
            self._vstore.add(int(kb_id), items)
            return
        self._vstore.add_items(int(kb_id), items)

    def _document_name_of(self, kb_id: int, document_id: int) -> str:
        existing = self._repo.get_document(int(kb_id), int(document_id))
        return existing.filename if existing is not None else ""

    def _update_document_status(
        self,
        *,
        kb_id: int,
        document_id: int,
        chunk_count: int,
        status: DocumentStatus,
        updated_at_ms: int,
    ) -> None:
        self._repo.update_document(
            int(kb_id),
            int(document_id),
            self._document_with_status(
                kb_id=int(kb_id),
                document_id=int(document_id),
                chunk_count=int(chunk_count),
                status=status,
                updated_at_ms=int(updated_at_ms),
            ),
        )

    def _document_with_status(
        self,
        *,
        kb_id: int,
        document_id: int,
        chunk_count: int,
        status: DocumentStatus,
        updated_at_ms: int,
    ) -> Document:
        existing = self._repo.get_document(int(kb_id), int(document_id))
        if existing is not None:
            return Document(
                kb_id=int(kb_id),
                document_id=int(document_id),
                filename=existing.filename,
                mime_type=existing.mime_type,
                created_at_ms=existing.created_at_ms,
                updated_at_ms=int(updated_at_ms),
                chunk_count=int(chunk_count),
                status=status,
                source_path=existing.source_path,
                summary=existing.summary,
                details=existing.details,
            )

        filename = self._document_name_of(kb_id, document_id)
        return Document(
            kb_id=int(kb_id),
            document_id=int(document_id),
            filename=filename,
            mime_type=self._guess_mime_type(filename),
            created_at_ms=int(updated_at_ms),
            updated_at_ms=int(updated_at_ms),
            chunk_count=int(chunk_count),
            status=status,
            source_path=None,
        )

    def _guess_mime_type(self, filename: str) -> str:
        lower = (filename or "").lower()
        if lower.endswith(".pdf"):
            return "application/pdf"
        if lower.endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/octet-stream"
