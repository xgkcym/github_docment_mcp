from datetime import datetime
from typing import Dict, Any, List, Optional

from core.types import ProcessingStatus
from src.core.settings import settings
from src.database.mongodb import mongodb_client
from src.utils.logger_handler import logger


class RepositoryManager:
    """管理仓库元数据和统计信息。"""
    def __init__(self):
        self.repos_collection = mongodb_client.get_collection(settings.repos_collection_name)
        self.docs_collection = mongodb_client.get_collection(settings.rag_collection_name)
    def get_repository_stats(self)->Dict[str,Any]:
        """获取整体仓库统计信息。"""
        return {}
        try:
            total_repos = self.repos_collection.count_documents({})
            total_docs = self.repos_collection.count_documents({})
            # 获取文件总文件各数
            total_files = 0
            total_tracked_files = 0
            # repos = self.repos_collection.find({},{'file_count':1,'files':1})
            return {}
        except Exception as e:
            logger.error(f"[数据库查询失败] 获取仓库统计信息失败,错误信息:${str(e)}")
            return {"error": str(e)}


    def get_repository_detail(self)-> List[Dict[str, Any]]:
        """获取所有仓库的详细信息。"""
        try:
            repos = []
            for repo_doc in self.repos_collection.find():
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
            repos_result = self.repos_collection.delete_one({"_id": repo_name})
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
            repos = self.repos_collection.distinct("repo_name")
            return sorted(repos) if repos else []
        except Exception as e:
            logger.error(f"获取可用仓库失败: {e}")
            return []


    def update_repository_info(self, repo_name: str,file_count: int = 0,branch: Optional[str] = "main",files_with_sha: Optional[List[Dict[str, str]]] = None)->bool:
        """增量更新仓库信息。"""
        try:
            if files_with_sha is None:
                files_with_sha = []
                # 获取现有仓库数据
            existing_repo = self.repos_collection.find_one({"_id": repo_name})
            if existing_repo:
                # 增量更新：与现有文件合并
                existing_files = existing_repo.get("files", [])
                existing_file_lookup = {f["path"]: f for f in existing_files}

                # 更新/添加新文件
                for file_info in files_with_sha:
                    existing_file_lookup[file_info["path"]] = {
                        "path": file_info["path"],
                        "sha": file_info["sha"],
                        "last_ingested": datetime.now(),
                        "status": "已导入",
                    }
                # 转换回列表
                merged_files = list(existing_file_lookup.values())

                # 只更新特定字段，不替换整个文档
                update_operation = {
                    "$set": {
                        "files": merged_files,
                        "file_count": len(merged_files),  # 使用实际计数
                        "last_updated": datetime.now(),
                        "status": ProcessingStatus.COMPLETE.value,
                        "branch": branch,
                        "tracking_enabled": True,
                    }
                }

                self.repos_collection.update_one({"_id":repo_name},update_operation)
            else:
                # 新仓库：创建全新条目
                file_tracking_data = []
                for file_info in files_with_sha:
                    file_tracking_data.append(
                        {
                            "path": file_info["path"],
                            "sha": file_info["sha"],
                            "last_ingested": datetime.now(),
                            "status": "已导入",
                        }
                    )
                update_data = {
                    "_id": repo_name,
                    "repo_name": repo_name,
                    "branch": branch,
                    "file_count": len(file_tracking_data),
                    "files": file_tracking_data,
                    "last_updated": datetime.now(),
                    "status": ProcessingStatus.COMPLETE.value,
                    "tracking_enabled": True,
                }
                self.repos_collection.insert_one(update_data)
                logger.info(
                    f"已为新仓库创建跟踪：{repo_name} "
                    f"包含 {len(file_tracking_data)} 个文件"
                )
            return True
        except Exception as e:
            logger.error("更新仓库信息失败: {e}")
            return False

repository_manager = RepositoryManager()



if  __name__ == "__main__":

    a = {
        "b":"123",
        "c":"456"
    }
    print(a.values())