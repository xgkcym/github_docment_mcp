import gradio as gr

from github.file_load import discover_repository_files
from ui.components.common import create_status_textbox, create_file_selector, create_progress_display


class IngestionTab:
    """处理文档导入标签页的 UI 和逻辑。"""
    def __init__(self):
        self.progress_state = {}


    def create_tab(self)->gr.TabItem:
        """创建导入标签页界面。"""
        with gr.TabItem("📥 文档导入") as tab:
            gr.Markdown("### 🚀 两步文档处理流程")
            gr.Markdown(
                "**步骤 1：** 从 GitHub 仓库获取 Markdown 文件 → **步骤 2：** 生成向量嵌入并存储在 MongoDB Atlas 中"
            )
            # 仓库输入部分
            with gr.Row(equal_height=True):
                with gr.Column(scale=2):
                    repo_input = gr.Textbox(
                        label="📂 GitHub 仓库 URL",
                        placeholder="输入：owner/repo 或 https://github.com/owner/repo（例如：gradio-app/gradio）",
                        value="",
                        info="输入包含 Markdown 文档的任何 GitHub 仓库",
                    )

                    branch_input = gr.Textbox(
                        label="🌿 分支（可选）",
                        placeholder="输入分支名称（默认：main）",
                        value="main",
                    )

                    load_btn = gr.Button(
                        "🔍 发现文档文件", variant="secondary"
                    )
                with gr.Column(scale=1):
                    status_output = create_status_textbox(
                        label="仓库发现状态",
                        placeholder="仓库扫描结果将显示在这里...",
                        lines=10,
                    )
            # 文件选择控制
            with gr.Row():
                select_all_btn = gr.Button(
                    "📋 全选文档", variant="secondary"
                )
                clear_all_btn = gr.Button("🗑️ 清除选择", variant="secondary")

            # 文件选择器
            with gr.Accordion("可用文档文件", open=False):
                file_selector = create_file_selector(
                    label="选择用于 RAG 处理的 Markdown 文件"
                )

            # 处理控制
            gr.Markdown("### 🔄 RAG 流程执行")

            with gr.Row():
                step1_btn = gr.Button(
                    "📥 步骤 1：从 GitHub 加载文件",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )
                step2_btn = gr.Button(
                    "🧠 步骤 2：处理和存储嵌入",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )
            with gr.Row():
                refresh_btn = gr.Button("🔄 刷新进度", variant="secondary")
                reset_btn = gr.Button("🗑️ 重置进度", variant="secondary")

            # 进度显示
            progress_display = create_progress_display(
                label="📊 实时处理进度",
                initial_value="🚀 准备开始两步处理...\n\n📋 步骤：\n1️⃣ 从 GitHub 仓库加载文件\n2️⃣ 生成嵌入并存储到向量数据库",
                lines=20,
            )

            # 状态管理
            files_state = gr.State([])
            progress_state = gr.State({})
            branch_state = gr.State("main")

            load_btn.click(
                fn=self._discover_files,
                inputs=[repo_input,branch_input],
                outputs=[file_selector,status_output,files_state,step1_btn,branch_state],
                show_api=False
            )

        return tab

    def _discover_files(self,repo_url:str,branch: str = "main"):
        """发现仓库中的文件。"""
        if not repo_url.strip():
            return (
                create_file_selector(visible=False),
                "请输入仓库 URL",
                [],
                gr.Button(interactive=False),
                "main",
            )
        # 使用提供的分支或默认使用 main
        if not branch.strip():
            branch = "main"


        try:
            files_data, message = discover_repository_files(repo_url, branch=branch)
        except Exception as e:
            return None
