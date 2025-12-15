import PyPDF2
import langextract as lx
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
    Extracts the title from the PDF's text using langextract and caches the result.
    This is a fallback for when the '/Title' metadata field is not available.
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            # Extract the first 3000 characters of text
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                if len(text) >= 3000:
                    break
            text = text[:3000]
    except Exception as e:
        logging.error(f"Error reading PDF {pdf_path} with PyPDF2: {e}")
        return None

    if not text:
        return None

    # Clean up extracted text to handle common extraction issues
    text = text.replace('\u2002', ' ')  # Replace EN SPACE with regular space
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        logging.warning(f"Extracted text from {pdf_path} is empty after cleaning. Skipping langextract.")
        return None

    # Use langextract to get the title
    prompt = "Extract the title of the scientific article from the following text."
    
    examples = [
        lx.data.ExampleData(
            text="The ultimate guide to writing scientific papers. John Doe. University of Science. Abstract: This paper discusses...",
            extractions=[
                lx.data.Extraction(
                    extraction_class="title",
                    extraction_text="The ultimate guide to writing scientific papers",
                )
            ],
        ),
        lx.data.ExampleData(
            text="""
Biochcmicd

Phcology,

Printedin Great Britain.

Vol. 42, Suppl.,pp. SE!?-S!X,
1991.

cm-29sy91 s3.00 + 0.00
@ 1991. Pergamon Press plc

FORMATION OF MOLECULAR IODINE DURING
OXIDATION OF IODIDE BY THE PEROXIDASE/H202
SYSTEM
IMPLICATIONS

FOR ANTITHYROID

THERAPY

JEAN-FRANCOK LAGORCE, JEAN-CLAUDE THOMES, GILBERT CATANZANO,
JACQUES BUXERAUD, MICHBLE RABY and CLAUDE RABY*
Department

of Chemical Pharmacy, Faculty of Pharmacy, 87025 Limoges, France
(Received 19 September 1990, accepted 19 August 1991)

Abstract-The

first step in the biogenesis of thyroid hormones is the oxidation of iodides taken up by
""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="title",
                    extraction_text="Formation of Molecular Iodine During Oxidation of Iodide by the Peroxidase/H2O2 System. Implications for Antithyroid Therapy",
                )
            ],
        ),
        lx.data.ExampleData(
            text="""
HUMAN MUTATION Mutation in Brief 31: E1304–E1318 (2010) Online

MUTATION IN BRIEF

HUMAN MUTATION
OFFICIAL JOURNAL

Compound Heterozygosity for a Novel Hemizygous
Missense Mutation and a Partial Deletion Affecting
the Catalytic Core of the H2O2-generating Enzyme
DUOX2 Associated with Transient Congenital
Hypothyroidism

www.hgvs.org

Candice Hoste*, Sabrina Rigutto*, Guy Van Vliet‡, Françoise Miot*, and Xavier De Deken*
*IRIBHM, Université Libre de Bruxelles (U.L.B.), Campus Erasme, 1070 Brussels, Belgium; ‡Endocrinology Service and
Research Center, Sainte-Justine Hospital, and Department of Pediatrics, Université de Montréal, 3175 Côte Ste-Catherine,
Montreal H3T 1C5 QC, Canada
*Correspondence to Xavier De Deken, IRIBHM, Université Libre de Bruxelles (U.L.B.), Campus Erasme, Bat.C., 808 route de
Lennik, B-1070 Bruxelles, Belgium. Fax: +32-2-5554655, Tel: +32-2-5554152. E-Mail: xdedeken@ulb.ac.be
Grant Sponsor Information: See Acknowledgments
Communicated by Jurgen Horst

ABSTRACT: Dual oxidases (DUOX) 1 and 2 are components of the thyroid H2O2-generating system.
""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="title",
                    extraction_text="Compound Heterozygosity for a Novel Hemizygous Missense Mutation and a Partial Deletion Affecting the Catalytic Core of the H2O2-generating Enzyme DUOX2 Associated with Transient Congenital Hypothyroidism",
                )
            ],
        ),
    ]

    extracted_title = None
    try:
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples
        )
        if result and result.extractions:
            extracted_title = result.extractions[0].extraction_text
    except Exception as e:
        logging.error(f"Error during langextract title extraction for {pdf_path}: {e}")

    # Cache the result to a .title file
    try:
        pdf_dir = os.path.dirname(pdf_path)
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        cache_file_path = os.path.join(pdf_dir, f"{pdf_basename}.title")
        with open(cache_file_path, 'w', encoding='utf-8') as f:
            f.write(extracted_title or "")  # Write title or empty string
        if extracted_title:
            logging.info(f"Cached extracted title for '{os.path.basename(pdf_path)}'.")
        else:
            logging.info(f"Created empty cache file for '{os.path.basename(pdf_path)}' (no title found).")
    except (IOError, OSError) as e:
        logging.error(f"Error writing cache file for {pdf_path}: {e}")

    return extracted_title


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
       b. If the filename doesn't match, attempt to match using the text content,
          which may involve caching and using the 'langextract' library.

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
                    logging.info(f"Empty cache file found for '{os.path.basename(pdf_path)}', skipping langextract.")
            except (IOError, OSError) as e:
                logging.error(f"Error reading cache file {cache_file_path}: {e}")
        
        else:
            content_title = get_title_from_text(pdf_path)
            if content_title:
                match = _find_best_match(content_title, metadata_set, 0.9)
                if match:
                    logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using text content (langextract).")
                    return match

        return None

    except Exception as e:
        logging.error(f"An unexpected error occurred in match_pdf_to_metadata for {pdf_path}: {e}")
        return None