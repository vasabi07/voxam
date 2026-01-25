"""
Encoding issue detection for PDF text extraction.

Detects when PyMuPDF extraction produces garbled output
(typically from Unicode math symbols, Greek letters, etc.)

Features:
- Detection of encoding issues (garbled symbols, equations)
- Detection of scattered equation layouts (V2 - educational docs)
- Detection of multi-column artifacts and repeated text
- Per-page OCR fallback using Gemini for problem pages only
- Hybrid extraction: PyMuPDF (fast) + targeted OCR (accurate)
"""

import re
from typing import Dict, List, Optional
import fitz


# =============================================================================
# Configuration
# =============================================================================

OCR_THRESHOLDS = {
    'isolated_chars_per_page': 5,       # Trigger if >5 isolated single chars
    'isolated_operators_per_page': 3,    # Trigger if >3 isolated operators
    'consecutive_short_lines': 3,        # Trigger if 3+ consecutive short lines
    'repeated_text_threshold': 3,        # Trigger if text repeated 3+ times
    'quality_score_threshold': 70,       # OCR if quality score < 70
}

# Patterns for detection
ISOLATED_LETTER_PATTERN = re.compile(r'^\s*[A-Za-z]\s*$')
ISOLATED_OPERATOR_PATTERN = re.compile(r'^\s*[=+\-*/×÷]\s*$')
ISOLATED_GREEK_PATTERN = re.compile(r'^\s*[∆∑∫πθαβγλσωδεζηικμνξρτυφχψΩΔΣΠ]\s*$')
ISOLATED_NUMBER_PATTERN = re.compile(r'^\s*\d{1,2}\s*$')  # Single/double digit numbers
MALFORMED_SYMBOL_PATTERN = re.compile(r'[∆∑∫][→←↑↓]|[→←↑↓][∆∑∫]')
UNICODE_REPLACEMENT_PATTERN = re.compile(r'[\ufffd\u25a1\u2022]')  # Replacement chars


# =============================================================================
# V2: Scattered Equation Detection
# =============================================================================

def detect_scattered_equations(text: str) -> Dict:
    """
    Detect pages where equations are scattered across lines.

    This happens when PyMuPDF extracts math formulas character-by-character
    instead of preserving the equation layout.

    Example of scattered equation (I = q/t):
        q
        I
        t
        =

    Patterns detected:
    - Isolated single letters (variable names)
    - Isolated operators (=, +, -, *, /)
    - Isolated Greek/math symbols (∆, ∑, ∫, π, etc.)
    - Consecutive short lines (3+ lines with <3 chars each)
    """
    issues = []
    problem_lines = []

    lines = text.split('\n')

    isolated_letters = 0
    isolated_operators = 0
    isolated_greek = 0
    isolated_numbers = 0
    consecutive_short = 0
    max_consecutive_short = 0

    for line_num, line in enumerate(lines):
        line_stripped = line.strip()
        line_len = len(line_stripped)
        line_issues = []

        # Track consecutive short lines
        if 0 < line_len <= 2:
            consecutive_short += 1
            max_consecutive_short = max(max_consecutive_short, consecutive_short)
        else:
            consecutive_short = 0

        # Check for isolated single letters (likely variables)
        if ISOLATED_LETTER_PATTERN.match(line):
            isolated_letters += 1
            line_issues.append('isolated_letter')

        # Check for isolated operators
        if ISOLATED_OPERATOR_PATTERN.match(line):
            isolated_operators += 1
            line_issues.append('isolated_operator')

        # Check for isolated Greek/math symbols
        if ISOLATED_GREEK_PATTERN.match(line):
            isolated_greek += 1
            line_issues.append('isolated_greek')

        # Check for isolated small numbers (often subscripts/superscripts)
        if ISOLATED_NUMBER_PATTERN.match(line) and line_len == 1:
            isolated_numbers += 1
            line_issues.append('isolated_number')

        if line_issues:
            problem_lines.append({
                'line_num': line_num + 1,
                'text': line_stripped,
                'issues': line_issues
            })

    # Determine if page has scattered equation issues
    has_issues = (
        isolated_letters >= OCR_THRESHOLDS['isolated_chars_per_page'] or
        isolated_operators >= OCR_THRESHOLDS['isolated_operators_per_page'] or
        isolated_greek >= 3 or
        max_consecutive_short >= OCR_THRESHOLDS['consecutive_short_lines']
    )

    if has_issues:
        if isolated_letters >= OCR_THRESHOLDS['isolated_chars_per_page']:
            issues.append(f'{isolated_letters} isolated letters (scattered variables)')
        if isolated_operators >= OCR_THRESHOLDS['isolated_operators_per_page']:
            issues.append(f'{isolated_operators} isolated operators')
        if isolated_greek >= 3:
            issues.append(f'{isolated_greek} isolated Greek/math symbols')
        if max_consecutive_short >= OCR_THRESHOLDS['consecutive_short_lines']:
            issues.append(f'{max_consecutive_short} consecutive short lines')

    return {
        'has_issues': has_issues,
        'issues': issues,
        'problem_lines': problem_lines[:20],  # Limit to first 20
        'metrics': {
            'isolated_letters': isolated_letters,
            'isolated_operators': isolated_operators,
            'isolated_greek': isolated_greek,
            'isolated_numbers': isolated_numbers,
            'max_consecutive_short': max_consecutive_short,
        }
    }


