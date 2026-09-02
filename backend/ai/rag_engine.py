"""
ai/rag_engine.py — Graph RAG (Retrieval-Augmented Generation) engine.
Combines Neo4j graph context with ChromaDB vector search and an Ollama
local LLM to answer investigator natural-language queries.
"""

import logging
from typing import Any, Dict, List, Optional

from graph.neo4j_client import neo4j_client
from config import settings

logger = logging.getLogger(__name__)

# Lazy-load heavy dependencies
_chroma_client = None
_collection    = None
_llm           = None
_embeddings    = None


def _get_chroma():
    global _chroma_client, _collection
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.HttpClient(host=settings.chroma_url.replace("http://", "").split(":")[0],
                                              port=int(settings.chroma_url.split(":")[-1]))
        _collection = _chroma_client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_ollama import OllamaLLM
        _llm = OllamaLLM(base_url=settings.ollama_url, model=settings.ollama_model)
    return _llm


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        from sentence_transformers import SentenceTransformer
        _embeddings = SentenceTransformer("all-MiniLM-L6-v2")
    return _embeddings


class RAGEngine:
    """Retrieval-Augmented Generation over the criminal knowledge graph."""

    async def add_document(self, text: str, doc_id: str, metadata: Dict = None):
        """Embed and store a document chunk in ChromaDB."""
        try:
            collection = _get_chroma()
            emb_model  = _get_embeddings()
            embedding  = emb_model.encode([text])[0].tolist()
            collection.upsert(
                documents=[text],
                embeddings=[embedding],
                ids=[doc_id],
                metadatas=[metadata or {}],
            )
        except Exception as e:
            logger.warning(f"ChromaDB add failed: {e}")

    async def retrieve_context(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve most relevant document chunks from ChromaDB."""
        try:
            collection = _get_chroma()
            emb_model  = _get_embeddings()
            q_emb      = emb_model.encode([query])[0].tolist()
            results    = collection.query(query_embeddings=[q_emb], n_results=top_k)
            return results.get("documents", [[]])[0]
        except Exception as e:
            logger.warning(f"ChromaDB retrieve failed: {e}")
            return []

    async def retrieve_graph_context(self, query: str) -> str:
        """
        Search the Neo4j graph for entities matching the query and
        return a structured text summary of their connections.
        """
        # Search entities
        entity_records = await neo4j_client.search_entities(query, limit=5)
        if not entity_records:
            return ""

        context_parts = []
        for rec in entity_records:
            n = rec.get("n", {})
            entity_id   = n.get("id", "")
            entity_name = n.get("name", "Unknown")
            labels      = rec.get("labels", [])

            if not entity_id:
                continue

            # Get neighbors
            neighbors = await neo4j_client.get_neighbors(entity_id, depth=1)
            neighbor_names = [nd.get("name", "") for nd in neighbors.get("nodes", [])
                              if nd.get("id") != entity_id][:10]

            context_parts.append(
                f"• {entity_name} [{', '.join(labels)}]:\n"
                f"  Known connections: {', '.join(neighbor_names) or 'None found'}\n"
                f"  Risk level: {n.get('risk_level', 'UNKNOWN')}\n"
                f"  PageRank: {n.get('pagerank', 'N/A')}"
            )

        return "\n\n".join(context_parts)

    async def answer(self, question: str) -> Dict[str, Any]:
        """
        Answer an investigator question using Graph RAG.

        Steps:
        1. Retrieve relevant documents from ChromaDB (vector search)
        2. Retrieve graph context from Neo4j (entity + relationship info)
        3. Combine context and query the LLM
        4. Return answer with cited sources
        """
        try:
            # Step 1: Document context
            doc_chunks = await self.retrieve_context(question, top_k=4)

            # Step 2: Graph context
            graph_ctx = await self.retrieve_graph_context(question)

            # Step 3: Build prompt
            doc_context = "\n---\n".join(doc_chunks) if doc_chunks else "No documents found."
            prompt = f"""You are an expert criminal intelligence analyst assistant.
Answer the investigator's question based ONLY on the provided intelligence context.
Be concise, factual, and cite specific entities when possible.
If you cannot answer from the context, say "Insufficient intelligence data."

=== GRAPH INTELLIGENCE CONTEXT ===
{graph_ctx or "No graph data available."}

=== DOCUMENT INTELLIGENCE CONTEXT ===
{doc_context}

=== INVESTIGATOR QUESTION ===
{question}

=== ANALYTICAL RESPONSE ==="""

            llm = _get_llm()
            answer_text = llm.invoke(prompt)

            return {
                "question": question,
                "answer": answer_text,
                "graph_entities_used": graph_ctx[:500] if graph_ctx else "",
                "documents_used": len(doc_chunks),
                "model": settings.ollama_model,
            }

        except Exception as e:
            logger.error(f"RAG answer failed: {e}")
            return {
                "question": question,
                "answer": f"LLM unavailable: {str(e)}. Ensure Ollama is running with model '{settings.ollama_model}'.",
                "graph_entities_used": "",
                "documents_used": 0,
                "model": settings.ollama_model,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
rag_engine = RAGEngine()
