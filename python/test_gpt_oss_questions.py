"""
Test GPT OSS 120B for question generation quality.
Evaluates Bloom's taxonomy distribution and question quality.
"""

import httpx
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

load_dotenv()

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class Difficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Question(BaseModel):
    text: str = Field(description="The question text")
    bloom_level: BloomLevel = Field(description="Bloom's taxonomy level")
    difficulty: Difficulty = Field(description="Difficulty level")
    question_type: str = Field(description="long_answer or multiple_choice")
    expected_time: int = Field(description="Expected time in minutes")
    key_points: Optional[List[str]] = Field(default=None, description="Key points for answer")
    options: Optional[List[str]] = Field(default=None, description="MCQ options")
    correct_answer: Optional[str] = Field(default=None, description="Correct answer for MCQ")


class QuestionSet(BaseModel):
    long_answer_questions: List[Question] = Field(description="Long answer questions")
    multiple_choice_questions: List[Question] = Field(description="Multiple choice questions")


# Sample section from the chapter
SAMPLE_SECTION = """
## Section: Animals - Nervous System

In animals, control and coordination are provided by nervous and muscular tissues. 
Touching a hot object is an urgent and dangerous situation. We need to detect it and respond to it.

All information from our environment is detected by specialized tips of some nerve cells. 
These receptors are usually located in our sense organs, such as the inner ear, the nose, 
the tongue, and so on. Gustatory receptors detect taste while olfactory receptors detect smell.

[IMAGE_1 page=2: Diagram of a neuron showing dendrites, cell body, and axon with labels]

The neuron has three main parts:
- Dendrites: acquire information from receptors or other neurons
- Cell body: contains the nucleus and most of the cell's organelles
- Axon: conducts electrical impulses away from the cell body

Signals are transmitted as electrical impulses and travel from dendrite to cell body to axon end. 
At the axon end, the electrical impulse releases chemicals that cross a gap (synapse) to the next neuron.
"""


