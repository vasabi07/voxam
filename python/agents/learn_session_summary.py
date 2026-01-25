"""
Pydantic models for LearnSession summary generation.
Following the CorrectionReport pattern for structured LLM output.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TopicCoverage(BaseModel):
    """Coverage analysis for a single topic."""
    topic_name: str = Field(description="Name of the topic covered")
    concepts_explained: List[str] = Field(default_factory=list, description="Key concepts that were explained")
    concepts_student_struggled_with: List[str] = Field(default_factory=list, description="Concepts the student found difficult")
    understanding_score: float = Field(ge=0.0, le=1.0, default=0.5, description="0-1 score of student understanding")


class LearnSessionSummary(BaseModel):
    """LLM-generated summary of a learn session."""
    # Overview
    session_title: str = Field(description="Brief title summarizing the session (e.g., 'Introduction to Photosynthesis')")
    summary: str = Field(description="2-3 sentence summary of what was learned and discussed")

    # Topic Analysis
    topics_covered: List[TopicCoverage] = Field(default_factory=list, description="Detailed coverage for each topic")
    total_topics_planned: int = Field(default=0, description="Total number of topics planned for this session")
    topics_completed: int = Field(default=0, description="Number of topics fully covered")

    # Student Performance
    overall_understanding: float = Field(ge=0.0, le=1.0, default=0.5, description="Overall understanding score 0-1")
    strengths: List[str] = Field(default_factory=list, description="What the student understood well")
    areas_to_review: List[str] = Field(default_factory=list, description="Concepts needing more practice")

    # Next Steps
    recommended_next_topics: List[str] = Field(default_factory=list, description="Topics to study next")
    study_tips: List[str] = Field(default_factory=list, description="Personalized study recommendations")

    # Meta
    message_count: int = Field(default=0, description="Total number of messages in the session")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = Field(default="nvidia/Nemotron-3-Nano-30B-A3B")


class LearnSessionInput(BaseModel):
    """Input data for generating a session summary."""
    thread_id: str
    lp_id: str
    user_id: Optional[str] = None
    topics: List[dict] = Field(default_factory=list, description="All topics from the Learn Pack")
    current_topic_index: int = Field(default=0, description="Index of the last topic being discussed")
    messages: List[dict] = Field(default_factory=list, description="Conversation history")


# Summary generation prompt template
SUMMARY_PROMPT = """You are an educational analyst. Analyze this tutoring session and generate a structured summary.

## SESSION INFO
- Topics planned: {topics_list}
- Current topic index: {current_topic_index}
- Message count: {message_count}

## CONVERSATION
{conversation}

## YOUR TASK
Analyze the conversation and extract:
1. A concise session title
2. A 2-3 sentence summary
3. For each topic discussed, list concepts explained and any the student struggled with
4. Overall understanding score (0-1)
5. Student's strengths and areas to review
6. Recommended next topics and study tips

## OUTPUT FORMAT
Return ONLY valid JSON matching this schema (no markdown code blocks):
{output_schema}
"""
