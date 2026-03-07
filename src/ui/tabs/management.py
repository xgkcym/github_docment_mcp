from typing import Tuple, List, Dict, Any

import gradio as gr
from gradio import Dropdown

from src.core.settings import settings
from src.database.repository import repository_manager
from src.utils.logger_handler import logger


class ManagementTab:
    """处理仓库管理标签页的UI和逻辑。"""
    def __init__(self,demo:gr.Blocks):
        self.demo = demo

    def create_tab(self)->gr.TabItem:
        """创建管理标签页界面。"""
        with gr.TabItem("📊 仓库管理",visible=settings.enable_repo_management) as tab:
            # gr.Markdown("### 📊 仓库管理")
            gr.Markdown("管理您已导入的仓库 - 查看详情并在需要时删除仓库。")
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
                    # 刷新统计
                    refresh_stats_btn.click(fn=self._load_repository_stats, outputs=[stats_json], show_api=False)
                with gr.Column(scale=2):
                    gr.Markdown("### 📋 仓库详情")
                    repos_table = gr.DataFrame(
                        headers=["仓库", "文件数", "最后更新", "状态"],
                        datatype=["str", "number", "str", "str"],
                        # label="已导入仓库",
                        interactive=False,
                        wrap=True,
                        max_height=300
                    )
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
                        choices=[],
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

            # 刷新仓库列表
            refresh_repos_btn.click(fn=self._load_repository_detail, outputs=[repos_table,delete_repo_dropdown], show_api=False)

            # 删除仓库下拉框发生变化，决定是否禁用按钮
            delete_repo_dropdown.change(
                fn=self._check_delete_button_state,
                inputs=[delete_repo_dropdown,confirm_delete],
                outputs=[delete_btn],
            )
            # 复选框发生变化时，决定是否禁用按钮
            confirm_delete.change(
                fn=self._check_delete_button_state,
                inputs=[delete_repo_dropdown, confirm_delete],
                outputs=[delete_btn],
            )

            # 删除按钮点击
            delete_btn.click(
                fn=self._delete_repository,
                inputs=[delete_repo_dropdown,confirm_delete],
                outputs=[deletion_status,delete_repo_dropdown,confirm_delete,repos_table],
                show_api=False,
            )

            #初始化加载数据
            self.demo.load(
                fn=self._load_repository_stats,
                outputs=[stats_json],
                show_api=False
            )
            self.demo.load(
                fn=self._load_repository_detail,
                outputs=[repos_table,delete_repo_dropdown],
                show_api=False
            )
            return tab

    def _load_repository_stats(self)->Dict[str,Any]:
        try:
            return repository_manager.get_repository_stats()
        except Exception as e:
            logger.error(f"加载仓库统计信息失败: {e}")
            return {"error": f"加载统计信息失败: {str(e)}"}


    def _load_repository_detail(self)->Tuple[List[List],Dropdown]:
        """加载仓库详情用于表格和下拉框。"""
        try:
            details = repository_manager.get_repository_detail()
            if not details:
                return  [["未找到仓库", 0, "N/A", "N/A"]],gr.Dropdown(
                    choices=[],
                    label="选择要删除的仓库",
                    value=None,
                    interactive=True,
                    allow_custom_value=True
                )
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
            return table_data,gr.Dropdown(
                choices=dropdown_choices,
                label="选择要删除的仓库",
                value=None,
                interactive=True,
                allow_custom_value=True
            )
        except Exception as e:
            logger.error(f"加载仓库详情信息失败: {e}")
            return [["加载仓库时出错", 0, str(e), "错误"]],gr.Dropdown(
                    choices=[],
                    label="选择要删除的仓库",
                    value=None,
                    interactive=True,
                    allow_custom_value=True
                )

    def _check_delete_button_state(self,repo_selected: str, confirmation_checked: bool)->gr.Button:
        if repo_selected and repo_selected.strip() != '' and confirmation_checked:
            return gr.Button(interactive=True)
        else:
            return gr.Button(interactive=False)

    def _delete_repository(self,repo_name: str, confirmed: bool):
        """删除仓库"""
        if not repo_name or repo_name == '':
            table_data, dropdown_choices = self._load_repository_detail()
            return (
                "❌ 未选择仓库。",
                gr.Dropdown(
                    choices=dropdown_choices,
                    value=None,
                    label="选择要删除的仓库",
                    interactive=True,
                    allow_custom_value=False,
                ),
                gr.Checkbox(value=confirmed),
                table_data,
            )
        if not confirmed:
            table_data, dropdown_choices = self._load_repository_detail()
            return (
                "❌ 请勾选确认框以确认删除。",
                gr.Dropdown(
                    choices=dropdown_choices,
                    value=repo_name,
                    label="选择要删除的仓库",
                    interactive=True,
                    allow_custom_value=False,
                ),
                gr.Checkbox(value=False),
                table_data,
            )
        try:
            logger.info(f"正在删除仓库：{repo_name}")
            result = repository_manager.delete_repository_data(repo_name)

            # 删除后刷新数据
            table_data, dropdown_choices = self._load_repository_detail()

            if result['success']:
                return (
                    f"✅ {result['message']}",
                    dropdown_choices,
                    gr.Checkbox(value=False),
                    table_data,
                )
            else:
                return (
                    f"❌ {result['message']}",
                    dropdown_choices,
                    gr.Checkbox(value=False),
                    table_data,
                )
        except Exception as e:
            raise e