"""
One-time setup: Create Neo4j vector indexes for ContentBlock embeddings.
This is like enabling pgvector in Postgres - run once per Neo4j database instance.

The index persists and automatically includes all future ingested documents.
You only need to re-run if you create a new Neo4j database or drop the index.
"""

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


def create_vector_indexes():
    """Create vector indexes for ContentBlock embeddings"""
    
    if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
        print("❌ Missing Neo4j credentials in .env")
        return
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("🔧 Creating Neo4j vector indexes...")
    
    with driver.session() as session:
        # Check if index already exists
        result = session.run("SHOW INDEXES")
        existing_indexes = [record["name"] for record in result]
        
        # Create vector index for ContentBlock.embedding (small model: 1536 dims)
        index_name = "contentBlockEmbeddingIdx"
        
        if index_name in existing_indexes:
            print(f"✅ Index '{index_name}' already exists")
        else:
            try:
                session.run("""
                    CREATE VECTOR INDEX contentBlockEmbeddingIdx IF NOT EXISTS
                    FOR (cb:ContentBlock)
                    ON cb.embedding
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 1536,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                print(f"✅ Created vector index: {index_name}")
                print("   - Node label: ContentBlock")
                print("   - Property: embedding")
                print("   - Dimensions: 1536 (text-embedding-3-small)")
                print("   - Similarity: cosine")
            except Exception as e:
                print(f"❌ Failed to create index: {e}")
        
        # Create Fulltext Index for Keyword Search (Hybrid Search)
        ft_index_name = "contentBlockFulltextIdx"
        
        if ft_index_name in existing_indexes:
            print(f"✅ Index '{ft_index_name}' already exists")
        else:
            try:
                session.run("""
                    CREATE FULLTEXT INDEX contentBlockFulltextIdx IF NOT EXISTS
                    FOR (n:ContentBlock)
                    ON EACH [n.text_content]
                """)
                print(f"✅ Created fulltext index: {ft_index_name}")
                print("   - Node label: ContentBlock")
                print("   - Property: text_content")
                print("   - Type: Lucene Fulltext")
            except Exception as e:
                print(f"❌ Failed to create fulltext index: {e}")
        
        # Optional: Create index for large embeddings (3072 dims) if you use them
        # Uncomment below if you add embedding_large to your ContentBlock
        """
        index_name_large = "contentBlockEmbeddingIdx_large"
        
        if index_name_large in existing_indexes:
            print(f"✅ Index '{index_name_large}' already exists")
        else:
            try:
                session.run(\"\"\"
                    CREATE VECTOR INDEX contentBlockEmbeddingIdx_large IF NOT EXISTS
                    FOR (cb:ContentBlock)
                    ON cb.embedding_large
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 3072,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                \"\"\")
                print(f"✅ Created vector index: {index_name_large}")
            except Exception as e:
                print(f"❌ Failed to create large index: {e}")
        """
    
    driver.close()
    print("\n✅ Vector index setup complete!")
    print("You can now use retrieval.py for vector search + graph expansion")


def verify_indexes():
    """Verify that indexes are created and working"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("\n🔍 Verifying indexes...")
    
    with driver.session() as session:
        # List all indexes
        result = session.run("SHOW INDEXES")
        indexes = list(result)
        
        print(f"\n📋 Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx['name']} ({idx['type']}) on {idx['labelsOrTypes']} → {idx['properties']}")
        
        # Check ContentBlock count
        result = session.run("MATCH (cb:ContentBlock) RETURN count(cb) AS count")
        count = result.single()["count"]
        print(f"\n📊 ContentBlock nodes: {count}")
        
        if count > 0:
            # Sample a ContentBlock to check embedding
            result = session.run("""
                MATCH (cb:ContentBlock)
                WHERE cb.embedding IS NOT NULL
                RETURN cb.block_id AS id, size(cb.embedding) AS emb_size
                LIMIT 1
            """)
            
            sample = result.single()
            if sample:
                print(f"✅ Sample block: {sample['id']}")
                print(f"   Embedding size: {sample['emb_size']} dimensions")
            else:
                print("⚠️  No ContentBlocks with embeddings found")
        else:
            print("⚠️  No ContentBlocks in database yet. Run ingestion_workflow.py first.")
    
    driver.close()


if __name__ == "__main__":
    print("🚀 Neo4j Vector Index Setup\n")
    
    create_vector_indexes()
    verify_indexes()
    
    print("\n" + "="*60)
    print("Next steps:")
    print("1. Run ingestion_workflow.py to ingest documents")
    print("2. Use retrieval.py to test vector search + graph expansion")
    print("3. Integrate retrieve_context() into your chat agent")
    print("="*60)
