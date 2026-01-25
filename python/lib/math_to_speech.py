"""
Convert mathematical notation to speakable text for TTS.

This module handles:
- Unicode symbols (², ³, π, ∫, etc.)
- LaTeX notation (\\frac{}, \\sqrt{}, ^{}, _{})
- Chemical formulas (H₂O → "H two O")
- Greek letters
- Mathematical operators
"""

import re
from typing import List, Tuple

# Symbol to spoken text mapping
SYMBOL_MAP = {
    # Superscripts
    "²": " squared",
    "³": " cubed",
    "⁴": " to the fourth",
    "⁵": " to the fifth",
    "⁶": " to the sixth",
    "⁷": " to the seventh",
    "⁸": " to the eighth",
    "⁹": " to the ninth",
    "⁰": " to the zero",
    "ⁿ": " to the n",

    # Subscripts (literal for chemistry: H₂O → "H two O")
    "₀": " zero ",
    "₁": " one ",
    "₂": " two ",
    "₃": " three ",
    "₄": " four ",
    "₅": " five ",
    "₆": " six ",
    "₇": " seven ",
    "₈": " eight ",
    "₉": " nine ",

    # Greek letters (lowercase)
    "α": " alpha ",
    "β": " beta ",
    "γ": " gamma ",
    "δ": " delta ",
    "ε": " epsilon ",
    "ζ": " zeta ",
    "η": " eta ",
    "θ": " theta ",
    "ι": " iota ",
    "κ": " kappa ",
    "λ": " lambda ",
    "μ": " mu ",
    "ν": " nu ",
    "ξ": " xi ",
    "π": " pi ",
    "ρ": " rho ",
    "σ": " sigma ",
    "τ": " tau ",
    "υ": " upsilon ",
    "φ": " phi ",
    "χ": " chi ",
    "ψ": " psi ",
    "ω": " omega ",

    # Greek letters (uppercase)
    "Α": " Alpha ",
    "Β": " Beta ",
    "Γ": " Gamma ",
    "Δ": " Delta ",
    "Ε": " Epsilon ",
    "Θ": " Theta ",
    "Λ": " Lambda ",
    "Π": " Pi ",
    "Σ": " Sigma ",
    "Φ": " Phi ",
    "Ψ": " Psi ",
    "Ω": " Omega ",

    # Mathematical operators
    "√": " square root of ",
    "∛": " cube root of ",
    "∜": " fourth root of ",
    "∫": " integral of ",
    "∬": " double integral of ",
    "∭": " triple integral of ",
    "∮": " contour integral of ",
    "∂": " partial ",
    "∇": " del ",
    "∑": " sum of ",
    "∏": " product of ",
    "∞": " infinity ",
    "∝": " proportional to ",
    "∆": " delta ",

    # Comparisons and relations
    "≤": " less than or equal to ",
    "≥": " greater than or equal to ",
    "≠": " not equal to ",
    "≈": " approximately equal to ",
    "≡": " identical to ",
    "≢": " not identical to ",
    "∼": " similar to ",
    "≪": " much less than ",
    "≫": " much greater than ",
    "±": " plus or minus ",
    "∓": " minus or plus ",
    "×": " times ",
    "÷": " divided by ",
    "·": " dot ",

    # Set notation
    "∈": " in ",
    "∉": " not in ",
    "⊂": " subset of ",
    "⊃": " superset of ",
    "⊆": " subset or equal to ",
    "⊇": " superset or equal to ",
    "∪": " union ",
    "∩": " intersection ",
    "∅": " empty set ",

    # Logic
    "∧": " and ",
    "∨": " or ",
    "¬": " not ",
    "⊕": " exclusive or ",
    "∀": " for all ",
    "∃": " there exists ",
    "∄": " there does not exist ",
    "⊢": " proves ",
    "⊨": " models ",
    "→": " implies ",
    "↔": " if and only if ",
    "⇒": " implies ",
    "⇔": " if and only if ",

    # Arrows (chemistry)
    "⟶": " yields ",
    "⇌": " reversible ",
    "↑": " gas evolved ",
    "↓": " precipitate ",

    # Fractions
    "½": " one half ",
    "⅓": " one third ",
    "⅔": " two thirds ",
    "¼": " one quarter ",
    "¾": " three quarters ",
    "⅕": " one fifth ",
    "⅖": " two fifths ",
    "⅗": " three fifths ",
    "⅘": " four fifths ",
    "⅙": " one sixth ",
    "⅚": " five sixths ",
    "⅛": " one eighth ",
    "⅜": " three eighths ",
    "⅝": " five eighths ",
    "⅞": " seven eighths ",

    # Units and misc
    "°": " degrees ",
    "′": " prime ",
    "″": " double prime ",
    "‰": " per mille ",
    "‱": " per ten thousand ",
    "ℏ": " h bar ",
    "ℓ": " ell ",
    "ℵ": " aleph ",
    "ℶ": " beth ",
}

