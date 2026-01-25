"""
Full ingestion test for Llama-4-Scout pipeline.

Tests the complete flow:
1. Llama extraction with page markers
2. PyMuPDF image extraction
3. Question generation
4. Image URL attachment
5. Neo4j persistence

Usage:
    uv run python test_full_ingestion.py <pdf_path>
"""

import sys
import uuid
import json
from pathlib import Path

from llama_ingestion import LlamaIngestionPipeline


def run_full_ingestion(pdf_path: str):
    """Run the complete ingestion pipeline."""
    
    # Generate IDs
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    user_id = "test_user_vasanth"
    title = Path(pdf_path).stem
    
    print(f"\n{'='*70}")
    print(f"🚀 FULL INGESTION TEST")
    print(f"{'='*70}")
    print(f"📄 File: {pdf_path}")
    print(f"📝 Doc ID: {doc_id}")
    print(f"👤 User ID: {user_id}")
    print(f"📖 Title: {title}")
    print(f"{'='*70}\n")
    
    # Configure pipeline
    config = {
        "question_model": "gpt-4.1",  # For question generation
    }
    
    pipeline = LlamaIngestionPipeline(config)
    
    # Run full ingestion
    try:
        result = pipeline.ingest_document(
            file_path=pdf_path,
            doc_id=doc_id,
            user_id=user_id,
            title=title,
            generate_questions=True,
            extract_images=True
        )
        
        print(f"\n{'='*70}")
        print(f"📊 INGESTION RESULT")
        print(f"{'='*70}")
        print(json.dumps(result, indent=2))
        
        # Query Neo4j to verify
        if pipeline.neo4j_driver:
            print(f"\n🔍 Verifying Neo4j data...")
            with pipeline.neo4j_driver.session() as session:
                # Count nodes
                doc_count = session.run(
                    "MATCH (d:Document {documentId: $doc_id}) RETURN count(d) as count",
                    doc_id=doc_id
                ).single()["count"]
                
                block_count = session.run(
                    """MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                    RETURN count(cb) as count""",
                    doc_id=doc_id
                ).single()["count"]
                
                qs_count = session.run(
                    """MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)-[:HAS_QUESTIONS]->(qs:QuestionSet)
                    RETURN count(qs) as count""",
                    doc_id=doc_id
                ).single()["count"]
                
                # Sample a question with image_url
                sample = session.run(
                    """MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)-[:HAS_QUESTIONS]->(qs:QuestionSet)
                    RETURN qs.questions as questions LIMIT 1""",
                    doc_id=doc_id
                ).single()
                
                print(f"\n   📊 Neo4j Verification:")
                print(f"      Documents: {doc_count}")
                print(f"      ContentBlocks: {block_count}")
                print(f"      QuestionSets: {qs_count}")
                
                if sample and sample["questions"]:
                    questions = json.loads(sample["questions"])
                    if questions:
                        q = questions[0]
                        print(f"\n   📝 Sample Question:")
                        print(f"      Text: {q.get('text', 'N/A')[:80]}...")
                        print(f"      Type: {q.get('question_type', 'N/A')}")
                        print(f"      Bloom: {q.get('bloom_level', 'N/A')}")
                        print(f"      Image URL: {q.get('image_url', 'None')}")
        
        print(f"\n✅ Full ingestion complete!")
        print(f"   Doc ID: {doc_id}")
        print(f"   You can query Neo4j with: MATCH (d:Document {{documentId: '{doc_id}'}}) RETURN d")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python test_full_ingestion.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    run_full_ingestion(pdf_path)
