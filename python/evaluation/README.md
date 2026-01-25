# VLM/OCR Model Evaluation

This directory contains tools for evaluating Vision-Language Models (VLMs) and OCR models for document ingestion in VOXAM.

## Quick Start

### 1. Local Testing (Free, No API Keys)

Test Granite-Docling locally on all 4 sample documents:

```bash
cd /Users/vasanth/voxam/python
source .venv/bin/activate

# Run local evaluation
python evaluation/local_evaluate.py --model granite-docling
```

Results will be saved to `evaluation/results/`.

### 2. DeepInfra API Testing

Test cloud-hosted models via DeepInfra:

```bash
export DEEPINFRA_API_KEY=your_key

# Test olmOCR-2
python evaluation/deepinfra_evaluate.py --model olmocr2

# Test Qwen2.5-VL
python evaluation/deepinfra_evaluate.py --model qwen-vl-7b

# Test all models
python evaluation/deepinfra_evaluate.py --model all
```

### 3. Replicate API Testing

Test dots.ocr and Marker via Replicate:

```bash
export REPLICATE_API_TOKEN=your_token

# Test dots.ocr (best multilingual)
python evaluation/replicate_evaluate.py --model dots-ocr

# Test Marker (PDF→MD)
python evaluation/replicate_evaluate.py --model marker
```

### 4. RunPod Serverless (Custom Deployment)

For models requiring dedicated deployment:

```bash
export RUNPOD_API_KEY=your_key

# Generate deployment files
python evaluation/runpod_evaluate.py --model minicpm-v4.5 --deploy

# After deploying to RunPod, run evaluation
python evaluation/runpod_evaluate.py --model minicpm-v4.5 --endpoint YOUR_ENDPOINT_ID
```

### 5. Compare Results

After running evaluations:

```bash
# Generate scoring template for manual quality assessment
python evaluation/compare_models.py --generate-template

# Edit results/scoring_template.json to add quality scores

# View comparison
python evaluation/compare_models.py --compare

# View final scores and ranking
python evaluation/compare_models.py --score
```

## Test Documents

| Subject | File | Key Features |
|---------|------|--------------|
| CS | `cs.pdf` | Code blocks, algorithms, flowcharts |
| Physics | `physics-chapter 3.pdf` | Equations, diagrams, formulas |
| Chemistry | `lech103.pdf` | Chemical formulas, structures, tables |
| Biology | `chapter1.pdf` | Diagrams, terminology, figures |

## Models Being Evaluated

### Tier 1: Best Overall
| Model | Params | Source | Best For |
|-------|--------|--------|----------|
| **MiniCPM-V 4.5** | 8B | RunPod | All-round accuracy |
| **OCRFlux-3B** | 3B | RunPod | Cross-page tables |
| **dots.ocr** | 1.7B | Replicate | 100+ languages |

### Tier 2: Specialized
| Model | Params | Source | Best For |
|-------|--------|--------|----------|
| **Granite-Docling** | 258M | Local | Fast extraction |
| **olmOCR-2** | 7B | DeepInfra | Math formulas |
| **Qwen2.5-VL** | 7B/72B | DeepInfra | Complex layouts |
| **DeepSeek-OCR** | 3B | RunPod | High throughput |

## Scoring Criteria

| Criteria | Weight | Description |
|----------|--------|-------------|
| Text Accuracy | 30% | How accurate is the extracted text? |
| Table Extraction | 20% | Are tables preserved as markdown? |
| Equation/Formula | 20% | LaTeX output quality |
| Diagram Handling | 10% | Are figures described/OCR'd? |
| Speed | 10% | Pages per second |
| Cost | 10% | $ per 1000 pages |

## Output Structure

```
evaluation/
├── results/
│   ├── granite-docling_summary.json
│   ├── granite-docling_cs_preview.md
│   ├── granite-docling_physics_preview.md
│   ├── ...
│   ├── deepinfra_olmocr2_summary.json
│   ├── replicate_dots-ocr_summary.json
│   ├── runpod_minicpm-v4.5_summary.json
│   └── scoring_template.json
└── runpod_deploy/
    ├── minicpm-v4.5_handler.py
    └── minicpm-v4.5.Dockerfile
```

## Cost Comparison

### API Costs (per 1000 pages)
| Provider | Model | Cost |
|----------|-------|------|
| DeepInfra | olmOCR-2 | ~$9 |
| DeepInfra | Qwen2.5-VL-7B | ~$5 |
| Replicate | dots.ocr | ~$18 |
| **Current (Gemini)** | - | **~$60-80** |

### Self-Hosted Costs (RunPod, per 1000 docs @ 20 pages)
| Model | GPU | Cost |
|-------|-----|------|
| Granite-Docling | L4 | ~$1.50 |
| DeepSeek-OCR | L4 | ~$1.30 |
| MiniCPM-V 4.5 | A40 | ~$4.00 |

**Potential savings: 95-98% vs current Gemini API!**

## Next Steps After Evaluation

1. **Select Winner**: Based on evaluation scores and cost analysis
2. **Implement Integration**: See `python/vlm_ingestion.py` (to be created)
3. **Hybrid Approach**: Consider using PyMuPDF for text-heavy pages, VLM for complex pages

## Architecture Options

### Option A: Simple OCR Replacement
```
Current: PyMuPDF → Gemini API (problem pages)
New:     PyMuPDF → [Winner Model] (problem pages)
```

### Option B: Full VLM Extraction
```
PDF → All pages as images → [Winner Model] → Structured markdown
```

### Option C: Hybrid (Recommended)
```
PDF → PyMuPDF (text-heavy pages)
    → [Winner Model] (complex pages with tables/equations/figures)
```
