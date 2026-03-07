import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from llama_index.vector_stores.chroma import ChromaVectorStore

from core.types import ProcessingStatus
from database.vector_store import get_vector_collection
from src.core.settings import settings
from src.database.mongodb import mongodb_client
from src.utils.logger_handler import logger


class RepositoryManager:
    """管理仓库元数据和统计信息。"""
    def __init__(self):
        self.repos_collection = mongodb_client.get_collection(settings.repos_collection_name)
        self.docs_collection = get_vector_collection()
    def get_repository_stats(self)->Dict[str,Any]:
        """获取整体仓库统计信息。"""
        try:
            total_repos = self.repos_collection.count_documents({})
            total_docs = self.docs_collection.get()
            # 获取文件总文件各数
            total_files = 0
            total_tracked_files = 0
            repos = self.repos_collection.find({},{'file_count':1,'files':1})
            for repo in repos:
                total_files += repo.get("file_count", 0)
                total_tracked_files += len(repo.get("files", []))

            # 获取集合大小估算
            try:
                stats = mongodb_client.database.command(
                    "collStats", settings.collection_name
                )
                collection_size = stats.get("size", 0)
            except Exception:
                collection_size = 0

            return {
                "total_repositories": total_repos,
                "total_documents": len(total_docs['ids']),
                "total_files": total_files,
                "total_tracked_files": total_tracked_files,
                "collection_size_bytes": collection_size,
                "collection_size_mb": (
                    round(collection_size / (1024 * 1024), 2)
                    if collection_size > 0
                    else 0
                ),
                "database_name": settings.db_name,
                "last_updated": datetime.now().isoformat(),
            }
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
                documents = self.docs_collection.get(
                    where={
                        "repo": repo_name
                    }
                )
                # if documents['metadatas'] and repo_doc.get("files", None) is None:
                #     new_documents = []
                #     for doc in documents['metadatas']:
                #         new_documents.append(
                #             json.loads(doc['_node_content'])['metadata']
                #         )
                #     documents =new_documents
                files_info = repo_doc.get("files", [])
                tracked_files = len(files_info)
                repos.append({
                    "name": repo_name,
                    "files": repo_doc.get("file_count", len(documents['ids'])),
                    "tracked_files": tracked_files,
                    "last_updated": repo_doc.get("last_updated", "未知"),
                    "status": repo_doc.get("status", "未知"),
                })
            return sorted(repos,key=lambda x: x["name"])
        except Exception as e:
            logger.error(f"[数据库查询失败] 获取仓库详情失败,错误信息:${str(e)}")
            return []

    def delete_repository_data(self,repo_name:str)->Dict[str, Any]:
        try:
            self.docs_collection.delete(where={"repo": repo_name})
            result = self.repos_collection.find({"repo_name": repo_name})
            self.repos_collection.delete_many({"repo_name": repo_name})
            file_count = 0
            branch_count = 0
            for doc in result:
                branch_count+=1
                file_count += doc.get("file_count",0)
            logger.info(
                f"已删除仓库 {repo_name}：{branch_count} 个分支，{file_count} 个文件"
            )
            return {
                "success": True,
                "branch": branch_count,
                # "repository_deleted": repos_result.deleted_count > 0,
                "message":    f"已删除仓库 {repo_name}：{branch_count} 个分支，{file_count} 个文件"
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

    def get_available_branches(self,repos_name:str):
        """获取分支列表。"""
        try:
            res = self.repos_collection.find({'repo_name':repos_name})
            branches = [repo['branch'] for  repo in res]
            return sorted(branches) if branches else []
        except Exception as e:
            logger.error(f"获取可用分支失败: {e}")
            return []


    def update_repository_info(self, repo_name: str,file_count: int = 0,branch: Optional[str] = "main",files_with_sha: Optional[List[Dict[str, str]]] = None)->bool:
        """增量更新仓库信息。"""
        try:
            if files_with_sha is None:
                files_with_sha = []
                # 获取现有仓库数据
            existing_repo = self.repos_collection.find_one({"repo_name": repo_name, "branch": branch})
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

                self.repos_collection.update_one({"repo_name":repo_name,"branch": branch},update_operation)
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
                    "_id": str(uuid.uuid4()),
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
            logger.error(f"更新仓库信息失败: {str(e)}")
            raise Exception(f"更新仓库信息失败: {str(e)}") from e

    def get_repository_files(self, repo_name: str,branch: str) -> List[Dict[str, Any]]:
        """获取仓库的跟踪文件。"""
        try:
            repo_doc = self.repos_collection.find_one({"repo_name": repo_name,"branch": branch})
            if repo_doc:
                return repo_doc.get("files", [])
            return []
        except Exception as e:
            logger.error(f"获取仓库文件失败 {repo_name}: {e}")
            return []

    def detect_file_changes(self,repo_name:str,branch:str, current_files: List[Dict[str, str]])-> Dict[str, List[Dict[str, str]]]:
        """
        通过比较 SHA 检测仓库文件的变化。

        参数:
            repo_name: 仓库名称
            current_files: 当前文件列表，包含路径和 SHA

        返回:
            包含"新文件"、"已修改"、"已删除"和"未变化"文件列表的字典
        """
        try:
            logger.info(f"=== 调试 detect_file_changes for {repo_name} ===")

            # 从数据库获取存储的文件
            stored_files = self.get_repository_files(repo_name,branch)
            logger.info(f"数据库中存储的文件：{len(stored_files)}")
            # 创建存储文件的查找表
            stored_lookup = {}
            for file_entry in stored_files:
                path = file_entry.get("path", file_entry.get("file_path", ""))
                sha = file_entry.get("sha", "")
                stored_lookup[path] = sha

            logger.info(f"存储的查找键：{list(stored_lookup.keys())[:5]}...")

            # 检查当前文件
            logger.info(f"来自 GitHub 的当前文件：{len(current_files)}")
            if current_files:
                logger.info(f"示例当前文件：{current_files[0]}")

            new_files = []
            modified_files = []
            unchanged_files = []

            for file_info in current_files:
                path = file_info["path"]
                current_sha = file_info["sha"]

                if path not in stored_lookup:
                    # 真正的新文件
                    new_files.append(file_info)
                    logger.debug(f"新文件：{path}")
                elif stored_lookup[path] != current_sha:
                    # 已修改的文件（SHA 改变）
                    modified_files.append(file_info)
                    logger.debug(
                        f"已修改：{path} (存储：{stored_lookup[path][:8]}, 当前：{current_sha[:8]})"
                    )
                else:
                    # 未变化的文件
                    unchanged_files.append(file_info)
                    logger.debug(f"未变化：{path}")

            # 检查已删除的文件
            current_paths = {f["path"] for f in current_files}
            deleted_files = []
            for stored_path, stored_sha in stored_lookup.items():
                if stored_path not in current_paths:
                    deleted_files.append({"path": stored_path, "sha": stored_sha})
                    logger.debug(f"已删除：{stored_path}")

            result = {
                "new": new_files,
                "modified": modified_files,
                "deleted": deleted_files,
                "unchanged": unchanged_files,
            }

            logger.info(
                f"变化检测结果：{len(new_files)} 个新文件，{len(modified_files)} 个已修改，{len(deleted_files)} 个已删除，{len(unchanged_files)} 个未变化"
            )

            return result
        except Exception as e:
            logger.error(f"检测 {repo_name} 的变化失败：{e}")
            return {"new": [], "modified": [], "deleted": [], "unchanged": []}



repository_manager = RepositoryManager()



if  __name__ == "__main__":
    res = repository_manager.repos_collection.find_one({'repo_name': "Arindam200/awesome-ai-apps","branch": "main"})
    print(res.get("files"))
    # print(get_vector_collection().count())

