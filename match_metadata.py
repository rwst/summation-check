import PyPDF2
import langextract as lx
import unicodedata
import difflib
import sys
import logging
import os

def normalize_text(text: str) -> str:
    """
    Normalize Unicode text to ASCII lowercase for comparison.
    """
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()


def get_title_from_text(pdf_path: str) -> str | None:
    """
    Extracts the title from the PDF's text using langextract.
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
        print(f"Error reading PDF {pdf_path} with PyPDF2: {e}", file=sys.stderr)
        return None

    if not text:
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
        print(f"Error during langextract title extraction for {pdf_path}: {e}", file=sys.stderr)

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
    Matches a PDF file to a metadata entry based on extracted title (using fuzzy matching).
    It tries matching in the following order: PDF metadata '/Title', filename, and finally text content.

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
                metadata_title = reader.metadata.get('/Title', '')
        except Exception:
            pass  # PyPDF2 might fail on some PDFs, that's ok.

        if metadata_title:
            match = _find_best_match(metadata_title, metadata_set, 0.9)
            if match:
                logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using '/Title' metadata field.")
                return match

        # --- 2. Attempt to match using the PDF filename ---
        basename = os.path.basename(pdf_path)
        filename_title = os.path.splitext(basename)[0]
        # Replace common separators with spaces for better matching
        filename_title = filename_title.replace('_', ' ').replace('-', ' ')
        
        match = _find_best_match(filename_title, metadata_set, 0.6)
        if match:
            logging.info(f"Matched PDF '{os.path.basename(pdf_path)}' using filename.")
            return match

        # --- 3. Fallback: attempt to match using text content (langextract) ---
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