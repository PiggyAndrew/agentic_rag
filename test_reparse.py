
import os
import shutil
import json
import numpy as np
from kb.knowledge_base import PersistentKnowledgeBaseController
from kb.vector_store import LocalVectorStore

def test_reparse():
    base_dir = "temp_test_kb"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    
    # Mock embedder
    class MockEmbedder:
        def embed_texts(self, texts):
            return np.random.rand(len(texts), 4) # 4-dim embeddings

    kb_ctrl = PersistentKnowledgeBaseController(base_dir=base_dir, embedder=MockEmbedder())
    kb_id = 1
    kb_ctrl.createKnowledgeBase(kb_id)
    
    # Add a file
    file_info = kb_ctrl.add_file(kb_id, "test.pdf", 0)
    file_id = file_info.id
    
    # 1. First parse: save 2 chunks
    chunks1 = ["chunk1", "chunk2"]
    kb_ctrl.save_chunks(kb_id, file_id, chunks1)
    
    # Verify vector store has 2 items
    vstore = LocalVectorStore(base_dir=base_dir)
    meta_path = vstore._meta_path(kb_id)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"First parse meta count: {len(meta)}")
    assert len(meta) == 2
    
    # Verify embeddings.npy shape
    emb_path = vstore._emb_path(kb_id)
    embs = np.load(emb_path)
    print(f"First parse embeddings shape: {embs.shape}")
    assert embs.shape == (2, 4)
    
    # 2. Re-parse: save 3 chunks (different content)
    chunks2 = ["chunkA", "chunkB", "chunkC"]
    kb_ctrl.save_chunks(kb_id, file_id, chunks2)
    
    # Verify vector store has 3 items (not 5)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"Second parse meta count: {len(meta)}")
    assert len(meta) == 3
    assert meta[0]["preview"] == "chunkA"
    
    # Verify embeddings.npy shape
    embs = np.load(emb_path)
    print(f"Second parse embeddings shape: {embs.shape}")
    assert embs.shape == (3, 4)
    
    # Cleanup
    shutil.rmtree(base_dir)
    print("Test passed!")

if __name__ == "__main__":
    test_reparse()
