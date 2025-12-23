"""
Correction Agent using Kimi-K2-Thinking for deep exam analysis.

This agent:
1. Receives exam conversation + question paper
2. Analyzes each answer against correct_answer and key_points
3. Calculates Bloom's taxonomy and difficulty breakdowns
4. Generates detailed feedback and recommendations
"""
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Kimi-K2-Thinking via DeepInfra
llm = ChatOpenAI(
    model="moonshotai/Kimi-K2-Thinking",
    base_url="https://api.deepinfra.com/v1/openai",
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    temperature=0.3,
    max_tokens=8000,
)


# ============ Schemas ============

class BloomBreakdown(BaseModel):
    remember: float = Field(default=0.0, description="Score % for remember-level questions")
    understand: float = Field(default=0.0, description="Score % for understand-level questions")
    apply: float = Field(default=0.0, description="Score % for apply-level questions")
    analyze: float = Field(default=0.0, description="Score % for analyze-level questions")
    evaluate: float = Field(default=0.0, description="Score % for evaluate-level questions")
    create: float = Field(default=0.0, description="Score % for create-level questions")


class QuestionResult(BaseModel):
    question_index: int
    question_text: str
    bloom_level: str
    difficulty: str
    user_answer_summary: str
    is_correct: Optional[bool] = None  # None if partial
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    key_points_covered: list[str] = []
    key_points_missed: list[str] = []
    improvement_tips: str = ""


class CorrectionReport(BaseModel):
    exam_id: str
    user_id: str
    
    # Scores
    total_score: float = Field(ge=0.0, le=100.0)
    questions_attempted: int
    questions_correct: int
    
    # Bloom's Taxonomy Breakdown
    bloom_breakdown: BloomBreakdown
    
    # Difficulty Breakdown
    basic_score: float = 0.0
    intermediate_score: float = 0.0
    advanced_score: float = 0.0
    
    # Analysis
    strengths: list[str] = []
    weaknesses: list[str] = []
    overall_feedback: str
    study_recommendations: list[str] = []
    
    # Per-question breakdown
    question_results: list[QuestionResult] = []
    
    # Meta
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = "Kimi-K2-Thinking"


class CorrectionInput(BaseModel):
    exam_id: str
    qp_id: str
    user_id: str
    thread_id: str
    mode: str = "exam"
    questions: list[dict]  # From QP in Redis
    messages: list[dict]   # From conversation
    total_questions: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


# ============ Prompts ============

CORRECTION_PROMPT = """You are an expert exam evaluator and educational analyst.

## EXAM QUESTIONS
Each question has metadata including bloom_level (remember/understand/apply/analyze/evaluate/create), difficulty (basic/intermediate/advanced), correct_answer, and key_points.

```json
{questions_json}
```

## EXAM CONVERSATION
This is the full conversation between the exam agent and student. Extract the student's answers for each question.

```
{conversation}
```

## YOUR TASK

1. **For each question:**
   - Identify the student's answer(s) from the conversation
   - Compare against correct_answer and key_points
   - Score from 0.0 (completely wrong) to 1.0 (perfect)
   - List which key_points were covered vs missed
   - Provide constructive feedback

2. **Calculate Bloom's Taxonomy Breakdown:**
   - Group questions by bloom_level
   - Calculate average score for each level
   - Return as percentages (0-100)

3. **Calculate Difficulty Breakdown:**
   - Group questions by difficulty (basic/intermediate/advanced)
   - Calculate average score for each level

4. **Provide Overall Analysis:**
   - 3-5 specific strengths (what they did well)
   - 3-5 specific weaknesses (areas needing improvement)
   - Overall feedback paragraph
   - 3-5 study recommendations

## OUTPUT FORMAT
Return ONLY valid JSON matching this schema (no markdown code blocks):
{output_schema}
"""


