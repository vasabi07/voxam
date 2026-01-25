
import os
import sys
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# Ensure we use the same Redis URL as the app
load_dotenv()
os.environ.setdefault("REDIS_URI", "redis://localhost:6379")

# Add path to allow imports
sys.path.append(os.getcwd())

async def run_part_1(thread_id):
    print(f"\n--- PART 1: Setting State (Thread: {thread_id}) ---")
    try:
        from agents.chat_agent import chat_graph
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1. Send a message to establish state
        print("sending: 'Hi, remember that the secret code is BANANA-42'")
        response = await chat_graph.ainvoke(
            {"messages": [HumanMessage(content="Hi, remember that the secret code is BANANA-42")]},
            config=config
        )
        print(f"✅ Part 1 complete. Msg count: {len(response['messages'])}")
        
    except Exception as e:
        print(f"❌ Part 1 Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

async def run_part_2(thread_id):
    print(f"\n--- PART 2: Verifying Persistence (Thread: {thread_id}) ---")
    try:
        # Re-import to simulate fresh start (though irrelevant in same script, 
        # the key is we rely on Redis not memory)
        from agents.chat_agent import chat_graph
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # 2. Ask for the state
        print("sending: 'What is the secret code I told you?'")
        response = await chat_graph.ainvoke(
            {"messages": [HumanMessage(content="What is the secret code I told you?")]},
            config=config
        )
        
        # Check message count
        msg_count = len(response["messages"])
        print(f"Message Count: {msg_count}")
        
        # Check history content
        all_content = " ".join([m.content for m in response["messages"]])
        
        if msg_count > 2:
            print("✅ SUCCESS: Found history (more than 1 message)!")
            if "BANANA" in all_content:
                print("✅ Found BANANA in history.")
            else:
                print("⚠️  BANANA not found in history content (might be summarized?)")
        else:
            print("❌ FAILURE: Only found current message. Persistence failed.")
            
    except Exception as e:
        print(f"❌ Part 2 Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_persistence.py [part1|part2] [thread_id]")
        sys.exit(1)
        
    mode = sys.argv[1]
    thread_id = sys.argv[2]
    
    if mode == "part1":
        asyncio.run(run_part_1(thread_id))
    elif mode == "part2":
        asyncio.run(run_part_2(thread_id))
