import time
from typing import List, Optional, Callable

from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter, MarkdownNodeParser
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.llms.openai_like import OpenAILike

from api.niu_trans import create_translate
from core.settings import settings
from database.repository import repository_manager
from database.vector_store import get_vector_store
from rag.models import IngestionProgress
from utils.logger_handler import logger


class DocumentIngestionPipeline:
    """处理带有进度跟踪的文档导入。"""

    def __init__(
            self, progress_callback: Optional[Callable[[IngestionProgress], None]] = None
    ):
        self.progress_callback = progress_callback

        self.text_splitter = SentenceSplitter(
            separator=settings.separator,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        Settings.text_splitter = self.text_splitter
        Settings.node_parser = self.text_splitter
        self.markdown_parser = MarkdownNodeParser()

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



    async def ingest_documents(self,documents: List[Document], repo_name: str, branch: str, files_with_sha: Optional[List[dict]],allow_trans:bool=settings.allow_trans) -> bool:
        """
           将文档导入向量存储。
           参数:
               documents: 要导入的文档列表
               repo_name: 用于元数据的仓库名称
       返回:
           成功返回 True，否则返回 False
       """
        if not documents:
            logger.warning("没有要导入的文档")
            return False

        start_time = time.time()
        total_docs = len(documents)

        try:
            if allow_trans:
                # 进行翻译
                translate = create_translate()
                new_documents = []
                for doc in documents:
                    new_documents.append(
                        Document(
                            text=translate.identification(doc.text),
                            doc_id=doc.doc_id,
                            metadata=doc.metadata,
                        )
                    )
                documents = new_documents


            # 根据文件类型选择不同的解析器
            transformations = []

            # 检查是否全是 Markdown
            has_markdown = any(
                doc.metadata.get("file_extension", "").lower() in ["md", "mdx"]
                for doc in documents
            )

            if has_markdown:
                # 对 Markdown 使用专用解析器，对普通文本使用 SentenceSplitter
                # LlamaIndex 会自动根据文档类型应用合适的解析
                transformations = [self.markdown_parser, self.text_splitter]
            else:
                transformations = [self.text_splitter]


            logger.info(f"开始为 {repo_name} 导入 {total_docs} 个文档")
            # 获取向量存储
            vector_store = get_vector_store()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            # 创建索引并导入文档
            index = VectorStoreIndex.from_documents(
                documents=documents,
                storage_context=storage_context,
                show_progress=True,  # 自己处理进度
                transformations=transformations
            )
            # 报告完成
            elapsed_time = time.time() - start_time

            # 使用 SHA 跟踪更新仓库元数据
            if files_with_sha is None:
                # 如果未提供，从文档中提取 SHA 信息
                files_with_sha = []
                for doc in documents:
                    file_path = doc.metadata.get("file_path", "")
                    file_sha = doc.metadata.get("sha", "")
                    if file_path and file_sha:
                        files_with_sha.append({"path": file_path, "sha": file_sha})
                    else:
                        logger.warning(f"文档缺少 SHA 信息：{file_path}")

            result = repository_manager.update_repository_info(repo_name=repo_name,branch=branch,files_with_sha=files_with_sha)
            if  result:
                logger.info(
                    f"成功在 {elapsed_time:.2f} 秒内为 {repo_name} 导入 {total_docs} 个文档"
                )
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"[文档导入失败] 错误信息:{str(e)}")
            return False



async def ingest_documents_async(
    documents: List[Document],
    repo_name: str,
    progress_callback: Optional[Callable[[IngestionProgress], None]] = None,
    branch: Optional[str] = "main",
    files_with_sha: Optional[List[dict]] = None,
    allow_trans:bool=settings.allow_trans
) -> bool:
    """
    文档导入的异步包装器。

    参数:
        documents: 要导入的文档列表
        repo_name: 用于元数据的仓库名称
        progress_callback: 可选的进度回调

    返回:
        成功返回 True，否则返回 False
    """
    pipeline = DocumentIngestionPipeline(progress_callback)
    return await pipeline.ingest_documents(documents, repo_name, branch, files_with_sha,allow_trans)
