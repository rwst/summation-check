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
    Matches a PDF file to a metadata entry based on extracted title (using fuzzy matching) and author surnames found in the first 1KB of text.

    :param pdf_path: Path to the PDF file.
    :param metadata_set: List of metadata dictionaries, each with 'title': str and 'authors': list[str] (surnames).
    :return: Matching metadata dict or None if no match.
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract title from PDF metadata
            extracted_title = reader.metadata.get('/Title', '')
            norm_extracted_title = normalize_text(extracted_title)
            
            # Extract text from PDF, accumulating up to approximately 1KB (1024 characters)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text() or ''
                text += page_text + ' '
                if len(text) >= 1024:
                    break
            text = text[:1024]
            norm_text = normalize_text(text)
            
            # Collect candidates where conditions are met
            candidates = []
            for meta in metadata_set:
                norm_meta_title = normalize_text(meta.get('title', ''))
                
                title_similarity = difflib.SequenceMatcher(None, norm_extracted_title, norm_meta_title).ratio()
                
                authors = meta.get('authors', [])
                norm_authors = [normalize_text(author) for author in authors]
                len_authors = len(norm_authors)
                
                matched_count = sum(1 for norm_author in norm_authors if norm_author in norm_text)
                
                if len_authors > 0:
                    matched_fraction = matched_count / len_authors
                else:
                    matched_fraction = 1.0  # Treat as fully matched if no authors
                
                # Exclude if title_similarity < 0.9 AND matched_fraction < 0.5
                if title_similarity < 0.9 and matched_fraction < 0.5:
                    continue
                
                candidates.append((title_similarity, meta))
            
            if candidates:
                # Return the metadata with the highest title similarity
                return max(candidates, key=lambda x: x[0])[1]
            else:
                return None
    
    except Exception:
        return None
