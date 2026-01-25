"""
Detect content types in educational text.

This module classifies text blocks into educational content types:
- Definition: Term definitions, glossary entries
- Example: Worked examples, sample problems
- Theorem: Theorems, lemmas, corollaries
- Proof: Mathematical proofs
- Procedure: Step-by-step instructions, algorithms
- Code: Programming code blocks
- Equation: Mathematical equations (standalone)
- Narrative: General explanatory text
"""

import re
from enum import Enum
from typing import List, Optional


class ContentType(str, Enum):
    """Educational content type classification."""
    DEFINITION = "definition"
    EXAMPLE = "example"
    THEOREM = "theorem"
    PROOF = "proof"
    PROCEDURE = "procedure"
    CODE = "code"
    EQUATION = "equation"
    NARRATIVE = "narrative"


# Detection patterns for each content type
DEFINITION_PATTERNS = [
    r"(?:is defined as|definition[:\s]|means that|refers to)",
    r"(?:we define|let us define|defined to be)",
    r"(?:^|\n)[A-Z][a-z][a-zA-Z\s]{1,25}:\s+[A-Za-z]",  # "Term: Definition..." at line start
    r"(?:glossary|terminology)[:\s]",
    r"[A-Z][a-z]+\s+[-–—]\s+[A-Za-z]",  # "Term - Definition..." with dash separator
]

EXAMPLE_PATTERNS = [
    r"(?:for example|e\.g\.|such as|consider the following)",
    r"(?:example\s*\d*[:\s]|sample[:\s]|illustration[:\s])",
    r"(?:worked example|solved problem|practice problem)",
    r"(?:let's see|let us consider|suppose that)",
]

THEOREM_PATTERNS = [
    r"(?:theorem|lemma|corollary|proposition|conjecture)\s*\d*[:\s.]",
    r"(?:law|principle|rule)\s*\d*[:\s]",
    r"(?:axiom|postulate)\s*\d*[:\s]",
]

PROOF_PATTERNS = [
    r"(?:proof[:\s.]|q\.e\.d\.|∎|□)",
    r"(?:we prove|to prove|it follows that)",
    r"(?:by induction|by contradiction|by contrapositive)",
    r"(?:hence proved|thus proved|this completes the proof)",
]

PROCEDURE_PATTERNS = [
    r"(?:step\s*\d+[:\s.]|procedure[:\s]|algorithm[:\s])",
    r"(?:method[:\s]|process[:\s]|technique[:\s])",
    r"(?:first,?\s*(?:we)?|second,?\s*(?:we)?|third,?\s*(?:we)?|finally,?\s*(?:we)?)",
    r"^\s*\d+\.\s+[A-Z]",  # Numbered list starting with capital
    r"(?:how to|steps to|instructions for)",
]

CODE_PATTERNS = [
    r"```[\w]*\n",  # Markdown code blocks
    r"(?:^|\n)\s*def \w+\s*\(",  # Python function definition
    r"(?:^|\n)\s*class \w+[:\(]",  # Python/Java class definition
    r"(?:^|\n)\s*from \w+ import",  # Python import
    r"(?:^|\n)\s*import \w+",  # Python/Java import at line start
    r"(?:public |private |protected )\s*(?:static )?\w+\s+\w+\s*\(",  # Java/C++ methods
    r"(?:^|\n)\s*(?:const |let |var )\w+\s*=",  # JavaScript variable declaration
    r"function\s*\w*\s*\([^)]*\)\s*\{",  # JavaScript function
    r"=>\s*\{",  # Arrow functions with body
    r"(?:^|\n)\s*SELECT\s+.+\s+FROM\s+\w+",  # SQL SELECT query (requires both SELECT and FROM)
    r"(?:print\(|console\.log\(|System\.out\.print)",  # Print statements (more specific)
    r"if __name__\s*==\s*['\"]__main__['\"]",  # Python main block
    r"^#!/",  # Shebang at file start
]

EQUATION_PATTERNS = [
    r"\$\$.+\$\$",  # Display math
    r"\\\[.+\\\]",  # LaTeX display
    r"(?:equation|formula|expression)[:\s]",
    r"[a-zA-Z]\s*=\s*[^,\n]{5,}",  # Variable = expression
]


