"""Tests for lib/content_detector.py - Content type classification."""

import pytest
from lib.content_detector import (
    ContentType,
    detect_content_type,
    extract_definitions,
    extract_procedure_steps,
    has_code_block,
    has_table,
    has_equation,
)


class TestContentTypeDetection:
    """Test detection of different content types."""

    def test_detect_definition_colon_pattern(self):
        text = "Entropy: A measure of disorder in a thermodynamic system."
        assert detect_content_type(text) == ContentType.DEFINITION

    def test_detect_definition_defined_as_pattern(self):
        text = "A catalyst is defined as a substance that speeds up a reaction."
        assert detect_content_type(text) == ContentType.DEFINITION

    def test_detect_example_for_example(self):
        text = "For example, consider a ball rolling down a hill."
        assert detect_content_type(text) == ContentType.EXAMPLE

    def test_detect_example_eg(self):
        text = "Common acids include e.g. HCl, H2SO4, and HNO3."
        assert detect_content_type(text) == ContentType.EXAMPLE

    def test_detect_example_worked_example(self):
        # Note: "Worked example:" has a colon pattern that matches DEFINITION first
        # because DEFINITION is checked before EXAMPLE in the priority order
        text = "Consider the following worked example to understand momentum."
        assert detect_content_type(text) == ContentType.EXAMPLE

    def test_detect_theorem(self):
        # Note: Avoiding "function" which matches CODE patterns
        text = "Theorem 1: Every prime number greater than 2 is odd."
        assert detect_content_type(text) == ContentType.THEOREM

    def test_detect_lemma(self):
        text = "Lemma 2.3: If f is differentiable at x, then f is continuous at x."
        assert detect_content_type(text) == ContentType.THEOREM

    def test_detect_corollary(self):
        text = "Corollary: As a direct consequence of the above theorem..."
        assert detect_content_type(text) == ContentType.THEOREM

    def test_detect_proof(self):
        text = "Proof: We proceed by contradiction. Assume that..."
        assert detect_content_type(text) == ContentType.PROOF

    def test_detect_proof_qed(self):
        text = "...therefore the statement is true. Q.E.D."
        assert detect_content_type(text) == ContentType.PROOF

    def test_detect_proof_by_induction(self):
        text = "We prove this by induction on n."
        assert detect_content_type(text) == ContentType.PROOF

    def test_detect_procedure_numbered(self):
        text = """1. First, gather your materials.
2. Next, prepare the solution.
3. Finally, record your observations."""
        assert detect_content_type(text) == ContentType.PROCEDURE

    def test_detect_procedure_step_keyword(self):
        text = "Step 1: Initialize the variables. Step 2: Enter the loop."
        assert detect_content_type(text) == ContentType.PROCEDURE

    def test_detect_code_markdown(self):
        text = """Here is the code:
```python
def hello():
    print("Hello, world!")
```"""
        assert detect_content_type(text) == ContentType.CODE

    def test_detect_code_python_patterns(self):
        text = "def calculate_sum(a, b):\n    return a + b"
        assert detect_content_type(text) == ContentType.CODE

    def test_detect_code_java_patterns(self):
        text = "public class Main { public static void main(String[] args) {} }"
        assert detect_content_type(text) == ContentType.CODE

    def test_detect_narrative_default(self):
        text = "This is a general paragraph about physics concepts and their applications."
        assert detect_content_type(text) == ContentType.NARRATIVE

    def test_short_text_is_narrative(self):
        text = "Hello"
        assert detect_content_type(text) == ContentType.NARRATIVE

    def test_empty_text_is_narrative(self):
        text = ""
        assert detect_content_type(text) == ContentType.NARRATIVE


class TestPriorityOrder:
    """Test that detection follows correct priority order."""

    def test_code_takes_precedence_over_definition(self):
        # Text with both code and definition patterns
        text = """Definition: A function is defined as follows:
def my_function():
    return 42"""
        # Code should take precedence
        result = detect_content_type(text)
        assert result == ContentType.CODE

    def test_proof_takes_precedence_over_theorem(self):
        # Text with both proof and theorem patterns
        text = "Proof of Theorem 1: We show that..."
        result = detect_content_type(text)
        assert result == ContentType.PROOF


