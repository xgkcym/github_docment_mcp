"""Doc-MCP 应用程序的类型定义。"""

from enum import Enum

from pydantic import BaseModel


class QueryMode(str, Enum):
    """文档检索的可用查询模式。"""

    DEFAULT = "default"
    TEXT_SEARCH = "text_search"
    HYBRID = "hybrid"


class ProcessingStatus(str, Enum):
    """处理状态指示器。"""

    PENDING = "pending"
    LOADING = "loading"
    LOADED = "loaded"
    VECTORIZING = "vectorizing"
    COMPLETE = "complete"
    ERROR = "error"


class DocumentMetadata(BaseModel):
    """文档元数据结构。"""

    file_path: str
    file_name: str
    file_extension: str
    directory: str
    repo: str
    branch: str
    sha: str
    size: int
    url: str
    raw_url: str
    type: str = "file"


class GitHubFileInfo(BaseModel):
    """GitHub 文件信息。"""

    path: str
    name: str
    sha: str
    size: int
    url: str
    download_url: str
    type: str
    encoding: str
    content: str