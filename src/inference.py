"""Strict local llama.cpp adapter; errors remain errors and are never replaced with canned advice."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.retrieval import LocalTfidfRetriever


class InferenceUnavailable(RuntimeError):
    pass


class SahayaPipeline:
    def __init__(self, retriever: LocalTfidfRetriever):
        self.retriever = retriever

    def answer(self, query: str, conversation: list[dict] | None = None) -> dict:
        if not query or not query.strip():
            raise ValueError("A question is required.")

        # Fold conversation buffer into the retrieval query (last 1-2 prior turns)
        retrieval_query = query.strip()
        recent_turns: list[dict] = []
        if conversation:
            recent_turns = [t for t in conversation if isinstance(t, dict)][-2:]
            prior_terms = [t.get("query", "") for t in recent_turns if t.get("query")]
            if prior_terms:
                retrieval_query = " ".join(prior_terms) + " " + retrieval_query

        results = self.retriever.search(retrieval_query)
        if not results or results[0].score <= 0:
            raise ValueError("No relevant official source was retrieved; Sahaya will not generate an ungrounded answer.")
        sources = [
            {"id": result.chunk["id"], "title": result.chunk["title"], "authority": result.chunk["authority"],
             "url": result.chunk["source_url"], "excerpt": result.chunk["text"], "score": round(result.score, 3)}
            for result in results if result.score > 0
        ]
        prompt = self._prompt(query, sources, recent_turns)
        answer = self._run_llama(prompt)
        return {"answer": answer, "source_chunks": sources, "confidence": self.retriever.confidence(results)}

    @staticmethod
    def _prompt(query: str, sources: list[dict], conversation: list[dict] | None = None) -> str:
        context = "\n\n".join(f"[{item['id']}] {item['excerpt']}" for item in sources)
        history = ""
        if conversation:
            history_lines = []
            for t in conversation[-2:]:
                q = str(t.get("query", "")).strip()
                a = str(t.get("answer", "")).strip()
                if q and a:
                    history_lines.append(f"PREVIOUS QUESTION: {q}\nPREVIOUS ANSWER: {a}")
            if history_lines:
                history = "\n\n" + "\n\n".join(history_lines) + "\n\n"
        return (
            "You are Sahaya, an offline assistant for ASHA workers. Answer only from the official source excerpts below. "
            "If the excerpts do not support an answer, say that the source does not contain enough information. "
            "Do not give dosage or diagnosis advice. Cite source IDs in square brackets. Keep the answer short.\n\n"
            f"OFFICIAL SOURCE EXCERPTS:\n{context}{history}\nQUESTION: {query}\nANSWER:"
        )

    @staticmethod
    def _run_llama(prompt: str) -> str:
        model_path = os.environ.get("SAHAYA_MODEL_PATH")
        executable = os.environ.get("SAHAYA_LLAMA_CLI", "llama-cli")
        if not model_path or not Path(model_path).is_file():
            raise InferenceUnavailable("Local Gemma GGUF is not configured. Set SAHAYA_MODEL_PATH to the approved local model file.")
        try:
            process = subprocess.run(
                [executable, "-m", model_path, "-p", prompt, "-n", "180", "--temp", "0"],
                capture_output=True, text=True, check=True, timeout=120
            )
        except FileNotFoundError as exc:
            raise InferenceUnavailable("llama.cpp CLI was not found. Set SAHAYA_LLAMA_CLI to its local executable.") from exc
        except subprocess.TimeoutExpired as exc:
            raise InferenceUnavailable("Local inference exceeded the 120-second demo limit; no answer was returned.") from exc
        except subprocess.CalledProcessError as exc:
            raise InferenceUnavailable(f"Local inference failed: {exc.stderr.strip() or 'unknown llama.cpp error'}") from exc
        answer = process.stdout.strip()
        if not answer:
            raise InferenceUnavailable("Local inference returned no answer.")
        return answer
