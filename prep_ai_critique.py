# prep_ai_critique.py
import os
import re
import fitz  # PyMuPDF

from logger import setup_logger

logger = setup_logger()


def get_pdf_texts_for_pmids(qc_list_items, pdf_folder):
    """
    Gets the set of PMIDs from the QC window's right list, finds the associated
    PDF for each PMID, reads the text, and returns a dictionary with PMID as key
    and PDF text as value.

    Args:
        qc_list_items (list): A list of strings from the QC window's right list.
        pdf_folder (str): The path to the folder containing the PDF files.

    Returns:
        dict: A dictionary where keys are PMIDs (str) and values are the
              extracted text from the corresponding PDFs (str).
    """
    pmid_texts = {}

    # Extract PMIDs from list items
    pmids = []
    for item_text in qc_list_items:
        # Item text is like "✓ 12345678 Some Title"
        match = re.search(r'(\d{8,})', item_text)
        if match:
            pmids.append(match.group(1))

    if not pmids:
        return {}

    # Find PDF for each PMID and extract text
    for pmid in pmids:
        found_pdf = False
        for filename in os.listdir(pdf_folder):
            if filename.startswith(f"PMID:{pmid}") and filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                try:
                    with fitz.open(pdf_path) as doc:
                        text = ""
                        for page in doc:
                            text += page.get_text()
                        pmid_texts[pmid] = text
                        logger.info(f"Successfully extracted text from {filename} for PMID {pmid}.")
                except Exception as e:
                    # Handle cases where PDF is corrupt or can't be read
                    error_message = f"Error reading PDF {filename} for PMID {pmid}: {e}"
                    logger.error(error_message)
                    pmid_texts[pmid] = error_message
                found_pdf = True
                break
        if not found_pdf:
            not_found_message = f"PDF file not found for PMID {pmid}."
            logger.warning(not_found_message)
            pmid_texts[pmid] = not_found_message

    return pmid_texts
