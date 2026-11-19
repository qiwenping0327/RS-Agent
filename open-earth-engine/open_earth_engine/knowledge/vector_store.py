"""
向量存储服务

基于 NumPy 实现的轻量级向量检索：
1. TF-IDF 词频统计
2. 词袋模型向量编码
3. 余弦相似度检索

不依赖 sentence-transformers 等外部模型，使用纯 NumPy 实现。
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("oea.vector_store")

CHINESE_PUNCTUATION = "，。！？、；：「」『』（）【】《》…—"
ENGLISH_PUNCTUATION = r".,!?;:'\"()[]{}<>-"


def tokenize(text: str) -> list[str]:
    """
    简单分词：中英文混合
    - 英文：按空格和标点分割，保留单词
    - 中文：按字符分割（简单的单字分词）
    """
    text = text.lower()
    
    for p in CHINESE_PUNCTUATION:
        text = text.replace(p, " ")
    for p in ENGLISH_PUNCTUATION:
        text = text.replace(p, " ")
    
    tokens = []
    for part in text.split():
        if re.match(r"^[a-zA-Z0-9_]+$", part):
            tokens.append(part)
        else:
            for char in part:
                if char.strip():
                    tokens.append(char)
    
    return tokens


@dataclass
class VectorDocument:
    doc_id: str
    text: str
    vector: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int = 0


class VectorStore:
    """
    基于 NumPy 的向量存储和检索服务

    使用 TF-IDF + 词袋模型：
    1. 构建词汇表（所有分词结果）
    2. 计算 TF-IDF 权重
    3. 生成文档向量
    4. 余弦相似度检索
    """

    def __init__(self, vocab_size: int = 5000):
        self.vocab_size = vocab_size
        self.vocab: dict[str, int] = {}
        self.vocab_counts: dict[str, int] = {}
        self.documents: dict[str, VectorDocument] = {}
        self.doc_count: int = 0
        self.idf: dict[str, float] = {}

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """计算词频 TF"""
        tf: dict[str, float] = {}
        total = len(tokens)
        if total == 0:
            return tf

        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        for token in tf:
            tf[token] = tf[token] / total

        return tf

    def _build_vocab(self, documents: list[tuple[str, str]]) -> None:
        """构建词汇表"""
        all_tokens: set[str] = set()
        doc_freq: dict[str, int] = {}

        for doc_id, text in documents:
            tokens = set(tokenize(text))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1
                all_tokens.add(token)

        self.doc_count = len(documents)

        sorted_tokens = sorted(all_tokens, key=lambda t: (-doc_freq.get(t, 0), t))
        selected_tokens = sorted_tokens[: self.vocab_size]

        self.vocab = {token: idx for idx, token in enumerate(selected_tokens)}
        self.vocab_counts = {k: doc_freq.get(k, 0) for k in selected_tokens}

        total_docs = max(self.doc_count, 1)
        self.idf = {
            token: math.log(total_docs / (doc_freq.get(token, 1) + 1))
            for token in selected_tokens
        }

    def _text_to_vector(self, text: str) -> tuple[np.ndarray, list[str]]:
        """将文本转换为向量"""
        tokens = tokenize(text)
        tf = self._compute_tf(tokens)

        vector_size = len(self.vocab)
        vector = np.zeros(vector_size, dtype=np.float32)

        for token, tf_value in tf.items():
            if token in self.vocab:
                idx = self.vocab[token]
                idf_value = self.idf.get(token, 0)
                vector[idx] = tf_value * idf_value

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector, tokens

    def build_index(self, documents: list[tuple[str, str, dict]]) -> None:
        """
        构建向量索引

        Args:
            documents: 文档列表，每个元素为 (doc_id, text, metadata)
        """
        self._build_vocab([(doc_id, text) for doc_id, text, _ in documents])

        self.documents = {}
        for doc_id, text, metadata in documents:
            vector, tokens = self._text_to_vector(text)
            self.documents[doc_id] = VectorDocument(
                doc_id=doc_id,
                text=text,
                vector=vector,
                metadata=metadata,
                token_count=len(tokens),
            )

        logger.info(f"Vector index built: {len(self.documents)} documents, vocab size: {len(self.vocab)}")

    def add_document(self, doc_id: str, text: str, metadata: dict = None) -> VectorDocument:
        """
        添加单个文档到索引
        """
        if doc_id not in self.documents:
            self.doc_count += 1

        tokens = tokenize(text)

        for token in set(tokens):
            if token not in self.vocab and len(self.vocab) < self.vocab_size:
                self.vocab[token] = len(self.vocab)
                self.vocab_counts[token] = 1
            elif token in self.vocab_counts:
                self.vocab_counts[token] += 1

        total_docs = max(self.doc_count, 1)
        self.idf = {
            token: math.log(total_docs / (self.vocab_counts.get(token, 1) + 1))
            for token in self.vocab
        }

        vector, _ = self._text_to_vector(text)
        doc = VectorDocument(
            doc_id=doc_id,
            text=text,
            vector=vector,
            metadata=metadata or {},
            token_count=len(tokens),
        )
        self.documents[doc_id] = doc

        return doc

    def remove_document(self, doc_id: str) -> bool:
        """
        从索引中删除文档
        """
        if doc_id in self.documents:
            del self.documents[doc_id]
            return True
        return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            min_score: 最小相似度阈值

        Returns:
            检索结果列表，按相似度降序排列
        """
        if not self.documents or not self.vocab:
            return []

        query_vector, _ = self._text_to_vector(query)

        if np.linalg.norm(query_vector) == 0:
            return []

        doc_ids = list(self.documents.keys())
        doc_vectors = np.vstack([self.documents[did].vector for did in doc_ids])

        similarities = np.dot(doc_vectors, query_vector)

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc_id = doc_ids[idx]
            score = float(similarities[idx])

            if score < min_score:
                continue

            doc = self.documents[doc_id]
            results.append({
                "doc_id": doc_id,
                "score": score,
                "text": doc.text,
                "metadata": doc.metadata,
            })

        return results

    def get_stats(self) -> dict[str, Any]:
        """获取索引统计信息"""
        return {
            "document_count": len(self.documents),
            "vocab_size": len(self.vocab),
            "average_token_count": (
                sum(d.token_count for d in self.documents.values()) / len(self.documents)
                if self.documents
                else 0
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """序列化"""
        return {
            "vocab_size": self.vocab_size,
            "vocab": self.vocab,
            "vocab_counts": self.vocab_counts,
            "doc_count": self.doc_count,
            "idf": self.idf,
            "documents": {
                doc_id: {
                    "doc_id": doc.doc_id,
                    "text": doc.text,
                    "vector": doc.vector.tolist(),
                    "metadata": doc.metadata,
                    "token_count": doc.token_count,
                }
                for doc_id, doc in self.documents.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorStore":
        """反序列化"""
        store = cls(vocab_size=data.get("vocab_size", 5000))
        store.vocab = data.get("vocab", {})
        store.vocab_counts = data.get("vocab_counts", {})
        store.doc_count = data.get("doc_count", 0)
        store.idf = data.get("idf", {})

        docs_data = data.get("documents", {})
        for doc_id, doc_data in docs_data.items():
            store.documents[doc_id] = VectorDocument(
                doc_id=doc_data["doc_id"],
                text=doc_data["text"],
                vector=np.array(doc_data["vector"], dtype=np.float32),
                metadata=doc_data.get("metadata", {}),
                token_count=doc_data.get("token_count", 0),
            )

        return store
