"""
RAG (Retrieval-Augmented Generation) 服务
提供智能上下文检索功能，使用 ChromaDB 作为向量数据库
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import hashlib
import json
from app.core.config import get_settings
import os

# 初始化 embedding 模型
# 使用轻量级中文模型，可根据需要更换
EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"

class RAGService:
    """RAG 服务 - 智能上下文检索"""
    
    _instance = None
    _client = None
    _embedding_model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._init_client()
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        settings = get_settings()
        
        # 使用持久化存储
        persist_dir = os.path.join(os.getcwd(), "chroma_db")
        os.makedirs(persist_dir, exist_ok=True)
        
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 加载 embedding 模型
        try:
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            print(f"[RAG] 加载 embedding 模型失败: {e}")
            # 如果模型加载失败，使用 ChromaDB 默认的 embedding
            self._embedding_model = None
    
    def _get_collection_name(self, project_id: int, memory_type: str) -> str:
        """获取集合名称"""
        return f"project_{project_id}_{memory_type}"
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示"""
        if self._embedding_model:
            return self._embedding_model.encode(text).tolist()
        return None
    
    def _get_id(self, content: str) -> str:
        """生成内容的唯一 ID"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def index_memory(self, project_id: int, memory_type: str, items: List[Dict[str, Any]]):
        """
        索引项目设定到向量数据库
        
        Args:
            project_id: 项目 ID
            memory_type: 设定类型 (outline, characters, world_building, key_points, storyline)
            items: 要索引的条目列表
        """
        collection_name = self._get_collection_name(project_id, memory_type)
        
        # 获取或创建集合
        try:
            collection = self._client.get_or_create_collection(name=collection_name)
        except Exception as e:
            print(f"[RAG] 创建集合失败: {e}")
            return
        
        # 准备数据
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        
        for i, item in enumerate(items):
            if isinstance(item, dict):
                # 处理字典类型的数据
                content = item.get("description", item.get("content", ""))
                title = item.get("title", item.get("name", ""))
                text = f"{title}: {content}" if title else content
                metadata = {**item, "index": i}
            elif isinstance(item, str):
                # 处理字符串类型的数据
                text = item
                metadata = {"content": item, "index": i}
            else:
                continue
            
            if not text.strip():
                continue
                
            doc_id = self._get_id(f"{project_id}_{memory_type}_{i}_{text[:50]}")
            ids.append(doc_id)
            documents.append(text)
            metadatas.append(metadata)
            
            # 计算 embedding
            if self._embedding_model:
                embedding = self._get_embedding(text)
                if embedding:
                    embeddings.append(embedding)
        
        if not ids:
            return
        
        # 添加到集合
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
            print(f"[RAG] 索引 {len(ids)} 条 {memory_type} 数据到项目 {project_id}")
        except Exception as e:
            print(f"[RAG] 索引失败: {e}")
    
    def search_memory(
        self, 
        project_id: int, 
        query: str, 
        memory_types: Optional[List[str]] = None,
        top_k: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        搜索相关的项目设定
        
        Args:
            project_id: 项目 ID
            query: 查询文本
            memory_types: 要搜索的设定类型列表，None 表示搜索所有类型
            top_k: 每个类型返回的最大结果数
            
        Returns:
            按类型分组的相关结果
        """
        if memory_types is None:
            memory_types = ["outline", "characters", "world_building", "key_points", "storyline"]
        
        results = {}
        query_embedding = self._get_embedding(query) if self._embedding_model else None
        
        for mem_type in memory_types:
            collection_name = self._get_collection_name(project_id, mem_type)
            
            try:
                collection = self._client.get_collection(name=collection_name)
                
                # 搜索
                if query_embedding:
                    search_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(top_k, collection.count()),
                        include=["documents", "metadatas", "distances"]
                    )
                else:
                    search_results = collection.query(
                        query_texts=[query],
                        n_results=min(top_k, collection.count()),
                        include=["documents", "metadatas", "distances"]
                    )
                
                # 格式化结果
                type_results = []
                if search_results["ids"] and search_results["ids"][0]:
                    for i, doc_id in enumerate(search_results["ids"][0]):
                        type_results.append({
                            "id": doc_id,
                            "content": search_results["documents"][0][i] if search_results["documents"] else "",
                            "metadata": search_results["metadatas"][0][i] if search_results["metadatas"] else {},
                            "score": 1 - (search_results["distances"][0][i] if search_results["distances"] else 0)
                        })
                
                if type_results:
                    results[mem_type] = type_results
                    
            except Exception as e:
                # 集合不存在或其他错误
                continue
        
        return results
    
    def delete_project_memory(self, project_id: int):
        """删除项目的所有向量数据"""
        memory_types = ["outline", "characters", "world_building", "key_points", "storyline"]
        
        for mem_type in memory_types:
            collection_name = self._get_collection_name(project_id, mem_type)
            try:
                self._client.delete_collection(name=collection_name)
            except:
                pass
    
    def build_context_string(
        self, 
        project_id: int, 
        query: str,
        max_length: int = 2000
    ) -> str:
        """
        构建用于 AI 上下文的文本
        
        Args:
            project_id: 项目 ID
            query: 当前查询/写作内容
            max_length: 最大字符数
            
        Returns:
            格式化后的上下文文本
        """
        results = self.search_memory(project_id, query, top_k=2)
        
        if not results:
            return ""
        
        context_parts = []
        total_length = 0
        
        # 按优先级排序
        priority_order = ["characters", "world_building", "outline", "key_points", "storyline"]
        
        for mem_type in priority_order:
            if mem_type not in results:
                continue
            
            type_label = {
                "characters": "角色设定",
                "world_building": "世界观",
                "outline": "大纲",
                "key_points": "关键情节",
                "storyline": "故事线"
            }.get(mem_type, mem_type)
            
            context_parts.append(f"\n【{type_label}】")
            
            for item in results[mem_type]:
                content = item["content"]
                if total_length + len(content) > max_length:
                    remaining = max_length - total_length
                    if remaining > 50:
                        context_parts.append(content[:remaining] + "...")
                    break
                context_parts.append(content)
                total_length += len(content)
            
            if total_length >= max_length:
                break
        
        return "\n".join(context_parts)


# 全局 RAG 服务实例
rag_service = RAGService()
