import time
from typing import List, Dict, Tuple

import gradio as gr
import asyncio
from core.types import ProcessingStatus
from database.repository import repository_manager
from github.file_load import discover_repository_files_with_changes, load_files_from_github
from rag.ingestion import ingest_documents_async
from ui.components.common import create_repository_dropdown, create_status_textbox, create_file_selector, \
    create_progress_display, format_progress_display
from utils.logger_handler import logger




class UpdateTab:
    def __init__(self,demo:gr.Blocks):
        self.demo = demo



    def create_tab(self)->gr.TabItem:
        """创建更新标签页界面。"""
        with gr.TabItem("🔄 仓库更新") as tab:
            gr.Markdown("### 🔄 增量仓库更新")
            gr.Markdown(
                "**智能更新：** 仅检测和处理变化的文件，实现高效的仓库维护。"
                "同时发现并导入尚未处理的新文件。"
            )
            # 仓库选择部分
            with gr.Row():
                with gr.Column(scale=2):
                    repo_dropdown = create_repository_dropdown(
                        choices=self._get_available_repos(),
                        label="📚 选择要更新的仓库",
                        allow_custom_value=False,
                    )
                    refresh_dropdown_btn = gr.Button(
                        "🔄 刷新仓库列表", variant="secondary", size="sm"
                    )
                    branch_dropdown = create_repository_dropdown(
                        choices=[],
                        label="🌿 选择要更新的分支",
                        allow_custom_value=True,
                    )
                    detect_changes_btn = gr.Button(
                        "🔍 检测变化和可用文件", variant="secondary"
                    )
                with gr.Column(scale=1):
                    status_output = create_status_textbox(
                        label="变化检测状态",
                        placeholder="变化检测结果将显示在这里...",
                        lines=10
                    )

            # 变化摘要部分
            with gr.Row():
                with gr.Column():
                    change_summary_display = gr.JSON(
                        label="📊 变化摘要",
                        value={"message": "运行变化检测查看摘要..."},
                    )

            # 文件选择部分
            with gr.Accordion("📁 变化的文件", open=False):
                with gr.Tabs():
                    with gr.TabItem("🆕 新文件"):
                        new_files_selector = create_file_selector(
                            label="要导入的新文件"
                        )
                        with gr.Row():
                            select_all_new_btn = gr.Button(
                                "✅ 全选新文件", variant="secondary", size="sm"
                            )
                            clear_new_btn = gr.Button(
                                "❌ 清除新文件选择", variant="secondary", size="sm"
                            )
                    with gr.TabItem("✏️ 已修改文件"):
                        modified_files_selector = create_file_selector(
                            label="要重新导入的已修改文件"
                        )
                        with gr.Row():
                            select_all_modified_btn = gr.Button(
                                "✅ 全选已修改文件", variant="secondary", size="sm"
                            )
                            clear_modified_btn = gr.Button(
                                "❌ 清除已修改文件选择", variant="secondary", size="sm"
                            )
                    with gr.TabItem("🗑️ 已删除文件"):
                        deleted_files_display = gr.Dataframe(
                            headers=["文件路径", "最后 SHA"],
                            datatype=["str", "str"],
                            label="从仓库中删除的文件",
                            interactive=False,
                        )

                    with gr.TabItem("📄 可用文件"):
                        available_files_selector = create_file_selector(
                            label="可用但尚未导入的文件"
                        )
                        with gr.Row():
                            select_all_available_btn = gr.Button(
                                "✅ 全选可用文件",
                                variant="secondary",
                                size="sm",
                            )
                            clear_available_btn = gr.Button(
                                "❌ 清除可用文件选择", variant="secondary", size="sm"
                            )

            # 更新控制
            gr.Markdown("### 🚀 执行更新")

            with gr.Row():
                update_changed_btn = gr.Button(
                    "🔄 处理变化的文件",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )
                ingest_available_btn = gr.Button(
                    "📥 导入可用文件",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )

            with gr.Row():
                delete_removed_btn = gr.Button(
                    "🗑️ 移除已删除文件", variant="stop", interactive=False
                )
                refresh_btn = gr.Button("🔄 刷新进度", variant="secondary")

            # 进度显示
            progress_display = create_progress_display(
                label="📊 更新进度",
                initial_value="🚀 准备检测变化和处理更新...",
                lines=15,
            )

            # 状态管理
            changes_state = gr.State({})
            available_files_state = gr.State([])
            progress_state = gr.State({})

            repo_dropdown.change(
                fn=self._get_available_branches,
                inputs=[repo_dropdown],
                outputs=[branch_dropdown],
                show_api=False
            )
            # 事件处理
            detect_changes_btn.click(
                fn=self._detect_changes_and_available,
                        inputs=[repo_dropdown, branch_dropdown],
                outputs=[
                    changes_state,
                    available_files_state,
                    status_output,
                    change_summary_display,
                    new_files_selector,
                    modified_files_selector,
                    deleted_files_display,
                    available_files_selector,
                    update_changed_btn,
                    ingest_available_btn,
                    delete_removed_btn,
                ],
                show_api=False,
            )

            # 选择辅助
            select_all_new_btn.click(
                fn=lambda changes: self._select_files_by_type(changes, "new"),
                inputs=[changes_state],
                outputs=[new_files_selector],
                show_api=False,
            )

            select_all_modified_btn.click(
                fn=lambda changes: self._select_files_by_type(changes, "modified"),
                inputs=[changes_state],
                outputs=[modified_files_selector],
                show_api=False,
            )

            select_all_available_btn.click(
                fn=self._select_all_available,
                inputs=[available_files_state],
                outputs=[available_files_selector],
                show_api=False,
            )

            clear_new_btn.click(
                fn=lambda: gr.CheckboxGroup(value=[]),
                outputs=[new_files_selector],
                show_api=False,
            )
            clear_modified_btn.click(
                fn=lambda: gr.CheckboxGroup(value=[]),
                outputs=[modified_files_selector],
                show_api=False,
            )
            clear_available_btn.click(
                fn=lambda: gr.CheckboxGroup(value=[]),
                outputs=[available_files_selector],
                show_api=False,
            )

            refresh_dropdown_btn.click(
                fn=self._refresh_repositories,
                outputs=[repo_dropdown],
                show_api=False,
            )

            # 更新操作
            update_changed_btn.click(
                fn=self._process_changed_files,
                inputs=[
                    repo_dropdown,
                    branch_dropdown,
                    new_files_selector,
                    modified_files_selector,
                    changes_state,
                ],
                outputs=[progress_state, progress_display],
                show_api=False,
            )

            ingest_available_btn.click(
                fn=self._ingest_available_files,
                inputs=[repo_dropdown, branch_dropdown, available_files_selector],
                outputs=[progress_state, progress_display],
                show_api=False,
            )

            delete_removed_btn.click(
                fn=self._delete_removed_files,
                inputs=[repo_dropdown, changes_state],
                outputs=[progress_state, progress_display],
                show_api=False,
            )

            refresh_btn.click(
                fn=self._refresh_progress,
                inputs=[progress_state],
                outputs=[progress_display],
                show_api=False,
            )

            self.demo.load(fn=self._get_available_repos, outputs=[repo_dropdown], show_api=False)

        return tab

    def _get_available_repos(self) -> List[str]:
        """获取可用仓库列表。"""
        try:
            repos = repository_manager.get_available_repositories()
            return repos if repos else ["没有可用仓库"]
        except Exception as e:
            logger.error(f"获取仓库时出错：{e}")
            return ['加载仓库时出错']

    def _get_available_branches(self,repo_name:str)->gr.Dropdown:
        """获取可用分支列表。"""
        try:
            branches = repository_manager.get_available_branches(repo_name)
            return create_repository_dropdown(
                choices=branches if branches else [],
                label="🌿 选择要更新的分支",
                allow_custom_value=True,
            )
        except Exception as e:
            logger.error(f"获取分支时出错：{e}")
            return create_repository_dropdown(
                choices=['获取分支时出错'],
                label="🌿 选择要更新的分支",
                allow_custom_value=True,
            )

    def _detect_changes_and_available(self,repo_name:str,branch:str)->Tuple[
        Dict,
        List,
        str,
        Dict,
        gr.CheckboxGroup,
        gr.CheckboxGroup,
        gr.Dataframe,
        gr.CheckboxGroup,
        gr.Button,
        gr.Button,
        gr.Button
    ]:
        """检测仓库的变化并查找可用文件。"""
        if  not repo_name or repo_name in [
            "没有可用仓库",
            "加载仓库时出错",
        ] :
            empty_changes = {"new": [], "modified": [], "deleted": [], "unchanged": []}
            return (
                empty_changes,
                [],
                "请选择一个有效的仓库。",
                {"error": "未选择仓库"},
                create_file_selector(visible=False),
                create_file_selector(visible=False),
                gr.Dataframe(value=[]),
                create_file_selector(visible=False),
                gr.Button(interactive=False),
                gr.Button(interactive=False),
                gr.Button(interactive=False),
            )
        if not branch:
            empty_changes = {"new": [], "modified": [], "deleted": [], "unchanged": []}
            return (
                empty_changes,
                [],
                "请选择一个有效的分支。",
                {"error": "未选择分支"},
                create_file_selector(visible=False),
                create_file_selector(visible=False),
                gr.Dataframe(value=[]),
                create_file_selector(visible=False),
                gr.Button(interactive=False),
                gr.Button(interactive=False),
                gr.Button(interactive=False),
            )
        try:
            logger.info(f"检测 {repo_name} 在分支 {branch} 上的变化")
            # 获取变化和可用文件
            result = discover_repository_files_with_changes(repo_name, repo_name, branch)
            changes = result["changes"]
            has_changes = result["has_changes"]
            message = result["message"]

            logger.info(
                f"变化检测结果：{len(changes['new'])} 新文件，{len(changes['modified'])} 已修改，{len(changes['deleted'])} 已删除，{len(changes['unchanged'])} 未变化"
            )
            # 计算可用文件（存在于仓库但尚未导入的文件）
            all_current_files = (
                    changes["new"] + changes["modified"] + changes["unchanged"]
            )
            ingested_files = repository_manager.get_repository_files(repo_name,branch)
            ingested_paths = {f["path"] for f in ingested_files}

            available_files = []
            for file_info in all_current_files:
                file_path = (
                    file_info["path"] if isinstance(file_info, dict) else file_info
                )
                if file_path not in ingested_paths:
                    available_files.append(file_path)

            logger.info(f"尚未导入的可用文件：{len(available_files)}")

            # 创建变化摘要
            change_summary = {
                "repository": repo_name,
                "branch": branch,
                "has_changes": has_changes,
                "new_files": len(changes["new"]),
                "modified_files": len(changes["modified"]),
                "deleted_files": len(changes["deleted"]),
                "unchanged_files": len(changes["unchanged"]),
                "available_files": len(available_files),
                "total_current_files": len(all_current_files),
                "ingested_files": len(ingested_paths),
            }

            # 准备文件选择器
            new_file_paths = [f["path"] for f in changes["new"]]
            modified_file_paths = [f["path"] for f in changes["modified"]]

            new_files_selector = create_file_selector(
                choices=new_file_paths,
                label=f"新文件 ({len(new_file_paths)})",
                visible=len(new_file_paths) > 0,
            )

            modified_files_selector = create_file_selector(
                choices=modified_file_paths,
                label=f"已修改文件 ({len(modified_file_paths)})",
                visible=len(modified_file_paths) > 0,
            )

            available_files_selector = create_file_selector(
                choices=available_files,
                label=f"可用文件 ({len(available_files)})",
                visible=len(available_files) > 0,
            )

            # 已删除文件显示
            deleted_data = []
            for deleted_file in changes["deleted"]:
                deleted_data.append([deleted_file["path"], deleted_file["sha"]])

            deleted_files_display = gr.Dataframe(
                value=deleted_data,
                headers=["文件路径", "最后 SHA"],
                datatype=["str", "str"],
                label=f"已删除文件 ({len(deleted_data)})",
                interactive=False,
            )

            # 根据可用操作启用按钮
            has_new_or_modified = (
                    len(changes["new"]) > 0 or len(changes["modified"]) > 0
            )
            has_available = len(available_files) > 0
            has_deleted = len(changes["deleted"]) > 0

            return (
                changes,
                available_files,
                message,
                change_summary,
                new_files_selector,
                modified_files_selector,
                deleted_files_display,
                available_files_selector,
                gr.Button(interactive=has_new_or_modified),
                gr.Button(interactive=has_available),
                gr.Button(interactive=has_deleted),
            )
        except  Exception as e:
            logger.error(f"检测变化时出错：{e}")
            empty_changes = {"new": [], "modified": [], "deleted": [], "unchanged": []}
            return (
                empty_changes,
                [],
                f"错误：{str(e)}",
                {"error": str(e)},
                create_file_selector(visible=False),
                create_file_selector(visible=False),
                gr.Dataframe(value=[]),
                create_file_selector(visible=False),
                gr.Button(interactive=False),
                gr.Button(interactive=False),
                gr.Button(interactive=False),
            )
    def _select_files_by_type(self, changes: Dict, file_type: str) -> gr.CheckboxGroup:
        """选择特定类型的所有文件。"""
        if not changes or file_type not in changes:
            return gr.CheckboxGroup(value=[])

        file_paths = [f["path"] for f in changes[file_type]]
        return gr.CheckboxGroup(value=file_paths)

    def _select_all_available(self, available_files: List[str]) -> gr.CheckboxGroup:
        """选择所有可用文件。"""
        return gr.CheckboxGroup(value=available_files)

    def _refresh_repositories(self) -> gr.Dropdown:
        """刷新仓库列表。"""
        try:
            repos = self._get_available_repos()
            logger.info(f"刷新仓库列表：找到 {len(repos)} 个仓库")
            return gr.Dropdown(choices=repos, value=None)
        except Exception as e:
            logger.error(f"刷新仓库时出错：{e}")
            return gr.Dropdown(choices=["加载仓库时出错"], value=None)

    async def _process_changed_files(
        self,
        repo_name: str,
        branch: str,
        selected_new: List[str],
        selected_modified: List[str],
        changes: Dict,
    ):
        """使用增量更新处理变化的文件（新文件和已修改文件）。"""
        if not repo_name or repo_name in [
            "没有可用仓库",
            "加载仓库时出错",
        ]:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 未选择仓库",
                "progress": 0,
            }
            yield error_progress, format_progress_display(error_progress)
            return

        all_selected = selected_new + selected_modified
        if not all_selected:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 未选择要处理的文件",
                "progress": 0,
            }
            yield error_progress, format_progress_display(error_progress)
            return

        try:
            start_time = time.time()

            # 初始进度
            initial_progress = {
                "status": ProcessingStatus.LOADING.value,
                "message": f"🔄 正在增量处理 {len(all_selected)} 个变化的文件",
                "progress": 0,
                "phase": "开始增量更新",
                "details": f"仓库：{repo_name}\n分支：{branch}\n文件数：{len(all_selected)}\n模式：增量（保留现有文件）",
                "step": "update_processing",
            }

            yield initial_progress, format_progress_display(initial_progress)

            # 步骤1：先删除已修改文件的旧版本
            if selected_modified:
                logger.info(
                    f"正在移除 {len(selected_modified)} 个已修改文件的旧版本"
                )
                removed_count = repository_manager.delete_specific_files(
                    repo_name, selected_modified
                )
                logger.info(f"已移除 {removed_count} 个旧文件版本")

            # 步骤2：加载选中的文件
            documents, failed_files = await load_files_from_github(
                repo_name, all_selected, branch
            )

            if not documents:
                error_progress = {
                    "status": ProcessingStatus.ERROR.value,
                    "message": "❌ 未能加载任何文档",
                    "progress": 0,
                    "details": f"所有 {len(all_selected)} 个文件加载失败",
                }
                yield error_progress, format_progress_display(error_progress)
                return

            # 更新进度
            loading_progress = {
                "status": ProcessingStatus.LOADED.value,
                "message": f"✅ 已加载 {len(documents)} 个文档用于增量更新",
                "progress": 50,
                "phase": "文件已加载 - 准备增量处理",
                "details": f"成功加载：{len(documents)}\n失败：{len(failed_files)}\n处理模式：增量",
                "step": "update_processing",
            }

            yield loading_progress, format_progress_display(loading_progress)

            # 步骤3：为跟踪创建带 SHA 的文件信息
            files_with_sha = []
            new_file_shas = {f["path"]: f["sha"] for f in changes.get("new", [])}
            modified_file_shas = {
                f["path"]: f["sha"] for f in changes.get("modified", [])
            }
            all_file_shas = {**new_file_shas, **modified_file_shas}

            for file_path in all_selected:
                if file_path in all_file_shas:
                    files_with_sha.append(
                        {"path": file_path, "sha": all_file_shas[file_path]}
                    )

            logger.info(f"正在处理 {len(documents)} 个文档，带 SHA 跟踪")

            # 步骤4：增量导入文档
            success = await ingest_documents_async(
                documents, repo_name, branch=branch, files_with_sha=files_with_sha
            )

            processing_time = time.time() - start_time

            if success:
                # 获取当前仓库统计
                current_stats = repository_manager.get_repository_stats()
                total_docs = current_stats.get("total_documents", "未知")

                completion_progress = {
                    "status": ProcessingStatus.COMPLETE.value,
                    "message": f"🎉 成功增量更新 {len(documents)} 个文件",
                    "progress": 100,
                    "phase": "增量更新完成",
                    "details": f"仓库：{repo_name}\n增量更新完成：\n• 新文件：{len(selected_new)}\n• 已修改文件：{len(selected_modified)}\n• 仓库文档总数：{total_docs}\n耗时：{processing_time:.1f}秒",
                    "step": "update_complete",
                    "processing_time": processing_time,
                    "documents_processed": len(documents),
                    "total_time": processing_time,
                    "update_mode": "incremental",
                }
            else:
                completion_progress = {
                    "status": ProcessingStatus.ERROR.value,
                    "message": "❌ 增量更新处理失败",
                    "progress": 0,
                    "details": "向量导入在增量更新过程中失败",
                }

            yield completion_progress, format_progress_display(completion_progress)

        except Exception as e:
            logger.error(f"处理变化的文件时出错：{e}")
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": f"❌ 增量更新失败：{str(e)}",
                "progress": 0,
                "error": str(e),
                "details": f"增量更新错误：{str(e)}",
            }
            yield error_progress, format_progress_display(error_progress)

    def _ingest_available_files(
            self, repo_name: str, branch: str, selected_files: List[str]
    ) -> Tuple[Dict, str]:
        """导入尚未处理的可用文件。"""
        if not selected_files:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 未选择要导入的文件",
                "progress": 0,
            }
            return error_progress, format_progress_display(error_progress)

        try:
            start_time = time.time()

            # 这需要是异步的，所以让我们创建一个异步包装器
            async def _async_ingest():
                # 加载和处理文件
                documents, failed_files = await load_files_from_github(
                    repo_name, selected_files, branch
                )

                if documents:
                    # 从文档中提取 SHA 信息用于跟踪
                    files_with_sha = []
                    for doc in documents:
                        file_path = doc.metadata.get("file_path", "")
                        file_sha = doc.metadata.get("sha", "")
                        if file_path and file_sha:
                            files_with_sha.append({"path": file_path, "sha": file_sha})

                    success = await ingest_documents_async(
                        documents,
                        repo_name,
                        branch=branch,
                        files_with_sha=files_with_sha,
                    )
                    processing_time = time.time() - start_time

                    if success:
                        completion_progress = {
                            "status": ProcessingStatus.COMPLETE.value,
                            "message": f"🎉 成功导入 {len(documents)} 个新文件",
                            "progress": 100,
                            "processing_time": processing_time,
                            "documents_processed": len(documents),
                            "total_time": processing_time,
                        }
                    else:
                        completion_progress = {
                            "status": ProcessingStatus.ERROR.value,
                            "message": "❌ 导入失败",
                            "progress": 0,
                        }
                else:
                    completion_progress = {
                        "status": ProcessingStatus.ERROR.value,
                        "message": "❌ 未能加载任何文档",
                        "progress": 0,
                    }

                return completion_progress, format_progress_display(completion_progress)

            # 运行异步函数
            return asyncio.run(_async_ingest())

        except Exception as e:
            logger.error(f"导入可用文件时出错：{e}")
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": f"❌ 导入失败：{str(e)}",
                "progress": 0,
            }
            return error_progress, format_progress_display(error_progress)

    def _delete_removed_files(self, repo_name: str, changes: Dict) -> Tuple[Dict, str]:
        """删除已从仓库中移除的文件。"""
        deleted_files = changes.get("deleted", [])
        if not deleted_files:
            info_progress = {
                "status": ProcessingStatus.COMPLETE.value,
                "message": "ℹ️ 没有需要删除的已删除文件",
                "progress": 100,
            }
            return info_progress, format_progress_display(info_progress)

        try:
            deleted_paths = [f["path"] for f in deleted_files]
            deleted_count = repository_manager.delete_specific_files(
                repo_name, deleted_paths
            )

            completion_progress = {
                "status": ProcessingStatus.COMPLETE.value,
                "message": f"🗑️ 从向量存储中移除了 {deleted_count} 个已删除文件",
                "progress": 100,
                "details": f"已删除文件：{len(deleted_files)}\n移除的向量条目：{deleted_count}",
            }

            return completion_progress, format_progress_display(completion_progress)

        except Exception as e:
            logger.error(f"删除已移除文件时出错：{e}")
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": f"❌ 删除文件失败：{str(e)}",
                "progress": 0,
            }
            return error_progress, format_progress_display(error_progress)

    def _refresh_progress(self, progress_state: Dict) -> str:
        """刷新进度显示。"""
        return format_progress_display(progress_state)