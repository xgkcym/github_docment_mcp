import time
from typing import List, Dict, Any

import gradio as gr
from click.core import batch

from core.settings import settings
from core.types import ProcessingStatus
from github.file_load import discover_repository_files, load_files_from_github
from rag.ingestion import ingest_documents_async
from ui.components.common import create_status_textbox, create_file_selector, create_progress_display, \
    format_progress_display
from utils.logger_handler import logger


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
                        value="https://github.com/Arindam200/awesome-ai-apps",
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
            with gr.Accordion("可用文档文件", open=True):
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
            # with gr.Row():
            #     refresh_btn = gr.Button("🔄 刷新进度", variant="secondary")
            #     reset_btn = gr.Button("🗑️ 重置进度", variant="secondary")

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

            # 查询github地址包含的数据
            load_btn.click(
                fn=self._discover_files,
                inputs=[repo_input,branch_input],
                outputs=[file_selector,status_output,files_state,step1_btn,branch_state],
                show_api=False
            )
            # 全选按钮
            select_all_btn.click(
                fn=self._select_all_files,
                inputs=[files_state],
                outputs=[file_selector],
                show_api=False,
            )

            # 清空选项按钮
            clear_all_btn.click(
                fn=self._clear_all_files,
                outputs=[file_selector],
                show_api=False,
            )

            #从github加载文件
            step1_btn.click(
                fn=self._start_file_loading_generator,
                inputs=[repo_input,file_selector,branch_state],
                outputs=[progress_state, progress_display, step2_btn],
                show_api=False,
            )

            step2_btn.click(
                fn=self._start_vector_ingestion,
                inputs=[progress_state],
                outputs=[progress_state, progress_display],
                show_api=False,
            )

            # refresh_btn.click(
            #     fn=self._refresh_progress,
            #     inputs=[progress_state],
            #     outputs=[progress_display],
            #     show_api=False,
            # )



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
            # 获取github的文档
            files_data, message = discover_repository_files(repo_url, branch=branch)

            if files_data:
                # 提取文件路径用于选择器（向后兼容）
                if isinstance(files_data[0], dict):
                    # 新格式：{"path": "...", "sha": "..."} 列表
                    file_paths = [file_info["path"] for file_info in files_data]
                else:
                    # 旧格式：文件路径列表
                    file_paths = files_data
                return (
                    create_file_selector(
                        choices=file_paths,
                        label=f"从 {repo_url}/{branch} 选择文件（{len(file_paths)} 个文件）",
                        visible=True,
                    ),
                    message,
                    files_data,  # 将完整数据（包含 SHA）存储在状态中
                    gr.Button(interactive=True),
                    branch,
                )
            else:
                return (
                    create_file_selector(visible=False),
                    message,
                    [],
                    gr.Button(interactive=False),
                    branch,
                )

        except Exception as e:
            logger.error(f"[github文件查找] 文件发现错误：{e}")
            return (
                create_file_selector(visible=False),
                f"错误：{str(e)}",
                [],
                gr.Button(interactive=False),
                branch,
            )


    def _select_all_files(self,available_files_data):
        """选择所有可用文件。"""
        if available_files_data:
            # 处理旧格式（路径列表）和新格式（字典列表）
            if isinstance(available_files_data[0], dict):
                # 新格式：从字典中提取文件路径
                file_paths = [file_info["path"] for file_info in available_files_data]
                return gr.CheckboxGroup(value=file_paths)
            else:
                # 旧格式：已经是文件路径列表
                return gr.CheckboxGroup(value=available_files_data)
        return  gr.CheckboxGroup(value=available_files_data)


    def _clear_all_files (self):
        """清空选择"""
        return  gr.CheckboxGroup(value=[])

    async def _start_file_loading_generator(self,repo_url:str,selected_files: List[str],branch: str = "main"):
        """开始文件加载，实时生成器更新。"""
        # 使用提供的分支或默认使用 main
        if not branch.strip():
            branch = "main"

        logger.info(
            f"开始从 {repo_url}/{branch} 加载 {len(selected_files)} 个文件"
        )

        if not selected_files:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 未选择要加载的文件",
                "progress": 0,
                "details": "请至少选择一个文件继续。",
                "step": "file_loading",
            }
            yield (
                error_progress,
                format_progress_display(error_progress),
                gr.Button(interactive=False),
            )
            return

        start_time = time.time()
        total_files = len(selected_files)

        if 'github.com' in repo_url:
            repo_name = (
                repo_url.replace("https://github.com/", "")
                .replace("http://github.com/", "")
                .strip("/")
            )
        else:
            repo_name = repo_url.strip()

        if "/" not in repo_name:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 无效的仓库 URL 格式",
                "progress": 0,
                "details": "预期格式：owner/repo 或 https://github.com/owner/repo",
                "step": "file_loading",
            }
            yield (
                error_progress,
                format_progress_display(error_progress),
                gr.Button(interactive=False),
            )
            return


        try:
            # 初始进度更新
            initial_progress = {
                "status": ProcessingStatus.LOADING.value,
                "message": f"🚀 开始从 {repo_name}/{branch} 加载文件",
                "progress": 0,
                "total_files": total_files,
                "processed_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "phase": "文件加载",
                "details": f"准备从分支 '{branch}' 加载 {total_files} 个文件...",
                "step": "file_loading",
                "repo_name": repo_name,
                "branch": branch,
            }
            yield (
                initial_progress,
                format_progress_display(initial_progress),
                gr.Button(interactive=False),
            )

            # 获取llamaIndex文档
            documents, failed_files  = await load_files_from_github(repo_url,selected_files,branch=branch,max_concurrent=settings.github_concurrent_requests)

            loading_time = time.time() - start_time

            # 从加载的文档中提取 SHA 信息用于跟踪
            files_with_sha = []
            for doc in documents:
                file_path = doc.metadata.get("file_path", "")
                file_sha = doc.metadata.get("sha", "")
                if file_path and file_sha:
                    files_with_sha.append({"path": file_path, "sha": file_sha})
            # 最终完成更新
            completion_progress = {
                "status": ProcessingStatus.LOADED.value,
                "message": f"✅ 文件加载完成！从 {branch} 加载了 {len(documents)} 个文档",
                "progress": 100,
                "phase": "文件加载成功",
                "details": (
                    f"🎯 分支 '{branch}' 的最终结果：\n✅ 成功加载：{len(documents)} 个文档\n❌ 失败文件：{len(failed_files)} 个\n⏱️ 总耗时：{loading_time:.1f}秒\n📊 成功率：{(len(documents) / (len(documents) + len(failed_files)) * 100):.1f}%"
                    if (len(documents) + len(failed_files)) > 0
                    else "100%"
                ),
                "step": "file_loading_complete",
                "loaded_documents": documents,
                "failed_files": failed_files,
                "files_with_sha": files_with_sha,  # 添加 SHA 跟踪数据
                "loading_time": loading_time,
                "repo_name": repo_name,
                "branch": branch,
                "total_files": total_files,
                "processed_files": total_files,
                "successful_files": len(documents),
            }
            yield (
                completion_progress,
                format_progress_display(completion_progress),
                gr.Button(interactive=True),  # 启用步骤 2 按钮
            )
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"{total_time:.1f}秒后文件加载错误：{e}")
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": f"❌ {total_time:.1f}秒后文件加载错误",
                "progress": 0,
                "phase": "加载失败",
                "details": f"从分支 '{branch}' 加载文件时发生严重错误：\n{str(e)}",
                "error": str(e),
                "step": "file_loading",
                "branch": branch,
            }
            yield (
                error_progress,
                format_progress_display(error_progress),
                gr.Button(interactive=False),
            )


    async def _start_vector_ingestion(self,current_progress: Dict[str, Any]):
        """开始向量导入过程。"""
        if current_progress.get("successful_files") == 0:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 没有要处理的文档",
                "progress": 0,
                "details": "请先加载文件。",
            }
            return error_progress, format_progress_display(error_progress)
        documents = current_progress.get("loaded_documents", [])
        repo_name = current_progress.get("repo_name", "")
        branch = current_progress.get("branch", "main")
        files_with_sha = current_progress.get("files_with_sha", [])

        if not documents:
            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 没有可用文档",
                "progress": 0,
                "details": "未找到要处理的文档。",
            }
            return error_progress, format_progress_display(error_progress)

        vector_start_time = time.time()

        try:
            logger.info(
                f"开始为来自 {repo_name}/{branch} 的 {len(documents)} 个文档进行向量导入"
            )
            success_list = []
            # 运行异步导入，避免事件循环问题
            for i in range(0,len(documents),settings.embed_batch_size):
                success = await ingest_documents_async(
                    documents[i:i + settings.embed_batch_size], repo_name, branch=branch, files_with_sha=files_with_sha,allow_trans=settings.allow_trans
                )
                success_list.append(success)

            vector_time = time.time() - vector_start_time
            loading_time = current_progress.get("loading_time", 0)
            total_time = loading_time + vector_time
            if True not in success_list:
                complete_progress = {
                    "status": ProcessingStatus.ERROR.value,
                    "message": "❌ 向量导入失败",
                    "progress": 0,
                    "details": "文档导入失败",
                }
            else:
                # 安全获取失败文件数据
                failed_files_data = current_progress.get("failed_files", [])
                failed_files_count = (
                    len(failed_files_data)
                    if isinstance(failed_files_data, list)
                    else (
                        failed_files_data if isinstance(failed_files_data, int) else 0
                    )
                )

                complete_progress = {
                    "status": ProcessingStatus.COMPLETE.value,
                    "message": f"🎉 {repo_name}/{branch} 的完整处理流程完成！",
                    "progress": 100,
                    "phase": "完成",
                    "details": f"成功为 {repo_name} 处理了 {len(documents)} 个文档，来自分支 '{branch}'，已启用 SHA 跟踪",
                    "step": "complete",
                    "total_time": total_time,
                    "documents_processed": len(documents),
                    "failed_files_count": failed_files_count,
                    "failed_files": failed_files_data,
                    "vector_time": vector_time,
                    "loading_time": loading_time,
                    "repo_name": repo_name,
                    "branch": branch,
                    "repository_updated": True,
                    "sha_tracking_enabled": True,  # 指示 SHA 跟踪已启用
                }

            return complete_progress, format_progress_display(complete_progress)
        except Exception as e:
            vector_time = time.time() - vector_start_time
            logger.error(f"{vector_time:.2f}秒后向量导入错误：{str(e)}")
            # 安全获取失败文件数据
            failed_files_data = current_progress.get("failed_files", [])
            failed_files_count = (
                len(failed_files_data)
                if isinstance(failed_files_data, list)
                else (failed_files_data if isinstance(failed_files_data, int) else 0)
            )

            error_progress = {
                "status": ProcessingStatus.ERROR.value,
                "message": "❌ 向量存储导入失败",
                "progress": 0,
                "phase": "失败",
                "details": f"错误：{str(e)}",
                "error": str(e),
                "step": "vector_ingestion",
                "failed_files_count": failed_files_count,
                "failed_files": failed_files_data,
                "branch": branch,
            }
            return error_progress, format_progress_display(error_progress)


    # def _refresh_progress(self,current_progress: Dict[str, Any]):
    #     return format_progress_display(current_progress)