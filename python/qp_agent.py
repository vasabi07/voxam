"""
this is the question paper generation agent.
retrieve all questions from the graphdb with the document info from user with duration form details. 
form a object with questions with their block content 
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from neo4j import GraphDatabase
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os
import json

from agents.exam_agent import REDIS_URI
load_dotenv()

# Neo4j connection details from environment
URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([URI, NEO4J_USER, NEO4J_PASSWORD]):
    raise ValueError("Missing required Neo4j environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")

AUTH = (NEO4J_USER, NEO4J_PASSWORD)

llm = init_chat_model(model="gpt-4.1",temperature=0)

def get_database_driver():
    """Get Neo4j driver"""
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        # Test the connection
        with driver.session() as session:
            session.run("RETURN 1")
        print("✅ Connected to Neo4j AuraDB")
        return driver
    except Exception as e:
        print(f"❌ Cannot connect to Neo4j AuraDB: {e}")
        raise e

class QuestionGroupResponse(BaseModel):
    """Response containing questions grouped by context"""
    question_groups: List[Dict[str, Any]] = Field(description="List of question groups, each with shared context and questions")
    total_questions: int = Field(description="Total number of questions across all groups")
    total_estimated_time: int = Field(description="Total estimated time for all questions")
    
class QuestionPlanResponse(BaseModel):
    """Structured response for question paper planning"""
    selected_question_ids: List[str] = Field(description="List of question IDs selected for the question paper")
    total_estimated_time: int = Field(description="Total estimated time for all selected questions in minutes")
    reasoning: str = Field(description="Brief explanation of the selection strategy and balance achieved")
    question_type_distribution: Optional[Dict[str, int]] = Field(default={}, description="Count of each question type selected")
    bloom_level_distribution: Optional[Dict[str, int]] = Field(default={}, description="Count of each Bloom's taxonomy level")
    difficulty_distribution: Optional[Dict[str, int]] = Field(default={}, description="Count of each difficulty level")
class QPInputState(BaseModel):
    qp_id: str  # Generated from Next.js (meeting.id)
    document_id: str
    duration: int 
    num_questions: Optional[int] = 10
    difficulty_levels: Optional[List[str]] = ["basic", "intermediate", "advanced"]
    question_types: Optional[List[str]] = ["long_answer", "multiple_choice"]
    bloom_levels: Optional[List[str]] = ["remember", "understand", "apply", "analyze", "evaluate"]
    type_of_qp: Optional[str] = "regular"
    
    # Workflow state
    all_questions_metadata: Optional[List[dict]] = []
    selected_question_ids: Optional[List[str]] = []
    selected_questions_with_content: Optional[List[dict]] = []
    grouped_questions: Optional[List[dict]] = []  # This will be our final output
    
    class Config:
        arbitrary_types_allowed = True


def get_all_questions_metadata(input_state: QPInputState):
    """
    Fetch lightweight question metadata for planning.
    Now queries QuestionSet nodes and parses JSON to get individual questions.
    """
    print(f"📋 Fetching question metadata for document: {input_state.document_id}")
    
    driver = get_database_driver()
    with driver as session:
        # Query QuestionSet nodes (not individual Question nodes)
        query = """
        MATCH (d:Document {documentId: $document_id})
              -[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
              -[:HAS_QUESTIONS]->(qs:QuestionSet)
        RETURN 
            cb.block_id as chunk_id,
            coalesce(cb.chunk_index, 0) as chunk_index,
            qs.questions as questions_json
        ORDER BY cb.chunk_index
        """
        
        result = session.execute_query(
            query,
            document_id=input_state.document_id
        )
        
        # Parse JSON and flatten questions with filtering
        questions_metadata = []
        for record in result.records:
            try:
                chunk_id = record.get("chunk_id", "")
                chunk_index = record.get("chunk_index", 0)
                questions_json = record.get("questions_json", "[]")
                
                # Parse the JSON array of questions
                block_questions = json.loads(questions_json) if questions_json else []
                
                for q in block_questions:
                    # Apply filters
                    if input_state.difficulty_levels and q.get("difficulty") not in input_state.difficulty_levels:
                        continue
                    if input_state.question_types and q.get("question_type") not in input_state.question_types:
                        continue
                    if input_state.bloom_levels and q.get("bloom_level") not in input_state.bloom_levels:
                        continue
                    
                    questions_metadata.append({
                        "question_id": q.get("question_id", ""),
                        "expected_time": q.get("expected_time", 5),
                        "bloom_level": q.get("bloom_level", "remember"),
                        "difficulty": q.get("difficulty", "basic"),
                        "question_type": q.get("question_type", "multiple_choice"),
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index
                    })
            except Exception as e:
                print(f"⚠️ Error processing record: {e}")
                continue
        
        print(f"✅ Found {len(questions_metadata)} questions matching criteria")
        
        # Update state
        input_state.all_questions_metadata = questions_metadata
        return input_state


def get_selected_questions_with_content(input_state: QPInputState):
    """
    Fetch full question content for selected questions only.
    Now queries QuestionSet and filters by selected IDs in Python.
    """
    if not input_state.selected_question_ids:
        print("⚠️ No questions selected yet")
        return input_state
    
    print(f"📄 Fetching full content for {len(input_state.selected_question_ids)} selected questions")
    
    # Build a set of selected IDs for fast lookup
    selected_ids_set = set(input_state.selected_question_ids)
    
    driver = get_database_driver()
    with driver as session:
        # Query QuestionSet nodes with their ContentBlock context
        query = """
        MATCH (cb:ContentBlock)-[:HAS_QUESTIONS]->(qs:QuestionSet)
        WHERE cb.doc_id = $document_id OR qs.doc_id = $document_id
        RETURN 
            cb.block_id as chunk_id,
            coalesce(cb.chunk_index, 0) as chunk_index,
            coalesce(cb.combined_context, '') as context_content,
            qs.questions as questions_json
        ORDER BY cb.chunk_index
        """
        
        result = session.execute_query(
            query,
            document_id=input_state.document_id
        )
        
        # Parse JSON and filter to only selected questions
        questions_with_content = []
        for record in result.records:
            try:
                chunk_id = record.get("chunk_id", "")
                chunk_index = record.get("chunk_index", 0)
                context_content = record.get("context_content", "")
                questions_json = record.get("questions_json", "[]")
                
                # Parse the JSON array of questions
                block_questions = json.loads(questions_json) if questions_json else []
                
                for q in block_questions:
                    # Only include selected questions
                    if q.get("question_id") in selected_ids_set:
                        questions_with_content.append({
                            "question_id": q.get("question_id", ""),
                            "text": q.get("text", ""),
                            "options": q.get("options", []),
                            "correct_answer": q.get("correct_answer", ""),
                            "explanation": q.get("explanation", ""),
                            "key_points": q.get("key_points", []),
                            "expected_time": q.get("expected_time", 0),
                            "bloom_level": q.get("bloom_level", ""),
                            "difficulty": q.get("difficulty", ""),
                            "question_type": q.get("question_type", ""),
                            "context_content": context_content,
                            "chunk_index": chunk_index,
                            "chunk_id": chunk_id,
                            # Image URL for frontend display (description is inline in context)
                            "image_url": q.get("image_url"),
                        })
            except Exception as e:
                print(f"⚠️ Error processing record: {e}")
                continue
        
        print(f"✅ Retrieved full content for {len(questions_with_content)} questions")
        
        # Update state
        input_state.selected_questions_with_content = questions_with_content
        return input_state


def _format_questions_by_chunk(questions_metadata):
    """Helper function to format questions grouped by chunk for the prompt"""
    chunks = {}
    for q in questions_metadata:
        chunk_id = q.get('chunk_id', 'unknown')
        chunk_index = q.get('chunk_index', 0)
        if chunk_id not in chunks:
            chunks[chunk_id] = {
                'chunk_index': chunk_index,
                'questions': []
            }
        chunks[chunk_id]['questions'].append({
            'id': q.get('question_id'),
            'type': q.get('question_type'),
            'difficulty': q.get('difficulty'),
            'bloom': q.get('bloom_level'),
            'time': q.get('expected_time')
        })
    
    # Format for prompt
    formatted = []
    for chunk_id in sorted(chunks.keys(), key=lambda x: chunks[x]['chunk_index']):
        chunk_info = chunks[chunk_id]
        formatted.append(f"Chunk {chunk_info['chunk_index']} ({chunk_id}): {len(chunk_info['questions'])} questions available")
        for q in chunk_info['questions'][:3]:  # Show first 3 as examples
            formatted.append(f"  - {q['id']}: {q['type']}, {q['difficulty']}, {q['bloom']}, {q['time']}min")
        if len(chunk_info['questions']) > 3:
            formatted.append(f"  - ... and {len(chunk_info['questions']) - 3} more")
    
    return "\n".join(formatted)


def plan_qp_generation(state: QPInputState) -> QPInputState:
    """
    Plan the question paper generation using AI with structured output:
    - Calculate time per question based on duration
    - Balance question types 
    - Ensure content coverage across chunks
    - Apply difficulty distribution
    - Consider Bloom's taxonomy levels
    """
    print(f"📋 Planning question paper with {state.num_questions} questions for {state.duration} minutes")
    
    if not state.all_questions_metadata:
        print("⚠️ No questions metadata available for planning")
        state.selected_question_ids = []
        return state
    
    # Create structured LLM chain with function calling method
    structured_llm = llm.with_structured_output(QuestionPlanResponse, method="function_calling")
    
    system_prompt = f"""
    You are an expert educational content planner.
    Given a pool of questions with metadata, select exactly {state.num_questions} questions for a question paper.
    
    CONSTRAINTS:
    - Total number of questions: {state.num_questions}
    - Total duration: {state.duration} minutes
    - Available questions: {len(state.all_questions_metadata)}
    
    CRITICAL REQUIREMENT - CONTENT COVERAGE:
    You MUST ensure questions are distributed across DIFFERENT chunks/topics to provide comprehensive coverage.
    Avoid selecting all questions from just 1-2 chunks. Aim to include questions from at least {min(state.num_questions // 2, len(set(q['chunk_id'] for q in state.all_questions_metadata)))} different chunks.
    
    BALANCING GUIDELINES (in order of priority):
    1. **Content Distribution**: Select from diverse chunks/topics (highest priority)
    2. **Time Management**: Ensure total estimated time ≤ {state.duration} minutes  
    3. **Cognitive Skills**: Mix Bloom's taxonomy levels (remember, understand, apply, etc.)
    4. **Question Types**: Balance multiple choice vs long answer questions
    5. **Difficulty**: Include varied difficulty levels
    
    AVAILABLE QUESTIONS BY CHUNK:
    {_format_questions_by_chunk(state.all_questions_metadata)}
    
    STRATEGY:
    1. First, identify all unique chunks available
    2. Select 1-2 questions from each major chunk/topic
    3. Ensure the selection covers the breadth of the document
    4. Then apply other balancing criteria within those constraints
    
    REQUIRED OUTPUT:
    - selected_question_ids: Array of exactly {state.num_questions} question IDs (ensure chunk diversity!)
    - total_estimated_time: Sum of expected_time for selected questions
    - reasoning: Explain your selection strategy focusing on content coverage
    - question_type_distribution: Count by type 
    - bloom_level_distribution: Count by bloom level
    - difficulty_distribution: Count by difficulty
    
    Remember: A good question paper tests the student's knowledge across the entire document, not just a few sections!
    """
    
    try:
        # Get structured response from LLM
        planning_response = structured_llm.invoke(system_prompt)
        
        # Validate that selected question IDs exist in our metadata
        available_ids = set(q["question_id"] for q in state.all_questions_metadata)
        selected_ids = planning_response.selected_question_ids
        valid_ids = [qid for qid in selected_ids if qid in available_ids]
        invalid_ids = [qid for qid in selected_ids if qid not in available_ids]
        
        if invalid_ids:
            print(f"⚠️ Found {len(invalid_ids)} invalid question IDs, removing them")
            print(f"Invalid IDs: {invalid_ids[:3]}...")  # Show first 3
        
        # Update state with only valid question IDs
        state.selected_question_ids = valid_ids
        
        # Print planning summary
        print(f"✅ Selected {len(state.selected_question_ids)} valid questions (out of {len(selected_ids)} requested)")
        print(f"📊 Estimated time: {planning_response.total_estimated_time} minutes")
        print(f"🎯 Question types: {planning_response.question_type_distribution}")
        print(f"🧠 Bloom levels: {planning_response.bloom_level_distribution}")
        print(f"📈 Difficulty: {planning_response.difficulty_distribution}")
        print(f"💡 Reasoning: {planning_response.reasoning}")
        
    except Exception as e:
        print(f"⚠️ AI planning failed, falling back to simple selection: {e}")
        # Fallback to simple selection
        selected_count = min(state.num_questions, len(state.all_questions_metadata))
        selected_questions = state.all_questions_metadata[:selected_count]
        state.selected_question_ids = [q["question_id"] for q in selected_questions]
        print(f"✅ Fallback: Selected {len(state.selected_question_ids)} questions")
    
    return state


def group_questions_by_context(state: QPInputState) -> QPInputState:
    """
    Group questions by their chunk context and convert to simplified format.
    Output format matches the simplified structure: {question_id, text, context}
    This is the final output ready for the exam agent.
    """
    print(f"📝 Grouping {len(state.selected_questions_with_content)} questions by context")
    
    if not state.selected_questions_with_content:
        print("⚠️ No questions to group")
        state.grouped_questions = []
        return state
    
    # Group questions by chunk_id
    context_groups = {}
    
    for question in state.selected_questions_with_content:
        chunk_id = question.get('chunk_id', 'unknown')
        
        if chunk_id not in context_groups:
            context_groups[chunk_id] = {
                'chunk_id': chunk_id,
                'chunk_index': question.get('chunk_index', 0),
                'context': question.get('context_content', ''),
                'questions': []
            }
        
        # Add question with ALL fields needed by exam agent
        question_data = {
            'question_id': question.get('question_id'),
            'text': question.get('text'),
            'question_type': question.get('question_type', 'long_answer'),
            'difficulty': question.get('difficulty', 'basic'),
            'bloom_level': question.get('bloom_level', 'remember'),
            'expected_time': question.get('expected_time', 5),
            'key_points': question.get('key_points', []),
            # MCQ-specific fields
            'options': question.get('options', []),
            'correct_answer': question.get('correct_answer', ''),
            'explanation': question.get('explanation', ''),
            # Image URL for frontend display (description is inline in context)
            'image_url': question.get('image_url'),
        }
        
        context_groups[chunk_id]['questions'].append(question_data)
    
    # Convert to flat list of questions for exam agent
    # Each question will have its own context, making it easy for Redis storage
    full_questions = []
    
    for group in sorted(context_groups.values(), key=lambda x: x['chunk_index']):
        for question in group['questions']:
            full_questions.append({
                'question_id': question['question_id'],
                'text': question['text'],
                'question_type': question['question_type'],
                'difficulty': question['difficulty'],
                'bloom_level': question['bloom_level'],
                'expected_time': question['expected_time'],
                'key_points': question['key_points'],
                'options': question['options'],
                'correct_answer': question['correct_answer'],
                'explanation': question['explanation'],
                'context': group['context'],  # Use the group's context for all questions
                # Image URL for frontend display (description is inline in context)
                'image_url': question.get('image_url'),
            })
    
    # Store as grouped questions
    state.grouped_questions = full_questions
    
    # Print summary
    total_questions = len(full_questions)
    mcq_count = sum(1 for q in full_questions if q['question_type'] == 'multiple_choice')
    long_answer_count = total_questions - mcq_count
    unique_contexts = len(set(q['context'] for q in full_questions))
    
    print(f"✅ Created {total_questions} questions ({mcq_count} MCQ, {long_answer_count} Long Answer)")
    print(f"📋 Unique contexts: {unique_contexts}")
    
    return state

def store_in_redis(state: QPInputState) -> QPInputState:
    """
    use the qp_id recieved from the user to store the final output in redis
    save as a json array of questions with their context
    """
    from redis import Redis
    qp_id = state.qp_id  # Use the qp_id from Next.js (meeting.id)

    # Use the imported REDIS_URI from environment (via exam_agent or os.getenv)
    # Parse the URI to get host/port if needed, or use from_url
    try:
        r = Redis.from_url(REDIS_URI, decode_responses=True)
        
        if not state.grouped_questions:
            print("⚠️ No grouped questions to store in Redis")
            return state    
            
        r.json().set(f"qp:{qp_id}:questions", '$', state.grouped_questions)
        print(f"✅ Stored {len(state.grouped_questions)} questions in Redis under qp_id: {qp_id}")
    except Exception as e:
        print(f"⚠️ Failed to store questions in Redis: {e}")
    
    return state


def store_in_postgres(state: QPInputState) -> QPInputState:
    """
    Update the QuestionPaper table in Supabase Postgres with:
      - status = 'READY'
      - questions = JSON array of grouped_questions
    
    This triggers the Supabase Realtime update that the frontend is listening to.
    """
    import json
    
    qp_id = state.qp_id
    
    if not state.grouped_questions:
        print("⚠️ No questions to store in Postgres")
        return state
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        print("⚠️ Supabase credentials not found, skipping Postgres update")
        print("   Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        return state
    
    try:
        from supabase import create_client
        
        supabase = create_client(supabase_url, supabase_service_key)
        
        # Update QuestionPaper with status=READY and questions JSON
        result = supabase.table("QuestionPaper").update({
            "status": "READY",
            "questions": state.grouped_questions,  # Supabase handles JSON serialization
            "updatedAt": "now()"  # Use current timestamp
        }).eq("id", qp_id).execute()
        
        if result.data:
            print(f"✅ Updated QuestionPaper {qp_id} in Postgres with status=READY")
            print(f"   Questions count: {len(state.grouped_questions)}")
        else:
            print(f"⚠️ No rows updated for QuestionPaper {qp_id} - may not exist yet")
            
    except ImportError:
        print("⚠️ supabase-py not installed. Run: pip install supabase")
        print("   Falling back to psycopg2...")
        
        # Fallback to direct Postgres connection
        try:
            import psycopg2
            database_url = os.getenv("DATABASE_URL")
            
            if not database_url:
                print("⚠️ DATABASE_URL not found, cannot update Postgres")
                return state
            
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            cursor.execute(
                '''UPDATE "QuestionPaper" 
                   SET status = %s, questions = %s, "updatedAt" = NOW() 
                   WHERE id = %s''',
                ('READY', json.dumps(state.grouped_questions), qp_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Updated QuestionPaper {qp_id} via psycopg2")
            
        except Exception as e:
            print(f"❌ Failed to update Postgres via psycopg2: {e}")
            
    except Exception as e:
        print(f"❌ Failed to update QuestionPaper in Postgres: {e}")
    
    return state

# Create LangGraph workflow
def create_qp_workflow() -> CompiledStateGraph:
    """
    Create the LangGraph workflow for question paper generation
    """
    # Define the state graph
    workflow = StateGraph(QPInputState)
    
    # Add nodes
    workflow.add_node("fetch_metadata", get_all_questions_metadata)
    workflow.add_node("plan_generation", plan_qp_generation)
    workflow.add_node("fetch_content", get_selected_questions_with_content)
    workflow.add_node("group_questions", group_questions_by_context)
    workflow.add_node("store_redis", store_in_redis)
    workflow.add_node("store_postgres", store_in_postgres)
    
    # Define the workflow edges
    workflow.set_entry_point("fetch_metadata")
    workflow.add_edge("fetch_metadata", "plan_generation")
    workflow.add_edge("plan_generation", "fetch_content")
    workflow.add_edge("fetch_content", "group_questions")
    workflow.add_edge("group_questions", "store_redis")
    workflow.add_edge("store_redis", "store_postgres")
    workflow.add_edge("store_postgres", END)
    
    # Compile the workflow
    return workflow.compile()


# Example usage
if __name__ == "__main__":
    # Create workflow
    app = create_qp_workflow()
    
    # Example input state
    input_state = QPInputState(
        document_id="doc_6254073599723273478",  # Use your actual document ID
        duration=30,  # 30 minutes
        num_questions=8,
        difficulty_levels=["basic", "intermediate"],
        question_types=["long_answer", "multiple_choice"],
        bloom_levels=["remember", "understand", "apply"],
        type_of_qp="regular"
    )
    
    # Run the workflow
    try:
        result = app.invoke(input_state)
        print(f"\n🎉 Workflow completed!")
        print(f"📊 Total questions metadata fetched: {len(result.get('all_questions_metadata', []))}")
        print(f"🎯 Selected question IDs: {len(result.get('selected_question_ids', []))}")
        print(f"📄 Questions with content: {len(result.get('selected_questions_with_content', []))}")
        print(f"📋 Question groups created: {len(result.get('grouped_questions', []))}")
        
        # Print the final grouped structure - this is what the exam agent will receive
        if result.get('grouped_questions'):
            print(f"\n📋 FINAL OUTPUT FOR EXAM AGENT (Simplified Format):")
            for i, question in enumerate(result['grouped_questions'][:3]):  # Show first 3 questions
                print(f"\n   📖 Question {i+1}:")
                print(f"      ID: {question['question_id']}")
                print(f"      Text: {question['text'][:100]}...")
                print(f"      Context: {question['context'][:100]}...")
            
            if len(result['grouped_questions']) > 3:
                print(f"\n   ... and {len(result['grouped_questions']) - 3} more questions")
            
            print(f"\n✅ Ready for Redis storage: {len(result['grouped_questions'])} questions in simplified format")
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()