# =============================================================================
# V2: Multi-column Artifact Detection
# =============================================================================

def detect_multicolumn_artifacts(text: str) -> Dict:
    """
    Detect multi-column layout extraction failures.

    This happens when PyMuPDF extracts text from multi-column layouts
    and the columns get interleaved or text gets repeated.

    Example (section header repeated):
        Rate of a
        Rate of a
        Rate of a
        Chemical
        Chemical
        Chemical

    Patterns detected:
    - Repeated consecutive lines (same text 3+ times)
    - Only counts if repeated text is meaningful (>5 chars to avoid short words)
    """
    issues = []
    problem_lines = []

    lines = text.split('\n')

    # Track repeated lines
    repeated_sequences = 0
    i = 0

    while i < len(lines) - 2:
        line = lines[i].strip()

        # Skip empty lines and very short lines (single words like "Unit", "Chapter")
        if not line or len(line) < 6:
            i += 1
            continue

        # Count consecutive repetitions
        repeat_count = 1
        j = i + 1
        while j < len(lines) and lines[j].strip() == line:
            repeat_count += 1
            j += 1

        # Require at least 4 repetitions for longer text, 5 for short text
        min_repeats = 4 if len(line) >= 10 else 5

        if repeat_count >= min_repeats:
            repeated_sequences += 1
            problem_lines.append({
                'line_num': i + 1,
                'text': line[:50] + ('...' if len(line) > 50 else ''),
                'issues': [f'repeated_{repeat_count}x']
            })
            i = j  # Skip past the repeated lines
        else:
            i += 1

    # Require at least 2 distinct repeated sequences to flag as issue
    has_issues = repeated_sequences >= 2

    if has_issues:
        issues.append(f'{repeated_sequences} repeated text sequences detected')

    return {
        'has_issues': has_issues,
        'issues': issues,
        'problem_lines': problem_lines,
        'metrics': {
            'repeated_sequences': repeated_sequences,
        }
    }


# =============================================================================
# V2: Symbol Corruption Detection
# =============================================================================

def detect_symbol_corruption(text: str) -> Dict:
    """
    Detect malformed symbol combinations and Unicode issues.

    This happens when font encoding causes symbols to merge incorrectly
    or Unicode replacement characters appear.

    Patterns detected:
    - Combined operators (∆→, →∆, etc.)
    - Unicode replacement characters (�, □, etc.)
    - Broken arrow sequences
    """
    issues = []
    problem_lines = []

    lines = text.split('\n')

    malformed_symbols = 0
    replacement_chars = 0

    for line_num, line in enumerate(lines):
        line_issues = []

        # Check for malformed symbol combinations
        malformed_matches = MALFORMED_SYMBOL_PATTERN.findall(line)
        if malformed_matches:
            malformed_symbols += len(malformed_matches)
            line_issues.append(f'malformed_symbol:{malformed_matches}')

        # Check for Unicode replacement characters
        replacement_matches = UNICODE_REPLACEMENT_PATTERN.findall(line)
        if replacement_matches:
            replacement_chars += len(replacement_matches)
            line_issues.append(f'replacement_char:{len(replacement_matches)}')

        if line_issues:
            problem_lines.append({
                'line_num': line_num + 1,
                'text': line[:100] + ('...' if len(line) > 100 else ''),
                'issues': line_issues
            })

    has_issues = malformed_symbols > 0 or replacement_chars >= 3

    if has_issues:
        if malformed_symbols > 0:
            issues.append(f'{malformed_symbols} malformed symbol combinations')
        if replacement_chars >= 3:
            issues.append(f'{replacement_chars} Unicode replacement characters')

    return {
        'has_issues': has_issues,
        'issues': issues,
        'problem_lines': problem_lines,
        'metrics': {
            'malformed_symbols': malformed_symbols,
            'replacement_chars': replacement_chars,
        }
    }


# =============================================================================
# V2: Page Quality Score
# =============================================================================

