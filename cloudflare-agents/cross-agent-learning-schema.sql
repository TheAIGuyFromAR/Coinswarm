-- Cross-Agent Learning Network Schema
-- Enables agents to share knowledge and learn from high performers

-- Knowledge sharing log (tracks when agents teach each other)
CREATE TABLE IF NOT EXISTS agent_knowledge_sharing (
    sharing_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Source agent (teacher)
    teacher_agent_id TEXT NOT NULL,
    teacher_fitness REAL NOT NULL,
    teacher_generation INTEGER NOT NULL,

    -- Target agent (student)
    student_agent_id TEXT NOT NULL,
    student_fitness_before REAL NOT NULL,
    student_generation INTEGER NOT NULL,

    -- What was shared
    knowledge_type TEXT NOT NULL, -- 'pattern_preference', 'combination_rule', 'market_condition', 'avoid_condition'
    knowledge_content TEXT NOT NULL, -- JSON of the knowledge shared
    knowledge_confidence REAL NOT NULL, -- 0-1 how confident the teacher is

    -- Adoption status
    adopted INTEGER DEFAULT 0, -- 0 = pending, 1 = adopted, -1 = rejected
    adoption_reason TEXT, -- Why adopted or rejected

    -- Performance tracking
    student_fitness_after REAL, -- Fitness after adopting knowledge
    fitness_delta REAL, -- Change in fitness (positive = knowledge helped)
    validation_sample_size INTEGER, -- How many trades were used to validate

    -- Success metrics
    knowledge_helped INTEGER, -- 1 if knowledge improved performance, 0 if neutral, -1 if hurt
    knowledge_validated_at TEXT,

    FOREIGN KEY (teacher_agent_id) REFERENCES trading_agents(agent_id),
    FOREIGN KEY (student_agent_id) REFERENCES trading_agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_teacher ON agent_knowledge_sharing(teacher_agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_student ON agent_knowledge_sharing(student_agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_timestamp ON agent_knowledge_sharing(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_success ON agent_knowledge_sharing(knowledge_helped);

-- Knowledge influence graph (tracks lineage of successful knowledge)
CREATE TABLE IF NOT EXISTS knowledge_influence_graph (
    influence_id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL, -- Links to original knowledge from agent_knowledge table
    original_creator_id TEXT NOT NULL, -- First agent who discovered this knowledge

    -- Propagation tracking
    current_holder_id TEXT NOT NULL, -- Current agent holding this knowledge
    propagation_depth INTEGER DEFAULT 0, -- How many times this knowledge has been shared (0 = original)
    propagation_path TEXT, -- JSON array of agent IDs showing knowledge flow

    -- Success tracking
    total_wins INTEGER DEFAULT 0, -- Across all agents who used this knowledge
    total_applications INTEGER DEFAULT 0, -- How many times this knowledge was applied
    average_roi REAL DEFAULT 0, -- Average ROI when this knowledge was used

    -- Validation
    confirmed_effective INTEGER DEFAULT 0, -- 1 if validated across multiple agents
    validation_count INTEGER DEFAULT 0, -- How many agents validated this knowledge

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_propagated_at TEXT,

    FOREIGN KEY (original_creator_id) REFERENCES trading_agents(agent_id),
    FOREIGN KEY (current_holder_id) REFERENCES trading_agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_influence_graph_creator ON knowledge_influence_graph(original_creator_id);
CREATE INDEX IF NOT EXISTS idx_influence_graph_holder ON knowledge_influence_graph(current_holder_id);
CREATE INDEX IF NOT EXISTS idx_influence_graph_effective ON knowledge_influence_graph(confirmed_effective DESC, average_roi DESC);

-- Network learning metrics (aggregate statistics)
CREATE TABLE IF NOT EXISTS network_learning_metrics (
    metric_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    cycle_number INTEGER NOT NULL,

    -- Network statistics
    total_agents INTEGER NOT NULL,
    active_agents INTEGER NOT NULL,
    knowledge_items INTEGER NOT NULL, -- Total unique knowledge pieces

    -- Sharing statistics
    sharing_events_this_cycle INTEGER DEFAULT 0,
    total_sharing_events INTEGER DEFAULT 0,
    successful_adoptions INTEGER DEFAULT 0, -- Knowledge that improved fitness
    failed_adoptions INTEGER DEFAULT 0, -- Knowledge that hurt fitness

    -- Performance metrics
    average_fitness REAL DEFAULT 0,
    top_agent_fitness REAL DEFAULT 0,
    fitness_improvement_rate REAL DEFAULT 0, -- % improvement per cycle

    -- Knowledge quality
    average_knowledge_confidence REAL DEFAULT 0,
    top_knowledge_propagation_depth INTEGER DEFAULT 0, -- Most shared knowledge
    network_learning_velocity REAL DEFAULT 0 -- How fast knowledge spreads
);

CREATE INDEX IF NOT EXISTS idx_network_metrics_cycle ON network_learning_metrics(cycle_number DESC);

-- View: Top knowledge propagators (agents who teach successfully)
CREATE VIEW IF NOT EXISTS top_knowledge_propagators AS
SELECT
    ta.agent_id,
    ta.agent_name,
    ta.personality,
    ta.fitness_score,
    COUNT(DISTINCT aks.sharing_id) as times_taught,
    SUM(CASE WHEN aks.knowledge_helped = 1 THEN 1 ELSE 0 END) as successful_teachings,
    SUM(CASE WHEN aks.knowledge_helped = -1 THEN 1 ELSE 0 END) as failed_teachings,
    CAST(SUM(CASE WHEN aks.knowledge_helped = 1 THEN 1 ELSE 0 END) AS REAL) /
        NULLIF(COUNT(DISTINCT aks.sharing_id), 0) as teaching_success_rate,
    AVG(aks.fitness_delta) as avg_student_improvement
FROM trading_agents ta
JOIN agent_knowledge_sharing aks ON ta.agent_id = aks.teacher_agent_id
WHERE aks.knowledge_validated_at IS NOT NULL
GROUP BY ta.agent_id, ta.agent_name, ta.personality, ta.fitness_score
ORDER BY teaching_success_rate DESC, times_taught DESC;

-- View: Top knowledge learners (agents who adopt successfully)
CREATE VIEW IF NOT EXISTS top_knowledge_learners AS
SELECT
    ta.agent_id,
    ta.agent_name,
    ta.personality,
    ta.fitness_score,
    COUNT(DISTINCT aks.sharing_id) as times_learned,
    SUM(CASE WHEN aks.adopted = 1 THEN 1 ELSE 0 END) as adoptions,
    SUM(CASE WHEN aks.knowledge_helped = 1 THEN 1 ELSE 0 END) as successful_adoptions,
    CAST(SUM(CASE WHEN aks.knowledge_helped = 1 THEN 1 ELSE 0 END) AS REAL) /
        NULLIF(SUM(CASE WHEN aks.adopted = 1 THEN 1 ELSE 0 END), 0) as learning_success_rate,
    AVG(aks.fitness_delta) as avg_improvement_from_learning
FROM trading_agents ta
JOIN agent_knowledge_sharing aks ON ta.agent_id = aks.student_agent_id
WHERE aks.knowledge_validated_at IS NOT NULL
GROUP BY ta.agent_id, ta.agent_name, ta.personality, ta.fitness_score
ORDER BY learning_success_rate DESC, adoptions DESC;

-- View: Most valuable knowledge (validated across multiple agents)
CREATE VIEW IF NOT EXISTS most_valuable_knowledge AS
SELECT
    kg.influence_id,
    kg.knowledge_id,
    creator.agent_name as creator_name,
    creator.personality as creator_personality,
    kg.propagation_depth,
    kg.validation_count,
    kg.total_wins,
    kg.total_applications,
    kg.average_roi,
    CAST(kg.total_wins AS REAL) / NULLIF(kg.total_applications, 0) as win_rate,
    kg.confirmed_effective
FROM knowledge_influence_graph kg
JOIN trading_agents creator ON kg.original_creator_id = creator.agent_id
WHERE kg.confirmed_effective = 1
ORDER BY kg.validation_count DESC, kg.average_roi DESC;

-- Comments
COMMENT ON TABLE agent_knowledge_sharing IS 'Tracks knowledge transfer between agents - high performers teach others';
COMMENT ON TABLE knowledge_influence_graph IS 'Tracks lineage and propagation of successful knowledge across agent network';
COMMENT ON TABLE network_learning_metrics IS 'Aggregate metrics showing how fast the network is learning and improving';
COMMENT ON COLUMN agent_knowledge_sharing.knowledge_helped IS '1 = knowledge improved student, 0 = neutral, -1 = hurt student';
COMMENT ON COLUMN agent_knowledge_sharing.fitness_delta IS 'Change in student fitness after adopting knowledge (positive = success)';
COMMENT ON COLUMN knowledge_influence_graph.propagation_depth IS 'How many times knowledge has been shared (0 = original creator)';
COMMENT ON COLUMN knowledge_influence_graph.propagation_path IS 'JSON array of agent IDs showing knowledge flow: ["agent1", "agent2", "agent3"]';
COMMENT ON COLUMN knowledge_influence_graph.confirmed_effective IS '1 if validated across multiple agents with positive results';
