"""
Azure Translator integration for FastAPI Azure Backend.

This module provides functions for interacting with Azure Translator.
"""

import logging
import uuid
import json
from typing import Optional, List, Dict, Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def translate_text(
    text: str,
    target_language: str,
    source_language: Optional[str] = None
) -> str:
    """
    Translate text using Azure Translator.
    
    Args:
        text: Text to translate
        target_language: Target language code
        source_language: Source language code (auto-detect if None)
        
    Returns:
        str: Translated text
    """
    # Prepare request
    url = f"{settings.AZURE_TRANSLATOR_ENDPOINT}/translate"
    
    params = {
        "api-version": "3.0",
        "to": target_language
    }
    
    if source_language:
        params["from"] = source_language
    
    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": settings.AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }
    
    body = [{
        "text": text
    }]
    
    # Send request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            params=params,
            headers=headers,
            json=body,
            timeout=30.0
        )
        
        response.raise_for_status()
        result = response.json()
    
    # Extract translated text
    translated_text = result[0]["translations"][0]["text"]
    
    return translated_text


async def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the language of text.
    
    Args:
        text: Text to detect language for
        
    Returns:
        Dict[str, Any]: Detected language information
    """
    # Prepare request
    url = f"{settings.AZURE_TRANSLATOR_ENDPOINT}/detect"
    
    params = {
        "api-version": "3.0"
    }
    
    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": settings.AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }
    
    body = [{
        "text": text
    }]
    
    # Send request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            params=params,
            headers=headers,
            json=body,
            timeout=30.0
        )
        
        response.raise_for_status()
        result = response.json()
    
    # Extract language information
    language_info = result[0]
    
    return language_info


async def translate_document(
    document_content: bytes,
    document_type: str,
    target_language: str,
    source_language: Optional[str] = None
) -> bytes:
    """
    Translate a document using Azure Translator.
    
    Args:
        document_content: Document content
        document_type: Document type (e.g., "text/html", "application/pdf")
        target_language: Target language code
        source_language: Source language code (auto-detect if None)
        
    Returns:
        bytes: Translated document content
    """
    # In a real implementation, this would use the Document Translation API
    # For this example, we'll just extract text and translate it
    
    # Extract text from document (simplified)
    text = document_content.decode("utf-8", errors="ignore")
    
    # Translate text
    translated_text = await translate_text(text, target_language, source_language)
    
    # Return as bytes
    return translated_text.encode("utf-8")


async def get_supported_languages() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get supported languages.
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Supported languages
    """
    # Prepare request
    url = f"{settings.AZURE_TRANSLATOR_ENDPOINT}/languages"
    
    params = {
        "api-version": "3.0",
        "scope": "translation"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Send request
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            headers=headers,
            timeout=30.0
        )
        
        response.raise_for_status()
        result = response.json()
    
    return result



async def initialize_translator_client() -> None:
    """
    Initialize the Azure Translator client.
    
    This function doesn't do much for the current httpx-based implementation,
    but serves as a placeholder for potential future SDK integrations.
    """
    logger.info("Initializing Azure Translator client")
    # No specific client to initialize for httpx-based calls
    logger.info("Azure Translator client initialized successfully")


def close_translator_client() -> None:
    """
    Close the Azure Translator client.
    
    This function doesn't do much for the current httpx-based implementation,
    but serves as a placeholder for potential future SDK integrations.
    """
    logger.info("Closing Azure Translator client")
    # No specific client to close for httpx-based calls
    logger.info("Azure Translator client closed successfully")