def calculate_page_quality_score(text: str) -> Dict:
    """
    Calculate overall page quality score (0-100).

    Higher score = better quality, less likely to need OCR.
    Lower score = more issues, should trigger OCR.

    Returns:
        {
            'score': int (0-100),
            'needs_ocr': bool,
            'issue_breakdown': {...},
            'all_issues': list of issue descriptions
        }
    """
    # Run all detection checks
    equation_check = detect_scattered_equations(text)
    multicolumn_check = detect_multicolumn_artifacts(text)
    symbol_check = detect_symbol_corruption(text)

    # Calculate penalty scores (each maxes out at certain points)
    equation_penalty = min(30, (
        equation_check['metrics']['isolated_letters'] * 2 +
        equation_check['metrics']['isolated_operators'] * 3 +
        equation_check['metrics']['isolated_greek'] * 3 +
        equation_check['metrics']['max_consecutive_short'] * 5
    ))

    multicolumn_penalty = min(20, (
        multicolumn_check['metrics']['repeated_sequences'] * 10
    ))

    symbol_penalty = min(20, (
        symbol_check['metrics']['malformed_symbols'] * 5 +
        symbol_check['metrics']['replacement_chars'] * 2
    ))

    # Calculate final score
    total_penalty = equation_penalty + multicolumn_penalty + symbol_penalty
    score = max(0, 100 - total_penalty)

    # Determine if OCR is needed
    needs_ocr = (
        score < OCR_THRESHOLDS['quality_score_threshold'] or
        equation_check['has_issues'] or
        multicolumn_check['has_issues'] or
        symbol_check['has_issues']
    )

    # Collect all issues
    all_issues = []
    all_issues.extend(equation_check['issues'])
    all_issues.extend(multicolumn_check['issues'])
    all_issues.extend(symbol_check['issues'])

    return {
        'score': score,
        'needs_ocr': needs_ocr,
        'issue_breakdown': {
            'equation_penalty': equation_penalty,
            'multicolumn_penalty': multicolumn_penalty,
            'symbol_penalty': symbol_penalty,
        },
        'all_issues': all_issues,
        'checks': {
            'scattered_equations': equation_check['has_issues'],
            'multicolumn_artifacts': multicolumn_check['has_issues'],
            'symbol_corruption': symbol_check['has_issues'],
        }
    }


def check_text_encoding(text: str) -> Dict:
    """
    Detect encoding issues in extracted text (V1 + V2 combined).

    V1 checks (symbol corruption):
    - Standalone ? replacing symbols (H?O, x = ?)
    - Consecutive ? sequences (?????)
    - Greek letter context with ?
    - Math/equation context with ?

    V2 checks (layout issues for educational docs):
    - Scattered equations (isolated letters/operators)
    - Multi-column artifacts (repeated text)
    - Symbol corruption (malformed glyphs)

    Returns:
        {
            'has_issues': bool,
            'issue_score': float (0-1, higher = more issues),
            'quality_score': int (0-100, higher = better quality),
            'needs_ocr': bool,
            'issues': list of issue descriptions,
            'problem_lines': list of {line_num, text, issues}
        }
    """
    issues = []
    problem_lines = []

    lines = text.split('\n')

    # ==========================================================================
    # V1: Original ? symbol checks
    # ==========================================================================
    for line_num, line in enumerate(lines):
        line_issues = []

        # 1. Standalone ? replacing symbols (H?O, x?)
        standalone_q = re.findall(r'(?<=[a-zA-Z0-9])\?(?=[a-zA-Z0-9])', line)
        if standalone_q:
            line_issues.append(f'symbol_replacement:{len(standalone_q)}')

        # 2. Operator context with ? (= ?, ? +, etc.)
        operator_q = re.findall(r'[=+\-*/→<>≤≥]\s*\?|\?\s*[=+\-*/→<>≤≥]', line)
        if operator_q:
            line_issues.append(f'garbled_operator:{len(operator_q)}')

        # 3. Consecutive ? sequences (?????)
        consecutive_q = re.findall(r'\?{2,}', line)
        if consecutive_q:
            line_issues.append(f'consecutive_q:{len(consecutive_q)}')

        # 4. Greek letter context with mid-word ?
        if re.search(r'(Greek|alpha|beta|theta|sigma|delta|pi|omega|gamma|lambda)\b[^?]*\?(?=[a-zA-Z0-9,])', line, re.I):
            line_issues.append('greek_context')

        # 5. Math/equation context with mid-expression ?
        if re.search(r'[=+\-*/]\s*\?\s*[a-zA-Z0-9(]', line):
            line_issues.append('math_context')

        # 6. Chemical formula context with ?
        if re.search(r'[A-Z][a-z]?\?[A-Za-z0-9]|[A-Z][a-z]?[0-9]\?[^?\s]', line):
            line_issues.append('chemical_context')

        if line_issues:
            problem_lines.append({
                'line_num': line_num + 1,
                'text': line[:100] + ('...' if len(line) > 100 else ''),
                'issues': line_issues
            })

    # ==========================================================================
    # V2: Educational document layout checks
    # ==========================================================================
    quality_result = calculate_page_quality_score(text)

    # Merge V2 issues
    issues.extend(quality_result['all_issues'])

    # Calculate V1 issue score
    v1_total_issues = sum(len(p['issues']) for p in problem_lines)
    v1_issue_score = min(1.0, v1_total_issues * 0.1)

    # V1 has issues if problem lines found
    v1_has_issues = len(problem_lines) > 0

    # Combined: has issues if either V1 or V2 found problems
    has_issues = v1_has_issues or quality_result['needs_ocr']

    # Summary for V1 issues
    if problem_lines:
        issues.insert(0, f'{len(problem_lines)} lines with V1 encoding issues')

    return {
        'has_issues': has_issues,
        'issue_score': v1_issue_score,
        'quality_score': quality_result['score'],
        'needs_ocr': quality_result['needs_ocr'],
        'issues': issues,
        'problem_lines': problem_lines,
        'v2_checks': quality_result['checks'],
    }


def check_page_encoding(page: fitz.Page) -> Dict:
    """Check a single PDF page for encoding issues (V1 + V2)."""
    text = page.get_text()
    result = check_text_encoding(text)
    result['page_num'] = page.number + 1
    result['char_count'] = len(text)
    return result


