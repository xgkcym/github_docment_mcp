
import gradio as gr

from .tabs.management import Management
from .tabs.update_tab import UpdateTab


class DocMCPApp:

    def __init__(self):

        self.management_tab = None

    def creat_interface(self)->gr.Blocks:
        with gr.Blocks(title="Document-MCP") as blocks:
            gr.Markdown("# 📚 Doc-MCP：文档 RAG 系统")
            gr.Markdown(
                "将 GitHub 文档仓库转换为可供 AI 智能体访问的 MCP（模型上下文协议）服务器。"
                "上传文档，生成向量嵌入，并通过智能上下文检索进行查询。"
            )
            self.management_tab = Management(blocks)
            self.update_tab = UpdateTab(blocks)
        return blocks

    def launch(self):
        blocks = self.creat_interface()
        return blocks.launch(mcp_server=True)


def create_app()->DocMCPApp:
    return DocMCPApp()


if __name__ == '__main__':
    try:
        app = create_app()
        app.launch()
    except Exception as ex:
        print(ex)