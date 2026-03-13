"""PDF parsing and text chunking."""
from __future__ import annotations

from dataclasses import dataclass

import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter


CHUNK_SIZE = 512        # tokens (approximate — splitter uses chars internally)
CHUNK_OVERLAP = 50
# ~4 chars per token on average for English text
_CHARS_PER_TOKEN = 4
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE * _CHARS_PER_TOKEN,
    chunk_overlap=CHUNK_OVERLAP * _CHARS_PER_TOKEN,
    separators=["\n\n", "\n", ". ", " ", ""],
)


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int


def pdf_to_chunks(pdf_bytes: bytes) -> list[Chunk]:
    """Parse a PDF and split into overlapping text chunks."""
    import pymupdf

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    markdown = pymupdf4llm.to_markdown(doc)
    doc.close()

    raw_chunks = _SPLITTER.split_text(markdown)

    return [
        Chunk(
            index=i,
            content=text,
            token_count=len(text) // _CHARS_PER_TOKEN,
        )
        for i, text in enumerate(raw_chunks)
        if text.strip()
    ]
