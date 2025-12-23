"""
LLM Quality Comparison Test (Cerebras)
======================================
Compares response quality and latency across models:
- Llama 3.3 70B
- Llama 3.1 8B
- Qwen 3 32B (replaces OpenAI OSS which isn't on Cerebras)

Outputs responses side-by-side for human evaluation.
"""
import os
import time
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))

# Models to test (Cerebras availability)
MODELS = [
    ("llama-3.3-70b", "Llama 3.3 70B"),
    ("llama3.1-8b", "Llama 3.1 8B"),
    ("gpt-oss-120b", "GPT OSS 120B"),
]

# Professor Venkat system prompt
SYSTEM_PROMPT = """You are Professor Venkat, a friendly Chemistry teacher conducting a voice exam.
You are asking students questions and providing feedback on their answers.

CONTEXT FROM COURSE MATERIALS:
Water (H₂O) is a chemical compound consisting of two hydrogen atoms covalently bonded to one oxygen atom.
Water is essential for life because:
1. It is a universal solvent
2. It regulates body temperature
3. It participates in metabolic reactions
4. It provides structural support to cells

INSTRUCTIONS:
1. Evaluate the student's answer against the context
2. Provide brief, encouraging feedback (2-3 sentences MAX)
3. If correct, praise and add a small insight
4. If incorrect, gently correct and explain
5. Speak naturally as if in a real conversation"""

# Test scenarios
TEST_CASES = [
    {
        "question": "What is the chemical formula of water?",
        "answer": "H2O",
        "type": "correct_simple",
    },
    {
        "question": "Why is water important for life?",
        "answer": "Water is important because it helps regulate body temperature and is a universal solvent.",
        "type": "correct_detailed",
    },
    {
        "question": "What is the chemical formula of water?",
        "answer": "CO2",
        "type": "wrong",
    },
    {
        "question": "Why is water important for life?",
        "answer": "It's important for drinking.",
        "type": "partial",
    },
]


def test_model(model_id: str, model_name: str, question: str, answer: str):
    """Test a single model with a Q&A pair"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question I asked: {question}\n\nStudent's answer: {answer}"},
    ]
    
    start = time.time()
    first_token_time = None
    tokens = []
    
    try:
        stream = client.chat.completions.create(
            model=model_id,
            messages=messages,
            stream=True,
            max_completion_tokens=100,
            temperature=0.7,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                if first_token_time is None:
                    first_token_time = time.time() - start
                tokens.append(chunk.choices[0].delta.content)
        
        total = time.time() - start
        response = "".join(tokens)
        
        return {
            "model": model_name,
            "ttft": first_token_time,
            "total": total,
            "response": response,
            "tokens": len(tokens),
        }
        
    except Exception as e:
        return {
            "model": model_name,
            "ttft": None,
            "total": None,
            "response": f"ERROR: {e}",
            "tokens": 0,
        }


def main():
    print("=" * 70)
    print("🧪 LLM QUALITY COMPARISON TEST (Cerebras)")
    print("=" * 70)
    
    for test_case in TEST_CASES:
        print(f"\n{'='*70}")
        print(f"📝 Test Type: {test_case['type'].upper()}")
        print(f"   Q: {test_case['question']}")
        print(f"   A: {test_case['answer']}")
        print("=" * 70)
        
        results = []
        
        for model_id, model_name in MODELS:
            result = test_model(model_id, model_name, test_case['question'], test_case['answer'])
            results.append(result)
            
            ttft_str = f"{result['ttft']:.3f}s" if result['ttft'] else "N/A"
            print(f"\n🤖 {model_name} (TTFT: {ttft_str})")
            print(f"   {result['response'][:200]}...")
        
        # Side-by-side latency
        print(f"\n⏱️  Latency Comparison:")
        for r in results:
            ttft_str = f"{r['ttft']:.3f}s" if r['ttft'] else "N/A"
            total_str = f"{r['total']:.3f}s" if r['total'] else "N/A"
            print(f"   {r['model']:<20} TTFT: {ttft_str:<8} Total: {total_str}")
    
    print("\n" + "=" * 70)
    print("✅ Test complete! Review responses above for quality comparison.")
    print("=" * 70)


if __name__ == "__main__":
    main()
