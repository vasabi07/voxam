# Source Citation Rules

When you retrieve content using `search_documents`, embed the sources in your response.

## The Citation Flow

1. **Call search_documents** with your query
2. **Parse the response** - it contains content AND a `SOURCES_FOR_CITATION` JSON block at the end
3. **Write your complete explanation** using the content
4. **At the END of your response**, add the sources marker (see format below)

## Source Marker Format

At the very END of your response, add this exact format:
```
<!-- SOURCES: [paste the JSON array from SOURCES_FOR_CITATION here] -->
```

## Example Workflow

User asks: "What is photosynthesis?"

Step 1 - You call:
```
search_documents("photosynthesis definition process")
```

Step 2 - Tool returns:
```
Found 3 relevant passages:

Photosynthesis is the process by which plants convert light energy...
[content continues]

SOURCES_FOR_CITATION: [{"page": 42, "page_end": 43, "title": "Chapter 3: Cell Biology", "doc_id": "abc-123", "doc_title": "Biology Textbook"}]
```

Step 3 - You write your full response:
```
Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize nutrients from carbon dioxide and water.

The process can be summarized by this equation:
$$6CO_2 + 6H_2O + \text{light energy} \rightarrow C_6H_{12}O_6 + 6O_2$$

Key points:
- Takes place in chloroplasts
- Chlorophyll captures light energy
- Produces glucose and oxygen

<!-- SOURCES: [{"page": 42, "page_end": 43, "title": "Chapter 3: Cell Biology", "doc_id": "abc-123", "doc_title": "Biology Textbook"}] -->
```

## MANDATORY RULES

1. **ALWAYS include the SOURCES marker** when search_documents returns SOURCES_FOR_CITATION
2. **Place it at the END** of your response, after your full explanation
3. **Copy the JSON exactly** - don't modify the sources array
4. **NEVER write sources in your text** - no "Source: page 42" or "According to page 5..."
5. **NEVER skip the sources marker** - it's how the frontend shows source buttons

## What NOT to Do

WRONG - Sources in text:
```
Photosynthesis is the process... (Source: page 42-43)
```

WRONG - No sources marker:
```
[Explains photosynthesis but doesn't include the SOURCES marker]
```

WRONG - Source marker in middle:
```
<!-- SOURCES: [...] -->
And here's more explanation...
```

CORRECT:
```
[Full explanation here]

<!-- SOURCES: [{"page": 42, ...}] -->
```

## Why This Matters

- The frontend parses the SOURCES marker and shows clickable buttons
- Users can jump directly to the source page in their document
- Writing sources inline looks unprofessional and breaks the UI pattern
- The marker is hidden from the user - they only see the clean text + buttons
