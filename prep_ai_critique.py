# prep_ai_critique.py
import os
import re
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from pydantic import BaseModel

from logger import setup_logger

logger = setup_logger()


class CritiqueResult(BaseModel):
    Critique: str
    SummaryOfCritique: str
    ImprovedShortText: str


def get_ai_critique(summary_text, pdf_texts, api_key):
    """
    Calls the Gemini API with the provided summary and PDF texts to get a critique.

    Args:
        summary_text (str): The summary text to be critiqued.
        pdf_texts (dict): A dictionary of PDF texts with PMID as key.
        api_key (str): The Gemini API key.

    Returns:
        CritiqueResult: A Pydantic model object with the critique, or an error string.
    """
    if not api_key:
        return "Error: GEMINI_API_KEY is not set."
    if not summary_text:
        return "Error: Summary text is empty or could not be found."
    if not pdf_texts:
        return "Error: No PDF documents were provided for critique."

    try:
        client = genai.Client(api_key=api_key)

        # Combine all PDF texts into a single string
        all_papers_content = ""
        for pmid, text in pdf_texts.items():
            all_papers_content += f"Start of paper with PUBMED_ID: {pmid}\n\n{text}\n\n---END OF PAPER---\n"

        prompt = """
You are given the concatenated text of one or more scientific articles, and in a second file a short text file with statements, backed up by references. First, check if all references in the short text also correspond to their full text as part of the papers file. Use the delimiter ---END OF PAPER--- to split papers.txt into individual papers. Then, for every part of the short text that ends with references, check: 1. all statements must be directly supported by experimental evidence in experimental papers or statements in review papers; 2. all statements must not misrepresent or exaggerate findings from the article(s); 3. If quantitative data (numbers, percentages, p-values) is mentioned, it must match the article(s) precisely. 4. all statements must not introduce information or conclusions not present in the cited article(s). 5. assuming the short text describes a chemical reaction or process, either the papers don't mention any results about regulators of the reaction/process, or the regulators are mentioned explicitly in the statements. 6. either all results were obtained using human cell lines, or the cell lines used, with their species, are mentioned explicitly in the statements. After judging all statements with references, write out your critique and, if some rules were broken, an improved short text that only changes those statements that you criticized.
        """

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                summary_text,
                all_papers_content,
                prompt
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": CritiqueResult
            }
        )

        # The response text should be a JSON string that can be parsed into the Pydantic model
        return CritiqueResult.model_validate_json(response.text)

    except Exception as e:
        logger.error(f"An error occurred during the Gemini API call: {e}")
        return f"An error occurred: {e}"


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