def check_pdf_encoding(pdf_path: str) -> Dict:
    """
    Check entire PDF for encoding issues (V1 + V2 combined).

    V1: Symbol corruption (? replacements)
    V2: Layout issues (scattered equations, multi-column artifacts)

    Returns:
        {
            'total_pages': int,
            'pages_with_issues': list of page results,
            'problem_page_numbers': list of ints (for OCR targeting),
            'overall_score': float (ratio of problem pages),
            'avg_quality_score': float (average page quality 0-100),
            'needs_ocr_fallback': bool,
            'issue_summary': {
                'scattered_equations': int,
                'multicolumn_artifacts': int,
                'symbol_corruption': int,
            }
        }
    """
    doc = fitz.open(pdf_path)

    results = {
        'total_pages': len(doc),
        'pages_with_issues': [],
        'problem_page_numbers': [],
        'overall_score': 0.0,
        'avg_quality_score': 100.0,
        'needs_ocr_fallback': False,
        'issue_summary': {
            'scattered_equations': 0,
            'multicolumn_artifacts': 0,
            'symbol_corruption': 0,
        }
    }

    quality_scores = []

    for page in doc:
        check = check_page_encoding(page)
        quality_scores.append(check.get('quality_score', 100))

        if check['has_issues']:
            results['pages_with_issues'].append(check)
            results['problem_page_numbers'].append(page.number + 1)

            # Track which V2 checks triggered
            v2_checks = check.get('v2_checks', {})
            if v2_checks.get('scattered_equations'):
                results['issue_summary']['scattered_equations'] += 1
            if v2_checks.get('multicolumn_artifacts'):
                results['issue_summary']['multicolumn_artifacts'] += 1
            if v2_checks.get('symbol_corruption'):
                results['issue_summary']['symbol_corruption'] += 1

    doc.close()

    # Calculate overall metrics
    if quality_scores:
        results['avg_quality_score'] = sum(quality_scores) / len(quality_scores)

    if results['pages_with_issues']:
        results['overall_score'] = len(results['pages_with_issues']) / results['total_pages']
        # Flag for OCR fallback if >10% of pages have issues (lowered from 20%)
        results['needs_ocr_fallback'] = results['overall_score'] > 0.1

    return results


def log_encoding_issues(check_result: Dict, doc_id: str = None) -> None:
    """Log encoding issues for monitoring (V1 + V2)."""
    # Handle both page-level and text-level results
    has_issues = check_result.get('has_issues', False)
    pages_with_issues = check_result.get('pages_with_issues', [])

    if not has_issues and not pages_with_issues:
        return

    prefix = f"[{doc_id}] " if doc_id else ""

    if 'pages_with_issues' in check_result:
        # PDF-level result
        pages = check_result['problem_page_numbers']
        score = check_result['overall_score']
        avg_quality = check_result.get('avg_quality_score', 100)

        print(f"   ⚠️ {prefix}Quality issues detected: {len(pages)} pages ({score:.0%})")
        print(f"      Avg quality score: {avg_quality:.0f}/100")
        print(f"      Problem pages: {pages[:15]}{'...' if len(pages) > 15 else ''}")

        # V2 issue breakdown
        summary = check_result.get('issue_summary', {})
        if any(summary.values()):
            print(f"      Issue breakdown:")
            if summary.get('scattered_equations'):
                print(f"        - Scattered equations: {summary['scattered_equations']} pages")
            if summary.get('multicolumn_artifacts'):
                print(f"        - Multi-column artifacts: {summary['multicolumn_artifacts']} pages")
            if summary.get('symbol_corruption'):
                print(f"        - Symbol corruption: {summary['symbol_corruption']} pages")

        if check_result['needs_ocr_fallback']:
            print(f"      💡 OCR fallback recommended for {len(pages)} pages")
    else:
        # Text-level result
        quality_score = check_result.get('quality_score', 100)
        print(f"   ⚠️ {prefix}Quality score: {quality_score}/100")
        if check_result.get('issues'):
            print(f"      Issues: {', '.join(check_result['issues'][:5])}")


# =============================================================================
# OCR Provider Configuration
# =============================================================================

# DeepInfra models for OCR fallback
DEEPINFRA_OCR_MODELS = {
    "olmocr2": {
        "id": "allenai/olmOCR-2-7B-1025",
        "name": "olmOCR-2 (7B)",
        "input_cost_per_m": 0.09,
        "output_cost_per_m": 0.19,
    },
    "gemma-12b": {
        "id": "google/gemma-3-12b-it",
        "name": "Gemma-3-12B-IT",
        "input_cost_per_m": 0.04,
        "output_cost_per_m": 0.13,
    },
    "mistral-small": {
        "id": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        "name": "Mistral-Small-3.1-24B",
        "input_cost_per_m": 0.075,
        "output_cost_per_m": 0.20,
    },
    "deepseek-ocr": {
        "id": "deepseek-ai/DeepSeek-OCR",
        "name": "DeepSeek-OCR",
        "input_cost_per_m": 0.03,
        "output_cost_per_m": 0.10,
    },
}

