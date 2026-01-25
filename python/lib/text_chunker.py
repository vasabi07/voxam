"""
Simple text chunking without external dependencies.

Splits text into chunks based on:
1. Paragraph boundaries (double newlines)
2. Character limits with overlap
3. Sentence boundaries when possible
"""

import re
from typing import List, Dict, Optional


def chunk_text(
    text: str,
    max_chars: int = 4000,
    min_chars: int = 500,
    overlap: int = 200
) -> List[Dict]:
    """
    Split text into chunks with smart boundaries.

    Args:
        text: Full text to chunk
        max_chars: Maximum characters per chunk
        min_chars: Minimum characters (combine small paragraphs)
        overlap: Character overlap between chunks

    Returns:
        List of chunk dicts: [{"text": ..., "index": ...}, ...]
    """
    # Split into paragraphs (double newline or multiple newlines)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        # If single paragraph exceeds max, split it
        if para_len > max_chars:
            # Flush current chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0

            # Split large paragraph by sentences
            sub_chunks = _split_large_paragraph(para, max_chars, overlap)
            chunks.extend(sub_chunks)
            continue

        # If adding this paragraph exceeds max, flush and start new
        if current_len + para_len + 2 > max_chars:  # +2 for \n\n
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))

                # Keep overlap from end of previous chunk
                if overlap > 0 and current_chunk:
                    overlap_text = "\n\n".join(current_chunk)[-overlap:]
                    # Find a clean break point
                    break_point = overlap_text.find('. ')
                    if break_point > 0:
                        overlap_text = overlap_text[break_point + 2:]
                    current_chunk = [overlap_text] if overlap_text.strip() else []
                    current_len = len(overlap_text)
                else:
                    current_chunk = []
                    current_len = 0

        current_chunk.append(para)
        current_len += para_len + 2

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Combine tiny chunks with next chunk
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if len(chunk) < min_chars and final_chunks:
            # Append to previous chunk if it won't exceed max
            if len(final_chunks[-1]) + len(chunk) + 2 <= max_chars * 1.2:
                final_chunks[-1] = final_chunks[-1] + "\n\n" + chunk
                continue
        final_chunks.append(chunk)

    # Return as list of dicts with index
    return [{"text": chunk, "index": i} for i, chunk in enumerate(final_chunks)]


def _split_large_paragraph(text: str, max_chars: int, overlap: int) -> List[str]:
    """Split a large paragraph by sentences."""
    # Split by sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        sent_len = len(sentence)

        if current_len + sent_len + 1 > max_chars:
            if current:
                chunks.append(" ".join(current))
                # Overlap: keep last sentence or portion
                if overlap > 0:
                    overlap_text = " ".join(current)[-overlap:]
                    current = [overlap_text] if overlap_text else []
                    current_len = len(overlap_text)
                else:
                    current = []
                    current_len = 0

        current.append(sentence)
        current_len += sent_len + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_pages(
    pages: List[str],
    max_chars: int = 4000,
    min_chars: int = 500,
    overlap: int = 200
) -> List[Dict]:
    """
    Chunk a list of page texts, preserving page number info.

    Args:
        pages: List of page texts (1 string per page)
        max_chars: Maximum characters per chunk
        min_chars: Minimum characters per chunk
        overlap: Character overlap between chunks

    Returns:
        List of chunk dicts: [{"text": ..., "index": ..., "page_start": ..., "page_end": ...}, ...]
    """
    # Combine all pages with page markers
    combined = []
    for i, page_text in enumerate(pages):
        page_num = i + 1
        combined.append(f"[PAGE_{page_num}]\n{page_text}")

    full_text = "\n\n".join(combined)

    # Chunk the combined text
    raw_chunks = chunk_text(full_text, max_chars, min_chars, overlap)

    # Extract page numbers from each chunk
    result = []
    for chunk_dict in raw_chunks:
        text = chunk_dict["text"]

        # Find page markers in this chunk
        page_markers = re.findall(r'\[PAGE_(\d+)\]', text)
        page_nums = [int(p) for p in page_markers] if page_markers else [1]

        # Clean out the page markers from final text
        clean_text = re.sub(r'\[PAGE_\d+\]\n?', '', text).strip()

        result.append({
            "text": clean_text,
            "index": chunk_dict["index"],
            "page_start": min(page_nums),
            "page_end": max(page_nums)
        })

    return result