def detect_content_type(text: str) -> ContentType:
    """
    Detect the primary content type of a text block.

    Args:
        text: The text block to classify

    Returns:
        ContentType enum value

    Examples:
        >>> detect_content_type("Definition: Entropy is a measure of disorder")
        ContentType.DEFINITION
        >>> detect_content_type("def calculate_sum(a, b):\\n    return a + b")
        ContentType.CODE
    """
    if not text or len(text.strip()) < 10:
        return ContentType.NARRATIVE

    text_lower = text.lower()
    text_stripped = text.strip()

    # Check patterns in priority order (most specific first)

    # 1. Code (highest priority - very distinctive)
    for pattern in CODE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return ContentType.CODE

    # 2. Proof (before theorem, as proofs often follow theorems)
    for pattern in PROOF_PATTERNS:
        if re.search(pattern, text_lower):
            return ContentType.PROOF

    # 3. Theorem/Lemma/Corollary
    for pattern in THEOREM_PATTERNS:
        if re.search(pattern, text_lower):
            return ContentType.THEOREM

    # 4. Definition (check both lower and original for patterns with case)
    for pattern in DEFINITION_PATTERNS:
        if re.search(pattern, text_lower) or re.search(pattern, text, re.MULTILINE):
            return ContentType.DEFINITION

    # 5. Example
    for pattern in EXAMPLE_PATTERNS:
        if re.search(pattern, text_lower):
            return ContentType.EXAMPLE

    # 6. Procedure (check for numbered steps)
    for pattern in PROCEDURE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return ContentType.PROCEDURE

    # 7. Standalone equation (if mostly math symbols)
    for pattern in EQUATION_PATTERNS:
        if re.search(pattern, text, re.DOTALL):
            # Only if it's short and equation-like
            if len(text_stripped) < 200:
                return ContentType.EQUATION

    # Default to narrative
    return ContentType.NARRATIVE


def extract_definitions(text: str) -> List[dict]:
    """
    Extract term-definition pairs from text.

    Args:
        text: Text containing definitions

    Returns:
        List of dicts with 'term' and 'definition' keys

    Examples:
        >>> extract_definitions("Entropy: A measure of disorder in a system.")
        [{'term': 'Entropy', 'definition': 'A measure of disorder in a system.'}]
    """
    definitions = []

    # Pattern 1: "Term: definition" or "Term - definition" or "Term — definition"
    pattern1 = r"([A-Z][a-zA-Z\s]{1,40})(?::|–|—|-)[\s]*([A-Z][^.!?]+[.!?])"
    matches = re.findall(pattern1, text)
    for term, definition in matches:
        term = term.strip()
        definition = definition.strip()
        if len(term) > 2 and len(definition) > 10:
            definitions.append({
                "term": term,
                "definition": definition,
            })

    # Pattern 2: "X is defined as Y"
    pattern2 = r"([A-Z][a-zA-Z\s]{1,40})\s+(?:is defined as|refers to|means)\s+([^.!?]+[.!?])"
    matches = re.findall(pattern2, text, re.IGNORECASE)
    for term, definition in matches:
        term = term.strip()
        definition = definition.strip()
        if len(term) > 2 and len(definition) > 10:
            # Avoid duplicates
            if not any(d["term"].lower() == term.lower() for d in definitions):
                definitions.append({
                    "term": term,
                    "definition": definition,
                })

    return definitions


def extract_procedure_steps(text: str) -> List[str]:
    """
    Extract numbered steps from procedural text.

    Args:
        text: Text containing numbered steps

    Returns:
        List of step strings

    Examples:
        >>> extract_procedure_steps("1. First step\\n2. Second step")
        ['Step 1: First step', 'Step 2: Second step']
    """
    steps = []

    # Pattern 1: "1. Step text" or "1) Step text"
    pattern1 = r"(?:^|\n)\s*(\d+)[.\)]\s+([^\n]+)"
    matches = re.findall(pattern1, text)
    for num, step_text in matches:
        step_text = step_text.strip()
        if len(step_text) > 5:
            steps.append(f"Step {num}: {step_text}")

    # Pattern 2: "Step 1: text" or "Step 1. text"
    if not steps:
        pattern2 = r"[Ss]tep\s*(\d+)[:\.\s]+([^\n]+)"
        matches = re.findall(pattern2, text)
        for num, step_text in matches:
            step_text = step_text.strip()
            if len(step_text) > 5:
                steps.append(f"Step {num}: {step_text}")

    return steps


def has_code_block(text: str) -> bool:
    """Check if text contains a code block."""
    return bool(re.search(r"```[\w]*\n.*?```", text, re.DOTALL))


def has_table(text: str) -> bool:
    """Check if text contains a markdown table."""
    # Look for markdown table pattern: | col1 | col2 |
    return bool(re.search(r"\|[^|]+\|[^|]+\|", text))


def has_equation(text: str) -> bool:
    """Check if text contains a mathematical equation."""
    patterns = [
        r"\$\$.+\$\$",  # Display math
        r"\$[^$]+\$",   # Inline math
        r"\\\[.+\\\]",  # LaTeX display
        r"\\\(.+\\\)",  # LaTeX inline
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.DOTALL):
            return True
    return False
