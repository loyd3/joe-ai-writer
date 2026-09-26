"""
全文搜索服务 - 支持长文本分段索引、向量语义搜索、精确位置定位

特性：
1. 长文本智能分段索引
2. 向量语义搜索（基于 ChromaDB）
3. 关键词精确匹配
4. 精确位置定位（段落、块、字符偏移）
5. 搜索结果高亮
"""

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

# chromadb / sentence_transformers / torch 为可选依赖：
# 本地环境 torch DLL 损坏时不应阻止整个后端启动
_chromadb = None
_chroma_settings = None
_SentenceTransformer = None
_VECTOR_DEPS_ERROR: Optional[str] = None


def _load_vector_deps() -> bool:
    """延迟加载向量检索依赖，失败时仅禁用语义搜索。"""
    global _chromadb, _chroma_settings, _SentenceTransformer, _VECTOR_DEPS_ERROR
    if _chromadb is not None and _SentenceTransformer is not None:
        return True
    if _VECTOR_DEPS_ERROR:
        return False
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        _chromadb = chromadb
        _chroma_settings = ChromaSettings
        _SentenceTransformer = SentenceTransformer
        return True
    except Exception as e:
        _VECTOR_DEPS_ERROR = str(e)
        print(f"[FullTextSearch] 向量检索依赖不可用，将仅使用关键词搜索: {e}")
        return False


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
        if not _load_vector_deps():
            self._client = None
            return

        persist_dir = os.path.join(os.getcwd(), "search_index")
        os.makedirs(persist_dir, exist_ok=True)
        
        try:
            self._client = _chromadb.PersistentClient(
                path=persist_dir,
                settings=_chroma_settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        except Exception as e:
            print(f"[FullTextSearch] ChromaDB 初始化失败: {e}")
            self._client = None
    
    def _ensure_embedding_model(self) -> bool:
        if self._embedding_model is not None:
            return True
        if self._embedding_load_attempted:
            return False
        self._embedding_load_attempted = True
        if not _load_vector_deps() or _SentenceTransformer is None:
            return False
        try:
            from app.core.config import configure_huggingface_env
            endpoint = configure_huggingface_env()
            print(f"[FullTextSearch] 正在加载 embedding 模型: {EMBEDDING_MODEL} (HF_ENDPOINT={endpoint})")
            self._embedding_model = _SentenceTransformer(EMBEDDING_MODEL)
            print(f"[FullTextSearch] Embedding 模型加载成功")
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
    
    def _block_text(self, block: Dict[str, Any]) -> str:
        """从块结构提取可检索文本，兼容 content / text / children。"""
        if not isinstance(block, dict):
            return str(block) if block else ""
        parts: List[str] = []
        for key in ("content", "text", "title", "caption"):
            val = block.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val)
            elif isinstance(val, list):
                for child in val:
                    child_text = self._block_text(child) if isinstance(child, dict) else str(child or "")
                    if child_text.strip():
                        parts.append(child_text)
        children = block.get("children")
        if isinstance(children, list):
            for child in children:
                child_text = self._block_text(child) if isinstance(child, dict) else str(child or "")
                if child_text.strip():
                    parts.append(child_text)
        return "\n".join(parts)

    def _chunks_to_text(self, content: Any) -> str:
        if not content:
            return ""
        if isinstance(content, str):
            return content
        
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                block_content = self._block_text(block)
                if block_content:
                    text_parts.append(block_content)
            elif isinstance(block, str) and block.strip():
                text_parts.append(block)
        return "\n\n".join(text_parts)

    @staticmethod
    def _as_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _tokenize_query(query: str) -> List[str]:
        """拆分查询词：空格/标点分隔；去重保序；过短单字保留（中文常靠单字）。"""
        raw = (query or "").strip()
        if not raw:
            return []
        parts = re.split(r"[\s,，、;；|｜/\\]+", raw)
        tokens: List[str] = []
        seen = set()
        for p in parts:
            t = p.strip()
            if not t:
                continue
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            tokens.append(t)
        if not tokens:
            tokens = [raw]
        return tokens
    
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
                    block_content = self._block_text(block)
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
                
                # overlap 按字符数回退，而不是按句列表下标
                overlap_text = chunk_text[-overlap:] if overlap > 0 and len(chunk_text) > overlap else (
                    chunk_text if overlap > 0 else ""
                )
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

    def _ensure_client(self) -> bool:
        if self._client is None:
            self._init_client()
        return self._client is not None
    
    def index_document(
        self,
        document_id: int,
        document_title: str,
        project_id: int,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        if not self._ensure_client():
            print("[FullTextSearch] 向量索引不可用，跳过文档索引")
            return 0

        text = self._chunks_to_text(content)
        if not text.strip():
            self.remove_document(document_id)
            return 0
        
        chunks = self._split_into_chunks(text, content)
        if not chunks:
            self.remove_document(document_id)
            return 0
        
        # 先清掉旧分片，避免文档缩短后残留幽灵 chunk
        self.remove_document(document_id)

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
        if not self._ensure_client():
            return
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
        if not self._ensure_client():
            return
        collection_name = self._get_global_collection_name()
        try:
            collection = self._client.get_collection(name=collection_name)
            
            all_results = collection.get(include=["metadatas"])
            ids_to_delete = []
            
            for i, metadata in enumerate(all_results["metadatas"]):
                if self._as_int(metadata.get("project_id")) == int(project_id):
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
        if not query or not text:
            return []
        
        matches: List[Tuple[int, int]] = []
        flags = 0 if case_sensitive else re.IGNORECASE
        tokens = self._tokenize_query(query)

        # 整句精确子串
        for match in re.finditer(re.escape(query.strip()), text, flags):
            matches.append((match.start(), match.end()))

        # 分词命中（支持「春 天」这类拆开搜）
        if len(tokens) > 1 or (tokens and tokens[0] != query.strip()):
            for token in tokens:
                if len(token) < 1:
                    continue
                for match in re.finditer(re.escape(token), text, flags):
                    span = (match.start(), match.end())
                    if span not in matches:
                        matches.append(span)

        matches.sort(key=lambda x: x[0])
        return matches

    def _keyword_hit_score(self, text: str, query: str, matches: List[Tuple[int, int]]) -> float:
        """关键词命中打分：整句命中最高；多词全中次之。"""
        if not matches:
            return 0.0
        q = query.strip()
        text_l = text.lower()
        q_l = q.lower()
        if q_l in text_l:
            # 精确子串：按出现次数提权，保底 0.85
            return min(1.0, 0.85 + min(0.15, len(matches) * 0.03))

        tokens = self._tokenize_query(q)
        if not tokens:
            return 0.0
        hit_tokens = sum(1 for t in tokens if t.lower() in text_l)
        if hit_tokens == 0:
            return 0.0
        # 要求全部 token 都出现才算有效 keyword 结果
        if hit_tokens < len(tokens):
            return 0.0
        return min(0.95, 0.55 + hit_tokens * 0.1 + min(0.2, len(matches) * 0.02))

    def _project_allowed(self, metadata: Dict[str, Any], project_ids: Optional[List[int]]) -> bool:
        if not project_ids:
            return True
        pid = self._as_int(metadata.get("project_id"))
        if pid is None:
            return False
        allowed = {int(x) for x in project_ids}
        return pid in allowed

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

    def search_documents_content(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = MAX_SEARCH_RESULTS,
    ) -> List[SearchResult]:
        """
        直接在文档内容上做关键词检索（不依赖向量索引）。
        documents 项：document_id, document_title, project_id, project_title, content
        """
        query = (query or "").strip()
        if len(query) < 1:
            return []

        results: List[SearchResult] = []
        tokens = self._tokenize_query(query)

        for doc in documents:
            content = doc.get("content")
            text = self._chunks_to_text(content)
            title = doc.get("document_title") or ""
            haystack = f"{title}\n{text}"
            if not haystack.strip():
                continue

            # 标题命中也算
            title_matches = self._find_keyword_matches(title, query)
            text_matches = self._find_keyword_matches(text, query)

            # 多词：正文/标题需覆盖全部 token
            hay_l = haystack.lower()
            if tokens and not all(t.lower() in hay_l for t in tokens):
                # 允许整句子串例外（已在 tokens 全等时由上面覆盖）
                if query.lower() not in hay_l:
                    continue

            if not title_matches and not text_matches and query.lower() not in hay_l:
                continue

            # 按块定位，便于跳转
            blocks = content if isinstance(content, list) else []
            block_hits = 0
            if isinstance(blocks, list):
                offset = 0
                for bi, block in enumerate(blocks):
                    if not isinstance(block, dict):
                        continue
                    block_text = self._block_text(block)
                    if not block_text:
                        continue
                    b_matches = self._find_keyword_matches(block_text, query)
                    token_ok = all(t.lower() in block_text.lower() for t in tokens) if tokens else False
                    phrase_ok = query.lower() in block_text.lower()
                    if b_matches or token_ok or phrase_ok:
                        score = self._keyword_hit_score(block_text, query, b_matches or [(0, min(len(query), len(block_text)))])
                        if title_matches:
                            score = min(1.0, score + 0.05)
                        ctx_s = b_matches[0][0] if b_matches else block_text.lower().find(tokens[0].lower() if tokens else query.lower())
                        if ctx_s < 0:
                            ctx_s = 0
                        ctx_e = b_matches[0][1] if b_matches else ctx_s + len(query)
                        context_before, context_after = self._extract_context(block_text, ctx_s, ctx_e, 50)
                        results.append(SearchResult(
                            document_id=int(doc["document_id"]),
                            document_title=title,
                            project_id=int(doc.get("project_id") or 0),
                            project_title=doc.get("project_title") or "",
                            chunk_index=bi,
                            content=block_text,
                            start_offset=offset + ctx_s,
                            end_offset=offset + ctx_e,
                            block_id=block.get("id"),
                            block_type=block.get("type"),
                            score=score,
                            match_type="keyword",
                            highlights=b_matches or [(ctx_s, ctx_e)],
                            context_before=context_before,
                            context_after=context_after,
                        ))
                        block_hits += 1
                        if block_hits >= 3:
                            break
                    offset += len(block_text) + 2

            # 无块结构或未命中块时，整篇回退一条
            if block_hits == 0:
                matches = text_matches or title_matches or self._find_keyword_matches(haystack, query)
                score = self._keyword_hit_score(haystack, query, matches or [(0, len(query))])
                if title_matches:
                    score = min(1.0, max(score, 0.9))
                if matches:
                    context_before, context_after = self._extract_context(
                        text or title, matches[0][0], matches[0][1], 50
                    )
                else:
                    context_before, context_after = "", ""
                results.append(SearchResult(
                    document_id=int(doc["document_id"]),
                    document_title=title,
                    project_id=int(doc.get("project_id") or 0),
                    project_title=doc.get("project_title") or "",
                    chunk_index=0,
                    content=(text or title)[:500],
                    start_offset=matches[0][0] if matches else 0,
                    end_offset=matches[0][1] if matches else 0,
                    block_id=None,
                    block_type=None,
                    score=score,
                    match_type="keyword",
                    highlights=matches[:20],
                    context_before=context_before,
                    context_after=context_after,
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
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
        results: List[SearchResult] = []
        seen_chunks = set()

        if not self._ensure_client():
            return results
        
        collection_name = self._get_global_collection_name()
        
        try:
            collection = self._client.get_collection(name=collection_name)
        except Exception:
            return results
        
        if use_semantic:
            if not self._embedding_model:
                self._ensure_embedding_model()
            
            query_embedding = None
            if self._embedding_model:
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
                            
                            if not self._project_allowed(metadata, project_ids):
                                continue
                            
                            doc_id_int = self._as_int(metadata.get("document_id")) or 0
                            chunk_idx = self._as_int(metadata.get("chunk_index")) or 0
                            chunk_key = f"{doc_id_int}_{chunk_idx}"
                            if chunk_key in seen_chunks:
                                continue
                            seen_chunks.add(chunk_key)
                            
                            content = semantic_results["documents"][0][i]
                            highlights = self._find_keyword_matches(content, query)
                            context_before, context_after = self._extract_context(
                                content,
                                highlights[0][0] if highlights else 0,
                                highlights[0][1] if highlights else min(len(query), len(content)),
                                50
                            )
                            
                            results.append(SearchResult(
                                document_id=doc_id_int,
                                document_title=metadata.get("document_title") or "",
                                project_id=self._as_int(metadata.get("project_id")) or 0,
                                project_title=metadata.get("project_title", "") or "",
                                chunk_index=chunk_idx,
                                content=content,
                                start_offset=self._as_int(metadata.get("start_offset")) or 0,
                                end_offset=self._as_int(metadata.get("end_offset")) or 0,
                                block_id=metadata.get("block_id") or None,
                                block_type=metadata.get("block_type") or None,
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
                        
                        if not self._project_allowed(metadata, project_ids):
                            continue
                        
                        doc_id_int = self._as_int(metadata.get("document_id")) or 0
                        chunk_idx = self._as_int(metadata.get("chunk_index")) or 0
                        chunk_key = f"{doc_id_int}_{chunk_idx}"
                        if chunk_key in seen_chunks:
                            continue
                        
                        content = keyword_results["documents"][i] or ""
                        matches = self._find_keyword_matches(content, query)
                        score = self._keyword_hit_score(content, query, matches)
                        if score <= 0:
                            continue

                        seen_chunks.add(chunk_key)
                        
                        context_before, context_after = self._extract_context(
                            content,
                            matches[0][0] if matches else 0,
                            matches[0][1] if matches else min(len(query), len(content)),
                            50
                        )
                        
                        results.append(SearchResult(
                            document_id=doc_id_int,
                            document_title=metadata.get("document_title") or "",
                            project_id=self._as_int(metadata.get("project_id")) or 0,
                            project_title=metadata.get("project_title", "") or "",
                            chunk_index=chunk_idx,
                            content=content,
                            start_offset=self._as_int(metadata.get("start_offset")) or 0,
                            end_offset=self._as_int(metadata.get("end_offset")) or 0,
                            block_id=metadata.get("block_id") or None,
                            block_type=metadata.get("block_type") or None,
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
        if not self._ensure_client():
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
                    
                    if self._as_int(metadata.get("document_id")) != int(document_id):
                        continue
                    
                    content = all_results["documents"][i] or ""
                    matches = self._find_keyword_matches(content, query)
                    score = self._keyword_hit_score(content, query, matches)
                    if score <= 0:
                        continue

                    context_before, context_after = self._extract_context(
                        content,
                        matches[0][0] if matches else 0,
                        matches[0][1] if matches else min(len(query), len(content)),
                        50
                    )
                    
                    results.append(SearchResult(
                        document_id=self._as_int(metadata.get("document_id")) or document_id,
                        document_title=metadata.get("document_title") or "",
                        project_id=self._as_int(metadata.get("project_id")) or 0,
                        project_title=metadata.get("project_title", "") or "",
                        chunk_index=self._as_int(metadata.get("chunk_index")) or 0,
                        content=content,
                        start_offset=self._as_int(metadata.get("start_offset")) or 0,
                        end_offset=self._as_int(metadata.get("end_offset")) or 0,
                        block_id=metadata.get("block_id") or None,
                        block_type=metadata.get("block_type") or None,
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
            "embedding_model_loaded": self._embedding_model is not None,
            "vector_search_available": self._ensure_client(),
        }
        
        if not self._client:
            return stats

        collection_name = self._get_global_collection_name()
        
        try:
            collection = self._client.get_collection(name=collection_name)
            all_results = collection.get(include=["metadatas"])
            
            stats["total_chunks"] = len(all_results["ids"])
            
            documents = set()
            projects = {}
            
            for metadata in all_results["metadatas"]:
                documents.add(self._as_int(metadata.get("document_id")))
                project_id = self._as_int(metadata.get("project_id"))
                if project_id:
                    projects[project_id] = projects.get(project_id, 0) + 1
            
            stats["total_documents"] = len([d for d in documents if d is not None])
            stats["projects"] = projects
            
        except Exception:
            pass
        
        return stats


fulltext_search_service = FullTextSearchService()
