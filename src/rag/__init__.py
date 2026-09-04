"""RAG package: Vector store, retriever, prompt builder, conversation buffer, and answer pipeline."""
from .conversation import ConversationBuffer, Turn, contextualize_query
from .pipeline import RAGPipeline, answer_query, corpus_stats, get_pipeline
from .prompt import INSUFFICIENT_INFO_ANSWER, SYSTEM_PROMPT, build_prompt
from .retriever import EmbeddingRetriever, RetrievedChunk, Retriever, TfidfRetriever, get_retriever

__all__ = [
    "ConversationBuffer",
    "EmbeddingRetriever",
    "INSUFFICIENT_INFO_ANSWER",
    "RAGPipeline",
    "RetrievedChunk",
    "Retriever",
    "SYSTEM_PROMPT",
    "TfidfRetriever",
    "Turn",
    "answer_query",
    "build_prompt",
    "contextualize_query",
    "corpus_stats",
    "get_pipeline",
    "get_retriever",
]
