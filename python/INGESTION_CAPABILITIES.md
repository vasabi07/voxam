# Ingestion Pipeline Capabilities

**Last Updated:** February 7, 2026

This document outlines what document types and content the VOXAM ingestion pipeline can handle, known limitations, and recommendations for users.

---

## Supported Document Formats

| Format | Extensions | Extraction Method | Status |
|--------|------------|-------------------|--------|
| **PDF (native)** | `.pdf` | PyMuPDF text extraction | ✅ Full support |
| **PDF (scanned)** | `.pdf` | Gemini 2.5 Flash OCR | ✅ Full support |
| **PDF (handwritten)** | `.pdf` | Gemini 2.5 Flash OCR | ✅ Good support |
| **Word Documents** | `.docx`, `.doc` | python-docx | ✅ Full support |
| **PowerPoint** | `.pptx`, `.ppt` | python-pptx | ✅ Full support |
| **Markdown** | `.md`, `.markdown` | Direct parsing | ✅ Full support |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp` | Gemini OCR | ✅ Full support |

### PDF Type Detection

The pipeline automatically detects PDF type based on text layer presence:

```
Avg chars/page > 200 → Native PDF (fast PyMuPDF extraction)
Avg chars/page ≤ 200 → Scanned PDF (OCR with Gemini/olmOCR)
```

---

## Content Extraction Capabilities

### Text Content

| Content Type | Support Level | Notes |
|--------------|---------------|-------|
| Plain text | ✅ Excellent | Preserves paragraphs and structure |
| Headers/titles | ✅ Excellent | Hierarchy detection via LLM |
| Lists (bullet/numbered) | ✅ Excellent | Preserved in markdown format |
| Multi-column layouts | ⚠️ Good | May need OCR fallback for complex layouts |
| Footnotes/endnotes | ⚠️ Good | Extracted but may lose positioning |

### Mathematical Content

| Content Type | Support Level | Notes |
|--------------|---------------|-------|
| Inline equations | ✅ Excellent | LaTeX extraction via Gemini |
| Display equations | ✅ Excellent | Preserved with formatting |
| Chemical formulas | ✅ Good | H₂O, NaCl, etc. |
| Physics notation | ✅ Good | Vectors, Greek letters |
| Complex matrices | ⚠️ Moderate | May lose alignment in very complex cases |

### Visual Content

| Content Type | Support Level | Notes |
|--------------|---------------|-------|
| Diagrams | ✅ Good | Extracted as images + AI descriptions |
| Graphs/charts | ✅ Good | Described by vision LLM |
| Tables | ✅ Good | Converted to markdown format |
| Photographs | ✅ Good | Stored in R2 with descriptions |
| Flowcharts | ⚠️ Moderate | Description quality varies |
| Handwritten diagrams | ⚠️ Moderate | Best effort OCR |

### Structured Content Detection

The pipeline automatically detects and extracts:

- **Definitions** - Key term definitions for flashcard-style learning
- **Procedures** - Step-by-step instructions
- **Equations** - Mathematical expressions with LaTeX
- **Code blocks** - Programming code with syntax
- **Tables** - Tabular data in markdown

Content types classified: `narrative`, `definition`, `example`, `theorem`, `procedure`, `summary`

---

## OCR Capabilities

### Multi-Model OCR Router

```
PDF uploaded
    │
    ├── Native PDF (text layer exists)
    │       └── PyMuPDF direct extraction (fastest)
    │
    └── Scanned/Image PDF (no text layer)
            │
            ├── Gemini 2.5 Flash (primary)
            │       └── Excellent for: handwriting, mixed layouts, equations
            │
            └── olmOCR via DeepInfra (fallback)
                    └── Good for: printed scans, standard layouts
