
import gradio as gr
from gradio import Blocks

from src.ui.tabs.management import ManagementTab
from src.ui.tabs.update import UpdateTab
from ui.tabs.ingestion import IngestionTab
from ui.tabs.query import QueryTab


class DocMCPApp:
    def __init__(self):
        self.ingestion_tab = IngestionTab()
        self.query_tab = QueryTab()
        self.management_tab = None
        self.update_tab = None

    def create_interface(self)->gr.Blocks:
        """创建主 Gradio 界面。"""
        with gr.Blocks(title="Document-MCP") as demo:
            gr.Markdown("# 📚 Doc-MCP：文档 RAG 系统")
            gr.Markdown(
                "将 GitHub 文档仓库转换为可供 AI 智能体访问的 MCP（模型上下文协议）服务器。"
                "上传文档，生成向量嵌入，并通过智能上下文检索进行查询。"
            )
            self.management_tab = ManagementTab(demo)
            self.update_tab = UpdateTab(demo)
            with gr.Tabs():
                self.ingestion_tab.create_tab()
                self.query_tab.create_tab()
                # self.management_tab.create_tab()
                self.update_tab.create_tab()
        return demo

    def launch(self):
        demo = self.create_interface()
        return demo.launch(mcp_server=True,share=True)


def create_app()->DocMCPApp:
    return DocMCPApp()


if __name__ == '__main__':
    try:
        demo = create_app()
        demo.launch()
    except Exception as ex:
        print(ex)