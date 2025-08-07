import PyPDF2
import unicodedata
import difflib

def normalize_text(text: str) -> str:
    """
    Normalize Unicode text to ASCII lowercase for comparison.
    """
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def match_pdf_to_metadata(pdf_path: str, metadata_set: list[dict]) -> dict | None:
    """
    Matches a PDF file to a metadata entry based on extracted title (using fuzzy matching).

    :param pdf_path: Path to the PDF file.
    :param metadata_set: List of metadata dictionaries, each with 'title': str.
    :return: Matching metadata dict or None if no match.
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract title from PDF metadata
            extracted_title = reader.metadata.get('/Title', '')
            if not extracted_title:
                return None
            norm_extracted_title = normalize_text(extracted_title)
            
            # Collect candidates where title similarity is high
            candidates = []
            for meta in metadata_set:
                norm_meta_title = normalize_text(meta.get('title', ''))
                
                title_similarity = difflib.SequenceMatcher(None, norm_extracted_title, norm_meta_title).ratio()
                
                # Use a threshold for title similarity to consider it a potential match
                if title_similarity >= 0.9:
                    candidates.append((title_similarity, meta))
            
            if candidates:
                # Return the metadata with the highest title similarity from the candidates
                return max(candidates, key=lambda x: x[0])[1]
            else:
                return None
    
    except Exception:
        return None

