"""
Optimize text for text-to-speech (TTS) output.

This module preprocesses text to make it sound natural when spoken:
- Converts mathematical notation to spoken form
- Expands abbreviations
- Handles citations and references
- Formats lists for natural pauses
- Converts tables and code to spoken descriptions
"""

import re
from typing import List, Optional

from lib.math_to_speech import equation_to_speech


# Common abbreviations and their expansions
ABBREVIATIONS = {
    # Academic
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "et cetera",
    "et al.": "and others",
    "vs.": "versus",
    "cf.": "compare",
    "viz.": "namely",
    "ibid.": "in the same place",
    "op. cit.": "in the work cited",
    "loc. cit.": "in the place cited",
    "N.B.": "note well",
    "P.S.": "postscript",
    "Q.E.D.": "which was to be demonstrated",

    # Document references
    "Fig.": "Figure",
    "Figs.": "Figures",
    "Eq.": "Equation",
    "Eqs.": "Equations",
    "Ch.": "Chapter",
    "Sec.": "Section",
    "Vol.": "Volume",
    "No.": "Number",
    "p.": "page",
    "pp.": "pages",
    "Ref.": "Reference",
    "Refs.": "References",
    "Tab.": "Table",

    # Titles
    "Dr.": "Doctor",
    "Prof.": "Professor",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Ms.": "Miss",
    "Jr.": "Junior",
    "Sr.": "Senior",

    # Units (common)
    "km": "kilometers",
    "cm": "centimeters",
    "mm": "millimeters",
    "kg": "kilograms",
    "mg": "milligrams",
    "ml": "milliliters",
    "Hz": "hertz",
    "kHz": "kilohertz",
    "MHz": "megahertz",
    "GHz": "gigahertz",

    # Time
    "min.": "minutes",
    "sec.": "seconds",
    "hr.": "hours",
    "approx.": "approximately",
}


def optimize_for_tts(text: str) -> str:
    """
    Optimize text for natural text-to-speech output.

    This is the main function called at runtime on LLM output
    before sending to TTS engine.

    Args:
        text: Raw text to optimize

    Returns:
        TTS-optimized text

    Examples:
        >>> optimize_for_tts("The formula is E = mc²")
        "The formula is E = mc squared"
        >>> optimize_for_tts("See Fig. 3 for details")
        "See Figure 3 for details"
    """
    if not text:
        return text

    # 1. Convert mathematical notation
    text = equation_to_speech(text)

    # 2. Expand abbreviations (case-sensitive for proper handling)
    for abbr, expanded in ABBREVIATIONS.items():
        # Use word boundaries to avoid partial matches
        text = re.sub(
            rf"\b{re.escape(abbr)}",
            expanded,
            text,
            flags=re.IGNORECASE if abbr[0].islower() else 0
        )

    # 3. Handle citations - remove inline citation numbers [1], [2,3], etc.
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)

    # 4. Handle author-year citations - (Smith, 2020), (Smith & Jones, 2021)
    text = re.sub(r'\([A-Z][a-z]+(?:\s*(?:&|and)\s*[A-Z][a-z]+)?,?\s*\d{4}[a-z]?\)', '', text)

    # 5. Handle URLs - replace with "link"
    text = re.sub(r'https?://\S+', ' link ', text)

    # 6. Handle email addresses
    text = re.sub(r'\S+@\S+\.\S+', ' email address ', text)

    # 7. Add pauses for numbered lists (1. Item → 1... Item)
    text = re.sub(r'(\d+)\.\s+', r'\1... ', text)

    # 8. Handle bullet points
    text = re.sub(r'^[\•\-\*]\s+', '... ', text, flags=re.MULTILINE)

    # 9. Handle em-dashes and en-dashes (add pauses)
    text = re.sub(r'\s*[—–]\s*', '... ', text)

    # 10. Handle parenthetical asides (add slight pauses)
    text = re.sub(r'\(([^)]+)\)', r'... \1 ...', text)

    # 11. Clean up multiple spaces and periods
    text = re.sub(r'\.{4,}', '...', text)
    text = re.sub(r'\s+', ' ', text)

    # 12. Clean up spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    return text.strip()


