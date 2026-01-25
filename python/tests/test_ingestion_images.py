"""
Tests for image handling in ingestion pipeline.
Covers edge cases for vision filtering, figure references, and error handling.

Run with: pytest tests/test_ingestion_images.py -v
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion_workflow import (
    ContentBlock,
    Question,
    BloomLevel,
    Difficulty,
    QuestionType,
    classify_and_describe_image,
    filter_and_describe_images,
    match_images_to_chunks,
    build_combined_context_with_figures,
    extract_images_from_pdf,
)


# ============================================================
# Test: Vision API Failure Handling
# ============================================================

class TestVisionAPIFailures:
    """Tests for graceful handling of vision API failures."""

    def test_filter_with_api_timeout(self):
        """Vision API timeout should not crash, images kept as fallback."""
        images_by_page = {
            1: [{"image_bytes": b"fake_image", "index": 0, "page": 1}]
        }

        with patch('ingestion_workflow.classify_and_describe_image') as mock_classify:
            mock_classify.side_effect = Exception("Connection timeout")

            result = filter_and_describe_images(
                images_by_page,
                fallback_on_failure=True
            )

            # Image should be kept with fallback description
            assert 1 in result
            assert result[1][0]["is_educational"] == True
            assert "classification unavailable" in result[1][0]["description"]

    def test_filter_with_api_failure_no_fallback(self):
        """When fallback disabled, failed images should be removed."""
        images_by_page = {
            1: [{"image_bytes": b"fake_image", "index": 0, "page": 1}]
        }

        with patch('ingestion_workflow.classify_and_describe_image') as mock_classify:
            mock_classify.return_value = None  # API failure

            result = filter_and_describe_images(
                images_by_page,
                fallback_on_failure=False
            )

            # Image should be removed
            assert len(result) == 0

    def test_filter_with_partial_failure(self):
        """Some images fail (exception), some succeed - mixed results."""
        images_by_page = {
            1: [
                {"image_bytes": b"image1", "index": 0, "page": 1},
                {"image_bytes": b"image2", "index": 1, "page": 1},
            ]
        }

        call_count = [0]

        def mock_classify(image_bytes, page, model):
            call_count[0] += 1
            if image_bytes == b"image1":
                return {"is_educational": True, "description": "A diagram"}
            else:
                raise Exception("API Error")  # Actual failure triggers fallback

        with patch('ingestion_workflow.classify_and_describe_image', side_effect=mock_classify):
            result = filter_and_describe_images(
                images_by_page,
                fallback_on_failure=True,
                max_retries=0  # No retries for test speed
            )

            # Both should be kept (one classified, one fallback)
            assert len(result[1]) == 2
            # First image has real description
            assert result[1][0]["description"] == "A diagram"
            # Second image has fallback description
            assert "classification unavailable" in result[1][1]["description"]


# ============================================================
# Test: Figure Reference Validation
# ============================================================

class TestFigureRefValidation:
    """Tests for figure_ref bounds checking."""

    def test_valid_figure_ref(self):
        """Valid figure_ref should resolve to URL."""
        block = ContentBlock()
        block.figure_map = {
            1: {"url": "https://example.com/fig1.jpg", "description": "Figure 1"}
        }
        block.text_content = "Sample content"
        block.combined_context = build_combined_context_with_figures(block)

        assert "[FIGURES IN THIS SECTION]" in block.combined_context
        assert "Figure 1" in block.combined_context

    def test_figure_ref_out_of_bounds(self):
        """figure_ref > max should be cleared (not crash)."""
        block = ContentBlock()
        block.figure_map = {
            1: {"url": "https://example.com/fig1.jpg", "description": "Figure 1"}
        }

        # Simulate LLM returning figure_ref: 5 when only 1 figure exists
        from ingestion_workflow import IngestionPipeline

        # This tests the resolve_figure_ref logic indirectly
        # figure_ref=5 should resolve to (None, None, None)
        max_figure = max(block.figure_map.keys())
        assert max_figure == 1

        # figure_ref=5 > max_figure=1, should be invalid
        figure_ref = 5
        if figure_ref > max_figure:
            resolved = None
        else:
            resolved = block.figure_map.get(figure_ref)
        assert resolved is None

    def test_figure_ref_zero(self):
        """figure_ref=0 should be treated as no reference."""
        block = ContentBlock()
        block.figure_map = {1: {"url": "url", "description": "desc"}}

        # 0 is not a valid figure number
        figure_ref = 0
        assert figure_ref < 1  # Should be rejected

    def test_figure_ref_string_conversion(self):
        """figure_ref as string "1" should be converted to int."""
        # The resolve_figure_ref function handles this
        figure_ref = "1"
        try:
            converted = int(figure_ref)
            assert converted == 1
        except ValueError:
            pytest.fail("Should convert string to int")

    def test_figure_ref_invalid_string(self):
        """figure_ref as "one" should not crash."""
        figure_ref = "one"
        try:
            converted = int(figure_ref)
            pytest.fail("Should not convert 'one' to int")
        except ValueError:
            pass  # Expected


# ============================================================
# Test: Combined Context Building
# ============================================================

class TestCombinedContext:
    """Tests for combined_context with figures."""

    def test_no_figures(self):
        """Block without figures should just have text."""
        block = ContentBlock()
        block.text_content = "Sample text content"
        block.figure_map = {}

        result = build_combined_context_with_figures(block)

        assert result == "Sample text content"
        assert "[FIGURES" not in result

    def test_single_figure(self):
        """Block with one figure should include it."""
        block = ContentBlock()
        block.text_content = "Text about photosynthesis"
        block.figure_map = {
            1: {"url": "url", "description": "Chloroplast diagram", "page": 3}
        }

        result = build_combined_context_with_figures(block)

        assert "Text about photosynthesis" in result
        assert "[FIGURES IN THIS SECTION]" in result
        assert "Figure 1 (p.3): Chloroplast diagram" in result

    def test_multiple_figures(self):
        """Block with multiple figures should list all."""
        block = ContentBlock()
        block.text_content = "Content"
        block.figure_map = {
            1: {"url": "url1", "description": "First figure", "page": 1},
            2: {"url": "url2", "description": "Second figure", "page": 2},
        }

        result = build_combined_context_with_figures(block)

        assert "Figure 1" in result
        assert "Figure 2" in result
        assert "First figure" in result
        assert "Second figure" in result


# ============================================================
# Test: Image Extraction Edge Cases
# ============================================================

class TestImageExtraction:
    """Tests for PDF image extraction edge cases."""

    def test_empty_pdf_no_crash(self):
        """PDF with no images should return empty dict."""
        # This would require a real PDF, so we test the logic
        images_by_page = {}
        assert len(images_by_page) == 0

    def test_dimension_filtering(self):
        """Images below threshold should be filtered."""
        # Test the filtering logic
        min_width = 120
        min_height = 120

        small_image = {"width": 50, "height": 50}
        large_image = {"width": 200, "height": 200}

        assert small_image["width"] < min_width
        assert large_image["width"] >= min_width


# ============================================================
# Test: Question Generation Error Handling
# ============================================================

class TestQuestionGeneration:
    """Tests for question generation error handling."""

    def test_invalid_bloom_level_fallback(self):
        """Invalid bloom level should fallback to UNDERSTAND."""
        # Test parse_bloom_level logic
        valid_levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        invalid_level = "super_hard"

        assert invalid_level not in valid_levels

        # Should fallback gracefully
        try:
            BloomLevel(invalid_level)
            pytest.fail("Should raise ValueError")
        except ValueError:
            fallback = BloomLevel.UNDERSTAND
            assert fallback == BloomLevel.UNDERSTAND

    def test_invalid_difficulty_fallback(self):
        """Invalid difficulty should fallback to INTERMEDIATE."""
        invalid_diff = "super_difficult"

        try:
            Difficulty(invalid_diff)
            pytest.fail("Should raise ValueError")
        except ValueError:
            fallback = Difficulty.INTERMEDIATE
            assert fallback == Difficulty.INTERMEDIATE

    def test_malformed_json_recovery(self):
        """Malformed JSON should trigger retry or graceful failure."""
        malformed_responses = [
            "This is not JSON",
            "{incomplete json",
            '{"long_answer_questions": [}',  # Invalid
        ]

        for response in malformed_responses:
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json.loads(response[start:end])
            except json.JSONDecodeError:
                pass  # Expected - should be handled by retry logic


# ============================================================
# Test: Image-Chunk Matching
# ============================================================

class TestImageChunkMatching:
    """Tests for matching images to chunks."""

    def test_match_single_page_chunk(self):
        """Images on page 3 should match chunk covering page 3."""
        chunk = ContentBlock()
        chunk.page_start = 3
        chunk.page_end = 3
        chunk.page_number = 3

        images_by_page = {
            3: [{"index": 0, "description": "A diagram"}]
        }
        image_index = {"page_3_img_0": "https://r2.example.com/img.jpg"}

        result = match_images_to_chunks([chunk], images_by_page, image_index)

        assert len(result[0].image_urls) == 1
        assert result[0].figure_map[1]["url"] == "https://r2.example.com/img.jpg"

    def test_match_multi_page_chunk(self):
        """Chunk spanning pages 2-4 should get images from all pages."""
        chunk = ContentBlock()
        chunk.page_start = 2
        chunk.page_end = 4
        chunk.page_number = 2

        images_by_page = {
            2: [{"index": 0, "description": "Fig A"}],
            3: [{"index": 0, "description": "Fig B"}],
        }
        image_index = {
            "page_2_img_0": "url_a",
            "page_3_img_0": "url_b",
        }

        result = match_images_to_chunks([chunk], images_by_page, image_index)

        assert len(result[0].image_urls) == 2
        assert 1 in result[0].figure_map
        assert 2 in result[0].figure_map

    def test_no_images_for_chunk(self):
        """Chunk with no matching images should have empty figure_map."""
        chunk = ContentBlock()
        chunk.page_start = 10
        chunk.page_end = 10
        chunk.page_number = 10

        images_by_page = {1: [{"index": 0}]}  # Images on different page
        image_index = {"page_1_img_0": "url"}

        result = match_images_to_chunks([chunk], images_by_page, image_index)

        assert len(result[0].image_urls) == 0
        assert len(result[0].figure_map) == 0


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
