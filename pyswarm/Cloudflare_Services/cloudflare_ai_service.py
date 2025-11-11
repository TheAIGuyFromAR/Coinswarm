# cloudflare_ai_service.py
# Service class for interacting with Cloudflare Workers AI from Python
# Note: Direct AI binding not yet available in Python Workers, so this is used
# via HTTP calls or through TypeScript worker proxies

from typing import List, Dict, Any, Optional
import json


class CloudflareAIService:
    """
    Service for generating embeddings using Cloudflare Workers AI.

    This class provides methods to generate vector embeddings for semantic search,
    clustering, and similarity matching. Designed for financial news, sentiment,
    and temporal pattern matching.

    Recommended Models:
    - @cf/baai/bge-large-en-v1.5 (1024 dims) - Best for English financial content
    - @cf/baai/bge-m3 - Best for multilingual content

    Official docs: https://developers.cloudflare.com/workers-ai/models/
    """

    # Model specifications
    MODELS = {
        "bge-large-en": {
            "id": "@cf/baai/bge-large-en-v1.5",
            "dimensions": 1024,
            "description": "Best for English financial/crypto news",
            "batch_support": True
        },
        "bge-base-en": {
            "id": "@cf/baai/bge-base-en-v1.5",
            "dimensions": 768,
            "description": "Balanced performance for English",
            "batch_support": True
        },
        "bge-small-en": {
            "id": "@cf/baai/bge-small-en-v1.5",
            "dimensions": 384,
            "description": "Fast, compact embeddings",
            "batch_support": True
        },
        "bge-m3": {
            "id": "@cf/baai/bge-m3",
            "dimensions": 1024,  # Default dense dimension
            "description": "Multilingual, multi-functionality",
            "batch_support": True
        },
        "embeddinggemma": {
            "id": "@cf/google/embeddinggemma-300m",
            "dimensions": 768,  # Check actual dimensions
            "description": "Google's 100+ language model",
            "batch_support": True
        }
    }

    def __init__(self, ai_binding=None, model: str = "bge-small-en"):
        """
        Initialize with optional AI binding from Cloudflare Python Workers.

        Args:
            ai_binding: The AI binding object, e.g. bindings["AI"]
                       If None, will need to use HTTP proxy method
            model: Model key from MODELS dict (default: "bge-small-en" for speed)
        """
        self.ai = ai_binding
        self.model_key = model
        self.model_config = self.MODELS.get(model)

        if not self.model_config:
            raise ValueError(f"Unknown model: {model}. Choose from {list(self.MODELS.keys())}")

    @property
    def model_id(self) -> str:
        """Get the full model ID for Workers AI"""
        return self.model_config["id"]

    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions for this model"""
        return self.model_config["dimensions"]

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding vector from text.

        Args:
            text (str): The text to embed (news article, sentiment summary, etc.)

        Returns:
            List[float]: Vector embedding of specified dimensions
        """
        if not self.ai:
            raise RuntimeError("AI binding not available. Use HTTP proxy method or TypeScript worker.")

        result = await self.ai.run(self.model_id, {"text": [text]})

        # Workers AI returns {"data": [[vector]]} for batch, or {"data": [vector]} for single
        if "data" in result:
            embeddings = result["data"]
            if isinstance(embeddings[0], list):
                return embeddings[0]  # First embedding from batch
            return embeddings

        raise RuntimeError(f"Unexpected AI response format: {result}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single batch request.
        More efficient than multiple single requests.

        Args:
            texts (List[str]): List of texts to embed

        Returns:
            List[List[float]]: List of vector embeddings
        """
        if not self.ai:
            raise RuntimeError("AI binding not available. Use HTTP proxy method or TypeScript worker.")

        if not self.model_config["batch_support"]:
            raise RuntimeError(f"Model {self.model_key} does not support batch processing")

        result = await self.ai.run(self.model_id, {"text": texts})

        if "data" in result:
            return result["data"]

        raise RuntimeError(f"Unexpected AI response format: {result}")

    async def embed_time_period_snapshot(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate embedding for a time period snapshot containing multiple data types.
        Combines news, sentiment, technical indicators into a single searchable representation.

        Args:
            snapshot_data (dict): Dictionary containing:
                - timestamp: Unix timestamp or ISO date
                - news_summary: Text summary of key news
                - sentiment_score: Overall sentiment (-1 to 1)
                - technical_setup: Description of technical indicators
                - social_summary: Social media sentiment summary
                - market_conditions: Overall market state description
                - metadata: Any additional context

        Returns:
            dict: Snapshot with added 'embedding' field
        """
        # Build a comprehensive text representation of the time period
        text_components = []

        if "news_summary" in snapshot_data:
            text_components.append(f"News: {snapshot_data['news_summary']}")

        if "sentiment_score" in snapshot_data:
            sentiment = snapshot_data["sentiment_score"]
            sentiment_text = "bullish" if sentiment > 0.2 else "bearish" if sentiment < -0.2 else "neutral"
            text_components.append(f"Sentiment: {sentiment_text} ({sentiment:.2f})")

        if "technical_setup" in snapshot_data:
            text_components.append(f"Technical: {snapshot_data['technical_setup']}")

        if "social_summary" in snapshot_data:
            text_components.append(f"Social: {snapshot_data['social_summary']}")

        if "market_conditions" in snapshot_data:
            text_components.append(f"Market: {snapshot_data['market_conditions']}")

        # Combine into single text for embedding
        combined_text = " | ".join(text_components)

        # Generate embedding
        embedding = await self.generate_embedding(combined_text)

        # Return snapshot with embedding
        return {
            **snapshot_data,
            "embedding": embedding,
            "embedding_text": combined_text,  # Store for debugging
            "embedding_model": self.model_id,
            "embedding_dimensions": len(embedding)
        }

    def format_for_vectorize(self,
                            snapshot_data: Dict[str, Any],
                            vector_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format an embedded snapshot for insertion into Cloudflare Vectorize.

        Args:
            snapshot_data: Snapshot with 'embedding' field
            vector_id: Optional custom ID (defaults to timestamp)

        Returns:
            dict: Formatted for Vectorize upsert with id, values, metadata
        """
        if "embedding" not in snapshot_data:
            raise ValueError("snapshot_data must have 'embedding' field. Call embed_time_period_snapshot first.")

        # Use timestamp as ID if not provided
        if not vector_id:
            vector_id = str(snapshot_data.get("timestamp", "unknown"))

        # Extract metadata (everything except the embedding)
        metadata = {k: v for k, v in snapshot_data.items() if k != "embedding"}

        return {
            "id": vector_id,
            "values": snapshot_data["embedding"],
            "metadata": metadata
        }

    @staticmethod
    def get_model_info(model_key: str = None) -> Dict[str, Any]:
        """
        Get information about available models.

        Args:
            model_key: Specific model to get info for, or None for all

        Returns:
            dict: Model information
        """
        if model_key:
            return CloudflareAIService.MODELS.get(model_key, {})
        return CloudflareAIService.MODELS
