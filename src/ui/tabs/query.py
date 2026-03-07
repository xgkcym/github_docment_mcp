from typing import Tuple, Dict, Any, Generator

import gradio as gr

from core.settings import settings
from database.repository import repository_manager
from rag.query import create_query_retriever
from ui.components.common import create_repository_dropdown, create_query_interface
from utils.logger_handler import logger


class QueryTab:
    """处理查询界面标签页的 UI 和逻辑。"""
    def __init__(self):
        pass


    def create_tab(self)->gr.TabItem:
         """创建查询标签页界面。"""
         with gr.TabItem("🤖 AI 文档助手") as tab:
             gr.Markdown("### 💬 智能文档问答")
             gr.Markdown(
                 "使用高级语义搜索查询您已处理的文档。获取带有来源引用的上下文答案。"
             )
             with gr.Row():
                 with gr.Column(scale=2):
                    # 仓库选择
                    with gr.Row():
                         repo_dropdown = create_repository_dropdown(
                             choices=self._get_available_repos(),
                             label="📚 选择文档仓库",
                         )

                         selected_repo_textbox = gr.Textbox(
                             label="🎯 已选仓库",
                             value="",
                             interactive=False,
                             visible=False,
                         )

                    refresh_repos_btn = gr.Button("🔄 刷新仓库列表", variant="secondary", size="md")
                    query_input,query_mode,query_btn,response_output,sources_output = create_query_interface()

             repo_dropdown.change(
                 fn=self._handle_repo_selection,
                 inputs=[repo_dropdown],
                 outputs=[repo_dropdown, selected_repo_textbox, query_btn],
                 show_api=False
             )
             refresh_repos_btn.click(
                 fn=self._refresh_repositories,
                 outputs=[repo_dropdown, selected_repo_textbox, query_btn],
                 show_api=False,
             )

             query_btn.click(
                 fn=self._execute_query_stream,
                 inputs=[selected_repo_textbox, query_mode, query_input],
                 outputs=[response_output, sources_output],
                 show_api=False,
             )
             query_input.submit(
                 fn=self._execute_query_stream,
                 inputs=[selected_repo_textbox, query_mode, query_input],
                 outputs=[response_output, sources_output],
                 show_api=False,
             )

             return tab

    def _get_available_repos(self):
        """获取可用仓库列表。"""
        try:
            repos = repository_manager.get_available_repositories()
            return repos if repos else ["没有可用仓库"]
        except Exception as e:
            logger.error(f"获取仓库时出错：{e}")
            return ["加载仓库时出错"]


    def _handle_repo_selection(self,selected_repo: str):
        """处理下拉框的仓库选择。"""
        if not selected_repo or selected_repo in [
            "没有可用仓库",
            "加载仓库时出错",
            "",
        ]:
            return (
                gr.Dropdown(visible=True),
                gr.Textbox(visible=False, value=""),
                gr.Button(interactive=False),
            )
        else:
            return (
                gr.Dropdown(visible=False),
                gr.Textbox(visible=True, value=selected_repo),
                gr.Button(interactive=True),
            )

    def _refresh_repositories(self):
        """刷新仓库列表。"""
        try:
            repos = self._get_available_repos()
            return (
                gr.Dropdown(choices=repos, value=None, visible=True),
                gr.Textbox(visible=False, value=""),
                gr.Button(interactive=False),
            )
        except Exception as e:
            logger.error(f"刷新仓库时出错：{e}")
            return (
                gr.Dropdown(
                    choices=["加载仓库时出错"], value=None, visible=True
                ),
                gr.Textbox(visible=False, value=""),
                gr.Button(interactive=False),
            )


    def _execute_query_stream(self,repo: str, mode: str, query: str)-> Generator[Tuple[str, Dict[str, Any]]]:
        """对仓库执行查询。"""
        if not query.strip():
            yield "请输入查询内容。", {"error": "查询内容为空"}
            return None

        if not repo or repo in [
            "没有可用仓库",
            "加载仓库时出错",
            "",
        ]:
            yield "请选择一个有效的仓库。", {
                "error": "未选择仓库"
            }
            return None


        try:
            # 创建查询检索器
            retriever = create_query_retriever(repo)

            for partial_result in retriever.make_query(query,mode,settings.similarity_top_k):
                if "error" in partial_result:
                    yield f"错误：{partial_result['error']}", {"error": partial_result["error"]}
                    return None
                response_text = partial_result.get("response", "无可用响应")
                source_nodes = partial_result.get("source_nodes", [])
                if not partial_result.get("streaming", False):
                    sources_output = {
                        "sources": source_nodes,
                        "repository": repo,
                        "mode": mode,
                        "processing_time": partial_result.get("processing_time", 0),
                        "total_sources": len(source_nodes),
                    }
                else:
                    # 流式过程中，sources_output 保持为空或显示"生成中..."
                    sources_output = {"status": "生成回答中..."}
                yield response_text, sources_output
        except Exception as e:
            logger.error(f"查询执行错误：{e}")
            error_msg = f"查询失败：{str(e)}"
            yield error_msg, {"error": str(e)}