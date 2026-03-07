import asyncio
from typing import Dict, List, Optional, Union, Any

import gradio as gr

from database.repository import repository_manager
from github.client import github_client
from github.file_load import load_files_from_github
from rag.query import create_query_retriever
from utils.logger_handler import logger


class MCPTab:
    def __init__(self):
        # 初始化通用输入组件
        self.repo_name_input = gr.Textbox(
            label="仓库名称", placeholder="输入仓库名称"
        )

        self.branch_input = gr.Textbox(
            label="分支",
            placeholder="输入分支名称（默认：main）",
            value="main",
        )

        self.file_extensions_input = gr.CheckboxGroup(
            label="文件扩展名",
            choices=[".md", ".mdx", ".txt", ".py"],
            value=[".md", ".mdx"],
        )

        self.single_file_path_input = gr.Textbox(
            label="文件路径", placeholder="输入文件路径"
        )

        self.multi_file_paths_input = gr.Textbox(
            label="文件路径（逗号分隔）",
            placeholder="输入文件路径，例如：file1.md,file2.md",
        )
        self.query_input = gr.Textbox(label="查询", placeholder="输入您的问题")

        self.search_mode_input = gr.Radio(
            label="搜索模式",
            choices=["default", "text_search", "hybrid"],
            value="default",
        )
        self.top_k_input = gr.Number(label="返回结果数量", value=5, precision=0)
    def create_tab(self)->gr.TabItem:
        """创建 MCP 标签页界面。"""
        with gr.TabItem("MCP", visible=False) as tab:
            with gr.Column():
                # 按钮
                list_repo_btn = gr.Button("列出仓库")
                list_repo_file_btn = gr.Button("列出仓库文件")
                get_file_content_btn = gr.Button("获取文件内容")
                get_multi_file_content_btn = gr.Button("获取多个文件内容")
                query_btn = gr.Button("查询仓库")

                # 通用输入部分
                with gr.Group():
                    gr.Markdown("### 仓库设置",padding=True)
                    self.repo_name_input.render()
                    self.branch_input.render()

                # 文件特定输入
                with gr.Group():
                    gr.Markdown("### 文件设置",padding=True)
                    self.file_extensions_input.render()
                    self.single_file_path_input.render()
                    self.multi_file_paths_input.render()

                # 查询特定输入
                with gr.Group():
                    gr.Markdown("### 查询设置" ,padding=True)
                    self.query_input.render()
                    self.search_mode_input.render()
                    self.top_k_input.render()

                # 输出
                output_block = gr.JSON(label="输出")

            # 定义每个按钮的操作
            list_repo_btn.click(
                fn=self.list_available_repos_docs, inputs=[], outputs=output_block
            )
            list_repo_file_btn.click(
                fn=self.list_repository_files,
                inputs=[
                    self.repo_name_input,
                    self.file_extensions_input,
                    self.branch_input,
                ],
                outputs=output_block,
            )

            get_file_content_btn.click(
                fn=self.get_single_file_content_from_repo,
                inputs=[
                    self.repo_name_input,
                    self.single_file_path_input,
                    self.branch_input,
                ],
                outputs=output_block,
            )

            get_multi_file_content_btn.click(
                fn=self.get_multi_file_content_from_repo,
                inputs=[
                    self.repo_name_input,
                    self.multi_file_paths_input,
                    self.branch_input,
                ],
                outputs=output_block,
            )

            query_btn.click(
                fn=self.query_doc,
                inputs=[
                    self.repo_name_input,
                    self.query_input,
                    self.search_mode_input,
                    self.top_k_input,
                ],
                outputs=output_block,
            )

            return  tab

    def list_available_repos_docs(self) -> List[Dict[str, str]]:
        """
        列出已导入的可用仓库文档。

        返回:
            List[Dict[str, str]]：包含仓库名称和分支的字典列表。
        """
        try:
            repos = repository_manager.repos_collection.find(
                {}, {"repo_name": 1, "branch": 1, "_id": 0}
            )
            return list(repos)
        except Exception as e:
            logger.error(f"获取仓库时出错：{e}")
            return []

    def list_repository_files(
        self,
        repo_name: str,
        file_extensions: Optional[List[str]] = None,
        branch: Optional[str] = None,
    ) ->  Union[List[str], Dict[str, str]]:
        """
        列出仓库中的文件，可选择按扩展名和分支过滤。
        参数:
            repo_name (str): 仓库名称。
            file_extensions (Optional[List[str]]): 要过滤的文件扩展名列表。默认为 [".md", ".mdx"]。
            branch (Optional[str]): 要列出文件的分支名称。默认为 main

        返回:
            List[str]: 仓库中的文件路径列表。
        """
        # 验证
        if not repo_name or not repo_name.strip():
            return {"error": "需要提供仓库名称"}

        if not branch or not branch.strip():
            branch = "main"

        if not file_extensions:
            file_extensions = [".md", ".mdx"]

        filtered_files, _ = github_client.get_repository_tree(
            repo_url=repo_name, file_extensions=file_extensions, branch=branch
        )

        return filtered_files

    def get_single_file_content_from_repo(
        self, repo_name: str, file_path: str, branch: Optional[str] = None
    ) -> Dict[str, str]:
        """
        获取仓库中单个文件的内容。

        参数:
            repo_name (str): 仓库名称。
            file_path (str): 仓库内的文件路径。
            branch (Optional[str]): 获取文件的分支名称。默认为 main。

        返回:
            str: 文件内容。
        """
        # 验证
        if not repo_name or not repo_name.strip():
            return {"error": "需要提供仓库名称"}

        if not file_path or not file_path.strip():
            return {"error": "需要提供文件路径"}

        if not branch or not branch.strip():
            branch = "main"

        import asyncio
        file, _ = asyncio.run(
            load_files_from_github(
                repo_url=repo_name, file_paths=[file_path], branch=branch
            )
        )

        return (
            {"file_path": file_path, "content": file[0].get_content()}
            if file
            else {"message": "未找到文件或文件为空"}
        )

    def get_multi_file_content_from_repo(
            self, repo_name: str, file_paths: List[str], branch: Optional[str] = None
    ) -> list[dict[str, str | Any]] | dict[str, str]:
        """
        获取仓库中多个文件的内容。

        参数:
            repo_name (str): 仓库名称。
            file_paths (List[str]): 仓库内的文件路径列表。
            branch (Optional[str]): 获取文件的分支名称。默认为 main。

        返回:
            List[str]: 文件内容列表。
        """
        # 验证
        if not repo_name or not repo_name.strip():
            return {"error": "需要提供仓库名称"}

        if not file_paths:
            return {"error": "需要提供文件路径"}

        if not branch or not branch.strip():
            branch = "main"

        if isinstance(file_paths, str):
            processed_file_paths = [
                file_path.strip() for file_path in file_paths.split(",")
            ]
            if not processed_file_paths or all(
                    not path for path in processed_file_paths
            ):
                return {"error": "至少需要一个有效的文件路径"}
        else:
            processed_file_paths = file_paths

        files, _ = asyncio.run(
            load_files_from_github(
                repo_url=repo_name, file_paths=processed_file_paths, branch=branch
            )
        )

        return [
            {"path": file.metadata["file_path"], "content": file.get_content()}
            for file in files
        ]

    def query_doc(
            self,
            repo_name: str,
            query: str,
            mode: Optional[str] = "default",
            top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        对仓库文档执行查询。

        参数:
            repo_name (str): 仓库名称。
            query (str): 用户的问题。
            mode Optional[str]: 搜索模式（default, text_search, hybrid）。可选，默认为 "default"。
            top_k Optional[int]: 返回的结果数量。可选，默认为 5。

        返回:
            Dict[str, any]: 包含响应和来源节点的字典。
        """
        # 验证
        if not repo_name or not repo_name.strip():
            return {"error": "需要提供仓库名称"}

        if not query or not query.strip():
            return {"error": "需要提供查询内容"}

        if mode not in ["default", "text_search", "hybrid"]:
            mode = "default"

        if top_k is None or top_k <= 0:
            top_k = 5

        if top_k > 100:
            top_k = 100

        return create_query_retriever(repo_name).make_query(query, mode, top_k)
