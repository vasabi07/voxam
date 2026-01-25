# Tool Selection Rules

Decision guide for choosing the right tool based on user intent.

## Decision Tree

```
User Query
    │
    ├─► "upload", "add document", "ingest" ──────────► request_upload_ui()
    │
    ├─► "create exam/quiz/test", "question paper" ──► request_qp_form()
    │
    ├─► "study", "learn", "tutor me" ───────────────► request_learn_form()
    │
    ├─► Structure questions ────────────────────────► query_structure()
    │   ("what chapters?", "list sections",
    │    "how many topics?", "show outline")
    │
    ├─► Content questions ──────────────────────────► search_documents()
    │   ("explain X", "what is Y?", "how does Z work?",
    │    "define...", "describe...")
    │
    ├─► Practice requests ──────────────────────────► get_questions()
    │   ("quiz me", "give me a question",
    │    "test my knowledge", "practice problem")
    │
    ├─► Need formatting guidance ───────────────────► get_rules()
    │   (math equations, citations, complex response)
    │
    └─► Ambiguous/unclear ──────────────────────────► Ask clarifying question
```

## When to Use Each Tool

### search_documents(query)
Use for understanding CONTENT:
- "What is Newton's third law?"
- "Explain the water cycle"
- "How does photosynthesis work?"
- "Define entropy"
- "What happened in the French Revolution?"

### query_structure(question)
Use for understanding ORGANIZATION:
- "What chapters are in this book?"
- "List the sections in Chapter 3"
- "How many definitions are there?"
- "What topics does this cover?"
- "Show me the outline"

### get_questions(chapter?, difficulty?, count?)
Use for PRACTICE:
- "Give me a question"
- "Quiz me on thermodynamics"
- "I want to practice Chapter 5"
- "Show me some hard problems"

### get_rules(topics)
Use BEFORE responding when you need guidance on:
- "math" - When your response will include equations
- "sources" - When you'll cite from search_documents
- "style" - For complex explanations needing structure
- "tools" - When unsure which tool to use

### UI Tools
- `request_upload_ui()` - User wants to add/upload a document
- `request_qp_form()` - User wants to create an exam/test
- `request_learn_form()` - User wants to start a study/tutoring session
- `show_sources(sources)` - Display citations after answering

### web_search(query)
Use ONLY when:
1. Content isn't in user's documents
2. You've offered to search the web
3. User explicitly confirmed (said yes/sure/ok)

## Chaining Tools

You can chain tools for complex queries:

**Example**: "Explain the main concept in Chapter 2"
1. First: `query_structure("what is chapter 2 about")` - understand what's there
2. Then: `search_documents("chapter 2 main concept")` - get the content

**Example**: "Quiz me on what we just discussed"
1. Recall the topic from conversation context
2. Call: `get_questions(chapter="relevant chapter")`

## When NOT to Use Tools

- Simple greetings ("Hi", "Hello") - just respond
- Follow-up clarifications - use conversation context
- Opinions or general knowledge not requiring documents
