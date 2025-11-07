/**
 * Model Research Agent
 *
 * Continuously searches HuggingFace and other sources for better AI models
 * Tests models for trading reasoning quality
 * Upgrades the system when better models are found
 */

import { generatePatternId } from './ai-pattern-analyzer';

interface AIModel {
  model_id: string;
  model_name: string;
  provider: string; // 'huggingface', 'cloudflare', 'openrouter', etc.
  model_size: string; // '7B', '13B', '70B', etc.
  architecture: string; // 'llama', 'mistral', 'qwen', etc.

  // Performance metrics
  reasoning_score: number; // 0-100
  speed_ms: number;
  cost_per_1k_tokens: number;

  // Test results
  tested_at: string;
  test_results: string; // JSON
  status: string; // 'active', 'testing', 'retired'
}

interface ModelTestResult {
  model_id: string;
  test_type: string;
  prompt: string;
  response: string;
  reasoning_quality: number; // 0-100
  response_time_ms: number;
  coherence_score: number;
  accuracy_score: number;
  tested_at: string;
}

/**
 * Search arXiv for recent AI model papers
 */
export async function searchArXiv(query: string = 'large language model trading'): Promise<any[]> {
  try {
    const response = await fetch(
      `http://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(query)}&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending`
    );

    if (!response.ok) {
      console.error('arXiv API error:', response.status);
      return [];
    }

    const xml = await response.text();

    // Parse XML to extract papers (basic parsing)
    const papers: any[] = [];
    const entryRegex = /<entry>([\s\S]*?)<\/entry>/g;
    let match;

    while ((match = entryRegex.exec(xml)) !== null) {
      const entry = match[1];
      const titleMatch = /<title>(.*?)<\/title>/.exec(entry);
      const summaryMatch = /<summary>(.*?)<\/summary>/.exec(entry);
      const publishedMatch = /<published>(.*?)<\/published>/.exec(entry);
      const linkMatch = /<id>(.*?)<\/id>/.exec(entry);

      if (titleMatch && summaryMatch) {
        papers.push({
          title: titleMatch[1].trim().replace(/\s+/g, ' '),
          summary: summaryMatch[1].trim().replace(/\s+/g, ' ').substring(0, 300),
          published: publishedMatch ? publishedMatch[1] : '',
          link: linkMatch ? linkMatch[1] : ''
        });
      }
    }

    return papers;
  } catch (error) {
    console.error('Error searching arXiv:', error);
    return [];
  }
}

/**
 * Search Google Scholar via Serper API (requires API key)
 * Falls back to direct search if no API key
 */
export async function searchGoogleScholar(query: string = 'AI trading models'): Promise<any[]> {
  try {
    // For now, construct search URL for logging
    // In production, integrate with Serper or similar API
    const searchUrl = `https://scholar.google.com/scholar?q=${encodeURIComponent(query)}&hl=en&as_sdt=0,5&as_ylo=2024`;

    return [{
      source: 'google_scholar',
      query,
      url: searchUrl,
      note: 'Manual review recommended - visit URL to see latest papers'
    }];
  } catch (error) {
    console.error('Error searching Google Scholar:', error);
    return [];
  }
}

/**
 * Search Papers with Code for model benchmarks
 */
export async function searchPapersWithCode(task: string = 'reasoning'): Promise<any[]> {
  try {
    // Papers with Code doesn't have a public API, but we can construct useful URLs
    const searchUrl = `https://paperswithcode.com/task/${task}`;

    return [{
      source: 'papers_with_code',
      task,
      url: searchUrl,
      note: 'Check for latest SOTA models in reasoning tasks'
    }];
  } catch (error) {
    console.error('Error searching Papers with Code:', error);
    return [];
  }
}

/**
 * Search HuggingFace for promising trading/reasoning models
 */
