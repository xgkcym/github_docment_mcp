from typing import Sequence, Any, List

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
        interactive=True
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