def format_conversation(messages: list[dict]) -> str:
    """Format messages for the prompt."""
    lines = []
    for msg in messages:
        role = msg.get("type", msg.get("role", "unknown"))
        content = msg.get("content", "")
        
        if role in ["human", "user"]:
            lines.append(f"STUDENT: {content}")
        elif role in ["ai", "assistant"]:
            lines.append(f"AGENT: {content}")
        elif role == "system":
            continue  # Skip system messages
        else:
            lines.append(f"{role.upper()}: {content}")
    
    return "\n".join(lines)


def generate_correction_report(input_data: CorrectionInput) -> CorrectionReport:
    """
    Generate a detailed correction report using Kimi-K2-Thinking.
    
    Args:
        input_data: CorrectionInput with questions and conversation
        
    Returns:
        CorrectionReport with full analysis
    """
    # Build the prompt
    output_schema = CorrectionReport.model_json_schema()
    
    prompt = CORRECTION_PROMPT.format(
        questions_json=json.dumps(input_data.questions, indent=2, default=str),
        conversation=format_conversation(input_data.messages),
        output_schema=json.dumps(output_schema, indent=2)
    )
    
    print(f"📝 Generating correction report for exam {input_data.exam_id}...")
    print(f"   Questions: {len(input_data.questions)}, Messages: {len(input_data.messages)}")
    
    # Call Kimi-K2-Thinking
    response = llm.invoke(prompt)
    
    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        report_data = json.loads(content)
        
        # Add metadata
        report_data["exam_id"] = input_data.exam_id
        report_data["user_id"] = input_data.user_id
        report_data["generated_at"] = datetime.utcnow().isoformat()
        report_data["model_used"] = "Kimi-K2-Thinking"
        
        return CorrectionReport(**report_data)
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Kimi response: {e}")
        print(f"   Raw response: {response.content[:500]}...")
        
        # Return a fallback report
        return CorrectionReport(
            exam_id=input_data.exam_id,
            user_id=input_data.user_id,
            total_score=0.0,
            questions_attempted=0,
            questions_correct=0,
            bloom_breakdown=BloomBreakdown(),
            overall_feedback="Failed to generate report. Please try again.",
            strengths=["Report generation failed"],
            weaknesses=["Unable to analyze responses"],
            study_recommendations=["Retake the exam for analysis"],
        )


# ============ Test ============

if __name__ == "__main__":
    # Test with mock data
    test_input = CorrectionInput(
        exam_id="test_exam_1",
        qp_id="qp1",
        user_id="user_123",
        thread_id="thread_123",
        mode="exam",
        total_questions=2,
        questions=[
            {
                "text": "What is the chemical formula of water?",
                "correct_answer": "H2O",
                "key_points": ["hydrogen", "oxygen", "2 hydrogen atoms", "1 oxygen atom"],
                "bloom_level": "remember",
                "difficulty": "basic",
                "question_type": "short_answer"
            },
            {
                "text": "Explain the process of photosynthesis",
                "correct_answer": "Photosynthesis converts CO2 and water into glucose using sunlight",
                "key_points": ["carbon dioxide", "water", "glucose", "sunlight", "chlorophyll", "oxygen released"],
                "bloom_level": "understand",
                "difficulty": "intermediate",
                "question_type": "long_answer"
            }
        ],
        messages=[
            {"type": "ai", "content": "Welcome to your exam. Question 1: What is the chemical formula of water?"},
            {"type": "human", "content": "H2O, it has 2 hydrogen and 1 oxygen"},
            {"type": "ai", "content": "Answer recorded. Ready for the next question?"},
            {"type": "human", "content": "Yes"},
            {"type": "ai", "content": "Question 2: Explain the process of photosynthesis"},
            {"type": "human", "content": "Plants use sunlight to convert carbon dioxide into glucose. They also release oxygen."},
            {"type": "ai", "content": "Answer recorded. That was the last question."},
        ]
    )
    
    report = generate_correction_report(test_input)
    print("\n=== CORRECTION REPORT ===")
    print(report.model_dump_json(indent=2))