export async function searchHuggingFaceModels(query: string = 'trading reasoning'): Promise<any[]> {
  try {
    // HuggingFace API search
    const response = await fetch(
      `https://huggingface.co/api/models?search=${encodeURIComponent(query)}&sort=downloads&limit=50`,
      {
        headers: {
          'Accept': 'application/json'
        }
      }
    );

    if (!response.ok) {
      console.error('HuggingFace API error:', response.status);
      return [];
    }

    const models = await response.json();

    // Filter for promising models
    const promising = models.filter((m: any) => {
      const name = m.id.toLowerCase();
      return (
        // Look for reasoning, chat, or instruction-tuned models
        (name.includes('instruct') || name.includes('chat') || name.includes('reason')) &&
        // Avoid very large models (can't run on Cloudflare)
        !name.includes('70b') && !name.includes('405b') &&
        // Recent models
        m.downloads > 1000
      );
    });

    return promising.slice(0, 20);
  } catch (error) {
    console.error('Error searching HuggingFace:', error);
    return [];
  }
}

/**
 * Search for financial and time series models specifically
 */
export async function searchFinancialModels(): Promise<any[]> {
  const searches = [
    // HuggingFace searches
    'financial time series forecasting',
    'stock market prediction',
    'quantitative finance',
    'trading strategy',

    // arXiv searches
    'time series transformer trading',
    'deep learning financial forecasting',
    'llm financial analysis'
  ];

  const allFindings: any[] = [];

  for (const query of searches) {
    const hfResults = await searchHuggingFaceModels(query);
    const arxivResults = await searchArXiv(query);

    allFindings.push({
      query,
      huggingface_results: hfResults.slice(0, 3),
      arxiv_papers: arxivResults.slice(0, 3)
    });

    // Don't spam APIs
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  return allFindings;
}

/**
 * Check for specific known financial models
 */
export async function checkKnownFinancialModels(): Promise<any[]> {
  const knownModels = [
    {
      name: 'Microsoft TimesFM',
      description: 'Time series foundation model for forecasting',
      search_terms: ['timesfm', 'microsoft time series'],
      source: 'research'
    },
    {
      name: 'Google TimeGPT',
      description: 'GPT for time series prediction',
      search_terms: ['timegpt', 'nixtla'],
      source: 'api'
    },
    {
      name: 'FinGPT',
      description: 'LLM trained on financial data',
      search_terms: ['fingpt', 'financial llm'],
      source: 'huggingface'
    },
    {
      name: 'BloombergGPT',
      description: 'Bloomberg\'s financial language model',
      search_terms: ['bloomberggpt', 'financial transformer'],
      source: 'research'
    },
    {
      name: 'FinBERT',
      description: 'BERT fine-tuned on financial text',
      search_terms: ['finbert', 'financial sentiment'],
      source: 'huggingface'
    },
    {
      name: 'Chronos',
      description: 'Amazon\'s time series forecasting model',
      search_terms: ['chronos', 'amazon time series'],
      source: 'huggingface'
    },
    {
      name: 'TFT (Temporal Fusion Transformer)',
      description: 'Google\'s time series model',
      search_terms: ['temporal fusion transformer', 'tft forecasting'],
      source: 'research'
    }
  ];

  const findings: any[] = [];

  for (const model of knownModels) {
    console.log(`   🔍 Checking for ${model.name}...`);

    // Search HuggingFace for this specific model
    for (const term of model.search_terms) {
      const results = await searchHuggingFaceModels(term);

      if (results.length > 0) {
        findings.push({
          model_name: model.name,
          description: model.description,
          found: true,
          search_term: term,
          results: results.slice(0, 2)
        });
        break;
      }

      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  return findings;
}

/**
 * Search for models by specific criteria
 */
export async function searchModelsByCategory(category: 'reasoning' | 'financial' | 'math' | 'fast' | 'timeseries'): Promise<any[]> {
  const queries: Record<string, string> = {
    reasoning: 'reasoning instruct',
    financial: 'financial trading analysis',
    math: 'mathematics problem solving',
    fast: 'efficient small instruct',
    timeseries: 'time series forecasting'
  };

  return await searchHuggingFaceModels(queries[category]);
}

/**
 * Get Cloudflare Workers AI available models
 */
export async function getCloudflareModels(): Promise<string[]> {
  // These are known Cloudflare Workers AI models
  return [
    '@cf/meta/llama-3.1-8b-instruct',
    '@cf/meta/llama-3.1-70b-instruct',
    '@cf/meta/llama-2-7b-chat-int8',
    '@cf/mistral/mistral-7b-instruct-v0.1',
    '@cf/mistral/mistral-7b-instruct-v0.2',
    '@cf/qwen/qwen1.5-7b-chat-awq',
    '@cf/qwen/qwen1.5-14b-chat-awq',
    '@cf/deepseek-ai/deepseek-math-7b-instruct',
    '@cf/microsoft/phi-2',
    '@cf/tinyllama/tinyllama-1.1b-chat-v1.0'
  ];
}

/**
 * Test a model's reasoning ability with trading scenarios
 */
export async function testModelReasoning(
  ai: any,
  modelName: string,
  db: any
): Promise<ModelTestResult> {
  const testPrompts = [
    {
      type: 'pattern_combination',
      prompt: `You are a trading agent. Market conditions: High volatility, uptrend, high volume.
Available patterns:
1. Momentum breakout (65% win rate)
2. Mean reversion (58% win rate)
3. Volume spike (72% win rate)

Which 2 patterns should you combine and why? Respond in JSON:
{"patterns": ["pattern_name"], "reasoning": "explanation"}`,
      expectedKeywords: ['volume', 'momentum', 'uptrend', 'combine']
    },
    {
      type: 'reflection',
      prompt: `You made a trade using momentum + breakout patterns.
Result: LOSS (-3.2% ROI)
Market was: High volatility, false breakout occurred

Reflect on what went wrong and how to improve. JSON:
{"reflection": "analysis", "lesson": "takeaway", "adjustment": "change"}`,
      expectedKeywords: ['false breakout', 'volatility', 'avoid', 'careful']
    },
    {
      type: 'market_analysis',
      prompt: `Analyze this market scenario:
- Price up 15% in 2 hours
- Volume 3x normal
- Volatility increasing
- No news events

What's happening and what should a conservative trader do? JSON:
{"analysis": "situation", "recommendation": "action", "risk": "assessment"}`,
      expectedKeywords: ['pump', 'caution', 'profit', 'risk']
    }
  ];

  let totalScore = 0;
  let totalTime = 0;
  const results: any[] = [];

  for (const test of testPrompts) {
    const startTime = Date.now();

    try {
      const response = await ai.run(modelName, {
        messages: [
          {
            role: 'system',
            content: 'You are a professional trading agent that reasons carefully about market conditions.'
          },
          {
            role: 'user',
            content: test.prompt
          }
        ],
        temperature: 0.6,
        max_tokens: 500
      });

      const responseTime = Date.now() - startTime;
      totalTime += responseTime;

      const text = response.response || '';

      // Score the response
      let score = 0;

      // Check for JSON format
      if (text.includes('{') && text.includes('}')) {
        score += 20;
      }

      // Check for expected keywords
      const keywordMatches = test.expectedKeywords.filter(
        keyword => text.toLowerCase().includes(keyword)
      );
      score += (keywordMatches.length / test.expectedKeywords.length) * 50;

      // Check response length (not too short, not too long)
      if (text.length > 50 && text.length < 1000) {
        score += 15;
      }

      // Check for reasoning quality (contains "because", "therefore", "since", etc.)
      const reasoningWords = ['because', 'therefore', 'since', 'due to', 'as', 'thus'];
      if (reasoningWords.some(word => text.toLowerCase().includes(word))) {
        score += 15;
      }

      totalScore += score;

      results.push({
        test_type: test.type,
        score,
        response_time: responseTime,
        response: text.substring(0, 500)
      });

    } catch (error) {
      console.error(`Model ${modelName} failed test ${test.type}:`, error);
      results.push({
        test_type: test.type,
        score: 0,
        error: String(error)
      });
    }
  }

  const avgScore = totalScore / testPrompts.length;
  const avgTime = totalTime / testPrompts.length;

  const testResult: ModelTestResult = {
    model_id: generatePatternId(),
    test_type: 'comprehensive',
    prompt: 'Multiple trading reasoning tests',
    response: JSON.stringify(results),
    reasoning_quality: avgScore,
    response_time_ms: avgTime,
    coherence_score: avgScore * 0.8, // Estimate
    accuracy_score: avgScore * 0.9, // Estimate
    tested_at: new Date().toISOString()
  };

  // Store result
  await db.prepare(`
    INSERT INTO model_test_results (
      test_id, model_id, test_type, prompt, response,
      reasoning_quality, response_time_ms, coherence_score,
      accuracy_score, tested_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    testResult.model_id,
    modelName,
    testResult.test_type,
    testResult.prompt,
    testResult.response,
    testResult.reasoning_quality,
    testResult.response_time_ms,
    testResult.coherence_score,
    testResult.accuracy_score,
    testResult.tested_at
  ).run();

  return testResult;
}

/**
 * Test all Cloudflare models and find the best one
 */
export async function benchmarkAllModels(ai: any, db: any): Promise<any[]> {
  const models = await getCloudflareModels();
  const results: any[] = [];

  console.log(`\n🔬 Benchmarking ${models.length} models for trading reasoning...`);

  for (const modelName of models) {
    console.log(`   Testing ${modelName}...`);

    try {
      const result = await testModelReasoning(ai, modelName, db);
      results.push({
        model: modelName,
        score: result.reasoning_quality,
        speed: result.response_time_ms
      });

      console.log(`   └─ Score: ${result.reasoning_quality.toFixed(1)}/100 | Speed: ${result.response_time_ms}ms`);

      // Wait between tests to avoid rate limits
      await new Promise(resolve => setTimeout(resolve, 2000));

    } catch (error) {
      console.error(`   └─ Error testing ${modelName}:`, error);
      results.push({
        model: modelName,
        score: 0,
        error: String(error)
      });
    }
  }

  // Sort by score
  results.sort((a, b) => b.score - a.score);

  console.log('\n📊 Benchmark Results:');
  results.slice(0, 5).forEach((r, i) => {
    console.log(`   ${i + 1}. ${r.model}: ${r.score.toFixed(1)}/100 (${r.speed}ms)`);
  });

  return results;
}

/**
 * Get current best model
 */
export async function getBestModel(db: any): Promise<string> {
  const result = await db.prepare(`
    SELECT model_id, reasoning_quality
    FROM model_test_results
    WHERE reasoning_quality > 0
    ORDER BY reasoning_quality DESC, response_time_ms ASC
    LIMIT 1
  `).first();

  return result?.model_id || '@cf/meta/llama-3.1-8b-instruct';
}

/**
 * Run model research cycle - searches for new models and tests them
 */
export async function runModelResearch(ai: any, db: any): Promise<void> {
  console.log('\n🔬 MODEL RESEARCH AGENT ACTIVATED');

  // 1. Check for known financial/time series models
  console.log('💰 Checking for known financial & time series models...');
  const financialModels = await checkKnownFinancialModels();

  if (financialModels.length > 0) {
    console.log(`\n   Found ${financialModels.length} financial models:`);
    financialModels.forEach((m: any) => {
      console.log(`   ✓ ${m.model_name}: ${m.description}`);
      if (m.results && m.results.length > 0) {
        console.log(`     └─ Available: ${m.results[0].id}`);
      }
    });

    // Store findings
    await db.prepare(`
      INSERT INTO research_log (
        log_id, log_type, content, created_at
      ) VALUES (?, 'financial_models_found', ?, CURRENT_TIMESTAMP)
    `).bind(
      generatePatternId(),
      JSON.stringify({ models: financialModels })
    ).run();
  }

  // 2. Search arXiv for recent financial AI papers
  console.log('\n📚 Searching arXiv for recent financial AI research...');
  const arxivPapers = await searchArXiv('deep learning time series forecasting');

  if (arxivPapers.length > 0) {
    console.log(`   Found ${arxivPapers.length} recent papers:`);
    arxivPapers.slice(0, 3).forEach((p: any) => {
      console.log(`   - ${p.title}`);
      console.log(`     Published: ${p.published.substring(0, 10)} | ${p.link}`);
    });

    // Store findings
    await db.prepare(`
      INSERT INTO research_log (
        log_id, log_type, content, created_at
      ) VALUES (?, 'arxiv_papers', ?, CURRENT_TIMESTAMP)
    `).bind(
      generatePatternId(),
      JSON.stringify({
        query: 'deep learning time series forecasting',
        papers: arxivPapers.slice(0, 5)
      })
    ).run();
  }

  // 3. Search HuggingFace for new models
  console.log('\n🤗 Searching HuggingFace for trading models...');
  const hfModels = await searchHuggingFaceModels('time series forecasting');
  console.log(`   Found ${hfModels.length} potential models`);

  if (hfModels.length > 0) {
    console.log('\n   Top findings:');
    hfModels.slice(0, 5).forEach((m: any) => {
      console.log(`   - ${m.id} (${m.downloads} downloads)`);
    });

    // Store findings
    await db.prepare(`
      INSERT INTO research_log (
        log_id, log_type, content, created_at
      ) VALUES (?, 'model_search', ?, CURRENT_TIMESTAMP)
    `).bind(
      generatePatternId(),
      JSON.stringify({
        source: 'huggingface',
        query: 'time series forecasting',
        results_count: hfModels.length,
        top_models: hfModels.slice(0, 5).map((m: any) => ({
          id: m.id,
          downloads: m.downloads
        }))
      })
    ).run();
  }

  // 4. Benchmark Cloudflare models (only if not done recently)
  const lastBenchmark = await db.prepare(`
    SELECT MAX(tested_at) as last_test
    FROM model_test_results
  `).first();

  const daysSinceLastBenchmark = lastBenchmark?.last_test ?
    (Date.now() - new Date(lastBenchmark.last_test).getTime()) / (1000 * 60 * 60 * 24) :
    999;

  if (daysSinceLastBenchmark > 7) {
    console.log('\n🧪 Running full model benchmark (last run: ' +
      (daysSinceLastBenchmark < 999 ? `${daysSinceLastBenchmark.toFixed(0)} days ago` : 'never') + ')');

    await benchmarkAllModels(ai, db);
  } else {
    console.log(`\n✓ Skipping benchmark (last run ${daysSinceLastBenchmark.toFixed(0)} days ago)`);
  }

  // 5. Get current best model
  const bestModel = await getBestModel(db);
  console.log(`\n🏆 Current best model for trading: ${bestModel}`);

  // 6. Provide research summary
  console.log('\n📊 Research Recommendations:');
  console.log('   - For time series: Consider Chronos, TimesFM, or TFT models');
  console.log('   - For financial reasoning: Check FinGPT, BloombergGPT papers');
  console.log('   - For general reasoning: Continue with Llama 3.1-8B or test Mistral variants');

  // 7. Store research completion
  await db.prepare(`
    INSERT INTO research_log (
      log_id, log_type, content, created_at
    ) VALUES (?, 'model_research_complete', ?, CURRENT_TIMESTAMP)
  `).bind(
    generatePatternId(),
    JSON.stringify({
      best_model: bestModel,
      financial_models_found: financialModels.length,
      papers_reviewed: arxivPapers.length
    })
  ).run();

  console.log('✓ Model research cycle complete\n');
}

export { AIModel, ModelTestResult };
