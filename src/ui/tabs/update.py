from typing import List, Dict, Tuple

import gradio as gr

from database.repository import repository_manager
from github.file_load import discover_repository_files_with_changes
from ui.components.common import create_repository_dropdown,create_status_textbox,create_file_selector,create_progress_display
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
                    branch_input = gr.Textbox(
                        label="🌿 分支",
                        placeholder="分支名称（默认：main）",
                        value="main",
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

            # detect_changes_btn.click(
            #     fn=self._detect_changes_and_available,
            #     inputs=[repo_dropdown,branch_input],
            #     outputs=[
            #         changes_state,
            #         available_files_state,
            #         status_output,
            #         change_summary_display,
            #         new_files_selector,
            #         modified_files_selector,
            #         deleted_files_display,
            #         available_files_selector,
            #         update_changed_btn,
            #         ingest_available_btn,
            #         delete_removed_btn,
            #     ],
            # )

        return tab

    def _get_available_repos(self) -> List[str]:
        """获取可用仓库列表。"""
        try:
            repos = repository_manager.get_available_repositories()
            return repos if repos else ["没有可用仓库"]
        except Exception as e:
            logger.error(f"获取仓库时出错：{e}")
            return ['加载仓库时出错']


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
        ]:
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
        if not branch.strip():
            branch = "main"


        try:
            logger.info(f"检测 {repo_name} 在分支 {branch} 上的变化")
            # 获取变化和可用文件
            result = discover_repository_files_with_changes(repo_name, repo_name, branch)
            return ()
        except  Exception as e:
            return ()