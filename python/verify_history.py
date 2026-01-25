
import asyncio
import os
from dotenv import load_dotenv
import redis.asyncio as redis
from agents.chat_agent import SafeAsyncRedisSaver, chat_graph
from langgraph.checkpoint.base import CheckpointTuple

load_dotenv()
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")

async def verify_history():
    print(f"Connecting to Redis at {REDIS_URI}...")
    redis_client = redis.from_url(REDIS_URI)
    checkpointer = SafeAsyncRedisSaver(redis_client=redis_client)
    
    # Use a test thread
    thread_id = "history_test_thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Clear previous
    async with redis_client.pipeline() as pipe:
        await pipe.flushdb() # WARNING: Flushes DB for test isolation!
        await pipe.execute()
    print("🧹 Flushed Redis for clean test.")

    print("\n1. Running chat to generate history...")
    # First turn
    await chat_graph.ainvoke(
        {"messages": [{"role": "user", "content": "Hello history"}]}, 
        config=config
    )
    
    # Second turn
    await chat_graph.ainvoke(
        {"messages": [{"role": "user", "content": "Another message"}]}, 
        config=config
    )
    
    print("\n2. Retrieving history...")
    count = 0
    # Use the checkpointer directly via the graph (which uses it) if possible
    # But graph instance in chat_agent is compiled with checkpointer
    # We can access graph.checkpointer
    
    # The graph in chat_agent.py has checkpointer attached
    history_iterator = chat_graph.aget_state_history(config)
    
    async for state in history_iterator:
        count += 1
        msg_count = len(state.values.get("messages", [])) if state.values else 0
        print(f"   Checkpoint {count}: ID={state.config['configurable'].get('checkpoint_id')} | Messages={msg_count}")
        
    if count > 1:
        print(f"\n✅ SUCCESS: Retrieved {count} checkpoints from history.")
    else:
        print(f"\n❌ FAILURE: Retrieved {count} checkpoints (expected > 1).")

if __name__ == "__main__":
    asyncio.run(verify_history())
