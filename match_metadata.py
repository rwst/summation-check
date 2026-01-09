import PyPDF2
import unicodedata
import difflib
import logging
import os
import re

def normalize_text(text: str) -> str:
    """
    Normalize Unicode text to ASCII lowercase for comparison.
    """
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()


def get_title_from_text(pdf_path: str) -> str | None:
    """
    Extracts the title from the PDF's text and caches the result.
    This is a fallback for when the '/Title' metadata field is not available.
    (Currently disabled - returns None)
    """
    return None


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
    Matches a PDF file to a metadata entry.

    The matching logic is as follows:
    1. Read the '/Title' metadata from the PDF.
    2. If the title is 8 characters or longer, it is used exclusively for matching.
       If it matches, the metadata is returned. If not, the process stops, and None is returned.
    3. If the title is shorter than 8 characters or absent, the logic proceeds to:
       a. Attempt to match using the PDF's filename.
       b. If the filename doesn't match, attempt to match using cached text content.

    :param pdf_path: Path to the PDF file.
    :param metadata_set: List of metadata dictionaries, each with 'title': str.
    :return: Matching metadata dict or None if no match.
    """
    try:
        # --- 1. Attempt to match using /Title metadata field ---
        metadata_title = ''
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                raw_title = reader.metadata.get('/Title', '')
                if raw_title:
                    metadata_title = raw_title.strip()
        except Exception:
            pass  # PyPDF2 might fail on some PDFs, that's ok.

        # If title is substantial, use it exclusively.
        if len(metadata_title) >= 8:
            logging.info(f"PDF '{os.path.basename(pdf_path)}' has a /Title field >= 8 chars. Using it exclusively for matching.")
            match = _find_best_match(metadata_title, metadata_set, 0.9)
            if not match:
                logging.info(f"No match found for '{os.path.basename(pdf_path)}' using its /Title. No further matching will be attempted.")
            else:
                logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using '/Title' metadata field.")
            return match

        # --- If /Title is short or missing, proceed with other methods ---
        logging.info(f"PDF '{os.path.basename(pdf_path)}' has a short or missing /Title. Proceeding with filename and content matching.")

        # --- 2. Attempt to match using the PDF filename ---
        basename = os.path.basename(pdf_path)
        filename_title = os.path.splitext(basename)[0]
        filename_title = filename_title.replace('_', ' ').replace('-', ' ')
        
        match = _find_best_match(filename_title, metadata_set, 0.6)
        if match:
            logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using filename.")
            return match

        # --- 3. Fallback: attempt to match using cached or extracted text content ---
        pdf_dir = os.path.dirname(pdf_path)
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        cache_file_path = os.path.join(pdf_dir, f"{pdf_basename}.title")
        content_title = None

        if os.path.exists(cache_file_path):
            try:
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    content_title = f.read().strip()
                if content_title:
                    logging.info(f"Read title from cache for '{os.path.basename(pdf_path)}'.")
                    match = _find_best_match(content_title, metadata_set, 0.9)
                    if match:
                        logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using cached title file.")
                        return match
                else:
                    logging.info(f"Empty cache file found for '{os.path.basename(pdf_path)}', skipping text extraction.")
            except (IOError, OSError) as e:
                logging.error(f"Error reading cache file {cache_file_path}: {e}")
        
        else:
            content_title = get_title_from_text(pdf_path)
            if content_title:
                match = _find_best_match(content_title, metadata_set, 0.9)
                if match:
                    logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using text content.")
                    return match

        return None

    except Exception as e:
        logging.error(f"An unexpected error occurred in match_pdf_to_metadata for {pdf_path}: {e}")
        return None