# OCR prompt for DeepInfra models
DEEPINFRA_OCR_PROMPT = """You are an expert document OCR system. Extract ALL text content from this document page.

Requirements:
1. Preserve the exact layout and structure of the text
2. Convert any mathematical equations to LaTeX format (wrapped in $ or $$)
3. Preserve tables using markdown table syntax
4. For diagrams/figures, provide a brief description in [brackets]
5. Include ALL text, even small captions and footnotes

Output the extracted text in clean markdown format."""


# =============================================================================
# Handwriting Detection
# =============================================================================

def detect_handwriting(image_b64: str, api_key: str = None) -> Dict:
    """
    Detect if an image contains handwritten content using Gemini vision.

    Uses a quick, cheap vision check to classify content as:
    - "handwritten" → Route to Gemini OCR (better for handwriting)
    - "printed" → Route to Mistral-Small OCR (better for LaTeX/equations)
    - "mixed" → Route to Gemini OCR (safer choice)

    Args:
        image_b64: Base64 encoded image (PNG/JPEG)
        api_key: Google API key (uses env var if not provided)

    Returns:
        {
            "content_type": "handwritten" | "printed" | "mixed",
            "confidence": float (0-1),
            "recommended_ocr": "gemini" | "deepinfra"
        }
    """
    import os
    import httpx

    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # Default to printed/Mistral if no Gemini key
        return {
            "content_type": "printed",
            "confidence": 0.5,
            "recommended_ocr": "deepinfra"
        }

    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": """Analyze this document image and classify the text content.

Answer with ONLY one of these exact responses:
- HANDWRITTEN (if most text is handwritten/cursive)
- PRINTED (if most text is typed/printed)
- MIXED (if significant amounts of both)