```

### Handwriting Support

| Handwriting Type | Support Level | Recommended Action |
|------------------|---------------|-------------------|
| Neat cursive | ✅ Good | Upload directly |
| Print handwriting | ✅ Good | Upload directly |
| Messy cursive | ⚠️ Moderate | Consider rewriting key parts |
| Mixed print/cursive | ⚠️ Moderate | Works but may have errors |
| Technical sketches | ⚠️ Moderate | Add typed annotations if critical |

---

## Known Limitations

### Document Issues

| Issue | Impact | Workaround |
|-------|--------|------------|
| Password-protected PDFs | ❌ Cannot process | Remove password before upload |
| Corrupted files | ❌ Cannot process | Re-export from source |
| DRM-protected documents | ❌ Cannot process | Use unprotected version |
| Very large files (>100 pages) | ⚠️ Slow processing | Consider splitting into chapters |
| Extremely low resolution scans | ⚠️ Poor OCR quality | Re-scan at 150+ DPI |

### Content Issues

| Issue | Impact | Workaround |
|-------|--------|------------|
| Watermarks | ⚠️ May appear in text | Use unwatermarked version |
| Overlapping text/images | ⚠️ Extraction issues | May need manual review |
| Rotated pages | ⚠️ OCR struggles | Rotate before upload |
| Multi-language documents | ⚠️ Mixed results | Best with single language |
| Artistic/decorative fonts | ⚠️ OCR errors | Standard fonts work best |

### Format-Specific Limitations

| Format | Limitation |
|--------|------------|
| **PDF** | Annotations/comments not extracted |
| **DOCX** | Track changes not preserved |
| **PPTX** | Speaker notes extracted but separate from slides |
| **PPTX** | Animations/transitions ignored |
| **Images** | No multi-page support (upload as PDF instead) |

---

## Chunking & Embedding Strategy

### Parameters

```python
CHUNK_MAX_CHARS = 4000      # Maximum chunk size
CHUNK_COMBINE_UNDER = 1500  # Combine small sections
CHUNK_NEW_AFTER = 3500      # Start new chunk threshold
CHUNK_OVERLAP = 500         # Context overlap between chunks
```

### Embedding Model

- **Model**: OpenAI `text-embedding-3-small`
- **Dimensions**: 1536
- **Similarity**: Cosine

### Topic-Level Grouping

Chunks are grouped into topic-level ContentBlocks based on:
1. Chapter/section headers (LLM-detected)
2. Semantic coherence
3. Page boundaries

---

## Quality Benchmarks

Tested on 4 document types (CS, Physics, Chemistry, Biology):

| Metric | PyMuPDF | Gemini OCR | olmOCR |
|--------|---------|------------|--------|
| Text accuracy | 98%+ | 95%+ | 92%+ |
| Table extraction | Good | Excellent | Good |
| Equation handling | N/A | Excellent | Good |
| Speed (20 pages) | 2-3s | 30-45s | 20-30s |
| Cost (1000 pages) | Free | ~$0.50 | ~$9 |

---

## Recommendations for Users

### Best Practices

1. **Use native PDFs when possible** - Export from Word/LaTeX rather than scanning
2. **Scan at 150+ DPI** - Higher resolution = better OCR
3. **Single language per document** - Mixed languages reduce accuracy
4. **Split large textbooks** - Upload chapter by chapter for faster processing
5. **Check critical content** - Review OCR output for equations and formulas

### Document Preparation Checklist

- [ ] File is not password protected
- [ ] File is not corrupted (opens normally)
- [ ] Pages are correctly oriented
- [ ] Scans are at least 150 DPI
- [ ] Watermarks removed if possible
- [ ] File size under 50MB (or split into parts)

### What Works Best

| Document Type | Expected Quality |
|---------------|------------------|
| Textbook PDFs (native) | ⭐⭐⭐⭐⭐ Excellent |
| Lecture slides (PPTX) | ⭐⭐⭐⭐⭐ Excellent |
| Class notes (typed) | ⭐⭐⭐⭐⭐ Excellent |
| Research papers | ⭐⭐⭐⭐ Very Good |
| Scanned textbooks | ⭐⭐⭐⭐ Very Good |
| Handwritten notes (neat) | ⭐⭐⭐ Good |
| Handwritten notes (messy) | ⭐⭐ Moderate |
| Whiteboard photos | ⭐⭐ Moderate |

---

## Future Improvements

- [ ] **Reranking layer** - Cross-encoder for better retrieval precision
- [ ] **Video/lecture support** - Whisper transcription + slide extraction
- [ ] **Multi-language optimization** - Better handling of mixed-language docs
- [ ] **Table structure preservation** - Improved complex table handling
- [ ] **Real-time progress** - WebSocket updates during ingestion

---

## Related Files

- `python/ingestion_workflow.py` - Main ingestion pipeline
- `python/evaluation/README.md` - OCR model evaluation framework
- `python/SCHEMA_REFERENCE.md` - Neo4j graph schema
- `python/retrieval.py` - Hybrid search implementation

---

*See `python/evaluation/results/` for detailed OCR comparison outputs across test documents.*
