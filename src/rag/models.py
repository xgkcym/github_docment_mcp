"""RAG 操作的 Pydantic 模型。"""

from typing import List, Optional

from pydantic import BaseModel, Field

from src.core.types import QueryMode


class SourceNode(BaseModel):
    """带有文件信息和相关性的来源节点。"""

    file_name: str = Field(description="文件名称")
    url: str = Field(description="文件的 GitHub URL")
    score: float = Field(description="相关性分数")
    content: str = Field(description="内容摘录")


class QueryRequest(BaseModel):
    """查询请求模型。"""

    repository: str = Field(description="要查询的仓库名称")
    query: str = Field(description="用户的问题")
    mode: QueryMode = Field(default=QueryMode.DEFAULT, description="搜索模式")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")


class QueryResponse(BaseModel):
    """查询响应模型。"""

    response: str = Field(description="AI 生成的响应")
    source_nodes: List[SourceNode] = Field(description="来源引用")
    repository: str = Field(description="查询的仓库")
    mode: QueryMode = Field(description="使用的搜索模式")
    processing_time: float = Field(description="查询处理时间（秒）")


class IngestionProgress(BaseModel):
    """导入进度跟踪。"""
    total_documents: int = Field(description="要处理的文档总数")
    processed_documents: int = Field(description="已处理的文档数")
    current_phase: str = Field(description="当前处理阶段")
    elapsed_time: float = Field(description="已用时间（秒）")
    estimated_remaining: Optional[float] = Field(
        default=None, description="预计剩余时间（秒）"
    )