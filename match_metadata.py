import PyPDF2
import fitz  # PyMuPDF
import unicodedata
import difflib
import sys

def normalize_text(text: str) -> str:
    """
    Normalize Unicode text to ASCII lowercase for comparison.
    """
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()


def get_title_from_text(pdf_path: str) -> str | None:
    """
    Extracts the title from the PDF's text using heuristics.
    This is a fallback for when the '/Title' metadata field is not available.

    The algorithm assumes the title is:
    1. On the first page.
    2. Has the largest font size.
    3. Is located near the top of the page.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        The extracted title string if successful, otherwise None.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path} with PyMuPDF: {e}", file=sys.stderr)
        return None

    if len(doc) == 0:
        print(f"PDF file {pdf_path} has no pages.", file=sys.stderr)
        return None

    first_page = doc[0]
    page_height = first_page.rect.height

    # Extract all text blocks with detailed information
    # MODIFIED LINE: Removed the 'flags' parameter for compatibility.
    blocks = first_page.get_text("dict")["blocks"]

    if not blocks:
        print(f"No text found on the first page of {pdf_path}.", file=sys.stderr)
        return None

    # --- 1. Heuristic: Find the largest font size ---
    max_font_size = 0
    # First pass to find the maximum font size on the page
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                if "spans" in line:
                    for span in line["spans"]:
                        if span["size"] > max_font_size:
                            max_font_size = span["size"]

    if max_font_size == 0:
        print("Could not determine font sizes on the first page.", file=sys.stderr)
        return None

    # --- 2. Filter candidates based on font size and position ---
    title_candidates = []
    # A small tolerance for font size variations
    font_size_tolerance = max_font_size * 0.05
    # Consider text in the top 40% of the page as potential titles
    upper_page_boundary = page_height * 0.40

    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                # Check vertical position of the line
                line_y_position = line["bbox"][1]
                if line_y_position > upper_page_boundary:
                    continue

                if "spans" in line:
                    for span in line["spans"]:
                        # Check if font size is close to the maximum
                        if abs(span["size"] - max_font_size) <= font_size_tolerance:
                            # Join all text in the line, as it's a title candidate
                            full_line_text = "".join(s["text"] for s in line["spans"]).strip()
                            title_candidates.append({
                                "text": full_line_text,
                                "y": line["bbox"][1]  # Use y-coordinate for sorting
                            })
                            break  # Move to the next line once a candidate is found

    if not title_candidates:
        print("No title candidates found based on font size and position.", file=sys.stderr)
        return None

    # --- 3. Group and assemble multi-line titles ---
    # Sort candidates vertically
    title_candidates.sort(key=lambda item: item['y'])

    # Remove duplicate lines that might have been added
    unique_titles = []
    seen_text = set()
    for item in title_candidates:
        if item['text'] not in seen_text:
            unique_titles.append(item['text'])
            seen_text.add(item['text'])

    # Join the text of the sorted candidates
    full_title = " ".join(unique_titles)

    # Simple clean up
    full_title = " ".join(full_title.split())

    return full_title if full_title else None


def _find_best_match(title_to_match: str, metadata_set: list[dict], similarity_threshold: float) -> dict | None:
    """
    Finds the best metadata match for a given title string based on a similarity threshold.

    :param title_to_match: The string to compare against the metadata titles.
    :param metadata_set: List of metadata dictionaries.
    :param similarity_threshold: The minimum similarity ratio for a match.
    :return: The best matching metadata dictionary or None.
    """
    if not title_to_match:
        return None

    norm_title_to_match = normalize_text(title_to_match)
    candidates = []
    for meta in metadata_set:
        norm_meta_title = normalize_text(meta.get('title', ''))
        similarity = difflib.SequenceMatcher(None, norm_title_to_match, norm_meta_title).ratio()
        if similarity >= similarity_threshold:
            candidates.append((similarity, meta))

    if candidates:
        return max(candidates, key=lambda x: x[0])[1]
    
    return None


def match_pdf_to_metadata(pdf_path: str, metadata_set: list[dict]) -> dict | None:
    """
    Matches a PDF file to a metadata entry based on extracted title (using fuzzy matching).
    First, it tries the title from PDF metadata/text. If that fails, it tries the filename.

    :param pdf_path: Path to the PDF file.
    :param metadata_set: List of metadata dictionaries, each with 'title': str.
    :return: Matching metadata dict or None if no match.
    """
    try:
        # --- 1. Attempt to match using title from PDF metadata or text content ---
        extracted_title = ''
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                extracted_title = reader.metadata.get('/Title', '')
        except Exception:
            pass  # PyPDF2 might fail on some PDFs, that's ok.

        if not extracted_title:
            extracted_title = get_title_from_text(pdf_path)

        if extracted_title:
            match = _find_best_match(extracted_title, metadata_set, 0.9)
            if match:
                return match

        # --- 2. Fallback: attempt to match using the PDF filename ---
        import os
        basename = os.path.basename(pdf_path)
        filename_title = os.path.splitext(basename)[0]
        # Replace common separators with spaces for better matching
        filename_title = filename_title.replace('_', ' ').replace('-', ' ')
        
        match = _find_best_match(filename_title, metadata_set, 0.6)
        if match:
            return match

        return None

    except Exception:
        return None