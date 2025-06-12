from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import settings

router = APIRouter()

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    embedding: list[float]
    model: str

from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=settings.OPENAI_API_KEY,
    api_version="2023-05-15",  # Or the version you're using
    azure_endpoint=settings.OPENAI_API_BASE
)


@router.post("/embed", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """
    Generate OpenAI embedding for the given text.
    """
    try:
        response = client.embeddings.create(
            input=request.text,
            model=settings.OPENAI_EMBEDDING_DEPLOYMENT,
        )
        embedding = response.data[0].embedding
        model = response.model
        return EmbeddingResponse(embedding=embedding, model=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
