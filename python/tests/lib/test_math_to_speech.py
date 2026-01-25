"""Tests for lib/math_to_speech.py - Mathematical notation to speech conversion."""

import pytest
from lib.math_to_speech import equation_to_speech, extract_equations, SYMBOL_MAP, PATTERNS


class TestSuperscripts:
    """Test superscript conversion."""

    def test_squared(self):
        assert "squared" in equation_to_speech("x²")

    def test_cubed(self):
        assert "cubed" in equation_to_speech("x³")

    def test_fourth_power(self):
        assert "fourth" in equation_to_speech("x⁴")

    def test_nth_power(self):
        assert "to the n" in equation_to_speech("xⁿ")


class TestSubscriptsChemistry:
    """Test subscript conversion for chemical formulas."""

    def test_water(self):
        result = equation_to_speech("H₂O")
        assert "two" in result.lower()
        assert "H" in result
        assert "O" in result

    def test_carbon_dioxide(self):
        result = equation_to_speech("CO₂")
        assert "two" in result.lower()

    def test_sulfuric_acid(self):
        result = equation_to_speech("H₂SO₄")
        assert "two" in result.lower()
        assert "four" in result.lower()


class TestGreekLetters:
    """Test Greek letter conversion."""

    def test_alpha(self):
        assert "alpha" in equation_to_speech("α").lower()

    def test_beta(self):
        assert "beta" in equation_to_speech("β").lower()

    def test_pi(self):
        assert "pi" in equation_to_speech("π").lower()

    def test_sigma_lowercase(self):
        assert "sigma" in equation_to_speech("σ").lower()

    def test_sigma_uppercase(self):
        assert "sigma" in equation_to_speech("Σ").lower()

    def test_omega(self):
        assert "omega" in equation_to_speech("ω").lower()

    def test_delta(self):
        assert "delta" in equation_to_speech("δ").lower()

    def test_theta(self):
        assert "theta" in equation_to_speech("θ").lower()


class TestOperators:
    """Test mathematical operator conversion."""

    def test_square_root(self):
        assert "square root" in equation_to_speech("√x").lower()

    def test_cube_root(self):
        assert "cube root" in equation_to_speech("∛x").lower()

    def test_integral(self):
        assert "integral" in equation_to_speech("∫f(x)dx").lower()

    def test_partial(self):
        assert "partial" in equation_to_speech("∂f/∂x").lower()

    def test_sum(self):
        assert "sum" in equation_to_speech("∑x").lower()

    def test_product(self):
        assert "product" in equation_to_speech("∏x").lower()

    def test_infinity(self):
        assert "infinity" in equation_to_speech("∞").lower()


class TestComparisons:
    """Test comparison operator conversion."""

    def test_less_than_or_equal(self):
        assert "less than or equal" in equation_to_speech("x ≤ y").lower()

    def test_greater_than_or_equal(self):
        assert "greater than or equal" in equation_to_speech("x ≥ y").lower()

    def test_not_equal(self):
        assert "not equal" in equation_to_speech("x ≠ y").lower()

    def test_approximately_equal(self):
        assert "approximately" in equation_to_speech("x ≈ y").lower()

    def test_plus_or_minus(self):
        assert "plus or minus" in equation_to_speech("x ± y").lower()


class TestFractions:
    """Test fraction conversion."""

    def test_half(self):
        assert "half" in equation_to_speech("½").lower()

    def test_quarter(self):
        assert "quarter" in equation_to_speech("¼").lower()

    def test_three_quarters(self):
        assert "three quarters" in equation_to_speech("¾").lower()

    def test_third(self):
        assert "third" in equation_to_speech("⅓").lower()

    def test_two_thirds(self):
        assert "two thirds" in equation_to_speech("⅔").lower()


class TestLatexPatterns:
    """Test LaTeX pattern conversion."""

    def test_latex_fraction(self):
        result = equation_to_speech("\\frac{1}{2}")
        assert "1" in result
        assert "over" in result.lower()
        assert "2" in result

    def test_latex_sqrt(self):
        result = equation_to_speech("\\sqrt{x}")
        assert "square root" in result.lower()
        assert "x" in result

    def test_latex_nth_root(self):
        result = equation_to_speech("\\sqrt[3]{x}")
        assert "3" in result
        assert "root" in result.lower()
        assert "x" in result

    def test_latex_power(self):
        result = equation_to_speech("x^{2}")
        assert "power" in result.lower()
        assert "2" in result

    def test_latex_subscript(self):
        result = equation_to_speech("x_{i}")
        assert "sub" in result.lower()
        assert "i" in result

    def test_simple_power(self):
        result = equation_to_speech("x^2")
        assert "squared" in result.lower()

    def test_simple_fraction(self):
        result = equation_to_speech("3/4")
        assert "3" in result
        assert "over" in result.lower()
        assert "4" in result


class TestCombinedExpressions:
    """Test combined/real-world expressions."""

    def test_einstein_equation(self):
        result = equation_to_speech("E = mc²")
        assert "E" in result
        assert "m" in result
        assert "c" in result
        assert "squared" in result.lower()

    def test_pythagorean(self):
        result = equation_to_speech("a² + b² = c²")
        assert "squared" in result.lower()

    def test_quadratic_formula(self):
        # x = (-b ± √(b² - 4ac)) / 2a
        result = equation_to_speech("x = (-b ± √(b² - 4ac)) / 2a")
        assert "plus or minus" in result.lower()
        assert "square root" in result.lower()
        assert "squared" in result.lower()

    def test_empty_string(self):
        assert equation_to_speech("") == ""

    def test_plain_text(self):
        text = "This is plain text without math"
        result = equation_to_speech(text)
        assert "This" in result
        assert "plain" in result


class TestExtractEquations:
    """Test equation extraction from text."""

    def test_inline_math(self):
        text = "The formula is $E = mc^2$ which is famous."
        equations = extract_equations(text)
        assert len(equations) >= 1
        assert any("E = mc^2" in eq["latex"] for eq in equations)

    def test_display_math_double_dollar(self):
        text = "Consider $$\\int_0^1 x^2 dx$$ as an example."
        equations = extract_equations(text)
        assert len(equations) >= 1
        assert any(eq["display"] is True for eq in equations)

    def test_display_math_brackets(self):
        text = "The equation \\[x = \\frac{-b}{2a}\\] is important."
        equations = extract_equations(text)
        assert len(equations) >= 1

    def test_no_equations(self):
        text = "This text has no mathematical equations."
        equations = extract_equations(text)
        assert len(equations) == 0

    def test_multiple_equations(self):
        text = "We have $a = 1$ and $b = 2$ and $c = 3$."
        equations = extract_equations(text)
        assert len(equations) == 3


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_preserved_in_plain_text(self):
        # Plain text should remain mostly intact
        text = "Hello, world!"
        assert equation_to_speech(text) == "Hello, world!"

    def test_multiple_spaces_collapsed(self):
        text = "a  +  b"  # Extra spaces
        result = equation_to_speech(text)
        assert "  " not in result  # Should collapse to single space

    def test_degrees_symbol(self):
        result = equation_to_speech("90°")
        assert "degrees" in result.lower()

    def test_chemistry_arrow(self):
        result = equation_to_speech("A → B")
        assert "yields" in result.lower() or "implies" in result.lower()

    def test_set_notation(self):
        result = equation_to_speech("x ∈ S")
        assert "in" in result.lower()
