PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE node_type (
    id TEXT PRIMARY KEY
) WITHOUT ROWID;

CREATE TABLE relation_type (
    id TEXT PRIMARY KEY,
    layer TEXT NOT NULL CHECK (layer IN ('methods', 'game-state')),
    domain_json TEXT NOT NULL,
    range_json TEXT NOT NULL,
    validator_predicate TEXT
) WITHOUT ROWID;

CREATE TABLE node (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL REFERENCES node_type(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64)
) WITHOUT ROWID;

CREATE TABLE edge (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL REFERENCES node(id),
    relation TEXT NOT NULL REFERENCES relation_type(id),
    target TEXT NOT NULL REFERENCES node(id),
    curated INTEGER NOT NULL CHECK (curated IN (0, 1)),
    label TEXT NOT NULL,
    evidence TEXT NOT NULL,
    UNIQUE (source, relation, target),
    CHECK (source <> target)
) WITHOUT ROWID;

CREATE TABLE competency_question (
    id TEXT PRIMARY KEY,
    question_en TEXT NOT NULL,
    question_ko TEXT NOT NULL,
    source_type TEXT NOT NULL REFERENCES node_type(id),
    relation TEXT NOT NULL REFERENCES relation_type(id),
    target_type TEXT NOT NULL REFERENCES node_type(id),
    required_sources_json TEXT NOT NULL,
    minimum_answers INTEGER NOT NULL CHECK (minimum_answers >= 1)
) WITHOUT ROWID;

CREATE TABLE benchmark_query (
    id TEXT PRIMARY KEY,
    question_en TEXT NOT NULL,
    question_ko TEXT NOT NULL,
    source TEXT NOT NULL REFERENCES node(id),
    relation TEXT NOT NULL REFERENCES relation_type(id),
    holdout_relation_id TEXT NOT NULL UNIQUE REFERENCES edge(id)
) WITHOUT ROWID;

CREATE TABLE benchmark_candidate (
    query_id TEXT NOT NULL REFERENCES benchmark_query(id),
    candidate_id TEXT NOT NULL,
    target TEXT NOT NULL REFERENCES node(id),
    relevant INTEGER NOT NULL CHECK (relevant IN (0, 1)),
    PRIMARY KEY (query_id, candidate_id),
    UNIQUE (query_id, target)
) WITHOUT ROWID;

CREATE TABLE strategy_run (
    strategy_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL CHECK (decision IN ('baseline', 'keep', 'discard')),
    precision REAL NOT NULL,
    recall REAL NOT NULL,
    f1 REAL NOT NULL,
    coverage REAL NOT NULL,
    mrr_realistic REAL NOT NULL,
    hits_at_1 REAL NOT NULL,
    hits_at_k REAL NOT NULL,
    ndcg_at_k REAL NOT NULL,
    brier_score REAL NOT NULL,
    semantic_at_k REAL NOT NULL,
    nonzero_weight_count INTEGER NOT NULL
) WITHOUT ROWID;

CREATE INDEX edge_by_source_relation ON edge(source, relation);
CREATE INDEX edge_by_target_relation ON edge(target, relation);
CREATE INDEX benchmark_candidate_by_target ON benchmark_candidate(target);
