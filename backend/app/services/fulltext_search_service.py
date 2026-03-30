"""
全文搜索服务 - 支持长文本分段索引、向量语义搜索、精确位置定位

特性：
1. 长文本智能分段索引
2. 向量语义搜索（基于 ChromaDB）
3. 关键词精确匹配
4. 精确位置定位（段落、块、字符偏移）
5. 搜索结果高亮
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import json
import re
import os
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings

EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MAX_SEARCH_RESULTS = 50


@dataclass
class TextChunk:
    index: int
    content: str
    start_offset: int
    end_offset: int
    block_id: Optional[str] = None
    block_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    document_id: int
    document_title: str
    project_id: int
    project_title: str
    chunk_index: int
    content: str
    start_offset: int
    end_offset: int
    block_id: Optional[str]
    block_type: Optional[str]
    score: float
    match_type: str
    highlights: List[Tuple[int, int]] = field(default_factory=list)
    context_before: str = ""
    context_after: str = ""


class FullTextSearchService:
    _instance = None
    _client = None
    _embedding_model = None
    _embedding_load_attempted = False
    _executor = ThreadPoolExecutor(max_workers=2)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._init_client()
    
    def _init_client(self):
        persist_dir = os.path.join(os.getcwd(), "search_index")
        os.makedirs(persist_dir, exist_ok=True)
        
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    
    def _ensure_embedding_model(self) -> bool:
        if FullTextSearchService._embedding_load_attempted:
            return self._embedding_model is not None
        FullTextSearchService._embedding_load_attempted = True
        try:
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            return True
        except Exception as e:
            print(f"[FullTextSearch] 加载 embedding 模型失败: {e}")
            self._embedding_model = None
            return False
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        self._ensure_embedding_model()
        if self._embedding_model:
            return self._embedding_model.encode(text).tolist()
        return None
    
    def _get_collection_name(self, project_id: int) -> str:
        return f"search_project_{project_id}"
    
    def _get_global_collection_name(self) -> str:
        return "global_document_index"
    
    def _chunks_to_text(self, content: Any) -> str:
        if not content:
            return ""
        if isinstance(content, str):
            return content
        
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                block_content = block.get("content", "")
                if block_content:
                    text_parts.append(block_content)
        return "\n\n".join(text_parts)
    
    def _split_into_chunks(
        self, 
        text: str, 
        content: Any,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP
    ) -> List[TextChunk]:
        if not text:
            return []
        
        chunks = []
        blocks_info = []
        
        if isinstance(content, list):
            current_offset = 0
            for block in content:
                if isinstance(block, dict):
                    block_content = block.get("content", "")
                    if block_content:
                        blocks_info.append({
                            "id": block.get("id"),
                            "type": block.get("type", "paragraph"),
                            "content": block_content,
                            "start": current_offset,
                            "end": current_offset + len(block_content)
                        })
                        current_offset += len(block_content) + 2
        
        if len(text) <= chunk_size:
            block_id = blocks_info[0]["id"] if blocks_info else None
            block_type = blocks_info[0]["type"] if blocks_info else None
            chunks.append(TextChunk(
                index=0,
                content=text,
                start_offset=0,
                end_offset=len(text),
                block_id=block_id,
                block_type=block_type
            ))
            return chunks
        
        sentences = re.split(r'([。！？\n.!?]+\s*)', text)
        sentences = [''.join(sentences[i:i+2]) for i in range(0, len(sentences)-1, 2)]
        if not sentences:
            sentences = [text]
        
        current_chunk = []
        current_size = 0
        current_start = 0
        chunk_index = 0
        
        for sent in sentences:
            sent_len = len(sent)
            
            if current_size + sent_len > chunk_size and current_chunk:
                chunk_text = ''.join(current_chunk)
                block_id, block_type = self._find_block_for_offset(
                    blocks_info, current_start, current_start + len(chunk_text)
                )
                chunks.append(TextChunk(
                    index=chunk_index,
                    content=chunk_text,
                    start_offset=current_start,
                    end_offset=current_start + len(chunk_text),
                    block_id=block_id,
                    block_type=block_type
                ))
                chunk_index += 1
                
                overlap_text = ''.join(current_chunk[-overlap:]) if overlap > 0 else ""
                current_chunk = [overlap_text, sent] if overlap_text else [sent]
                current_size = len(overlap_text) + sent_len
                current_start = current_start + len(chunk_text) - len(overlap_text)
            else:
                current_chunk.append(sent)
                current_size += sent_len
        
        if current_chunk:
            chunk_text = ''.join(current_chunk)
            block_id, block_type = self._find_block_for_offset(
                blocks_info, current_start, current_start + len(chunk_text)
            )
            chunks.append(TextChunk(
                index=chunk_index,
                content=chunk_text,
                start_offset=current_start,
                end_offset=current_start + len(chunk_text),
                block_id=block_id,
                block_type=block_type
            ))
        
        return chunks
    
    def _find_block_for_offset(
        self, 
        blocks_info: List[Dict], 
        start: int, 
        end: int
    ) -> Tuple[Optional[str], Optional[str]]:
        if not blocks_info:
            return None, None
        
        for block in blocks_info:
            if block["start"] <= start < block["end"]:
                return block["id"], block["type"]
        
        return blocks_info[0]["id"], blocks_info[0]["type"]
    
    def _generate_chunk_id(self, document_id: int, chunk_index: int) -> str:
        return f"doc_{document_id}_chunk_{chunk_index}"
    
    def index_document(
        self,
        document_id: int,
        document_title: str,
        project_id: int,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        text = self._chunks_to_text(content)
        if not text.strip():
            return 0
        
        chunks = self._split_into_chunks(text, content)
        if not chunks:
            return 0
        
        self._ensure_embedding_model()
        collection_name = self._get_global_collection_name()
        
        try:
            collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"[FullTextSearch] 创建集合失败: {e}")
            return 0
        
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        
        for chunk in chunks:
            chunk_id = self._generate_chunk_id(document_id, chunk.index)
            ids.append(chunk_id)
            documents.append(chunk.content)
            
            chunk_metadata = {
                "document_id": document_id,
                "document_title": document_title,
                "project_id": project_id,
                "chunk_index": chunk.index,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "block_id": chunk.block_id or "",
                "block_type": chunk.block_type or "",
                "indexed_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            metadatas.append(chunk_metadata)
            
            if self._embedding_model:
                embedding = self._get_embedding(chunk.content)
                if embedding:
                    embeddings.append(embedding)
        
        try:
            if embeddings and len(embeddings) == len(ids):
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            return len(ids)
        except Exception as e:
            print(f"[FullTextSearch] 索引失败: {e}")
            return 0
    
    def remove_document(self, document_id: int):
        collection_name = self._get_global_collection_name()
        try:
            collection = self._client.get_collection(name=collection_name)
            
            all_ids = collection.get()["ids"]
            ids_to_delete = [
                id for id in all_ids 
                if id.startswith(f"doc_{document_id}_chunk_")
            ]
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
        except Exception:
            pass
    
    def remove_project(self, project_id: int):
        collection_name = self._get_global_collection_name()
        try:
            collection = self._client.get_collection(name=collection_name)
            
            all_results = collection.get(include=["metadatas"])
            ids_to_delete = []
            
            for i, metadata in enumerate(all_results["metadatas"]):
                if metadata.get("project_id") == project_id:
                    ids_to_delete.append(all_results["ids"][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
        except Exception:
            pass
    
    def _find_keyword_matches(
        self, 
        text: str, 
        query: str,
        case_sensitive: bool = False
    ) -> List[Tuple[int, int]]:
        if not query:
            return []
        
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE
        
        pattern = re.escape(query)
        for match in re.finditer(pattern, text, flags):
            matches.append((match.start(), match.end()))
        
        return matches
    
    def _extract_context(
        self, 
        text: str, 
        start: int, 
        end: int, 
        context_size: int = 100
    ) -> Tuple[str, str]:
        context_before_start = max(0, start - context_size)
        context_after_end = min(len(text), end + context_size)
        
        context_before = text[context_before_start:start]
        context_after = text[end:context_after_end]
        
        if context_before_start > 0 and '\n' in context_before:
            context_before = context_before[context_before.rfind('\n') + 1:]
        
        if context_after_end < len(text) and '\n' in context_after:
            context_after = context_after[:context_after.find('\n')]
        
        return context_before, context_after
    
    def search(
        self,
        query: str,
        user_id: int,
        project_ids: Optional[List[int]] = None,
        top_k: int = MAX_SEARCH_RESULTS,
        use_semantic: bool = True,
        use_keyword: bool = True,
        min_score: float = 0.3
    ) -> List[SearchResult]:
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.strip()
        results = []
        seen_chunks = set()
        
        collection_name = self._get_global_collection_name()
        
        try:
            collection = self._client.get_collection(name=collection_name)
        except Exception:
            return []
        
        if use_semantic and self._embedding_model:
            query_embedding = self._get_embedding(query)
            
            if query_embedding:
                try:
                    semantic_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=top_k * 2,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if semantic_results["ids"] and semantic_results["ids"][0]:
                        for i, doc_id in enumerate(semantic_results["ids"][0]):
                            metadata = semantic_results["metadatas"][0][i]
                            distance = semantic_results["distances"][0][i] if semantic_results["distances"] else 0
                            score = 1 - distance
                            
                            if score < min_score:
                                continue
                            
                            if project_ids and metadata.get("project_id") not in project_ids:
                                continue
                            
                            chunk_key = f"{metadata['document_id']}_{metadata['chunk_index']}"
                            if chunk_key in seen_chunks:
                                continue
                            seen_chunks.add(chunk_key)
                            
                            content = semantic_results["documents"][0][i]
                            highlights = self._find_keyword_matches(content, query)
                            context_before, context_after = self._extract_context(
                                content,
                                highlights[0][0] if highlights else 0,
                                highlights[0][1] if highlights else len(query),
                                50
                            )
                            
                            results.append(SearchResult(
                                document_id=metadata["document_id"],
                                document_title=metadata["document_title"],
                                project_id=metadata["project_id"],
                                project_title=metadata.get("project_title", ""),
                                chunk_index=metadata["chunk_index"],
                                content=content,
                                start_offset=metadata["start_offset"],
                                end_offset=metadata["end_offset"],
                                block_id=metadata.get("block_id"),
                                block_type=metadata.get("block_type"),
                                score=score,
                                match_type="semantic",
                                highlights=highlights,
                                context_before=context_before,
                                context_after=context_after
                            ))
                except Exception as e:
                    print(f"[FullTextSearch] 语义搜索失败: {e}")
        
        if use_keyword:
            try:
                keyword_results = collection.get(
                    include=["documents", "metadatas"]
                )
                
                if keyword_results["ids"]:
                    for i, doc_id in enumerate(keyword_results["ids"]):
                        metadata = keyword_results["metadatas"][i]
                        
                        if project_ids and metadata.get("project_id") not in project_ids:
                            continue
                        
                        chunk_key = f"{metadata['document_id']}_{metadata['chunk_index']}"
                        if chunk_key in seen_chunks:
                            continue
                        
                        content = keyword_results["documents"][i]
                        matches = self._find_keyword_matches(content, query)
                        
                        if matches:
                            seen_chunks.add(chunk_key)
                            
                            score = min(1.0, len(matches) * 0.3)
                            context_before, context_after = self._extract_context(
                                content,
                                matches[0][0],
                                matches[0][1],
                                50
                            )
                            
                            results.append(SearchResult(
                                document_id=metadata["document_id"],
                                document_title=metadata["document_title"],
                                project_id=metadata["project_id"],
                                project_title=metadata.get("project_title", ""),
                                chunk_index=metadata["chunk_index"],
                                content=content,
                                start_offset=metadata["start_offset"],
                                end_offset=metadata["end_offset"],
                                block_id=metadata.get("block_id"),
                                block_type=metadata.get("block_type"),
                                score=score,
                                match_type="keyword",
                                highlights=matches,
                                context_before=context_before,
                                context_after=context_after
                            ))
            except Exception as e:
                print(f"[FullTextSearch] 关键词搜索失败: {e}")
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def search_in_document(
        self,
        query: str,
        document_id: int,
        top_k: int = 10
    ) -> List[SearchResult]:
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.strip()
        results = []
        
        collection_name = self._get_global_collection_name()
        
        try:
            collection = self._client.get_collection(name=collection_name)
        except Exception:
            return []
        
        try:
            all_results = collection.get(
                include=["documents", "metadatas"]
            )
            
            if all_results["ids"]:
                for i, chunk_id in enumerate(all_results["ids"]):
                    metadata = all_results["metadatas"][i]
                    
                    if metadata.get("document_id") != document_id:
                        continue
                    
                    content = all_results["documents"][i]
                    matches = self._find_keyword_matches(content, query)
                    
                    if matches:
                        score = min(1.0, len(matches) * 0.3)
                        context_before, context_after = self._extract_context(
                            content,
                            matches[0][0],
                            matches[0][1],
                            50
                        )
                        
                        results.append(SearchResult(
                            document_id=metadata["document_id"],
                            document_title=metadata["document_title"],
                            project_id=metadata["project_id"],
                            project_title=metadata.get("project_title", ""),
                            chunk_index=metadata["chunk_index"],
                            content=content,
                            start_offset=metadata["start_offset"],
                            end_offset=metadata["end_offset"],
                            block_id=metadata.get("block_id"),
                            block_type=metadata.get("block_type"),
                            score=score,
                            match_type="keyword",
                            highlights=matches,
                            context_before=context_before,
                            context_after=context_after
                        ))
        except Exception as e:
            print(f"[FullTextSearch] 文档内搜索失败: {e}")
        
        results.sort(key=lambda x: x.start_offset)
        return results[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total_chunks": 0,
            "total_documents": 0,
            "projects": {},
            "embedding_model_loaded": self._embedding_model is not None
        }
        
        collection_name = self._get_global_collection_name()
        
        try:
            collection = self._client.get_collection(name=collection_name)
            all_results = collection.get(include=["metadatas"])
            
            stats["total_chunks"] = len(all_results["ids"])
            
            documents = set()
            projects = {}
            
            for metadata in all_results["metadatas"]:
                documents.add(metadata.get("document_id"))
                project_id = metadata.get("project_id")
                if project_id:
                    projects[project_id] = projects.get(project_id, 0) + 1
            
            stats["total_documents"] = len(documents)
            stats["projects"] = projects
            
        except Exception:
            pass
        
        return stats


fulltext_search_service = FullTextSearchService()
