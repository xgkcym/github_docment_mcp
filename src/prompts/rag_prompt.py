

def query_prompt(query:str,doc_str:str)->str:
    return f"""
    你是一个专业的技术文档助手。基于以下检索到的文档片段，回答用户的问题。
    
    文档片段：
    {doc_str}

    用户问题：{query}

    请给出准确、简洁的回答。如果文档中没有相关信息，请明确说明"根据现有文档无法回答"。

    回答：
    """
