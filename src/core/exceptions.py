"""Doc-MCP 应用程序的自定义异常。"""


class DocMCPError(Exception):
    """Doc-MCP 的基础异常。"""

    pass


class GitHubError(DocMCPError):
    """GitHub 相关错误。"""

    pass


class GitHubRateLimitError(GitHubError):
    """超出 GitHub 速率限制。"""

    pass


class GitHubAuthenticationError(GitHubError):
    """GitHub 认证失败。"""

    pass


class GitHubRepositoryNotFoundError(GitHubError):
    """未找到 GitHub 仓库。"""

    pass


class VectorStoreError(DocMCPError):
    """向量存储操作错误。"""

    pass


class IngestionError(DocMCPError):
    """文档导入错误。"""

    pass


class QueryError(DocMCPError):
    """查询处理错误。"""

    pass