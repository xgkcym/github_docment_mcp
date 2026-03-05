import chromadb
from chromadb import Client, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from core.exceptions import VectorStoreError
from core.settings import settings
from utils.logger_handler import logger



def get_vector_store():
    """获取配置好的向量存储实例。"""
    try:
        chroma_client = chromadb.PersistentClient(path=settings.chroma_data_url)
        # 创建或获取集合（collection）
        collection = chroma_client.get_or_create_collection(
            settings.rag_collection_name,
            metadata={
                "hnsw:space": "cosine",
                # "hnsw:M": 32,  # 默认16→32，连接数翻倍，提升召回
                # "hnsw:efConstruction": 400,  # 默认100→400，建索引更精细
                # "hnsw:efSearch": 200,  # 默认100→200，查询时搜索更广
                # "hnsw:num_threads": 4,  # 多线程加速
            }
        )

        # 记录集合状态
        return ChromaVectorStore(chroma_collection=collection)

    except Exception as e:
        logger.error(f"获取向量存储失败：{e}")
        raise VectorStoreError(f"获取向量存储失败：{e}")



