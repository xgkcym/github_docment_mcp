from typing import Dict, List, Tuple, Optional

from llama_index.core import Document

from core.exceptions import GitHubError
from core.settings import settings
from core.types import GitHubFileInfo, DocumentMetadata
from github.client import github_client
from github.parse import parse_github_url, build_github_web_url
from utils.logger_handler import logger





def discover_repository_files(
    repo_url: str,
    branch: str = "main",
    file_extensions: List[str] = None,
    include_sha: bool = True,
):
    """
    发现 GitHub 仓库中的文件。

    参数:
        repo_url: GitHub 仓库 URL 或 owner/repo 格式
        branch: Git 分支名称
        file_extensions: 要筛选的文件扩展名列表

    返回:
        元组（文件路径列表，状态消息）
    """
    if file_extensions is None:
        file_extensions = settings.file_extensions
    try:
        return github_client.get_repository_tree(repo_url, branch, file_extensions,include_sha=include_sha)
    except Exception as e:
        logger.error(f"发现 {repo_url} 中的文件失败：{e}")
        return [], f"错误：{str(e)}"
def discover_repository_files_with_changes(
    repo_url: str,
    repo_name: str,
    branch: str = "main",
    file_extensions: List[str] = None,) -> Dict[str, any]:
    """
   发现文件并与存储的仓库状态比较变化。

   参数:
       repo_url: GitHub 仓库 URL
       repo_name: 用于比较的仓库名称
       branch: Git 分支名称
       file_extensions: 要筛选的文件扩展名列表

   返回:
       包含文件发现结果和变化检测的字典
   """
    try:
        # 获取带有 SHA 的当前文件
        current_files, message = discover_repository_files(repo_url,branch,file_extensions)
    except Exception as e:
        pass


async def load_files_from_github(
    repo_url: str,
    file_paths: List[str],
    branch: str = "main",
    max_concurrent: int = 10
)->Tuple[List[Document], List[str]]:
    """
    从 GitHub 仓库加载多个文件。

    参数:
        repo_url: GitHub 仓库 URL 或 owner/repo 格式
        file_paths: 要加载的文件路径列表
        branch: Git 分支名称
        max_concurrent: 最大并发请求数

    返回:
        元组（已加载文档列表，失败文件路径列表）
    """
    if not file_paths:
        logger.warning("未提供文件路径")
        return [], []

    try:
        # 解析仓库名称用于元数据
        owner, repo = parse_github_url(repo_url)
        repo_name = f"{owner}/{repo}"
    except Exception as e:
        raise GitHubError(f"无效的仓库 URL：{e}") from e

    logger.info(f"正在从 {repo_name} 加载 {len(file_paths)} 个文件")

    # 从 GitHub 获取文件 成功信息和失败信息
    file_infos, failed_paths = await github_client.get_multiple_files(
        repo_url, file_paths, branch, max_concurrent
    )
    # 转换为 LlamaIndex 文档
    documents = []
    for file_info in file_infos:
        try:
            document = create_document_from_file_info(file_info, repo_name, branch)
            documents.append(document)
        except Exception as e:
            logger.error(f"无法从 {file_info.path} 创建文档：{e}")
            failed_paths.append(file_info.path)

    logger.info(
        f"成功加载 {len(documents)} 个文档，{len(failed_paths)} 个失败"
    )
    return documents, failed_paths

def create_document_from_file_info(file_info:GitHubFileInfo,repo_name:str,branch:str)->Document:
    """从 GitHub 文件信息创建 LlamaIndex 文档。"""
    try:
        owner, repo = parse_github_url(repo_name)
        web_url = build_github_web_url(owner, repo, file_info.path, branch)
    except Exception as e:
        logger.warning(f"无法为 {file_info.path} 构建网页 URL：{e}")
        web_url = file_info.url

    # 创建文档元数据
    metadata = DocumentMetadata(
        file_path=file_info.path,
        file_name=file_info.name,
        file_extension=file_info.path.split(".")[-1] if "." in file_info.path else "",
        directory=(
            "/".join(file_info.path.split("/")[:-1]) if "/" in file_info.path else ""
        ),
        repo=repo_name,
        branch=branch,
        sha=file_info.sha,
        size=file_info.size,
        url=web_url,
        raw_url=file_info.download_url,
        type=file_info.type,
    )

    # 创建 LlamaIndex 文档
    document = Document(
        text=file_info.content,
        doc_id=f"{repo_name}:{branch}:{file_info.path}",
        metadata=metadata.dict(),
    )

    return document