def generate_questions_gpt_oss(section_content: str, section_title: str) -> dict:
    """Generate questions using GPT OSS 120B."""
    
    prompt = f"""Generate educational questions for this section.

## Section: {section_title}

## Content:
{section_content}

## Instructions:
1. Generate 3 long answer questions covering key concepts
2. Generate 3 multiple choice questions (4 options each with correct answer marked)
3. Follow Bloom's Taxonomy distribution:
   - At least 1 question at 'remember' level (recall facts from content)
   - At least 1 question at 'understand' level (explain concepts in content)
   - At least 1 question at 'apply' or 'analyze' level (apply or analyze knowledge from content)
4. Vary difficulty across basic, intermediate, advanced
5. Reference the IMAGE marker when relevant
6. Include key_points for long answer questions (answers must come from the content)
7. Include expected_time in minutes

CRITICAL: ALL questions MUST be answerable using ONLY the provided content. 
- For 'apply' and 'analyze' questions: challenge students to think deeper about what IS in the content
- Do NOT require external knowledge or information not present in the section
- The key_points answer should be derivable from the provided text

Return JSON matching this schema:
{{
  "long_answer_questions": [
    {{
      "text": "question text",
      "bloom_level": "remember|understand|apply|analyze|evaluate|create",
      "difficulty": "basic|intermediate|advanced",
      "question_type": "long_answer",
      "expected_time": 5,
      "key_points": ["point1", "point2"]
    }}
  ],
  "multiple_choice_questions": [
    {{
      "text": "question text",
      "bloom_level": "remember|understand|apply|analyze|evaluate|create",
      "difficulty": "basic|intermediate|advanced",
      "question_type": "multiple_choice",
      "expected_time": 2,
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A"
    }}
  ]
}}"""

    response = httpx.post(
        DEEPINFRA_URL,
        headers={
            "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-oss-120b",
            "messages": [
                {"role": "system", "content": "Reasoning: high\nYou are an educational assessment expert. Generate high-quality questions following Bloom's Taxonomy. Always respond with valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.3
        },
        timeout=120.0
    )
    
    result = response.json()
    
    if "error" in result:
        print(f"API Error: {result['error']}")
        return {}, {}
    
    content = result["choices"][0]["message"]["content"]
    
    # Extract JSON from content (may have markdown code blocks)
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    else:
        # Try to find raw JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
    
    # Parse JSON
    questions = json.loads(content)
    return questions, result.get("usage", {})


def evaluate_bloom_distribution(questions: dict) -> dict:
    """Evaluate Bloom's Taxonomy distribution."""
    all_questions = questions.get("long_answer_questions", []) + questions.get("multiple_choice_questions", [])
    
    bloom_counts = {level.value: 0 for level in BloomLevel}
    difficulty_counts = {level.value: 0 for level in Difficulty}
    
    for q in all_questions:
        bloom = q.get("bloom_level", "").lower()
        diff = q.get("difficulty", "").lower()
        
        if bloom in bloom_counts:
            bloom_counts[bloom] += 1
        if diff in difficulty_counts:
            difficulty_counts[diff] += 1
    
    # Bloom's ideal distribution (for educational assessment)
    # Remember: 20%, Understand: 30%, Apply: 25%, Analyze: 15%, Evaluate: 10%
    total = len(all_questions)
    
    return {
        "total_questions": total,
        "bloom_distribution": bloom_counts,
        "difficulty_distribution": difficulty_counts,
        "has_remember": bloom_counts.get("remember", 0) > 0,
        "has_understand": bloom_counts.get("understand", 0) > 0,
        "has_apply_or_analyze": (bloom_counts.get("apply", 0) + bloom_counts.get("analyze", 0)) > 0,
        "bloom_coverage": sum(1 for v in bloom_counts.values() if v > 0)
    }


def main():
    print("=" * 70)
    print("🧪 GPT OSS 120B QUESTION GENERATION TEST")
    print("=" * 70)
    
    print("\n📝 Generating questions with GPT OSS 120B...")
    questions, usage = generate_questions_gpt_oss(SAMPLE_SECTION, "Animals - Nervous System")
    
    print(f"\n📊 Token Usage: {usage.get('prompt_tokens', 'N/A')} in, {usage.get('completion_tokens', 'N/A')} out")
    
    # Display questions
    print("\n" + "=" * 70)
    print("📚 GENERATED QUESTIONS")
    print("=" * 70)
    
    print("\n📖 Long Answer Questions:")
    for i, q in enumerate(questions.get("long_answer_questions", []), 1):
        print(f"\n  Q{i} [{q.get('bloom_level', 'N/A')}, {q.get('difficulty', 'N/A')}, {q.get('expected_time', 'N/A')}min]:")
        print(f"     {q.get('text', 'N/A')}")
        if q.get("key_points"):
            print(f"     Key points: {q['key_points']}")
    
    print("\n📖 Multiple Choice Questions:")
    for i, q in enumerate(questions.get("multiple_choice_questions", []), 1):
        print(f"\n  Q{i} [{q.get('bloom_level', 'N/A')}, {q.get('difficulty', 'N/A')}, {q.get('expected_time', 'N/A')}min]:")
        print(f"     {q.get('text', 'N/A')}")
        if q.get("options"):
            for opt in q["options"]:
                print(f"        {opt}")
        if q.get("correct_answer"):
            print(f"     ✓ Correct: {q['correct_answer']}")
    
    # Evaluate Bloom's distribution
    print("\n" + "=" * 70)
    print("📊 BLOOM'S TAXONOMY EVALUATION")
    print("=" * 70)
    
    eval_result = evaluate_bloom_distribution(questions)
    
    print(f"\n   Total questions: {eval_result['total_questions']}")
    print(f"\n   Bloom's Distribution:")
    for level, count in eval_result['bloom_distribution'].items():
        bar = "█" * count + "░" * (6 - count)
        print(f"      {level:12} [{bar}] {count}")
    
    print(f"\n   Difficulty Distribution:")
    for level, count in eval_result['difficulty_distribution'].items():
        bar = "█" * count + "░" * (6 - count)
        print(f"      {level:12} [{bar}] {count}")
    
    print(f"\n   ✅ Has 'remember' questions: {eval_result['has_remember']}")
    print(f"   ✅ Has 'understand' questions: {eval_result['has_understand']}")
    print(f"   ✅ Has 'apply/analyze' questions: {eval_result['has_apply_or_analyze']}")
    print(f"   📈 Bloom levels covered: {eval_result['bloom_coverage']}/6")
    
    # Quality verdict
    print("\n" + "=" * 70)
    is_good = (
        eval_result['has_remember'] and 
        eval_result['has_understand'] and 
        eval_result['has_apply_or_analyze'] and
        eval_result['bloom_coverage'] >= 3
    )
    
    if is_good:
        print("✅ QUALITY VERDICT: GOOD - Follows Bloom's Taxonomy principles")
    else:
        print("⚠️  QUALITY VERDICT: NEEDS IMPROVEMENT - Missing Bloom's levels")
    print("=" * 70)


if __name__ == "__main__":
    main()
