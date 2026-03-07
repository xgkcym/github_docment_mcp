# cross_encoder_reranker.py - 优化版

import os
from typing import List
from llama_index.core.schema import NodeWithScore
from sentence_transformers import CrossEncoder
import torch

from core.settings import settings

os.environ["HF_TOKEN"] = settings.hf_token


class CrossEncoderReranker:
    def __init__(
            self,
            model_name: str = settings.cross_encoder_model,
            batch_size: int = 8,  # 关键：批处理
            max_length: int = 512,  # 截断长度，默认可能太长
            device: str = None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # - BAAI/bge-reranker-large(推荐，中文友好)
        # - BAAI/bge-reranker-base(轻量版)
        # - cross-encoder/ms-marco-MiniLM-L-6-v2(英文)
        self.model = CrossEncoder(
            model_name,
            device=self.device,
            max_length=max_length,  # 减少 token 数，加速
        )
        self.batch_size = batch_size
        self.model_name = model_name

    def rerank(self, query: str, nodes: List[NodeWithScore], top_k: int = 20) -> List[NodeWithScore]:
        if not nodes:
            return nodes

        # 准备输入对
        pairs = [[query, node.get_content()] for node in nodes]

        # 关键：批处理推理（原代码是串行）
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,  # 一次处理 8 条
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        # 排序
        reranked = [
            NodeWithScore(node=nodes[i].node, score=float(scores[i]))
            for i in range(len(nodes))
        ]
        reranked.sort(key=lambda x: x.score, reverse=True)

        return reranked[:top_k]