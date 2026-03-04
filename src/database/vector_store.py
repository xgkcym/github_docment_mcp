import chromadb
from chromadb import Client, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from core.exceptions import VectorStoreError
from core.settings import settings
from utils.logger_handler import logger



def get_vector_store():
    """获取配置好的向量存储实例。"""
    try:
        # 初始化 Chroma 客户端
        # chroma_client = Client(
        #     Settings(
        #         persist_directory=settings.chroma_data_url,
        #     ),
        # )
        chroma_client = chromadb.PersistentClient(path=settings.chroma_data_url)
        # 创建或获取集合（collection）
        collection = chroma_client.get_or_create_collection(settings.rag_collection_name)
        return ChromaVectorStore(chroma_collection=collection)

    except Exception as e:
        logger.error(f"获取向量存储失败：{e}")
        raise VectorStoreError(f"获取向量存储失败：{e}")



