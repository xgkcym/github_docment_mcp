import time
from typing import Dict, Any, Generator

from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.vector_stores import FilterOperator,MetadataFilters, MetadataFilter
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.llms.openai_like import OpenAILike

from core.exceptions import QueryError
from core.settings import  settings
from database.vector_store import get_vector_store
from prompts.rag_prompt import query_prompt
from rag.cross_encoder_reranker import CrossEncoderReranker
from utils.logger_handler import logger


class QueryRetriever:
    """处理文档检索和查询处理。"""

    def __init__(self,repo_name:str, use_rerank: bool = True):
        Settings.llm = OpenAILike(
            is_chat_model=True,
            model=settings.default_llm_model,
            api_key=settings.default_llm_api_key,
            api_base=settings.default_llm_base_url,
        )
        Settings.embed_model = DashScopeEmbedding(
            model_name=settings.default_embedding_model,
            api_key=settings.default_embedding_api_key,
            embed_batch_size=settings.embed_batch_size,
        )
        self.repo_name = repo_name
        self.vector_store_index = VectorStoreIndex.from_vector_store(get_vector_store())
        # 创建仓库过滤器
        self.filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="repo",
                    value=repo_name,
                    operator=FilterOperator.EQ,
                )
            ]
        )

        # 初始化重排序器
        self.use_rerank = use_rerank
        if use_rerank:
            try:
                self.reranker = CrossEncoderReranker(settings.cross_encoder_model)
                logger.info("Cross-Encoder 重排序器初始化成功")
            except Exception as e:
                logger.warning(f"重排序器初始化失败: {e}，将不使用重排序")
                self.use_rerank = False

    def make_query(
        self, query: str, mode: str = "default", top_k: int = settings.similarity_top_k
    ) -> Generator[Dict[str, Any],None,None]:
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
            if not top_k:
                top_k = settings.similarity_top_k

            logger.info(f"为 {self.repo_name} 处理查询：'{query[:100]}...'")

            # 创建带有仓库过滤的查询引擎
            query_engine = self.vector_store_index.as_query_engine(
                similarity_top_k=top_k,
                vector_store_query_mode=mode,
                filters=self.filters,
                # response_mode="refine",
                response_mode="compact",
            )
            initial_nodes  = query_engine.retrieve(query)

            logger.info(f"初始检索到 {len(initial_nodes)} 个节点")

            if self.use_rerank and len(initial_nodes) > settings.cross_encoder_top_k * 2:
                initial_nodes.sort(key=lambda x: x.score or 0, reverse=True)
                initial_nodes = initial_nodes[0:settings.cross_encoder_top_k * 2]
                final_nodes = self.reranker.rerank(query, initial_nodes, top_k=settings.cross_encoder_top_k)
            else:
                final_nodes = initial_nodes[:settings.cross_encoder_top_k]

            logger.info(f"重排序后检索到 {len(final_nodes)} 个节点")
            context = "\n\n---\n\n".join([
                f"来源 [{i + 1}] {n.metadata.get('file_name', '未知')}:\n{n.get_content()[:500]}"
                for i, n in enumerate(final_nodes)
            ])
            prompt = query_prompt(query,context)
            response = Settings.llm.stream_complete(prompt)

            accumulated_text = ""
            for delta in response:
                # delta 是 CompletionResponse 对象，delta.text 是新生成的内容
                accumulated_text += delta.delta or ""
                # 实时 yield 当前累积的文本
                yield {
                    "response": accumulated_text,
                    "source_nodes": [],  # 流式过程中先不返回来源
                    "streaming": True,
                }


            # 处理来源节点
            source_nodes = []
            for node in final_nodes:
                score = float(node.score) if node.score else 0.0
                # bge-reranker 分数范围约 -5 到 5，大于 0 就算相关
                if self.use_rerank and score < -2:  # 重排序用更宽松的阈值
                    continue
                elif not self.use_rerank and score < 0.6:  # 向量搜索用原来的阈值
                    continue
                try:
                    source_node = {
                        "file_name": node.metadata.get("file_name", "未知"),
                        "url": node.metadata.get("url", "#"),
                        "score": score,  # 转换为浮点数
                        "content": node.get_content()[:500],  # 使用 get_content() 方法
                    }
                    source_nodes.append(source_node)
                except Exception as e:
                    logger.error(f"格式化来源节点时出错：{e}")
                    continue

            # 格式化响应（与工作代码结构匹配）
            processing_time = time.time() - start_time
            logger.info(
                f"查询在 {processing_time:.2f} 秒内完成，找到 {len(source_nodes)} 个来源"
            )
            yield {
                "response": accumulated_text,
                "source_nodes": source_nodes,
                "repository": self.repo_name,
                "mode": mode,
                "streaming": False,
                "processing_time": processing_time,
                "total_sources": len(source_nodes),
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"查询在 {processing_time:.2f} 秒后失败：{e}")
            yield {
                "error": str(e),
                "repository": self.repo_name,
                "mode": mode,
                "processing_time": processing_time,
            }




def create_query_retriever(repo_name: str) -> QueryRetriever:
    """创建查询检索器的工厂函数。"""
    return QueryRetriever(repo_name)



if __name__ == '__main__':
    retriever = create_query_retriever("Arindam200/awesome-ai-apps")
    for result in retriever.make_query("一共有多少个RAG应用项目，都有哪些"):
        print(result)
