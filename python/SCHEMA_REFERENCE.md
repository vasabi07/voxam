# Neo4j Schema Reference

**Last Updated:** November 12, 2025

This document defines the canonical Neo4j graph schema used across all agents.

---

## Node Labels

### User
```cypher
(:User {
  id: String  // User identifier
})
```

### Document
```cypher
(:Document {
  documentId: String,  // Unique document identifier
  title: String,
  source: String,      // Original filename
  created_at: DateTime
})
```

### ContentBlock
```cypher
(:ContentBlock {
  block_id: String,           // Format: "{doc_id}::block::{index}"
  chunk_index: Integer,       // Sequential index within document
  text_content: String,       // Raw text content
  summary: String,            // Optional summary
  combined_context: String,   // Text + image captions + table descriptions
  page_from: Integer,         // Starting page number
  page_to: Integer,           // Ending page number
  has_images: Boolean,
  has_tables: Boolean,
  image_count: Integer,
  table_count: Integer,
  embedding: Float[1536]      // Vector embedding for semantic search
})
```

### Question
```cypher
(:Question {
  id: String,                 // Format: "{block_id}::q::{index}"
  text: String,
  bloom_level: String,        // "remember", "understand", "apply", etc.
  difficulty: String,         // "basic", "intermediate", "advanced"
  question_type: String,      // "long_answer", "multiple_choice"
  expected_time: Integer,     // Minutes
  key_points: [String],       // Expected answer key points
  options: [String],          // MCQ options (if applicable)
  correct_answer: String,     // MCQ correct answer (if applicable)
  explanation: String         // MCQ explanation (if applicable)
})
```

---

## Relationships

### User → Document
```cypher
(:User)-[:UPLOADED]->(:Document)
```
**Description:** Links users to documents they uploaded.

### Document → ContentBlock
```cypher
(:Document)-[:HAS_CONTENT_BLOCK]->(:ContentBlock)
```
**Description:** Links documents to their content blocks (chunks with embeddings).

### ContentBlock → Question
```cypher
(:ContentBlock)-[:GENERATED_QUESTION]->(:Question)
```
**Description:** Links content blocks to questions generated from them. This is the ONLY link between content and questions.

---

## Complete Graph Structure

```
(:User {id})
    |
    [:UPLOADED]
    ↓
(:Document {documentId, title, source})
    |
    [:HAS_CONTENT_BLOCK]
    ↓
(:ContentBlock {
  block_id,
  combined_context,
  embedding[1536],
  ...
})
    |
    [:GENERATED_QUESTION]
    ↓
(:Question {
  id,
  text,
  bloom_level,
  difficulty,
  ...
})
```

---

## Usage by Agent

### Chat Agent (`agents/chat_agent.py`)
**Uses:** Vector search on `ContentBlock.embedding`

```cypher
// Semantic search for context
CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 30, $query_vector)
YIELD node, score
RETURN node.combined_context, node.block_id, score
```

### Exam Agent (`agents/exam_agent.py`)
**Uses:** Questions from Redis (pre-selected by QP agent)

No direct Neo4j queries during exam - all data comes from Redis cache.

### Question Paper Agent (`qp_agent.py`)
**Uses:** Question metadata for selection

```cypher
// Fetch all questions for a document
MATCH (d:Document {documentId: $document_id})
      -[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
      -[:GENERATED_QUESTION]->(q:Question)
WHERE q.difficulty IN $difficulty_levels
  AND q.question_type IN $question_types
RETURN q.id, q.expected_time, q.bloom_level, 
       cb.block_id, cb.chunk_index
ORDER BY cb.chunk_index
```

```cypher
// Fetch full question content for selected IDs
MATCH (cb:ContentBlock)-[:GENERATED_QUESTION]->(q:Question)
WHERE q.id IN $question_ids
RETURN q.*, cb.combined_context, cb.block_id
```

### Ingestion Pipeline (`ingestion_workflow.py`)
**Creates:** All nodes and relationships

```cypher
// Create document
MERGE (u:User {id: $user_id})
MERGE (d:Document {documentId: $doc_id})
MERGE (u)-[:UPLOADED]->(d)

// Create content block with embedding
MATCH (d:Document {documentId: $doc_id})
CREATE (cb:ContentBlock {
  block_id: $block_id,
  combined_context: $combined_context,
  embedding: $embedding,
  ...
})
MERGE (d)-[:HAS_CONTENT_BLOCK]->(cb)

// Create question
MATCH (cb:ContentBlock {block_id: $block_id})
MATCH (d:Document {documentId: $doc_id})
CREATE (q:Question {...})
MERGE (cb)-[:GENERATED_QUESTION]->(q)
MERGE (d)-[:HAS_QUESTIONS]->(q)
```

---

## Vector Index

```cypher
// Create vector index (run once via setup_vector_index.py)
CREATE VECTOR INDEX contentBlockEmbeddingIdx IF NOT EXISTS
FOR (cb:ContentBlock)
ON cb.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}
```

---

## Migration Notes

**Previous Schema (Deprecated):**
- ❌ Node: `Chunk` → Now: `ContentBlock`
- ❌ Relationship: `HAS_CHUNK` → Now: `HAS_CONTENT_BLOCK`
- ❌ Relationship: `HAS_QUESTION` → Now: `GENERATED_QUESTION`
- ❌ Property: `Document.id` → Now: `Document.documentId`
- ❌ Property: `Chunk.id` → Now: `ContentBlock.block_id`
- ❌ Property: `Chunk.content` → Now: `ContentBlock.combined_context`

**Updated Files:**
- ✅ `ingestion_workflow.py` - Uses new schema
- ✅ `qp_agent.py` - Updated to use new schema
- ✅ `retrieval.py` - Uses new schema
- 🔄 `agents/exam_agent.py` - No changes needed (uses Redis)
- 🔄 `agents/chat_agent.py` - Will use `retrieval.py` which is updated

---

## Verification Queries

```cypher
// Check node counts
MATCH (u:User) RETURN count(u) as users;
MATCH (d:Document) RETURN count(d) as documents;
MATCH (cb:ContentBlock) RETURN count(cb) as content_blocks;
MATCH (q:Question) RETURN count(q) as questions;

// Check relationships
MATCH ()-[r:UPLOADED]->() RETURN count(r);
MATCH ()-[r:HAS_CONTENT_BLOCK]->() RETURN count(r);
MATCH ()-[r:GENERATED_QUESTION]->() RETURN count(r);
MATCH ()-[r:HAS_QUESTIONS]->() RETURN count(r);

// Check embeddings
MATCH (cb:ContentBlock)
WHERE cb.embedding IS NOT NULL
RETURN count(cb) as blocks_with_embeddings;

// Sample data
MATCH (d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)-[:GENERATED_QUESTION]->(q:Question)
RETURN d.documentId, cb.block_id, q.text
LIMIT 5;
```
