from typing import Dict, Any, List

from src.core.settings import settings
from src.database.mongodb import mongodb_client
from src.utils.logger_handler import logger


class RepositoryManager:
    """管理仓库元数据和统计信息。"""
    def __init__(self):
        self.repos_connection = mongodb_client.get_connection(settings.repos_collection_name)
        self.docs_collection = mongodb_client.get_connection(settings.rag_collection_name)
    def get_repository_stats(self)->Dict[str,Any]:
        """获取整体仓库统计信息。"""
        try:
            total_repos = self.repos_connection.count_documents({})
            total_docs = self.repos_connection.count_documents({})
            # 获取文件总文件各数
            total_files = 0
            total_tracked_files = 0
            # repos = self.repos_connection.find({},{'file_count':1,'files':1})
            return {}
        except Exception as e:
            logger.error(f"[数据库查询失败] 获取仓库统计信息失败,错误信息:${str(e)}")
            return {"error": str(e)}


    def get_repository_detail(self)-> List[Dict[str, Any]]:
        """获取所有仓库的详细信息。"""
        try:
            repos = []
            for repo_doc in self.repos_connection.find():
                # 统计该仓库的文档数
                repo_name = repo_doc.get("repo_name", "未知")
                doc_count = self.docs_collection.count_documents({
                    "metadata.repo": repo_name
                })
                repos.append({
                    "name": repo_name,
                    "files":repo_doc.get("files", doc_count),
                    "last_updated": repo_doc.get("last_updated", "未知"),
                    "status": repo_doc.get("status", "未知"),
                })
            return sorted(repos,key=lambda x: x["name"])
        except Exception as e:
            logger.error(f"[数据库查询失败] 获取仓库详情失败,错误信息:${str(e)}")
            return []
    def delete_repository_data(self,repo_name:str)->Dict[str, Any]:
        try:
            docs_result = self.docs_collection.delete_many({"metadata.repo": repo_name})
            repos_result = self.repos_connection.delete_one({"_id": repo_name})
            logger.info(
                f"已删除仓库 {repo_name}：{docs_result.deleted_count} 个文档，{repos_result.deleted_count} 条仓库条目"
            )
            return {
                "success": True,
                "documents_deleted": docs_result.deleted_count,
                "repository_deleted": repos_result.deleted_count > 0,
                "message": f"成功删除仓库 '{repo_name}' 的 {docs_result.deleted_count} 个文档",
            }
        except Exception as e:
            logger.error(f"[删除仓库]:--{repo_name}--仓库删除失败,错误信息:{str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"删除仓库 '{repo_name}' 失败：{str(e)}",
            }


    def get_available_repositories(self)->List[str]:
        """获取可用仓库列表。"""
        try:
            repos = self.repos_connection.distinct("repo_name")
            return sorted(repos) if repos else []
        except Exception as e:
            logger.error(f"获取可用仓库失败: {e}")
            return []
repository_manager = RepositoryManager()