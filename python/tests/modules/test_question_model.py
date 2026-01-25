"""Tests for Question model in ingestion_workflow.py."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pydantic import ValidationError
from ingestion_workflow import Question, BloomLevel, Difficulty, QuestionType


class TestBloomLevelEnum:
    """Test BloomLevel enum values."""

    def test_all_levels_exist(self):
        expected = ["REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"]
        for level in expected:
            assert hasattr(BloomLevel, level)

    def test_level_values(self):
        assert BloomLevel.REMEMBER.value == "remember"
        assert BloomLevel.UNDERSTAND.value == "understand"
        assert BloomLevel.APPLY.value == "apply"
        assert BloomLevel.ANALYZE.value == "analyze"
        assert BloomLevel.EVALUATE.value == "evaluate"
        assert BloomLevel.CREATE.value == "create"

    def test_create_level_exists(self):
        # CREATE was added in the overhaul
        assert BloomLevel.CREATE.value == "create"

    def test_is_string_enum(self):
        assert isinstance(BloomLevel.REMEMBER.value, str)


class TestDifficultyEnum:
    """Test Difficulty enum values."""

    def test_all_levels_exist(self):
        expected = ["BASIC", "INTERMEDIATE", "ADVANCED"]
        for level in expected:
            assert hasattr(Difficulty, level)

    def test_difficulty_values(self):
        assert Difficulty.BASIC.value == "basic"
        assert Difficulty.INTERMEDIATE.value == "intermediate"
        assert Difficulty.ADVANCED.value == "advanced"


class TestQuestionTypeEnum:
    """Test QuestionType enum values."""

    def test_types_exist(self):
        assert hasattr(QuestionType, "LONG_ANSWER")
        assert hasattr(QuestionType, "MULTIPLE_CHOICE")

    def test_type_values(self):
        assert QuestionType.LONG_ANSWER.value == "long_answer"
        assert QuestionType.MULTIPLE_CHOICE.value == "multiple_choice"


class TestQuestionCreation:
    """Test Question model creation."""

    def test_create_minimal_question(self):
        q = Question(
            text="What is entropy?",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Measure of disorder", "Thermodynamic concept"]
        )
        assert q.text == "What is entropy?"
        assert q.bloom_level == BloomLevel.UNDERSTAND

    def test_create_mcq(self):
        q = Question(
            text="Which is the largest planet?",
            bloom_level=BloomLevel.REMEMBER,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.MULTIPLE_CHOICE,
            expected_time=30,
            key_points=["Jupiter is largest"],
            options=["Mars", "Jupiter", "Saturn", "Earth"],
            correct_answer="B"
        )
        assert q.question_type == QuestionType.MULTIPLE_CHOICE
        assert len(q.options) == 4
        assert q.correct_answer == "B"


class TestQuestionRequiredFields:
    """Test required fields validation."""

    def test_text_required(self):
        with pytest.raises(ValidationError):
            Question(
                bloom_level=BloomLevel.UNDERSTAND,
                difficulty=Difficulty.BASIC,
                question_type=QuestionType.LONG_ANSWER,
                expected_time=60,
                key_points=["Point 1"]
            )

    def test_bloom_level_required(self):
        with pytest.raises(ValidationError):
            Question(
                text="What is X?",
                difficulty=Difficulty.BASIC,
                question_type=QuestionType.LONG_ANSWER,
                expected_time=60,
                key_points=["Point 1"]
            )

    def test_key_points_required(self):
        with pytest.raises(ValidationError):
            Question(
                text="What is X?",
                bloom_level=BloomLevel.UNDERSTAND,
                difficulty=Difficulty.BASIC,
                question_type=QuestionType.LONG_ANSWER,
                expected_time=60
            )


class TestQuestionOptionalFields:
    """Test optional fields."""

    def test_options_optional(self):
        q = Question(
            text="Explain entropy.",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Key point"]
        )
        assert q.options is None

    def test_correct_answer_optional(self):
        q = Question(
            text="Explain entropy.",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Key point"]
        )
        assert q.correct_answer is None

    def test_spoken_text_optional(self):
        q = Question(
            text="What is E = mc²?",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Einstein's equation"]
        )
        assert q.spoken_text is None

    def test_spoken_options_optional(self):
        q = Question(
            text="Choose the answer.",
            bloom_level=BloomLevel.REMEMBER,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.MULTIPLE_CHOICE,
            expected_time=30,
            key_points=["Key point"],
            options=["A", "B", "C", "D"],
            correct_answer="A"
        )
        assert q.spoken_options is None


class TestQuestionTTSFields:
    """Test TTS-related fields."""

    def test_spoken_text_can_be_set(self):
        q = Question(
            text="What is E = mc²?",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Energy mass equivalence"],
            spoken_text="What is E equals m c squared?"
        )
        assert q.spoken_text == "What is E equals m c squared?"

    def test_spoken_options_can_be_set(self):
        q = Question(
            text="Which equation is correct?",
            bloom_level=BloomLevel.REMEMBER,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.MULTIPLE_CHOICE,
            expected_time=30,
            key_points=["E = mc²"],
            options=["E = mc²", "E = mc³", "E = m²c", "E = mc"],
            correct_answer="A",
            spoken_options=[
                "E equals m c squared",
                "E equals m c cubed",
                "E equals m squared c",
                "E equals m c"
            ]
        )
        assert len(q.spoken_options) == 4
        assert "squared" in q.spoken_options[0]


class TestQuestionImageFields:
    """Test image-related fields."""

    def test_figure_ref_optional(self):
        q = Question(
            text="Describe the diagram.",
            bloom_level=BloomLevel.ANALYZE,
            difficulty=Difficulty.INTERMEDIATE,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=120,
            key_points=["Key observation"]
        )
        assert q.figure_ref is None

    def test_figure_ref_can_be_set(self):
        q = Question(
            text="Refer to Figure 1.",
            bloom_level=BloomLevel.ANALYZE,
            difficulty=Difficulty.INTERMEDIATE,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=120,
            key_points=["Key observation"],
            figure_ref=1
        )
        assert q.figure_ref == 1

    def test_image_url_optional(self):
        q = Question(
            text="What does the graph show?",
            bloom_level=BloomLevel.ANALYZE,
            difficulty=Difficulty.INTERMEDIATE,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=120,
            key_points=["Trend analysis"]
        )
        assert q.image_url is None

    def test_image_description_optional(self):
        q = Question(
            text="Analyze the circuit.",
            bloom_level=BloomLevel.ANALYZE,
            difficulty=Difficulty.ADVANCED,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=180,
            key_points=["Circuit behavior"]
        )
        assert q.image_description is None


class TestQuestionSerialization:
    """Test Question serialization."""

    def test_to_dict(self):
        q = Question(
            text="Explain X.",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Point A", "Point B"]
        )
        d = q.model_dump()
        assert d["text"] == "Explain X."
        assert d["bloom_level"] == "understand"
        assert d["difficulty"] == "basic"
        assert d["key_points"] == ["Point A", "Point B"]

    def test_to_json(self):
        q = Question(
            text="What is Y?",
            bloom_level=BloomLevel.REMEMBER,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=30,
            key_points=["Definition of Y"]
        )
        json_str = q.model_dump_json()
        assert "What is Y?" in json_str
        assert "remember" in json_str

    def test_from_dict(self):
        data = {
            "text": "Test question",
            "bloom_level": "apply",
            "difficulty": "intermediate",
            "question_type": "long_answer",
            "expected_time": 90,
            "key_points": ["Point 1"]
        }
        q = Question.model_validate(data)
        assert q.text == "Test question"
        assert q.bloom_level == BloomLevel.APPLY


class TestQuestionKeyPoints:
    """Test key_points field specifically."""

    def test_key_points_is_list(self):
        q = Question(
            text="Explain Z.",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Point 1", "Point 2", "Point 3"]
        )
        assert isinstance(q.key_points, list)
        assert len(q.key_points) == 3

    def test_key_points_content(self):
        key_points = [
            "First key concept",
            "Second important idea",
            "Third main point"
        ]
        q = Question(
            text="Summarize the topic.",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.INTERMEDIATE,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=90,
            key_points=key_points
        )
        assert q.key_points[0] == "First key concept"
        assert q.key_points[2] == "Third main point"


class TestQuestionNoExplanationField:
    """Test that explanation field is not present (removed in overhaul)."""

    def test_no_explanation_field(self):
        q = Question(
            text="Test question.",
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=Difficulty.BASIC,
            question_type=QuestionType.LONG_ANSWER,
            expected_time=60,
            key_points=["Key point"]
        )
        # explanation should not be a field (generated at runtime by correction_agent)
        assert not hasattr(q, "explanation") or q.model_fields.get("explanation") is None
