import os
from typing import List, Dict, Any
from llama_index.core.schema import NodeWithScore, TextNode
import numpy as np
from sentence_transformers import CrossEncoder

from core.settings import settings
os.environ["HF_TOKEN"] = settings.hf_token

class CrossEncoderReranker:
    """基于 Cross-Encoder 的重排序器"""

    def __init__(self, model_name: str = settings.cross_encoder_model):
        """
        可选模型：
        - BAAI/bge-reranker-large (推荐，中文友好)
        - BAAI/bge-reranker-base (轻量版)
        - cross-encoder/ms-marco-MiniLM-L-6-v2 (英文)
        """
        self.model = CrossEncoder(model_name)
        self.model_name = model_name

    def rerank(self, query: str, nodes: List[NodeWithScore], top_k: int = settings.cross_encoder_top_k) -> List[NodeWithScore]:
        """对检索结果进行重排序"""
        if not nodes:
            return nodes

        # 准备输入对
        pairs = [[query, node.get_content()] for node in nodes]

        # 预测相关性分数
        scores = self.model.predict(pairs)

        # 创建新的节点列表（带新分数）
        reranked_nodes = []
        for node, score in zip(nodes, scores):
            # 使用 reranker 分数（通常范围更大，更准确）
            new_node = NodeWithScore(
                node=node.node,
                score=float(score)  # Cross-Encoder 给出的相关性分数
            )
            reranked_nodes.append(new_node)

        # 按新分数排序
        reranked_nodes.sort(key=lambda x: x.score, reverse=True)

        return reranked_nodes[:top_k]

