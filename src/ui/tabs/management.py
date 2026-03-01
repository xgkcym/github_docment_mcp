from typing import Tuple, List, Dict, Any

import gradio as gr

from src.core.settings import settings
from src.database.repository import repository_manager
from src.utils.logger_handler import logger


class Management:
    """处理仓库管理标签页的UI和逻辑。"""
    def __init__(self,blocks:gr.Blocks):
        self.blocks = blocks

    def create_tab(self)->gr.TabItem:
        """创建管理标签页界面。"""
        with gr.TabItem("📊 仓库管理",visible=settings.enable_repo_management) as tab:
            # gr.Markdown("### 📊 仓库管理")
            gr.Markdown("管理您已导入的仓库 - 查看详情并在需要时删除仓库。")
            initial_table_data, initial_dropdown_choices = self._load_repository_detail()
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📊 仓库统计")
                    stats_json = gr.Json(
                        label="数据库统计",
                        value={"message":"点击刷新加载统计信息..."}
                    )
                    refresh_stats_btn = gr.Button(
                        "🔄 刷新统计", variant="secondary"
                    )
                with gr.Column(scale=2):
                    gr.Markdown("### 📋 仓库详情")
                    repos_table = gr.DataFrame(
                        headers=["仓库", "文件数", "最后更新", "状态"],
                        datatype=["str", "number", "str", "str"],
                        label="已导入仓库",
                        interactive=False,
                        wrap=True,
                        max_height=300
                    )
                    repos_table.value = initial_table_data
                    refresh_repos_btn = gr.Button(
                        "🔄 刷新仓库列表", variant="secondary"
                    )
            # 删除部分
            gr.Markdown("### 🗑️ 删除仓库")
            gr.Markdown(
                "**⚠️ 警告：** 这将永久删除所选仓库的所有文档和元数据。"
            )
            with gr.Row():
                with gr.Column(scale=2):
                    delete_repo_dropdown = gr.Dropdown(
                        choices=initial_dropdown_choices,
                        label="选择要删除的仓库",
                        value=None,
                        interactive=True,
                        allow_custom_value=True
                    )
                    confirm_delete = gr.Checkbox(
                        label="我了解此操作无法撤销", value=False
                    )
                    delete_btn = gr.Button(
                        "🗑️ 删除仓库",
                        variant="stop",
                        size="lg",
                        interactive=False,
                    )

                with gr.Column(scale=1):
                    deletion_status = gr.Textbox(
                        label="删除状态",
                        value="选择仓库并确认以确认删除。",
                        interactive=False,
                        lines=6,
                    )

        return tab

    def _load_repository_stats(self)->Dict[str,Any]:
        try:
            return repository_manager.get_repository_stats()
        except Exception as e:
            logger.error(f"加载仓库统计信息失败: {e}")
            return {"error": f"加载统计信息失败: {str(e)}"}


    def _load_repository_detail(self)->Tuple[List[List],List[str]]:
        """加载仓库详情用于表格和下拉框。"""
        try:
            details = repository_manager.get_repository_detail()
            if not details:
                return  [["未找到仓库", 0, "N/A", "N/A"]],[]
            # 格式化数据表格
            table_data = []
            dropdown_choices = []
            for repo in details:
                repo_name = repo.get("name","未知")
                last_updated = repo.get("last_updated", "未知")
                if hasattr(last_updated,'strftime'):
                    last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
                elif last_updated != '未知':
                    last_updated = str(last_updated)
                table_data.append([
                    repo_name,
                    repo.get("files", 0),
                    last_updated,
                    repo.get("status", "未知"),
                ])
                if repo_name != '未知':
                    dropdown_choices.append(repo.get("name"))

            return table_data,dropdown_choices
        except Exception as e:
            logger.error(f"加载仓库详情信息失败: {e}")
            return [["加载仓库时出错", 0, str(e), "错误"]], []