"""
Cerebras LLM Latency Test
==========================
Tests Cerebras inference latency with exam agent scenario.
Measures TTFT (Time to First Token) and total time.
"""
import os
import time
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))

MODEL = "llama-3.3-70b"

# Simulated exam context (same as DeepInfra test)
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
2. Provide brief, encouraging feedback (2-3 sentences)
3. If correct, praise and add a small insight
4. If incorrect, gently correct and explain"""

CURRENT_QUESTION = "What is the chemical formula of water, and why is it important for life?"

STUDENT_ANSWERS = {
    "correct": "Water has the formula H2O. It's important because it's a universal solvent and helps regulate body temperature.",
    "partial": "Water is H2O. It's important for drinking.",
    "wrong": "Water is made of oxygen and carbon. It's important for breathing.",
}


def test_streaming(student_answer: str, label: str):
    """Test streaming LLM response"""
    print(f"\n📝 Testing: {label.upper()} answer")
    print(f"   Student: \"{student_answer[:60]}...\"")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {CURRENT_QUESTION}\n\nStudent's answer: {student_answer}"},
    ]
    
    start = time.time()
    first_token_time = None
    tokens = []
    
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            max_completion_tokens=150,
            temperature=0.7,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                if first_token_time is None:
                    first_token_time = time.time() - start
                tokens.append(chunk.choices[0].delta.content)
        
        total = time.time() - start
        response = "".join(tokens)
        
        print(f"   🚀 TTFT: {first_token_time:.3f}s | Total: {total:.3f}s | Tokens: {len(tokens)}")
        print(f"   🤖 Response: \"{response[:100]}...\"")
        
        return first_token_time, total
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, None


def test_non_streaming(student_answer: str, label: str):
    """Test non-streaming LLM response"""
    print(f"\n📝 Testing NON-STREAMING: {label}")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {CURRENT_QUESTION}\n\nStudent's answer: {student_answer}"},
    ]
    
    start = time.time()
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=False,
            max_completion_tokens=150,
            temperature=0.7,
        )
        
        total = time.time() - start
        content = response.choices[0].message.content
        
        print(f"   ⏱️  Total time: {total:.3f}s")
        print(f"   🤖 Response: \"{content[:100]}...\"")
        
        return total
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    print("=" * 60)
    print("🧠 CEREBRAS LLM LATENCY TEST - Llama 3.3 70B")
    print("   (Known for ultra-fast inference)")
    print("=" * 60)
    
    results = {}
    
    for label, answer in STUDENT_ANSWERS.items():
        ttft, total = test_streaming(answer, label)
        results[label] = {"ttft": ttft, "total": total}
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY - Streaming LLM Response")
    print("=" * 60)
    print(f"{'Answer Type':<12} {'TTFT':<12} {'Total':<12}")
    print("-" * 40)
    
    for label, data in results.items():
        ttft_str = f"{data['ttft']:.3f}s" if data['ttft'] else "N/A"
        total_str = f"{data['total']:.3f}s" if data['total'] else "N/A"
        print(f"{label:<12} {ttft_str:<12} {total_str:<12}")
    
    # Non-streaming comparison
    print("\n" + "=" * 60)
    print("📊 Non-Streaming Comparison")
    print("=" * 60)
    
    ns_total = test_non_streaming(STUDENT_ANSWERS["correct"], "correct")
    if ns_total and results['correct']['ttft']:
        print(f"\n   Non-streaming total: {ns_total:.3f}s")
        print(f"   Streaming TTFT advantage: {ns_total - results['correct']['ttft']:.3f}s faster first token")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
