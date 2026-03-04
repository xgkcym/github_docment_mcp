from typing import Sequence, Any, List, Dict

import gradio as gr



def create_repository_dropdown(choices:List[str] = None, label: str = "选择仓库",allow_custom_value:bool=False)->gr.Dropdown:
    if choices is None:
        choices = ['没有可用仓库']
    return gr.Dropdown(
        choices=choices,
        label=label,
        value=None,
        interactive=True,
        allow_custom_value=allow_custom_value
    )

def create_status_textbox( label: str = "状态",
    placeholder: str = "状态将显示在这里...",
    lines: int = 4,)->gr.Textbox:
    return gr.Textbox(
        label=label,
        placeholder=placeholder,
        lines=lines,
        interactive=False
    )


def create_file_selector( choices: List[str] = None, label: str = "选择文件", visible: bool = False)-> gr.CheckboxGroup:
    """创建文件选择器组件。"""
    if choices is None:
        choices = []
    return gr.CheckboxGroup(
        label=label,
        choices=choices,
        visible=visible,
        interactive=True,
    )

def create_progress_display(
    label: str = "进度", initial_value: str = "准备开始...", lines: int = 20
) -> gr.Textbox:
    """创建标准化的进度显示组件。"""
    return gr.Textbox(
        label=label,
        value=initial_value,
        interactive=False,
        lines=lines,
        max_lines=lines + 5,
    )


def format_progress_display(progress_state: Dict[str, Any]) -> str:
    """将进度状态格式化为可读显示，包含增强的详细信息"""
    if not progress_state:
        return "🚀 准备开始导入...\n\n📋 **两步流程：**\n1️⃣ 从 GitHub 仓库加载文件\n2️⃣ 生成嵌入并存储到向量数据库"

    status = progress_state.get("status", "未知")
    message = progress_state.get("message", "")
    progress = progress_state.get("progress", 0)
    phase = progress_state.get("phase", "")
    details = progress_state.get("details", "")

    # 安全计算进度条
    try:
        filled = max(0, min(int(progress / 2.5), 40))  # 确保 0-40 范围
        progress_bar = "█" * filled + "░" * (40 - filled)
    except (ZeroDivisionError, ValueError, TypeError):
        progress_bar = "░" * 40
        progress = 0

    # 状态表情映射
    status_emoji = {
        "loading": "⏳",
        "loaded": "✅",
        "vectorizing": "🧠",
        "complete": "🎉",
        "error": "❌",
    }

    emoji = status_emoji.get(status, "🔄")

    output = f"{emoji} **{message}**\n\n"

    # 阶段和进度部分
    output += f"📊 **当前阶段：** {phase}\n"
    output += f"📈 **进度：** {progress:.1f}%\n"
    output += f"[{progress_bar}] {progress:.1f}%\n\n"

    # 更新模式指示
    if progress_state.get("update_mode") == "incremental":
        output += "🔄 **更新模式：** 增量（保留现有文件）\n\n"

    # 文件加载的步骤特定详情
    if progress_state.get("step") == "file_loading":
        processed = progress_state.get("processed_files", 0)
        total = progress_state.get("total_files", 0)
        successful = progress_state.get("successful_files", 0)
        failed = progress_state.get("failed_files", 0)

        if total > 0:
            output += "📁 **文件处理状态：**\n"
            output += f"   • 总文件数：{total}\n"
            output += f"   • 已处理：{processed}/{total}\n"
            output += f"   • ✅ 成功：{successful}\n"
            output += f"   • ❌ 失败：{failed}\n"

            if "current_batch" in progress_state and "total_batches" in progress_state:
                output += f"   • 📦 当前批次：{progress_state['current_batch']}/{progress_state['total_batches']}\n"
            output += "\n"

    # 向量导入的步骤特定详情
    elif progress_state.get("step") == "vector_ingestion":
        docs_count = progress_state.get("documents_count", 0)
        repo_name = progress_state.get("repo_name", "未知")

        if docs_count > 0:
            output += "🧠 **向量处理状态：**\n"
            output += f"   • 仓库：{repo_name}\n"
            output += f"   • 文档数：{docs_count:,}\n"
            output += f"   • 阶段：{phase}\n\n"

    # 详细信息
    if details:
        output += f"📝 **详细信息：**\n{details}\n"

    # 完成时的最终摘要
    if status == "complete":
        total_time = progress_state.get("total_time", 0)
        docs_processed = progress_state.get("documents_processed", 0)
        failed_files = progress_state.get("failed_files", 0)
        vector_time = progress_state.get("vector_time", 0)
        loading_time = progress_state.get("loading_time", 0)
        repo_name = progress_state.get("repo_name", "未知")
        processing_time = progress_state.get("processing_time", total_time)

        update_mode = progress_state.get("update_mode", "standard")
        mode_label = "增量更新" if update_mode == "incremental" else "操作"

        output += f"\n🎊 **{mode_label}成功完成！**\n"
        output += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += f"🎯 **仓库：** {repo_name}\n"
        output += f"📄 **处理的文档数：** {docs_processed:,}\n"

        # 安全处理失败文件
        failed_count = 0
        if isinstance(failed_files, list):
            failed_count = len(failed_files)
        elif isinstance(failed_files, int):
            failed_count = failed_files

        output += f"❌ **失败的文件：** {failed_count}\n"

        if processing_time > 0:
            output += f"⏱️ **总耗时：** {processing_time:.1f} 秒\n"
            if loading_time > 0:
                output += f"   ├─ 文件加载：{loading_time:.1f}秒\n"
            if vector_time > 0:
                output += f"   └─ 向量处理：{vector_time:.1f}秒\n"

            # 安全计算处理速率
            if docs_processed > 0 and processing_time > 0:
                try:
                    rate = docs_processed / processing_time
                    output += f"📊 **处理速率：** {rate:.1f} 文档/秒\n\n"
                except ZeroDivisionError:
                    output += "📊 **处理速率：** 不可用\n\n"

        if update_mode == "incremental":
            output += "🔄 **模式：** 增量更新（保留现有文件）\n"

        output += "🚀 **下一步：** 前往“查询界面”标签页开始提问！"

    elif status == "error":
        error = progress_state.get("error", "未知错误")
        output += "\n💥 **发生错误**\n"
        output += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += (
            f"❌ **错误详情：** {error[:300]}{'...' if len(error) > 300 else ''}\n"
        )
        output += "\n🔧 **故障排除建议：**\n"
        output += "   • 检查您的 GitHub 令牌权限\n"
        output += "   • 验证仓库 URL 格式\n"
        output += "   • 确保所选文件存在\n"
        output += "   • 检查网络连接\n"

    return output

def create_query_interface() -> tuple:
    """创建查询界面组件。"""
    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(
                label="询问关于您的文档的问题",
                placeholder="如何实现自定义组件？有哪些可用的 API 端点？",
                lines=5,
                info="用自然语言提问关于您的文档的问题",
            )

            query_mode = gr.Radio(
                choices=["default", "text_search", "hybrid"],
                label="搜索策略",
                value="default",
                info="• default：语义相似度\n• text_search：关键词匹配\n• hybrid：组合方法",
            )

            query_button = gr.Button(
                "🚀 搜索文档", variant="primary", size="lg"
            )

            sources_output = gr.JSON(
                label="来源引用和元数据",
                value={"message": "来源文档摘录将显示在这里..."},
            )

        with gr.Column(scale=2):
            gr.Markdown("### 🤖 AI 助手回复")
            response_output = gr.Markdown(
                label="AI 助手回复",
                show_copy_button=True,
            )

    return query_input, query_mode, query_button, response_output, sources_output