# Regex patterns for complex expressions (order matters!)
PATTERNS: List[Tuple[str, str]] = [
    # LaTeX fractions: \frac{a}{b} → "a over b"
    (r"\\frac\{([^}]+)\}\{([^}]+)\}", r" \1 over \2 "),

    # LaTeX square root: \sqrt{x} → "square root of x"
    (r"\\sqrt\{([^}]+)\}", r" square root of \1 "),

    # LaTeX nth root: \sqrt[n]{x} → "nth root of x"
    (r"\\sqrt\[([^\]]+)\]\{([^}]+)\}", r" \1 root of \2 "),

    # LaTeX powers: x^{2} → "x to the power of 2"
    (r"\^\{([^}]+)\}", r" to the power of \1 "),

    # LaTeX subscripts: x_{i} → "x sub i"
    (r"_\{([^}]+)\}", r" sub \1 "),

    # Simple powers: x^2 → "x squared", x^3 → "x cubed"
    (r"\^2(?![0-9])", " squared "),
    (r"\^3(?![0-9])", " cubed "),
    (r"\^n(?![a-z])", " to the n "),

    # Simple fractions: 3/4 → "3 over 4"
    (r"(\d+)\s*/\s*(\d+)", r" \1 over \2 "),

    # LaTeX integral with limits: \int_{a}^{b} → "integral from a to b"
    (r"\\int_\{([^}]+)\}\^\{([^}]+)\}", r" integral from \1 to \2 of "),

    # LaTeX sum with limits: \sum_{i=1}^{n} → "sum from i equals 1 to n"
    (r"\\sum_\{([^}]+)\}\^\{([^}]+)\}", r" sum from \1 to \2 of "),

    # LaTeX limit: \lim_{x \to a} → "limit as x approaches a"
    (r"\\lim_\{([^}]+)\\to([^}]+)\}", r" limit as \1 approaches \2 of "),

    # Inline math delimiters (remove them)
    (r"\$([^$]+)\$", r" \1 "),

    # Display math delimiters (remove them)
    (r"\\\[(.+?)\\\]", r" \1 "),
    (r"\\\((.+?)\\\)", r" \1 "),
]


def equation_to_speech(text: str) -> str:
    """
    Convert mathematical notation to speakable text.

    Args:
        text: Text containing mathematical notation

    Returns:
        Text with math converted to spoken form

    Examples:
        >>> equation_to_speech("E = mc²")
        "E = mc squared"
        >>> equation_to_speech("H₂O")
        "H two O"
        >>> equation_to_speech("∫f(x)dx")
        "integral of f(x)dx"
    """
    if not text:
        return text

    # Apply regex patterns first (order matters for LaTeX)
    for pattern, replacement in PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)

    # Apply symbol replacements
    for symbol, spoken in SYMBOL_MAP.items():
        text = text.replace(symbol, spoken)

    # Clean up: remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Clean up: remove spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    return text.strip()


def extract_equations(text: str) -> List[dict]:
    """
    Extract equations from text with their LaTeX and spoken forms.

    Args:
        text: Text potentially containing equations

    Returns:
        List of dicts with 'latex' and 'spoken' keys
    """
    equations = []

    # Find inline math: $...$
    inline_pattern = r"\$([^$]+)\$"
    for match in re.finditer(inline_pattern, text):
        latex = match.group(1)
        equations.append({
            "latex": latex,
            "spoken": equation_to_speech(latex),
            "display": False,
        })

    # Find display math: \[...\] or $$...$$
    display_patterns = [
        r"\\\[(.+?)\\\]",
        r"\$\$(.+?)\$\$",
    ]
    for pattern in display_patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            latex = match.group(1)
            equations.append({
                "latex": latex,
                "spoken": equation_to_speech(latex),
                "display": True,
            })

    return equations