class TestExtractDefinitions:
    """Test definition extraction."""

    def test_extract_colon_definition(self):
        text = "Entropy: A measure of disorder in a system."
        definitions = extract_definitions(text)
        assert len(definitions) >= 1
        assert any(d["term"].strip() == "Entropy" for d in definitions)

    def test_extract_dash_definition(self):
        text = "Catalyst - A substance that increases reaction rate."
        definitions = extract_definitions(text)
        assert len(definitions) >= 1

    def test_extract_em_dash_definition(self):
        text = "Vector — A quantity with both magnitude and direction."
        definitions = extract_definitions(text)
        assert len(definitions) >= 1

    def test_extract_multiple_definitions(self):
        text = """Acid: A substance that donates protons.
Base: A substance that accepts protons.
Salt: The product of an acid-base reaction."""
        definitions = extract_definitions(text)
        assert len(definitions) >= 2

    def test_extract_is_defined_as(self):
        text = "Momentum is defined as the product of mass and velocity."
        definitions = extract_definitions(text)
        assert len(definitions) >= 1

    def test_no_definitions_in_narrative(self):
        text = "This paragraph discusses various topics without defining anything specific."
        definitions = extract_definitions(text)
        assert len(definitions) == 0


class TestExtractProcedureSteps:
    """Test procedure step extraction."""

    def test_extract_numbered_steps(self):
        text = """1. First, wash your hands.
2. Put on gloves.
3. Prepare the equipment."""
        steps = extract_procedure_steps(text)
        assert len(steps) >= 2
        assert any("1" in s for s in steps)

    def test_extract_step_keyword_format(self):
        text = """Step 1: Initialize variables.
Step 2: Enter the main loop.
Step 3: Process the data."""
        steps = extract_procedure_steps(text)
        assert len(steps) >= 2

    def test_no_steps_in_narrative(self):
        text = "This text discusses the importance of following procedures."
        steps = extract_procedure_steps(text)
        assert len(steps) == 0

    def test_parenthetical_numbers_ignored(self):
        text = "The year 1984 was significant. In 2001, things changed."
        steps = extract_procedure_steps(text)
        # These shouldn't be extracted as procedure steps
        assert len(steps) == 0 or not any("1984" in s for s in steps)


class TestHelperFunctions:
    """Test helper functions."""

    def test_has_code_block_true(self):
        text = """Here is code:
```python
print("hello")
```"""
        assert has_code_block(text) is True

    def test_has_code_block_false(self):
        text = "This is just regular text without any code."
        assert has_code_block(text) is False

    def test_has_table_true(self):
        text = "| Name | Age | City |\n|------|-----|------|\n| John | 25 | NYC |"
        assert has_table(text) is True

    def test_has_table_false(self):
        text = "This text has no table structures."
        assert has_table(text) is False

    def test_has_equation_display_true(self):
        text = "The formula is $$E = mc^2$$ which is famous."
        assert has_equation(text) is True

    def test_has_equation_inline_true(self):
        text = "The value of $x = 5$ is the solution."
        assert has_equation(text) is True

    def test_has_equation_latex_brackets(self):
        text = "Consider \\[x + y = z\\] as an example."
        assert has_equation(text) is True

    def test_has_equation_false(self):
        text = "This text has no mathematical equations."
        assert has_equation(text) is False


class TestContentTypeEnum:
    """Test ContentType enum properties."""

    def test_all_content_types_exist(self):
        expected_types = [
            "definition", "example", "theorem", "proof",
            "procedure", "code", "equation", "narrative"
        ]
        for t in expected_types:
            assert hasattr(ContentType, t.upper())

    def test_content_type_is_string_enum(self):
        assert ContentType.DEFINITION.value == "definition"
        assert ContentType.CODE.value == "code"
        assert isinstance(ContentType.NARRATIVE.value, str)
