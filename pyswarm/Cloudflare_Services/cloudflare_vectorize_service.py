# cloudflare_vectorize_service.py
# Service class for interacting with Cloudflare Vectorize from Python Workers

from typing import List, Dict, Any, Optional


class CloudflareVectorizeService:
    """
    Service for storing and querying vector embeddings in Cloudflare Vectorize.

    Vectorize is Cloudflare's vector database for semantic search and similarity matching.
    Perfect for finding similar time periods based on market conditions, news, and sentiment.

    Official docs: https://developers.cloudflare.com/vectorize/

    Usage:
        # In your WorkerEntrypoint fetch handler:
        service = CloudflareVectorizeService(bindings["VECTORIZE"])

        # Store embeddings
        await service.upsert(vectors)

        # Find similar time periods
        matches = await service.query(current_embedding, top_k=10)
    """

    def __init__(self, vectorize_binding):
        """
        Initialize with the Vectorize binding from Cloudflare Python Workers.

        Args:
            vectorize_binding: The Vectorize binding object, e.g. bindings["VECTORIZE"]
        """
        self.vectorize = vectorize_binding

    async def upsert(self, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in the index.

        Args:
            vectors (list): List of vector objects, each containing:
                - id (str): Unique identifier (e.g., timestamp)
                - values (list[float]): The embedding vector
                - metadata (dict, optional): Associated data for filtering/display

        Example:
            vectors = [
                {
                    "id": "2024-01-15T12:00:00Z",
                    "values": [0.1, 0.2, ...],  # 1024-dim embedding
                    "metadata": {
                        "timestamp": 1705320000,
                        "sentiment_score": 0.65,
                        "news_summary": "Bitcoin rally...",
                        "technical_setup": "Bullish momentum..."
                    }
                }
            ]

        Returns:
            dict: Response with count of vectors upserted and any errors
        """
        return await self.vectorize.upsert(vectors)

    async def query(self,
                    vector: List[float],
                    top_k: int = 10,
                    filter: Optional[Dict[str, Any]] = None,
                    return_values: bool = False,
                    return_metadata: bool = True) -> Dict[str, Any]:
        """
        Find the most similar vectors to the query vector.

        Args:
            vector (list[float]): Query embedding vector
            top_k (int): Number of similar results to return (default: 10)
            filter (dict, optional): Metadata filters to narrow results
            return_values (bool): Whether to return the vector values (default: False)
            return_metadata (bool): Whether to return metadata (default: True)

        Returns:
            dict: Response containing:
                - matches: List of similar vectors with id, score, metadata
                - count: Number of matches returned

        Example:
            # Find similar time periods
            results = await service.query(
                vector=current_embedding,
                top_k=5,
                filter={"sentiment_score": {"$gte": 0.5}}  # Only bullish periods
            )

            for match in results["matches"]:
                print(f"Similar period: {match['id']}")
                print(f"Similarity: {match['score']}")
                print(f"Context: {match['metadata']['news_summary']}")
        """
        query_params = {
            "vector": vector,
            "topK": top_k,
            "returnValues": return_values,
            "returnMetadata": return_metadata
        }

        if filter:
            query_params["filter"] = filter

        return await self.vectorize.query(**query_params)

    async def get_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve specific vectors by their IDs.

        Args:
            ids (list[str]): List of vector IDs to retrieve

        Returns:
            dict: Response with vectors matching the IDs
        """
        return await self.vectorize.getByIds(ids)

    async def delete_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        """
        Delete specific vectors by their IDs.

        Args:
            ids (list[str]): List of vector IDs to delete

        Returns:
            dict: Response confirming deletion
        """
        return await self.vectorize.deleteByIds(ids)

    async def find_similar_time_periods(self,
                                       current_snapshot: Dict[str, Any],
                                       top_k: int = 10,
                                       min_similarity: float = 0.7,
                                       exclude_recent_days: int = 30) -> List[Dict[str, Any]]:
        """
        High-level method to find historical time periods similar to current conditions.

        Args:
            current_snapshot (dict): Must contain 'embedding' field
            top_k (int): Number of similar periods to find
            min_similarity (float): Minimum similarity score (0-1)
            exclude_recent_days (int): Don't include periods within this many days

        Returns:
            list: Similar time periods with metadata and similarity scores
        """
        if "embedding" not in current_snapshot:
            raise ValueError("current_snapshot must have 'embedding' field")

        # Build filter to exclude recent periods if timestamp provided
        metadata_filter = None
        if "timestamp" in current_snapshot and exclude_recent_days > 0:
            cutoff_timestamp = current_snapshot["timestamp"] - (exclude_recent_days * 24 * 60 * 60)
            metadata_filter = {
                "timestamp": {"$lt": cutoff_timestamp}
            }

        # Query for similar vectors
        results = await self.query(
            vector=current_snapshot["embedding"],
            top_k=top_k * 2,  # Get extra to filter by similarity threshold
            filter=metadata_filter,
            return_metadata=True
        )

        # Filter by minimum similarity and format results
        similar_periods = []
        for match in results.get("matches", []):
            if match["score"] >= min_similarity:
                similar_periods.append({
                    "id": match["id"],
                    "similarity_score": match["score"],
                    "metadata": match.get("metadata", {}),
                    "timestamp": match.get("metadata", {}).get("timestamp"),
                    "news_summary": match.get("metadata", {}).get("news_summary"),
                    "technical_setup": match.get("metadata", {}).get("technical_setup"),
                    "sentiment_score": match.get("metadata", {}).get("sentiment_score")
                })

                if len(similar_periods) >= top_k:
                    break

        return similar_periods

    async def get_index_info(self) -> Dict[str, Any]:
        """
        Get information about the Vectorize index.

        Returns:
            dict: Index configuration and statistics
        """
        return await self.vectorize.describe()


class VectorizeQueryBuilder:
    """
    Helper class to build complex Vectorize metadata filters.

    Supports operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
    """

    @staticmethod
    def equals(field: str, value: Any) -> Dict:
        """Field equals value"""
        return {field: {"$eq": value}}

    @staticmethod
    def not_equals(field: str, value: Any) -> Dict:
        """Field not equals value"""
        return {field: {"$ne": value}}

    @staticmethod
    def greater_than(field: str, value: float) -> Dict:
        """Field greater than value"""
        return {field: {"$gt": value}}

    @staticmethod
    def greater_than_or_equal(field: str, value: float) -> Dict:
        """Field greater than or equal to value"""
        return {field: {"$gte": value}}

    @staticmethod
    def less_than(field: str, value: float) -> Dict:
        """Field less than value"""
        return {field: {"$lt": value}}

    @staticmethod
    def less_than_or_equal(field: str, value: float) -> Dict:
        """Field less than or equal to value"""
        return {field: {"$lte": value}}

    @staticmethod
    def in_list(field: str, values: List[Any]) -> Dict:
        """Field value in list"""
        return {field: {"$in": values}}

    @staticmethod
    def not_in_list(field: str, values: List[Any]) -> Dict:
        """Field value not in list"""
        return {field: {"$nin": values}}

    @staticmethod
    def sentiment_bullish(threshold: float = 0.2) -> Dict:
        """Filter for bullish sentiment"""
        return VectorizeQueryBuilder.greater_than_or_equal("sentiment_score", threshold)

    @staticmethod
    def sentiment_bearish(threshold: float = -0.2) -> Dict:
        """Filter for bearish sentiment"""
        return VectorizeQueryBuilder.less_than_or_equal("sentiment_score", threshold)

    @staticmethod
    def time_range(start_timestamp: int, end_timestamp: int) -> Dict:
        """Filter for time range"""
        return {
            "timestamp": {
                "$gte": start_timestamp,
                "$lte": end_timestamp
            }
        }
