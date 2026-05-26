def split_text_into_chunks(
    text: str,
    chunk_size: int = 700,
    overlap: int = 100,
) -> list[str]:
    """
    Split long text into overlapping word-based chunks.

    Default:
    - chunk_size = 700 words
    - overlap = 100 words

    This is simple and reliable for the first RAG version.
    Later, we can replace this with token-based chunking.
    """
    cleaned_text = text.strip()

    if not cleaned_text:
        return []

    words = cleaned_text.split()

    if len(words) <= chunk_size:
        return [cleaned_text]

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        chunks.append(chunk_text)

        if end >= len(words):
            break

        start = end - overlap

    return chunks
