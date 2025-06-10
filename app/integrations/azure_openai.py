"""
Azure OpenAI integration for FastAPI Azure Backend.

This module provides functions for interacting with Azure OpenAI.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

import openai
from openai import AsyncAzureOpenAI

from config import settings

logger = logging.getLogger(__name__)

# Global OpenAI client
client = None


async def initialize_openai_client() -> None:
    """
    Initialize the Azure OpenAI client.
    
    This function should be called during application startup.
    """
    global client
    
    logger.info("Initializing Azure OpenAI client")
    
    # Create the client
    client = AsyncAzureOpenAI(
        api_key=settings.OPENAI_API_KEY,
        api_version=settings.OPENAI_API_VERSION,
        azure_endpoint=settings.OPENAI_API_BASE
    )
    
    logger.info("Azure OpenAI client initialized successfully")


async def generate_chat_completion(
    messages: List[Dict[str, Any]],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stop: Optional[List[str]] = None
) -> Tuple[str, Dict[str, int]]:
    """
    Generate a chat completion.
    
    Args:
        messages: List of messages
        model: Model to use
        temperature: Temperature for sampling
        max_tokens: Maximum number of tokens to generate
        stop: Stop sequences
        
    Returns:
        Tuple[str, Dict[str, int]]: Generated completion and token usage
    """
    if not client:
        initialize_openai_client()
    
    # Use default model if not specified
    if not model:
        model = settings.AZURE_OPENAI_DEPLOYMENT_NAME
    
    # Prepare request parameters
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    if max_tokens:
        params["max_tokens"] = max_tokens
    
    if stop:
        params["stop"] = stop
    
    # Call the API
    response = await client.chat.completions.create(**params)
    
    # Extract completion
    completion = response.choices[0].message.content
    
    # Extract usage
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }
    
    return completion, usage


async def generate_summary(
    text: str,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None
) -> str:
    """
    Generate a summary of text.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of summary
        min_length: Minimum length of summary
        
    Returns:
        str: Generated summary
    """
    if not client:
        initialize_openai_client()
    
    # Prepare system message
    system_message = "You are a helpful assistant that summarizes text."
    if max_length and min_length:
        system_message += f" Create a summary between {min_length} and {max_length} words."
    elif max_length:
        system_message += f" Create a summary of at most {max_length} words."
    elif min_length:
        system_message += f" Create a summary of at least {min_length} words."
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
    ]
    
    # Generate completion
    summary, _ = await generate_chat_completion(messages)
    
    return summary


async def generate_embeddings(text: str) -> List[float]:
    """
    Generate embeddings for text.
    
    Args:
        text: Text to generate embeddings for
        
    Returns:
        List[float]: Generated embeddings
    """
    if not client:
        initialize_openai_client()
    
    # Call the API
    response = await client.embeddings.create(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
        input=text
    )
    
    # Extract embeddings
    embeddings = response.data[0].embedding
    
    return embeddings


async def generate_content(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> str:
    """
    Generate content based on a prompt.
    
    Args:
        prompt: Prompt text
        system_prompt: System prompt
        temperature: Temperature for sampling
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        str: Generated content
    """
    if not client:
        initialize_openai_client()
    
    # Prepare messages
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    # Generate completion
    content, _ = await generate_chat_completion(
        messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return content
