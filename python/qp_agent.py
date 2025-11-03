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

# Neo4j connection details (read from environment where possible)
# Set NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD in your environment for production
URI = os.getenv("NEO4J_URI", "neo4j+s://4368da67.databases.neo4j.io")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "R3vOL-3PBOuI-pJDxtla-PhRnPRdJNfQJOT6gBfrjb0"))

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
    Returns only essential fields needed for question selection.
    """
    print(f"📋 Fetching question metadata for document: {input_state.document_id}")
    
    driver = get_database_driver()
    with driver as session:
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_CHUNK]->(c:Chunk)-[:HAS_QUESTION]->(q:Question)
        WHERE ($difficulty_levels IS NULL OR q.difficulty IN $difficulty_levels)
        AND ($question_types IS NULL OR q.question_type IN $question_types)
        AND ($bloom_levels IS NULL OR q.bloom_level IN $bloom_levels)
        RETURN 
            q.id as question_id,
            coalesce(q.expected_time, 5) as expected_time,
            coalesce(q.bloom_level, 'remember') as bloom_level,
            coalesce(q.difficulty, 'basic') as difficulty,
            coalesce(q.question_type, 'multiple_choice') as question_type,
            c.id as chunk_id,
            coalesce(c.chunk_index, 0) as chunk_index
        ORDER BY c.chunk_index
        """
        
        result = session.execute_query(
            query,
            document_id=input_state.document_id,
            difficulty_levels=input_state.difficulty_levels,
            question_types=input_state.question_types,
            bloom_levels=input_state.bloom_levels
        )
        
        # Convert to list of dictionaries with safe field access
        questions_metadata = []
        for record in result.records:
            try:
                questions_metadata.append({
                    "question_id": record.get("question_id", ""),
                    "expected_time": record.get("expected_time", 5),
                    "bloom_level": record.get("bloom_level", "remember"),
                    "difficulty": record.get("difficulty", "basic"),
                    "question_type": record.get("question_type", "multiple_choice"),
                    "chunk_id": record.get("chunk_id", ""),
                    "chunk_index": record.get("chunk_index", 0)
                })
            except Exception as e:
                print(f"⚠️ Error processing record: {e}")
                print(f"Record keys: {list(record.keys())}")
                continue
        
        print(f"✅ Found {len(questions_metadata)} questions matching criteria")
        
        # Update state
        input_state.all_questions_metadata = questions_metadata
        return input_state


def get_selected_questions_with_content(input_state: QPInputState):
    """
    Fetch full question content for selected questions only.
    This is called after planning to get complete question data.
    """
    if not input_state.selected_question_ids:
        print("⚠️ No questions selected yet")
        return input_state
    
    print(f"📄 Fetching full content for {len(input_state.selected_question_ids)} selected questions")
    
    driver = get_database_driver()
    with driver as session:
        query = """
        MATCH (c:Chunk)-[:HAS_QUESTION]->(q:Question)
        WHERE q.id IN $question_ids
        RETURN 
            coalesce(q.id, '') as question_id,
            coalesce(q.text, '') as text,
            coalesce(q.options, []) as options,
            coalesce(q.correct_answer, '') as correct_answer,
            coalesce(q.explanation, '') as explanation,
            coalesce(q.key_points, []) as key_points,
            coalesce(q.expected_time, 0) as expected_time,
            coalesce(q.bloom_level, '') as bloom_level,
            coalesce(q.difficulty, '') as difficulty,
            coalesce(q.question_type, '') as question_type,
            coalesce(c.content, '') as context_content,
            coalesce(c.chunk_index, 0) as chunk_index,
            coalesce(c.id, '') as chunk_id
        ORDER BY c.chunk_index
        """
        
        result = session.execute_query(
            query,
            question_ids=input_state.selected_question_ids
        )
        
        # Convert to list of dictionaries with safe field access
        questions_with_content = []
        for record in result.records:
            questions_with_content.append({
                "question_id": record.get("question_id", ""),
                "text": record.get("text", ""),
                "options": record.get("options", []),
                "correct_answer": record.get("correct_answer", ""),
                "explanation": record.get("explanation", ""),
                "key_points": record.get("key_points", []),
                "expected_time": record.get("expected_time", 0),
                "bloom_level": record.get("bloom_level", ""),
                "difficulty": record.get("difficulty", ""),
                "question_type": record.get("question_type", ""),
                "context_content": record.get("context_content", ""),
                "chunk_index": record.get("chunk_index", 0),
                "chunk_id": record.get("chunk_id", "")
            })
        
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
                'context': question.get('context_content', ''),  # Renamed from context_content to context
                'questions': []
            }
        
        # Add question in simplified format - only essential fields
        question_data = {
            'question_id': question.get('question_id'),
            'text': question.get('text'),
            'context': question.get('context_content', '')  # Each question gets its context
        }
        
        context_groups[chunk_id]['questions'].append(question_data)
    
    # Convert to flat list of questions (simplified format for exam agent)
    # Each question will have its own context, making it easy for Redis storage
    simplified_questions = []
    
    for group in sorted(context_groups.values(), key=lambda x: x['chunk_index']):
        for question in group['questions']:
            simplified_questions.append({
                'question_id': question['question_id'],
                'text': question['text'], 
                'context': group['context']  # Use the group's context for all questions in that group
            })
    
    # Store as grouped questions for compatibility, but in simplified format
    state.grouped_questions = simplified_questions
    
    # Print summary
    total_questions = len(simplified_questions)
    unique_contexts = len(set(q['context'] for q in simplified_questions))
    
    print(f"✅ Created {total_questions} questions with {unique_contexts} unique contexts")
    print(f"📋 Simplified format: question_id, text, context")
    
    return state

def store_in_redis(state: QPInputState) -> QPInputState:
    """
    use the qp_id recieved from the user to store the final output in redis
    save as a json array of questions with their context
    """
    from redis import Redis
    REDIS_URI = "redis://localhost:6379"
    qp_id = state.qp_id  # Use the qp_id from Next.js (meeting.id)

    r = Redis(host="localhost", port=6379, decode_responses=True)
    if not state.grouped_questions:
        print("⚠️ No grouped questions to store in Redis")
        return state    
    try:
        r.json().set(f"qp:{qp_id}:questions", '$', state.grouped_questions)
        print(f"✅ Stored {len(state.grouped_questions)} questions in Redis under qp_id: {qp_id}")
    except Exception as e:
        print(f"⚠️ Failed to store questions in Redis: {e}")
    
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
    
    # Define the workflow edges
    workflow.set_entry_point("fetch_metadata")
    workflow.add_edge("fetch_metadata", "plan_generation")
    workflow.add_edge("plan_generation", "fetch_content")
    workflow.add_edge("fetch_content", "group_questions")
    workflow.add_edge("group_questions", "store_redis")
    workflow.add_edge("store_redis", END)
    
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