Just respond with the single word, nothing else."""},
                        {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                    ]
                }],
                "generationConfig": {
                    "maxOutputTokens": 10,
                    "temperature": 0
                }
            },
            timeout=15.0
        )

        if response.status_code == 200:
            result = response.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip().upper()

            if "HANDWRITTEN" in text:
                return {
                    "content_type": "handwritten",
                    "confidence": 0.9,
                    "recommended_ocr": "gemini"
                }
            elif "MIXED" in text:
                return {
                    "content_type": "mixed",
                    "confidence": 0.7,
                    "recommended_ocr": "gemini"
                }
            else:
                return {
                    "content_type": "printed",
                    "confidence": 0.9,
                    "recommended_ocr": "deepinfra"
                }
        else:
            # Default to printed on error
            return {
                "content_type": "printed",
                "confidence": 0.5,
                "recommended_ocr": "deepinfra"
            }

    except Exception as e:
        print(f"   ⚠️ Handwriting detection error: {e}")
        return {
            "content_type": "printed",
            "confidence": 0.5,
            "recommended_ocr": "deepinfra"
        }


def detect_document_type(pdf_path: str) -> Dict:
    """
    Detect if a PDF is handwritten, printed, or scanned.

    Checks first page to determine content type and recommended OCR provider.

    Returns:
        {
            "pdf_type": "native" | "scanned",
            "content_type": "handwritten" | "printed" | "mixed",
            "recommended_ocr": "gemini" | "deepinfra",
            "needs_full_ocr": bool
        }
    """
    import os
    import base64
    from pdf2image import convert_from_path
    from io import BytesIO

    doc = fitz.open(pdf_path)
    total_chars = sum(len(page.get_text()) for page in doc)
    avg_chars = total_chars / len(doc) if len(doc) > 0 else 0
    doc.close()

    # Check if native or scanned
    is_scanned = avg_chars < 200

    # For scanned/low-text PDFs, check if handwritten
    if is_scanned or avg_chars < 500:
        # Convert first page to image for handwriting check
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=100)
            if images:
                buffer = BytesIO()
                images[0].save(buffer, format="PNG")
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                hw_check = detect_handwriting(b64)

                return {
                    "pdf_type": "scanned" if is_scanned else "native",
                    "content_type": hw_check["content_type"],
                    "recommended_ocr": hw_check["recommended_ocr"],
                    "needs_full_ocr": is_scanned,
                    "avg_chars_per_page": avg_chars
                }
        except Exception as e:
            print(f"   ⚠️ Document type detection error: {e}")

    # Native PDF with good text extraction
    return {
        "pdf_type": "native",
        "content_type": "printed",
        "recommended_ocr": "deepinfra",
        "needs_full_ocr": False,
        "avg_chars_per_page": avg_chars
    }


# =============================================================================
# Image Upload Support (PNG, JPEG, etc.)
# =============================================================================

SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp']


def extract_image_with_ocr(
    image_path: str,
    ocr_provider: str = "auto",
    deepinfra_model: str = "mistral-small"
) -> List[str]:
    """
    Extract text from an image file using OCR.

    Supports: PNG, JPEG, TIFF, BMP, WEBP

    Args:
        image_path: Path to image file
        ocr_provider: "auto" (detect handwriting), "gemini", or "deepinfra"
        deepinfra_model: Model for DeepInfra OCR

    Returns:
        List with single string (to match PDF extraction format)
    """
    import os
    import base64
    from PIL import Image
    from io import BytesIO

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(f"Unsupported image format: {ext}. Supported: {SUPPORTED_IMAGE_FORMATS}")

    print(f"🖼️  Processing image: {os.path.basename(image_path)}")

    # Load and convert image to PNG base64
    img = Image.open(image_path)

    # Convert to RGB if necessary (for RGBA or palette images)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Auto-detect handwriting if provider is "auto"
    if ocr_provider == "auto":
        print("   🔍 Detecting content type...")
        hw_check = detect_handwriting(b64)
        ocr_provider = hw_check["recommended_ocr"]
        print(f"   📝 Content type: {hw_check['content_type']} → using {ocr_provider}")

    # Run OCR
    api_key = os.getenv("GOOGLE_API_KEY") if ocr_provider == "gemini" else os.getenv("DEEPINFRA_API_KEY")

    if ocr_provider == "gemini":
        text = ocr_page_gemini(b64, 1, api_key)
    else:
        text = ocr_page_deepinfra(b64, 1, api_key, deepinfra_model)

    if text:
        print(f"   ✅ Extracted {len(text)} characters")
        return [text]
    else:
        print("   ⚠️ OCR returned no text")
        return [""]


def extract_images_with_ocr(
    image_paths: List[str],
    ocr_provider: str = "auto",
    deepinfra_model: str = "mistral-small",
    parallel: bool = True,
    max_concurrent: int = 10
) -> List[str]:
    """
    Extract text from multiple images using parallel OCR.

    Args:
        image_paths: List of image file paths
        ocr_provider: "auto", "gemini", or "deepinfra"
        deepinfra_model: Model for DeepInfra OCR
        parallel: Use parallel processing
        max_concurrent: Max concurrent requests

    Returns:
        List of extracted text strings (one per image)
    """
    import os
    import base64
    import asyncio
    import httpx
    from PIL import Image
    from io import BytesIO

    print(f"🖼️  Processing {len(image_paths)} images...")

    # Convert all images to base64
    images_b64 = []
    for path in image_paths:
        try:
            img = Image.open(path)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            images_b64.append(base64.b64encode(buffer.getvalue()).decode("utf-8"))
        except Exception as e:
            print(f"   ⚠️ Failed to load {path}: {e}")
            images_b64.append(None)

    # Detect content type from first valid image
    first_valid = next((b64 for b64 in images_b64 if b64), None)
    if ocr_provider == "auto" and first_valid:
        print("   🔍 Detecting content type...")
        hw_check = detect_handwriting(first_valid)
        ocr_provider = hw_check["recommended_ocr"]
        print(f"   📝 Content type: {hw_check['content_type']} → using {ocr_provider}")

    # For now, process sequentially (can add parallel later if needed)
    # Gemini doesn't have async support in our current implementation
    results = []
    api_key = os.getenv("GOOGLE_API_KEY") if ocr_provider == "gemini" else os.getenv("DEEPINFRA_API_KEY")

    for i, b64 in enumerate(images_b64):
        if b64 is None:
            results.append("")
            continue

        if ocr_provider == "gemini":
            text = ocr_page_gemini(b64, i + 1, api_key)
        else:
            text = ocr_page_deepinfra(b64, i + 1, api_key, deepinfra_model)

        results.append(text or "")
        print(f"   ✅ Image {i + 1}/{len(image_paths)}: {len(text or '')} chars")

    return results


def ocr_page_gemini(image_b64: str, page_num: int, api_key: str) -> Optional[str]:
    """OCR a page using Gemini API."""
    import httpx

    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": "Extract ALL text from this image. Preserve formatting, line breaks, and structure. Include all equations, formulas, and symbols. Output only the extracted text."},
                        {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                    ]
                }]
            },
            timeout=60.0
        )

        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"      ⚠️ Page {page_num}: Gemini OCR failed ({response.status_code})")
            return None
    except Exception as e:
        print(f"      ⚠️ Page {page_num}: Gemini OCR error - {e}")
        return None


def ocr_page_deepinfra(
    image_b64: str,
    page_num: int,
    api_key: str,
    model: str = "olmocr2"
) -> Optional[str]:
    """
    OCR a page using DeepInfra API.

    Args:
        image_b64: Base64 encoded PNG image
        page_num: Page number for logging
        api_key: DeepInfra API key
        model: Model key from DEEPINFRA_OCR_MODELS

    Returns:
        Extracted text or None on error
    """
    import httpx

    model_info = DEEPINFRA_OCR_MODELS.get(model)
    if not model_info:
        print(f"      ⚠️ Unknown DeepInfra model: {model}")
        return None

    model_id = model_info["id"]

    try:
        response = httpx.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": DEEPINFRA_OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 4096,
            },
            timeout=120.0,
        )

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"      ⚠️ Page {page_num}: DeepInfra OCR failed ({response.status_code})")
            return None
    except Exception as e:
        print(f"      ⚠️ Page {page_num}: DeepInfra OCR error - {e}")
        return None


async def async_ocr_page_deepinfra(
    image_b64: str,
    page_num: int,
    api_key: str,
    model: str = "mistral-small",
    client: "httpx.AsyncClient" = None
) -> tuple[int, Optional[str]]:
    """
    Async OCR a page using DeepInfra API.

    Returns:
        Tuple of (page_num, extracted_text or None)
    """
    import httpx

    model_info = DEEPINFRA_OCR_MODELS.get(model)
    if not model_info:
        return page_num, None

    model_id = model_info["id"]

    try:
        # Use provided client or create new one
        if client:
            response = await client.post(
                "https://api.deepinfra.com/v1/openai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_id,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": DEEPINFRA_OCR_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    },
                                },
                            ],
                        }
                    ],
                    "max_tokens": 4096,
                },
                timeout=120.0,
            )
        else:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.post(
                    "https://api.deepinfra.com/v1/openai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_id,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": DEEPINFRA_OCR_PROMPT},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{image_b64}"
                                        },
                                    },
                                ],
                            }
                        ],
                        "max_tokens": 4096,
                    },
                    timeout=120.0,
                )

        if response.status_code == 200:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            print(f"      ✅ Page {page_num}: {len(text)} chars via OCR")
            return page_num, text
        else:
            print(f"      ⚠️ Page {page_num}: DeepInfra OCR failed ({response.status_code})")
            return page_num, None
    except Exception as e:
        print(f"      ⚠️ Page {page_num}: DeepInfra OCR error - {e}")
        return page_num, None


async def ocr_problem_pages_async(
    pdf_path: str,
    page_numbers: List[int],
    ocr_provider: str = "deepinfra",
    deepinfra_model: str = "mistral-small",
    max_concurrent: int = 10
) -> Dict[int, str]:
    """
    OCR multiple pages in PARALLEL using async requests.

    With 10 concurrent requests:
    - 20 pages @ 13s each = 26s total (vs 260s sequential)
    - 30 pages @ 13s each = 39s total (vs 390s sequential)

    Args:
        pdf_path: Path to PDF file
        page_numbers: 1-indexed page numbers to OCR
        ocr_provider: "deepinfra" (gemini not yet async)
        deepinfra_model: Model key (mistral-small recommended)
        max_concurrent: Max concurrent API requests (default 10)

    Returns:
        Dict mapping page_number -> ocr_text
    """
    import os
    import base64
    import asyncio
    import httpx
    from pdf2image import convert_from_path
    from io import BytesIO

    if ocr_provider != "deepinfra":
        print(f"   ⚠️ Async OCR only supports deepinfra, falling back to sequential")
        return ocr_problem_pages(pdf_path, page_numbers, ocr_provider, deepinfra_model)

    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        print("   ⚠️ No DEEPINFRA_API_KEY, skipping OCR fallback")
        return {}

    model_info = DEEPINFRA_OCR_MODELS.get(deepinfra_model)
    provider_name = f"DeepInfra ({model_info['name'] if model_info else deepinfra_model})"

    print(f"   🚀 Parallel OCR for {len(page_numbers)} pages using {provider_name} (max {max_concurrent} concurrent)")

    # Step 1: Convert all pages to images first (CPU-bound, done sequentially)
    print(f"      📄 Converting pages to images...")
    page_images = {}
    for page_num in page_numbers:
        try:
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150
            )
            if images:
                buffer = BytesIO()
                images[0].save(buffer, format="PNG")
                page_images[page_num] = base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"      ⚠️ Page {page_num}: Image conversion error - {e}")

    print(f"      ✅ Converted {len(page_images)} pages to images")

    # Step 2: OCR all pages in parallel (I/O-bound, async)
    print(f"      🔄 Starting parallel OCR requests...")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_ocr(page_num: int, b64: str, client: httpx.AsyncClient):
        async with semaphore:
            return await async_ocr_page_deepinfra(b64, page_num, api_key, deepinfra_model, client)

    results = {}
    async with httpx.AsyncClient() as client:
        tasks = [
            bounded_ocr(page_num, b64, client)
            for page_num, b64 in page_images.items()
        ]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, Exception):
                print(f"      ⚠️ OCR task error: {result}")
            elif result and result[1]:
                page_num, text = result
                results[page_num] = text

    print(f"      ✅ Completed OCR for {len(results)}/{len(page_numbers)} pages")
    return results


def ocr_problem_pages_parallel(
    pdf_path: str,
    page_numbers: List[int],
    ocr_provider: str = "deepinfra",
    deepinfra_model: str = "mistral-small",
    max_concurrent: int = 10
) -> Dict[int, str]:
    """
    Synchronous wrapper for parallel OCR.

    Use this from sync code - it handles the async event loop internally.
    """
    import asyncio

    try:
        # Check if we're already in an async context
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context - use nest_asyncio or thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                ocr_problem_pages_async(pdf_path, page_numbers, ocr_provider, deepinfra_model, max_concurrent)
            )
            return future.result()
    except RuntimeError:
        # No running loop - safe to use asyncio.run
        return asyncio.run(
            ocr_problem_pages_async(pdf_path, page_numbers, ocr_provider, deepinfra_model, max_concurrent)
        )


def ocr_problem_pages(
    pdf_path: str,
    page_numbers: List[int],
    ocr_provider: str = "deepinfra",
    deepinfra_model: str = "mistral-small"
) -> Dict[int, str]:
    """
    OCR specific pages that have encoding issues.

    Args:
        pdf_path: Path to PDF file
        page_numbers: 1-indexed page numbers to OCR
        ocr_provider: "gemini" or "deepinfra"
        deepinfra_model: Model key if using deepinfra (olmocr2, gemma-12b, mistral-small, deepseek-ocr)

    Returns:
        Dict mapping page_number -> ocr_text
    """
    import os
    import base64
    from pdf2image import convert_from_path
    from io import BytesIO

    # Get API key based on provider
    if ocr_provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("   ⚠️ No GOOGLE_API_KEY, skipping OCR fallback")
            return {}
        provider_name = "Gemini"
    elif ocr_provider == "deepinfra":
        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            print("   ⚠️ No DEEPINFRA_API_KEY, skipping OCR fallback")
            return {}
        model_info = DEEPINFRA_OCR_MODELS.get(deepinfra_model)
        provider_name = f"DeepInfra ({model_info['name'] if model_info else deepinfra_model})"
    else:
        print(f"   ⚠️ Unknown OCR provider: {ocr_provider}")
        return {}

    print(f"   🔄 OCR fallback for pages: {page_numbers} using {provider_name}")

    results = {}

    for page_num in page_numbers:
        try:
            # Convert single page to image
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150
            )

            if not images:
                continue

            img = images[0]

            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Call appropriate OCR provider
            if ocr_provider == "gemini":
                text = ocr_page_gemini(b64, page_num, api_key)
            else:  # deepinfra
                text = ocr_page_deepinfra(b64, page_num, api_key, deepinfra_model)

            if text:
                results[page_num] = text
                print(f"      ✅ Page {page_num}: {len(text)} chars via OCR")

        except Exception as e:
            print(f"      ⚠️ Page {page_num}: OCR error - {e}")

    return results


def extract_pdf_with_fallback(
    pdf_path: str,
    doc_id: str = None,
    ocr_provider: str = "auto",
    deepinfra_model: str = "mistral-small",
    parallel: bool = True,
    max_concurrent: int = 10
) -> List[str]:
    """
    Extract PDF text using PyMuPDF with OCR fallback for problem pages.

    OCR Provider Routing:
    - "auto" (default): Detect handwriting → Gemini for handwritten, Mistral for printed
    - "deepinfra": Force DeepInfra Mistral-Small (best for LaTeX/equations)
    - "gemini": Force Gemini (best for handwriting)

    PARALLEL MODE (default):
    - 20 pages @ 13s each = ~26s total (vs 260s sequential)
    - 30 pages @ 13s each = ~39s total (vs 390s sequential)

    Args:
        pdf_path: Path to PDF file
        doc_id: Optional document ID for logging
        ocr_provider: "auto" (smart routing), "deepinfra", or "gemini"
        deepinfra_model: Model key for deepinfra - "mistral-small" (default, best for LaTeX),
                        "olmocr2", "gemma-12b", or "deepseek-ocr"
        parallel: Use parallel async OCR (default True, 10x faster)
        max_concurrent: Max concurrent OCR requests (default 10)

    Returns:
        List of page texts (1 string per page), with OCR substitutions applied
    """
    import base64
    from pdf2image import convert_from_path
    from io import BytesIO

    doc = fitz.open(pdf_path)
    pages_text = []

    # Step 1: Extract all pages with PyMuPDF
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()

    # Step 2: Check for encoding issues
    encoding_check = check_pdf_encoding(pdf_path)

    if encoding_check['pages_with_issues']:
        log_encoding_issues(encoding_check, doc_id)

        # Step 2.5: Auto-detect handwriting if provider is "auto"
        actual_provider = ocr_provider
        if ocr_provider == "auto":
            print("   🔍 Detecting content type (handwritten vs printed)...")
            # Check first problem page
            first_problem_page = encoding_check['problem_page_numbers'][0]
            try:
                images = convert_from_path(pdf_path, first_page=first_problem_page, last_page=first_problem_page, dpi=100)
                if images:
                    buffer = BytesIO()
                    images[0].save(buffer, format="PNG")
                    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    hw_check = detect_handwriting(b64)
                    actual_provider = hw_check["recommended_ocr"]
                    print(f"   📝 Content type: {hw_check['content_type']} → using {actual_provider}")
                else:
                    actual_provider = "deepinfra"
            except Exception as e:
                print(f"   ⚠️ Handwriting detection failed: {e}, defaulting to deepinfra")
                actual_provider = "deepinfra"

        # Step 3: OCR the problem pages (parallel or sequential)
        if parallel and actual_provider == "deepinfra":
            ocr_results = ocr_problem_pages_parallel(
                pdf_path,
                encoding_check['problem_page_numbers'],
                ocr_provider=actual_provider,
                deepinfra_model=deepinfra_model,
                max_concurrent=max_concurrent
            )
        else:
            ocr_results = ocr_problem_pages(
                pdf_path,
                encoding_check['problem_page_numbers'],
                ocr_provider=actual_provider,
                deepinfra_model=deepinfra_model
            )

        # Step 4: Swap in OCR text for problem pages
        for page_num, ocr_text in ocr_results.items():
            idx = page_num - 1  # Convert to 0-indexed
            if 0 <= idx < len(pages_text):
                pages_text[idx] = ocr_text
                print(f"      ↔️ Page {page_num}: Swapped PyMuPDF → OCR")

    return pages_text
