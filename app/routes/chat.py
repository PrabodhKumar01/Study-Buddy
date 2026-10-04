"""Chat and question-answering routes.

Handles user study questions, validates inputs, queries the RAG pipeline,
and returns synthesized answers with document/page citations.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.rag import rag_service

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    """Input payload for asking study questions."""

    question: str = Field(
        ...,
        min_length=1,
        description="The user's question about their uploaded study materials.",
        examples=["What is deadlock?"],
    )


class SourceItem(BaseModel):
    """Source citation indicating document and page location."""

    document: str
    page: int
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None


class ChatResponse(BaseModel):
    """Response containing synthesized answer and source citations."""

    answer: str
    sources: List[SourceItem] = []


@router.post("", response_model=ChatResponse, summary="Ask a question about uploaded study materials")
@router.post("/", include_in_schema=False, response_model=ChatResponse)
async def chat_with_study_materials(request: ChatRequest):
    """Process a user study question using the RAG pipeline.

    1. Embeds question.
    2. Searches local vector store for relevant chunks.
    3. Instructs local LLM to answer strictly from the context.
    4. Returns answer and source citations.
    """
    clean_question = request.question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The question cannot be empty or just whitespace.",
        )

    try:
        result = await rag_service.answer_query(clean_question)
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while answering your question: {str(exc)}",
        )
