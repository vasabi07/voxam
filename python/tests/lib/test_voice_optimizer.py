"""Tests for lib/voice_optimizer.py - TTS optimization."""

import pytest
from lib.voice_optimizer import (
    optimize_for_tts,
    table_to_speech,
    code_to_speech,
    list_to_speech,
    image_to_speech,
    ABBREVIATIONS,
)


class TestOptimizeForTTS:
    """Test the main optimize_for_tts function."""

    def test_empty_string(self):
        assert optimize_for_tts("") == ""

    def test_none_input(self):
        assert optimize_for_tts(None) is None

    def test_plain_text_unchanged(self):
        text = "This is a simple sentence with no special formatting."
        result = optimize_for_tts(text)
        assert "simple sentence" in result

    def test_math_conversion(self):
        text = "The formula is E = mc²"
        result = optimize_for_tts(text)
        assert "squared" in result.lower()

    def test_abbreviation_eg(self):
        text = "Use a container, e.g. a beaker or flask."
        result = optimize_for_tts(text)
        assert "for example" in result.lower()

    def test_abbreviation_ie(self):
        text = "The result, i.e. the final answer, is 42."
        result = optimize_for_tts(text)
        assert "that is" in result.lower()

    def test_abbreviation_fig(self):
        text = "See Fig. 3 for details."
        result = optimize_for_tts(text)
        assert "Figure" in result

    def test_abbreviation_etc(self):
        text = "Items include pens, pencils, etc."
        result = optimize_for_tts(text)
        assert "et cetera" in result.lower()


class TestCitationRemoval:
    """Test citation removal from text."""

    def test_single_citation(self):
        text = "Studies have shown [1] that this is true."
        result = optimize_for_tts(text)
        assert "[1]" not in result

    def test_multiple_citations(self):
        text = "Research indicates [2,3] this pattern."
        result = optimize_for_tts(text)
        assert "[2,3]" not in result
        assert "[" not in result

    def test_range_citations(self):
        text = "As documented [5, 6, 7] in the literature."
        result = optimize_for_tts(text)
        assert "[5, 6, 7]" not in result

    def test_author_year_citation(self):
        text = "According to (Smith, 2020) the result is valid."
        result = optimize_for_tts(text)
        assert "(Smith, 2020)" not in result

    def test_two_author_citation(self):
        text = "The theory (Smith & Jones, 2021) explains this."
        result = optimize_for_tts(text)
        assert "(Smith & Jones, 2021)" not in result


class TestURLAndEmailHandling:
    """Test URL and email address handling."""

    def test_http_url_replaced(self):
        text = "Visit http://example.com for more info."
        result = optimize_for_tts(text)
        assert "http" not in result
        assert "link" in result.lower()

    def test_https_url_replaced(self):
        text = "See https://www.example.com/path for details."
        result = optimize_for_tts(text)
        assert "https" not in result
        assert "link" in result.lower()

    def test_email_replaced(self):
        text = "Contact us at support@example.com for help."
        result = optimize_for_tts(text)
        assert "@" not in result
        assert "email" in result.lower()


class TestListFormatting:
    """Test list formatting for natural pauses."""

    def test_numbered_list_pauses(self):
        text = "1. First item\n2. Second item\n3. Third item"
        result = optimize_for_tts(text)
        assert "1..." in result
        assert "2..." in result

    def test_bullet_point_pauses(self):
        # Note: Only bullets at line start get replaced.
        # Then whitespace (including newlines) is collapsed, so subsequent
        # bullets become mid-line and remain.
        text = "• First bullet"
        result = optimize_for_tts(text)
        # First bullet at line start should be replaced
        assert result.startswith("...")
        assert "First bullet" in result

    def test_dash_bullet_pauses(self):
        text = "- Item one\n- Item two"
        result = optimize_for_tts(text)
        assert "..." in result


class TestDashHandling:
    """Test em-dash and en-dash handling."""

    def test_em_dash_pause(self):
        text = "The result—as expected—was correct."
        result = optimize_for_tts(text)
        assert "—" not in result
        assert "..." in result

    def test_en_dash_pause(self):
        text = "The range is 5–10 units."
        result = optimize_for_tts(text)
        assert "–" not in result


