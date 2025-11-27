# Vector Search Implementation - Phase 1 Complete ✅

## What Was Done

### 1. **Environment Setup**
- ✅ Moved Neo4j credentials from hardcoded to `.env`
- ✅ Added Neo4j credentials to python/.env

### 2. **Embedding Integration**
- ✅ Added `embed_text()` function using OpenAI `text-embedding-3-small` (1536 dims)
- ✅ Integrated embedding generation into `enrich_content_blocks()`
- ✅ Populates `ContentBlock.embeddings` field during ingestion

### 3. **Neo4j Graph Structure**
Created simple graph persistence with:
- `(:User)-[:UPLOADED]->(:Document)-[:HAS_CONTENT_BLOCK]->(:ContentBlock)`
- `(:ContentBlock)-[:GENERATED_QUESTION]->(:Question)` linking questions to source
- `(:Document)-[:HAS_QUESTIONS]->(:Question)` preserving exam agent compatibility

**Note**: No adjacency edges (NEXT_CHUNK) - using pure k-nearest vector search instead.

### 4. **Files Created/Modified**

**Modified:**
- `python/ingestion_workflow.py` - Added embeddings + Neo4j persistence
- `python/qp_agent.py` - Removed hardcoded credentials
- `python/.env` - Added Neo4j credentials

**Created:**
- `python/retrieval.py` - Vector search + graph expansion module
- `python/setup_vector_index.py` - Neo4j vector index creation script

## Architecture

### ContentBlock = Chunk
Your existing `ContentBlock` IS the chunk - no new concepts needed:
```python
ContentBlock:
  - text_content         # Raw text
  - summary              # Optional summary
  - combined_context     # Text + captions + tables (what we embed)
  - embeddings           # 1536-dim vector from text-embedding-3-small
  - image_captions       # Multimodal context
  - related_tables       # Tabular data
  - questions            # Generated questions
  - meta                 # Page numbers, etc.
```

### Graph Schema
```cypher
(:User {id})
  -[:UPLOADED]->
(:Document {documentId, title, source})
  -[:HAS_CONTENT_BLOCK]->
(:ContentBlock {
  block_id, chunk_index,
  text_content, summary, combined_context,
  embedding[1536],           # Vector for search
  page_from, page_to,
  has_images, has_tables
})
  -[:GENERATED_QUESTION]->(:Question)        # Links to questions

(:Document)-[:HAS_QUESTIONS]->(:Question)   # Preserves exam agent's structure
```

### Retrieval Strategy

**Pure k-Nearest Vector Search (Simplified):**

1. **Vector Search**: Query Neo4j vector index for top-k ContentBlocks by cosine similarity
2. **Ranking**: Sort by relevance score (higher = more similar)
3. **Context Assembly**: Build prompt context with provenance headers (doc ID, page numbers, scores)

**Why no graph expansion?**
- Simpler, faster queries
- Better for Q&A (gets best semantic matches anywhere in document)
- Easier to debug and maintain
- Can add later if needed

## Usage

### 1. Setup Vector Index (One-time)
```bash
cd /Users/vasanth/voxam/python
python setup_vector_index.py
```

This creates the Neo4j vector index on `ContentBlock.embedding`.

### 2. Ingest Documents
```python
from ingestion_workflow import IngestionPipeline

config = {"vision_llm": "gpt-4o-mini", "text_llm": "gpt-4.1"}
pipeline = IngestionPipeline(config)

# Extract + enrich + persist
doc_meta = {
    "user_id": "user123",
    "doc_id": "chapter1",
    "title": "Chapter 1",
    "source": "textbook.pdf"
}

content_blocks = pipeline.extract_pdf("textbook.pdf")
enriched = pipeline.enrich_content_blocks(content_blocks)
pipeline.persist_to_neo4j(doc_meta["doc_id"], doc_meta, enriched)
```

### 3. Retrieve Context for Chat Agent
```python
from retrieval import retrieve_context

# Get context for user query (pure k-nearest vector search)
query = "Explain photosynthesis in plants"
context = retrieve_context(query, k=30)  # Get top 30 most similar chunks

# Use in chat agent prompt
prompt = f"""
Context:
{context}

Question: {query}

Answer:
"""
```

## Benefits Over Pure Database Storage

1. **Semantic Search**: Finds conceptually similar content, not just keyword matches
2. **Multimodal Context**: Embeddings include image captions and table descriptions
3. **Provenance**: Every chunk has document ID and page numbers
4. **Question Traceability**: Questions linked to source content blocks
5. **Exam Agent Compatible**: Doesn't break existing `Document→Questions` structure
6. **Scalable**: Can search across thousands of documents efficiently

## Next Steps (Optional Enhancements)

### Phase 2 - Increase k if needed
- Test with different k values (20, 30, 40, 50)
- Measure quality vs. cost trade-off

### Phase 3 - Advanced Features (if needed)
- Add graph expansion with NEXT_CHUNK edges for narrative flow
- Add semantic similarity edges between related blocks
- Implement cross-encoder reranking for top-k refinement
- Add hybrid search (vector + keyword BM25)

### Phase 4 - Evaluation
- Create test set of student questions
- Measure answer quality
- A/B test different k values

## Integration with Chat Agent

Your chat agent can now use vector search:

```python
# In agents/chat_agent.py
from retrieval import retrieve_context

def handle_query(user_query: str):
    # Get semantic context via vector search
    context = retrieve_context(user_query, k=30)
    
    # Build prompt with context
    prompt = f"Context:\\n{context}\\n\\nQuestion: {user_query}\\n\\nAnswer:"
    
    # Call LLM
    response = llm.invoke(prompt)
    return response
```

## Exam Agent Compatibility ✅

The exam agent (`qp_agent.py`) is **completely unaffected** because:
1. It uses `Document→Questions` relationships (still exists)
2. It doesn't query ContentBlocks at all
3. All existing Cypher queries still work
4. We only **added** new node types, didn't modify existing ones

## Testing

### Test Ingestion
```bash
cd /Users/vasanth/voxam/python
python ingestion_workflow.py
```

### Test Retrieval
```bash
python retrieval.py
```

### Verify in Neo4j Browser
```cypher
// Count nodes
MATCH (cb:ContentBlock) RETURN count(cb);
MATCH (q:Question) RETURN count(q);

// Sample vector search
MATCH (cb:ContentBlock)
WHERE cb.embedding IS NOT NULL
RETURN cb.block_id, cb.text_content[..100]
LIMIT 5;

// Check relationships
MATCH (d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
RETURN d.documentId, count(cb) as num_blocks;
```

## Cost Estimates

- **Embeddings**: ~$0.0001 per 1K tokens (text-embedding-3-small)
- **For 100-page PDF**: ~$0.50-$1.00 in embedding costs
- **Neo4j AuraDB**: Free tier sufficient for testing (<100k nodes)

## Key Files Reference

| File | Purpose |
|------|---------|
| `ingestion_workflow.py` | PDF extraction → enrichment → Neo4j persistence |
| `retrieval.py` | Vector search + graph expansion |
| `setup_vector_index.py` | One-time vector index creation |
| `qp_agent.py` | Question paper agent (unchanged) |
| `agents/chat_agent.py` | Chat agent (will use retrieval.py) |
