/**
 * Cloudflare Workers AI Embedding Worker
 *
 * TypeScript worker that generates embeddings using Workers AI.
 * Designed to work with Python workers via HTTP or Queue messages.
 *
 * Features:
 * - Single and batch embedding generation
 * - Automatic Vectorize storage
 * - Time period snapshot embedding
 * - Similar period search
 */

// Type definitions
interface Env {
  AI: Ai;
  VECTORIZE: VectorizeIndex;
  DB: D1Database;
}

interface EmbeddingRequest {
  text: string | string[];
  model?: string;
  store_in_vectorize?: boolean;
  metadata?: Record<string, any>;
}

interface TimeSnapshotRequest {
  timestamp: number | string;
  news_summary?: string;
  sentiment_score?: number;
  technical_setup?: string;
  social_summary?: string;
  market_conditions?: string;
  metadata?: Record<string, any>;
  store_in_vectorize?: boolean;
}

interface SimilaritySearchRequest {
  current_snapshot: TimeSnapshotRequest;
  top_k?: number;
  min_similarity?: float;
  exclude_recent_days?: number;
  filter?: Record<string, any>;
}

// Model configurations
const MODELS = {
  "bge-large-en": {
    id: "@cf/baai/bge-large-en-v1.5",
    dimensions: 1024,
    description: "Best for English financial/crypto news"
  },
  "bge-base-en": {
    id: "@cf/baai/bge-base-en-v1.5",
    dimensions: 768,
    description: "Balanced performance"
  },
  "bge-small-en": {
    id: "@cf/baai/bge-small-en-v1.5",
    dimensions: 384,
    description: "Fast and compact"
  },
  "bge-m3": {
    id: "@cf/baai/bge-m3",
    dimensions: 1024,
    description: "Multilingual support"
  },
  "embeddinggemma": {
    id: "@cf/google/embeddinggemma-300m",
    dimensions: 768,
    description: "Google's latest multilingual model"
  }
};

// Using bge-large-en for MAXIMUM ACCURACY (1024 dims)
// Best semantic understanding for complex market narratives
// Query time: ~60-90ms (perfect for low-frequency queries where accuracy matters most)
// Note: For high-frequency agent memory, consider bge-base-en or bge-small-en
const DEFAULT_MODEL = "bge-large-en";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // CORS headers for cross-origin requests
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      // Route: GET /models - List available models
      if (path === '/models' && request.method === 'GET') {
        return Response.json({ models: MODELS }, { headers: corsHeaders });
      }

      // Route: POST /embed - Generate embeddings
      if (path === '/embed' && request.method === 'POST') {
        const body: EmbeddingRequest = await request.json();
        const result = await generateEmbedding(env, body);
        return Response.json(result, { headers: corsHeaders });
      }

      // Route: POST /embed/snapshot - Embed time period snapshot
      if (path === '/embed/snapshot' && request.method === 'POST') {
        const body: TimeSnapshotRequest = await request.json();
        const result = await embedTimeSnapshot(env, body);
        return Response.json(result, { headers: corsHeaders });
      }

      // Route: POST /search/similar - Find similar time periods
      if (path === '/search/similar' && request.method === 'POST') {
        const body: SimilaritySearchRequest = await request.json();
        const result = await findSimilarPeriods(env, body);
        return Response.json(result, { headers: corsHeaders });
      }

      // Route: GET /health - Health check
      if (path === '/health' || path === '/') {
        return Response.json({
          status: 'ok',
          service: 'embedding-worker',
          models: Object.keys(MODELS),
          default_model: DEFAULT_MODEL
        }, { headers: corsHeaders });
      }

      return Response.json(
        { error: 'Not found', available_routes: ['/models', '/embed', '/embed/snapshot', '/search/similar', '/health'] },
        { status: 404, headers: corsHeaders }
      );

    } catch (error: any) {
      console.error('Error:', error);
      return Response.json(
        { error: error.message || 'Internal server error' },
        { status: 500, headers: corsHeaders }
      );
    }
  }
};

/**
 * Generate embeddings from text
 */
async function generateEmbedding(env: Env, request: EmbeddingRequest): Promise<any> {
  const model = request.model || DEFAULT_MODEL;
  const modelConfig = MODELS[model as keyof typeof MODELS];

  if (!modelConfig) {
    throw new Error(`Unknown model: ${model}. Available: ${Object.keys(MODELS).join(', ')}`);
  }

  // Prepare input - ensure it's an array
  const texts = Array.isArray(request.text) ? request.text : [request.text];

  // Run AI model
  const response = await env.AI.run(modelConfig.id, { text: texts });

  // Extract embeddings
  const embeddings = response.data;

  // If store_in_vectorize is true, store them
  if (request.store_in_vectorize && env.VECTORIZE) {
    const vectors = embeddings.map((embedding: number[], index: number) => ({
      id: `embed_${Date.now()}_${index}`,
      values: embedding,
      metadata: {
        ...request.metadata,
        text: texts[index],
        model: modelConfig.id,
        timestamp: Date.now()
      }
    }));

    await env.VECTORIZE.upsert(vectors);
  }

  return {
    success: true,
    embeddings: embeddings,
    model: modelConfig.id,
    dimensions: modelConfig.dimensions,
    count: embeddings.length
  };
}

