import time
from typing import Dict, Any

from llama_cloud import MetadataFilters, MetadataFilter
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.vector_stores import FilterOperator
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.llms.openai_like import OpenAILike

from core.exceptions import QueryError
from core.settings import  settings
from database.vector_store import get_vector_store
from utils.logger_handler import logger


class QueryRetriever:
    """处理文档检索和查询处理。"""

    def __init__(self,repo_name:str):
        Settings.llm = OpenAILike(
            is_chat_model=True,
            model=settings.default_llm_model,
            api_key=settings.default_llm_api_key,
            api_base=settings.default_llm_base_url,
        )
        Settings.embed_model = DashScopeEmbedding(
            model_name=settings.default_embedding_model,
            api_key=settings.default_embedding_api_key,
            embed_batch_size=settings.embed_batch_size
        )
        self.repo_name = repo_name
        vector_store = get_vector_store()
        self.vector_store_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        # 创建仓库过滤器
        self.filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="metadata.repo",
                    value=repo_name,
                    operator=FilterOperator.EQ,
                )
            ]
        )

    def make_query(
        self, query: str, mode: str = "default", top_k: int = settings.similarity_top_k
    ) -> Dict[str, Any]:
        """
        对仓库文档执行查询。

        参数:
            query: 用户的问题
            mode: 搜索模式（default, text_search, hybrid）
            top_k: 返回的结果数量

        返回:
            包含响应和来源节点的字典
        """
        start_time = time.time()

        try:
            # 验证输入
            if not query.strip():
                raise QueryError("查询内容为空")

            logger.info(f"为 {self.repo_name} 处理查询：'{query[:100]}...'")

            # 创建带有仓库过滤的查询引擎
            query_engine = self.vector_store_index.as_query_engine(
                similarity_top_k=top_k,
                vector_store_query_mode=mode,
                filters=self.filters,
                response_mode="refine",
            )
            # 执行查询
            response = query_engine.query(query)
            print("===" * 30)
            print(response)
            print("===" * 30)

        except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"查询在 {processing_time:.2f} 秒后失败：{e}")
                return {
                    "error": str(e),
                    "repository": self.repo_name,
                    "mode": mode,
                    "processing_time": processing_time,
                }




def create_query_retriever(repo_name: str) -> QueryRetriever:
    """创建查询检索器的工厂函数。"""
    return QueryRetriever(repo_name)