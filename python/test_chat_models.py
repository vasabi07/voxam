"""
Chat Model Quality Comparison (DeepInfra)
==========================================
Compares models for the RAG chat interface:
- Nemotron 3 Nano 30B (new, cheap, reasoning-optimized)
- Llama 3.3 70B (baseline)
- GPT-4o-mini (current, via OpenAI)

Tests with RAG-style prompts (context + question).
"""
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# DeepInfra client
deepinfra_client = OpenAI(
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    base_url="https://api.deepinfra.com/v1/openai",
)

# OpenAI client for GPT-4o-mini comparison
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Models to test
MODELS = [
    ("nvidia/Nemotron-3-Nano-30B-A3B", "Nemotron 3 Nano 30B", deepinfra_client),
    ("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B", deepinfra_client),
    ("gpt-4o-mini", "GPT-4o-mini", openai_client),
]

# RAG-style system prompt (simulating chat_agent.py)
SYSTEM_PROMPT = """You are an intelligent study assistant for Voxam, an AI-powered exam preparation platform.

CONTEXT FROM COURSE MATERIALS:
Water (H₂O) is a chemical compound consisting of two hydrogen atoms covalently bonded to one oxygen atom.
Water is essential for life because:
1. It is a universal solvent - dissolves many substances
2. It regulates body temperature through sweating and respiration
3. It participates in metabolic reactions like hydrolysis
4. It provides structural support to cells through turgor pressure

Photosynthesis is the process by which plants convert light energy into chemical energy.
The equation is: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂

INSTRUCTIONS:
1. Answer based ONLY on the provided context
2. Be helpful and educational
3. Cite sources when possible
4. Keep responses concise (2-3 sentences preferred)"""

# Test questions
TEST_QUESTIONS = [
    "What is the chemical formula of water?",
    "Why is water important for cells?",
    "Explain photosynthesis in simple terms.",
    "What are the products of photosynthesis?",
]


def test_model(client, model_id: str, model_name: str, question: str):
    """Test a single model"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    start = time.time()
    first_token_time = None
    tokens = []
    
    try:
        stream = client.chat.completions.create(
            model=model_id,
            messages=messages,
            stream=True,
            max_tokens=150,
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
        }
        
    except Exception as e:
        return {
            "model": model_name,
            "ttft": None,
            "total": None,
            "response": f"ERROR: {e}",
        }


def main():
    print("=" * 70)
    print("🧪 CHAT MODEL QUALITY COMPARISON")
    print("   (RAG-style prompts for chat interface)")
    print("=" * 70)
    
    all_results = {model[1]: [] for model in MODELS}
    
    for question in TEST_QUESTIONS:
        print(f"\n{'='*70}")
        print(f"❓ Question: {question}")
        print("=" * 70)
        
        for model_id, model_name, client in MODELS:
            result = test_model(client, model_id, model_name, question)
            all_results[model_name].append(result)
            
            ttft_str = f"{result['ttft']:.3f}s" if result['ttft'] else "N/A"
            print(f"\n🤖 {model_name} (TTFT: {ttft_str})")
            print(f"   {result['response'][:150]}...")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 LATENCY SUMMARY (Average)")
    print("=" * 70)
    
    for model_name, results in all_results.items():
        ttfts = [r['ttft'] for r in results if r['ttft']]
        totals = [r['total'] for r in results if r['total']]
        
        if ttfts:
            avg_ttft = sum(ttfts) / len(ttfts)
            avg_total = sum(totals) / len(totals)
            print(f"   {model_name:<25} TTFT: {avg_ttft:.3f}s  Total: {avg_total:.3f}s")
    
    print("\n" + "=" * 70)
    print("💰 COST COMPARISON (per chat: 2K input + 500 output)")
    print("=" * 70)
    print("   Nemotron 3 Nano 30B:  ₹0.012")
    print("   Llama 3.3 70B:        ₹0.017")
    print("   GPT-4o-mini:          ₹0.050")
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