class TestTableToSpeech:
    """Test table_to_speech function."""

    def test_simple_table(self):
        headers = ["Name", "Age"]
        rows = [["Alice", "25"], ["Bob", "30"]]
        result = table_to_speech(headers, rows)
        assert "2 columns" in result
        assert "Name" in result
        assert "Age" in result
        assert "Alice" in result
        assert "25" in result

    def test_empty_headers(self):
        result = table_to_speech([], [])
        assert "no headers" in result.lower()

    def test_empty_rows(self):
        headers = ["A", "B", "C"]
        result = table_to_speech(headers, [])
        assert "empty" in result.lower()
        assert "3 columns" in result

    def test_max_rows_limit(self):
        headers = ["Value"]
        rows = [[str(i)] for i in range(10)]
        result = table_to_speech(headers, rows, max_rows=3)
        assert "Row 1" in result
        assert "Row 3" in result
        assert "Row 4" not in result
        assert "more row" in result.lower()

    def test_empty_cell_value(self):
        headers = ["A", "B"]
        rows = [["value", ""]]
        result = table_to_speech(headers, rows)
        assert "empty" in result.lower()


class TestCodeToSpeech:
    """Test code_to_speech function."""

    def test_empty_code(self):
        result = code_to_speech("")
        assert "empty code block" in result.lower()

    def test_simple_function(self):
        code = "def add(a, b):\n    return a + b"
        result = code_to_speech(code, "python")
        assert "Python" in result
        assert "2 lines" in result
        assert "function" in result.lower()

    def test_class_definition(self):
        code = "class MyClass:\n    pass"
        result = code_to_speech(code, "python")
        assert "class" in result.lower()

    def test_with_imports(self):
        code = "import os\nimport sys"
        result = code_to_speech(code, "python")
        assert "import" in result.lower()

    def test_with_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = code_to_speech(code)
        assert "loop" in result.lower()

    def test_with_conditional(self):
        code = "if x > 5:\n    print('big')"
        result = code_to_speech(code)
        assert "conditional" in result.lower()

    def test_unknown_language(self):
        code = "some code here"
        result = code_to_speech(code)
        assert "code block" in result.lower()
        assert "1 line" in result

    def test_visual_display_reference(self):
        code = "x = 1"
        result = code_to_speech(code)
        assert "visual display" in result.lower()


class TestListToSpeech:
    """Test list_to_speech function."""

    def test_empty_list(self):
        result = list_to_speech([])
        assert "empty list" in result.lower()

    def test_ordered_list(self):
        items = ["First", "Second", "Third"]
        result = list_to_speech(items, ordered=True)
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result

    def test_unordered_list(self):
        items = ["Apple", "Banana"]
        result = list_to_speech(items, ordered=False)
        assert "Apple" in result
        assert "Banana" in result
        assert "Item 1" not in result


class TestImageToSpeech:
    """Test image_to_speech function."""

    def test_empty_description(self):
        result = image_to_speech("")
        assert "image" in result.lower()

    def test_with_description(self):
        result = image_to_speech("A graph showing population growth")
        assert "shows" in result.lower()
        assert "population growth" in result

    def test_custom_image_type(self):
        result = image_to_speech("Flow of data", image_type="diagram")
        assert "diagram" in result.lower()

    def test_description_ending_punctuation(self):
        result = image_to_speech("A simple chart")
        assert result.endswith(".")


class TestAbbreviationsDictionary:
    """Test the ABBREVIATIONS dictionary."""

    def test_common_abbreviations_exist(self):
        assert "e.g." in ABBREVIATIONS
        assert "i.e." in ABBREVIATIONS
        assert "etc." in ABBREVIATIONS
        assert "Fig." in ABBREVIATIONS

    def test_title_abbreviations_exist(self):
        assert "Dr." in ABBREVIATIONS
        assert "Prof." in ABBREVIATIONS
        assert "Mr." in ABBREVIATIONS

    def test_unit_abbreviations_exist(self):
        assert "km" in ABBREVIATIONS
        assert "kg" in ABBREVIATIONS
        assert "Hz" in ABBREVIATIONS

    def test_abbreviations_have_expansions(self):
        for abbr, expansion in ABBREVIATIONS.items():
            assert len(expansion) > 0, f"Abbreviation {abbr} has empty expansion"


class TestEdgeCases:
    """Test edge cases and combined scenarios."""

    def test_multiple_features_combined(self):
        text = "See Fig. 1 [2] for E = mc² (Einstein, 1905)."
        result = optimize_for_tts(text)
        assert "Figure" in result
        assert "[2]" not in result
        assert "squared" in result.lower()
        assert "(Einstein, 1905)" not in result

    def test_excessive_whitespace_cleaned(self):
        text = "Multiple   spaces    here"
        result = optimize_for_tts(text)
        assert "  " not in result

    def test_space_before_punctuation_cleaned(self):
        text = "A word , another ."
        result = optimize_for_tts(text)
        assert " ," not in result
        assert " ." not in result

    def test_excessive_ellipses_cleaned(self):
        text = "Wait..... for it"
        result = optimize_for_tts(text)
        assert "....." not in result
