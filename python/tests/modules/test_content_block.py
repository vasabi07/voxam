"""Tests for ContentBlock model in ingestion_workflow.py."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ingestion_workflow import ContentBlock


class TestContentBlockBasicFields:
    """Test that basic fields exist and have correct defaults."""

    def test_can_instantiate(self):
        block = ContentBlock()
        assert block is not None

    def test_chunk_index_default(self):
        block = ContentBlock()
        assert block.chunk_index == 0

    def test_text_content_default(self):
        block = ContentBlock()
        assert block.text_content == ""

    def test_combined_context_default(self):
        block = ContentBlock()
        assert block.combined_context == ""

    def test_page_number_default(self):
        block = ContentBlock()
        assert block.page_number == 1

    def test_embeddings_default(self):
        block = ContentBlock()
        assert block.embeddings == []


class TestContentBlockLegacyFields:
    """Test legacy fields are preserved."""

    def test_related_tables_default(self):
        block = ContentBlock()
        assert block.related_tables == []

    def test_image_captions_default(self):
        block = ContentBlock()
        assert block.image_captions == []

    def test_table_descriptions_default(self):
        block = ContentBlock()
        assert block.table_descriptions == []


class TestContentBlockHierarchyFields:
    """Test hierarchy fields."""

    def test_chapter_title_default(self):
        block = ContentBlock()
        assert block.chapter_title is None

    def test_section_title_default(self):
        block = ContentBlock()
        assert block.section_title is None

    def test_heading_level_default(self):
        block = ContentBlock()
        assert block.heading_level == 0

    def test_can_set_hierarchy(self):
        block = ContentBlock()
        block.chapter_title = "Chapter 1: Introduction"
        block.section_title = "1.1 Overview"
        block.heading_level = 2
        assert block.chapter_title == "Chapter 1: Introduction"
        assert block.section_title == "1.1 Overview"
        assert block.heading_level == 2


class TestContentBlockNewFields:
    """Test NEW fields added in the ingestion overhaul."""

    def test_content_type_default(self):
        block = ContentBlock()
        assert block.content_type == "narrative"

    def test_content_type_assignment(self):
        block = ContentBlock()
        valid_types = ["definition", "example", "theorem", "proof",
                       "procedure", "code", "equation", "narrative"]
        for content_type in valid_types:
            block.content_type = content_type
            assert block.content_type == content_type

    def test_definitions_default(self):
        block = ContentBlock()
        assert block.definitions == []
        assert isinstance(block.definitions, list)

    def test_definitions_structure(self):
        block = ContentBlock()
        block.definitions = [
            {"term": "Entropy", "definition": "A measure of disorder"},
            {"term": "Catalyst", "definition": "A substance that speeds reactions"}
        ]
        assert len(block.definitions) == 2
        assert block.definitions[0]["term"] == "Entropy"
        assert "disorder" in block.definitions[0]["definition"]

    def test_procedure_steps_default(self):
        block = ContentBlock()
        assert block.procedure_steps == []

    def test_procedure_steps_structure(self):
        block = ContentBlock()
        block.procedure_steps = [
            "Step 1: Gather materials",
            "Step 2: Mix solution",
            "Step 3: Heat mixture"
        ]
        assert len(block.procedure_steps) == 3
        assert "Gather" in block.procedure_steps[0]

    def test_equations_default(self):
        block = ContentBlock()
        assert block.equations == []

    def test_equations_structure(self):
        block = ContentBlock()
        block.equations = [
            {"latex": "E = mc^2", "spoken": "E equals m c squared", "context": "Einstein's equation"}
        ]
        assert len(block.equations) == 1
        assert block.equations[0]["latex"] == "E = mc^2"
        assert "squared" in block.equations[0]["spoken"]

    def test_code_blocks_default(self):
        block = ContentBlock()
        assert block.code_blocks == []

    def test_code_blocks_structure(self):
        block = ContentBlock()
        block.code_blocks = [
            {"language": "python", "code": "def add(a, b):\n    return a + b",
             "description": "Function that adds two numbers"}
        ]
        assert len(block.code_blocks) == 1
        assert block.code_blocks[0]["language"] == "python"
        assert "def add" in block.code_blocks[0]["code"]

    def test_tables_default(self):
        block = ContentBlock()
        assert block.tables == []

    def test_tables_structure(self):
        block = ContentBlock()
        block.tables = [
            {
                "headers": ["Name", "Age", "City"],
                "rows": [["Alice", "25", "NYC"], ["Bob", "30", "LA"]],
                "description": "User information table",
                "spoken": "A table with user names, ages, and cities."
            }
        ]
        assert len(block.tables) == 1
        assert len(block.tables[0]["headers"]) == 3
        assert len(block.tables[0]["rows"]) == 2
        assert "spoken" in block.tables[0]

    def test_image_types_default(self):
        block = ContentBlock()
        assert block.image_types == []

    def test_image_types_structure(self):
        block = ContentBlock()
        block.image_types = ["diagram", "graph", "flowchart"]
        assert len(block.image_types) == 3
        assert "diagram" in block.image_types


class TestContentBlockImageFields:
    """Test image-related fields."""

    def test_image_urls_default(self):
        block = ContentBlock()
        assert block.image_urls == []

    def test_image_descriptions_default(self):
        block = ContentBlock()
        assert block.image_descriptions == []

    def test_figure_map_default(self):
        block = ContentBlock()
        assert block.figure_map == {}

    def test_figure_map_structure(self):
        block = ContentBlock()
        block.figure_map = {
            1: {"url": "https://example.com/fig1.png",
                "description": "Circuit diagram",
                "page": 5}
        }
        assert 1 in block.figure_map
        assert block.figure_map[1]["url"] == "https://example.com/fig1.png"


class TestContentBlockPageTracking:
    """Test page tracking fields."""

    def test_page_start_default(self):
        block = ContentBlock()
        assert block.page_start == 1

    def test_page_end_default(self):
        block = ContentBlock()
        assert block.page_end == 1

    def test_bbox_default(self):
        block = ContentBlock()
        assert block.bbox is None

    def test_bbox_assignment(self):
        block = ContentBlock()
        block.bbox = [10.0, 20.0, 100.0, 200.0]
        assert block.bbox == [10.0, 20.0, 100.0, 200.0]


class TestContentBlockQuestions:
    """Test question-related fields."""

    def test_questions_default(self):
        block = ContentBlock()
        assert block.questions == []

    def test_meta_default(self):
        block = ContentBlock()
        assert block.meta == {}
