"""
VOXAM Core Utilities Library

This package provides utilities for:
- math_to_speech: Convert mathematical notation to speakable text
- content_detector: Detect content types (definition, example, code, etc.)
- voice_optimizer: Optimize text for TTS output
- supabase_client: Supabase database client
- tts_queue: TTS audio queue management
"""

from lib.math_to_speech import equation_to_speech, SYMBOL_MAP, PATTERNS
from lib.content_detector import (
    ContentType,
    detect_content_type,
    extract_definitions,
    extract_procedure_steps,
)
from lib.voice_optimizer import (
    optimize_for_tts,
    table_to_speech,
    code_to_speech,
)

__all__ = [
    # math_to_speech
    "equation_to_speech",
    "SYMBOL_MAP",
    "PATTERNS",
    # content_detector
    "ContentType",
    "detect_content_type",
    "extract_definitions",
    "extract_procedure_steps",
    # voice_optimizer
    "optimize_for_tts",
    "table_to_speech",
    "code_to_speech",
]