def table_to_speech(headers: List[str], rows: List[List[str]], max_rows: int = 5) -> str:
    """
    Convert a table to natural speech.

    Args:
        headers: List of column header names
        rows: List of row data (each row is a list of cell values)
        max_rows: Maximum rows to read aloud (default 5)

    Returns:
        Spoken description of the table

    Examples:
        >>> table_to_speech(["Name", "Age"], [["Alice", "25"], ["Bob", "30"]])
        "This table has 2 columns: Name, Age. Row 1: Name: Alice; Age: 25. Row 2: Name: Bob; Age: 30."
    """
    if not headers:
        return "This is a table with no headers."

    lines = []

    # Describe structure
    col_count = len(headers)
    row_count = len(rows)
    lines.append(f"This table has {col_count} columns: {', '.join(headers)}.")

    if row_count == 0:
        lines.append("The table is empty.")
        return " ".join(lines)

    # Read rows (limited)
    rows_to_read = min(max_rows, row_count)
    for i, row in enumerate(rows[:rows_to_read]):
        # Build row description
        cells = []
        for j, cell in enumerate(row):
            if j < len(headers):
                cell_value = str(cell).strip() if cell else "empty"
                cells.append(f"{headers[j]}: {cell_value}")
        row_text = "; ".join(cells)
        lines.append(f"Row {i + 1}: {row_text}.")

    # Mention remaining rows
    if row_count > max_rows:
        remaining = row_count - max_rows
        lines.append(f"And {remaining} more row{'s' if remaining > 1 else ''}.")

    return " ".join(lines)


def code_to_speech(code: str, language: str = "unknown") -> str:
    """
    Convert code to a spoken description (not literal reading).

    Args:
        code: The code block content
        language: Programming language (if known)

    Returns:
        Spoken description of the code

    Examples:
        >>> code_to_speech("def add(a, b):\\n    return a + b", "python")
        "This is a Python code block with 2 lines. It defines a function. Please refer to the visual display for the exact code."
    """
    if not code:
        return "This is an empty code block."

    lines = code.strip().split('\n')
    line_count = len(lines)

    # Format language name
    lang_display = language.capitalize() if language and language != "unknown" else ""

    # Basic description
    if lang_display:
        desc = f"This is a {lang_display} code block with {line_count} line{'s' if line_count > 1 else ''}."
    else:
        desc = f"This is a code block with {line_count} line{'s' if line_count > 1 else ''}."

    # Try to identify what the code does (simple heuristics)
    code_lower = code.lower()
    purposes = []

    if 'def ' in code or 'function ' in code:
        purposes.append("defines a function")
    if 'class ' in code:
        purposes.append("defines a class")
    if 'import ' in code or 'require' in code or 'include' in code:
        purposes.append("imports modules")
    if 'for ' in code or 'while ' in code:
        purposes.append("contains a loop")
    if 'if ' in code:
        purposes.append("contains conditional logic")
    if 'return ' in code:
        purposes.append("returns a value")
    if 'print' in code_lower or 'console.log' in code_lower or 'system.out' in code_lower:
        purposes.append("outputs to console")

    if purposes:
        desc += f" It {', '.join(purposes[:2])}."

    desc += " Please refer to the visual display for the exact code."

    return desc


def list_to_speech(items: List[str], ordered: bool = True) -> str:
    """
    Convert a list to natural speech.

    Args:
        items: List items
        ordered: Whether it's an ordered (numbered) list

    Returns:
        Spoken version of the list
    """
    if not items:
        return "This is an empty list."

    lines = []
    for i, item in enumerate(items):
        if ordered:
            lines.append(f"Item {i + 1}: {item}")
        else:
            lines.append(item)

    return ". ".join(lines) + "."


def image_to_speech(description: str, image_type: str = "image") -> str:
    """
    Format an image description for speech.

    Args:
        description: Image description text
        image_type: Type of image (diagram, graph, photo, etc.)

    Returns:
        Speech-formatted description
    """
    if not description:
        return f"There is a {image_type} here."

    # Clean up the description
    description = description.strip()
    if not description.endswith('.'):
        description += '.'

    return f"This {image_type} shows: {description}"