/**
 * Embed a time period snapshot combining multiple data sources
 */
async function embedTimeSnapshot(env: Env, snapshot: TimeSnapshotRequest): Promise<any> {
  // Build comprehensive text representation
  const textComponents: string[] = [];

  if (snapshot.news_summary) {
    textComponents.push(`News: ${snapshot.news_summary}`);
  }

  if (snapshot.sentiment_score !== undefined) {
    const sentiment = snapshot.sentiment_score > 0.2 ? 'bullish' :
                     snapshot.sentiment_score < -0.2 ? 'bearish' : 'neutral';
    textComponents.push(`Sentiment: ${sentiment} (${snapshot.sentiment_score.toFixed(2)})`);
  }

  if (snapshot.technical_setup) {
    textComponents.push(`Technical: ${snapshot.technical_setup}`);
  }

  if (snapshot.social_summary) {
    textComponents.push(`Social: ${snapshot.social_summary}`);
  }

  if (snapshot.market_conditions) {
    textComponents.push(`Market: ${snapshot.market_conditions}`);
  }

  const combinedText = textComponents.join(' | ');

  if (!combinedText) {
    throw new Error('Snapshot must contain at least one text field');
  }

  // Generate embedding
  const modelConfig = MODELS[DEFAULT_MODEL];
  const response = await env.AI.run(modelConfig.id, { text: [combinedText] });
  const embedding = response.data[0];

  // Prepare vector ID
  const vectorId = typeof snapshot.timestamp === 'string'
    ? snapshot.timestamp
    : new Date(snapshot.timestamp).toISOString();

  // Store in Vectorize if requested
  if (snapshot.store_in_vectorize && env.VECTORIZE) {
    await env.VECTORIZE.upsert([{
      id: vectorId,
      values: embedding,
      metadata: {
        timestamp: typeof snapshot.timestamp === 'number' ? snapshot.timestamp : new Date(snapshot.timestamp).getTime(),
        news_summary: snapshot.news_summary,
        sentiment_score: snapshot.sentiment_score,
        technical_setup: snapshot.technical_setup,
        social_summary: snapshot.social_summary,
        market_conditions: snapshot.market_conditions,
        embedding_text: combinedText,
        model: modelConfig.id,
        ...snapshot.metadata
      }
    }]);
  }

  return {
    success: true,
    id: vectorId,
    embedding: embedding,
    embedding_text: combinedText,
    model: modelConfig.id,
    dimensions: embedding.length,
    stored_in_vectorize: snapshot.store_in_vectorize || false
  };
}

/**
 * Find similar historical time periods
 */
async function findSimilarPeriods(env: Env, request: SimilaritySearchRequest): Promise<any> {
  // First, embed the current snapshot
  const currentEmbedding = await embedTimeSnapshot(env, {
    ...request.current_snapshot,
    store_in_vectorize: false  // Don't store the query
  });

  // Prepare query parameters
  const topK = request.top_k || 10;
  const minSimilarity = request.min_similarity || 0.7;

  // Build filter to exclude recent periods if specified
  let filter = request.filter || {};

  if (request.exclude_recent_days && request.current_snapshot.timestamp) {
    const currentTimestamp = typeof request.current_snapshot.timestamp === 'number'
      ? request.current_snapshot.timestamp
      : new Date(request.current_snapshot.timestamp).getTime();

    const cutoffTimestamp = currentTimestamp - (request.exclude_recent_days * 24 * 60 * 60 * 1000);

    filter = {
      ...filter,
      timestamp: { $lt: cutoffTimestamp }
    };
  }

  // Query Vectorize for similar vectors
  const queryParams: any = {
    vector: currentEmbedding.embedding,
    topK: topK * 2,  // Get extras to filter by similarity
    returnMetadata: true,
    returnValues: false
  };

  if (Object.keys(filter).length > 0) {
    queryParams.filter = filter;
  }

  const results = await env.VECTORIZE.query(queryParams);

  // Filter by minimum similarity and format results
  const similarPeriods = results.matches
    .filter((match: any) => match.score >= minSimilarity)
    .slice(0, topK)
    .map((match: any) => ({
      id: match.id,
      similarity_score: match.score,
      timestamp: match.metadata?.timestamp,
      news_summary: match.metadata?.news_summary,
      sentiment_score: match.metadata?.sentiment_score,
      technical_setup: match.metadata?.technical_setup,
      social_summary: match.metadata?.social_summary,
      market_conditions: match.metadata?.market_conditions,
      metadata: match.metadata
    }));

  return {
    success: true,
    current_snapshot: {
      id: currentEmbedding.id,
      embedding_text: currentEmbedding.embedding_text
    },
    similar_periods: similarPeriods,
    count: similarPeriods.length,
    query_params: {
      top_k: topK,
      min_similarity: minSimilarity,
      exclude_recent_days: request.exclude_recent_days
    }
  };
}
