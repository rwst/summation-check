import xml.etree.ElementTree as ET
import csv
import sys
import os
import argparse
import subprocess

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Extract reaction data, process related papers, and generate output files.")
    parser.add_argument("-d", "--directory", required=True, help="Directory to search for PubMed files and write output.")
    parser.add_argument("-f", "--file", required=True, help="Reactome data markup XML file.")
    parser.add_argument("-i", "--id", required=True, help="DB_ID of the reaction to process.")
    return parser.parse_args()

def find_reaction_details(xml_filepath, target_reaction_id):
    """
    Finds a specific reaction in the XML and extracts its summary and literature PubMed IDs.
    """
    try:
        tree = ET.parse(xml_filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file '{xml_filepath}': {e}")
        return None, None
    except FileNotFoundError:
        print(f"Error: XML file not found at '{xml_filepath}'")
        return None, None

    reactome_node = root.find('reactome')
    if reactome_node is None:
        print("Error: <reactome> tag not found in XML.")
        return None, None

    # --- Pre-cache Summation and LiteratureReference instances ---
    summations_by_id = {}
    summation_parent_node = reactome_node.find('Summation')
    if summation_parent_node is not None:
        for inst in summation_parent_node.findall('instance'):
            db_id_val = None
            text_val = None
            for child_attr in inst.findall('attribute'):
                if child_attr.get('name') == 'DB_ID':
                    db_id_val = child_attr.get('value')
                elif child_attr.get('name') == 'text':
                    text_val = child_attr.get('value')
            if not db_id_val:  # Fallback
                db_id_val = inst.get('DB_ID')
            if db_id_val:
                summations_by_id[db_id_val] = text_val if text_val is not None else ''

    literature_refs_by_id = {}
    literature_parent_node = reactome_node.find('LiteratureReference')
    if literature_parent_node is not None:
        for inst in literature_parent_node.findall('instance'):
            db_id_val = None
            pubmed_val = None
            for child_attr in inst.findall('attribute'):
                if child_attr.get('name') == 'DB_ID':
                    db_id_val = child_attr.get('value')
                elif child_attr.get('name') == 'pubMedIdentifier':
                    pubmed_val = child_attr.get('value')
            if not db_id_val:  # Fallback
                db_id_val = inst.get('DB_ID')
            if db_id_val:
                literature_refs_by_id[db_id_val] = pubmed_val if pubmed_val is not None else ''
    # --- End Caching ---

    reaction_parent_node = reactome_node.find('Reaction')
    blackboxevent_parent_node = reactome_node.find('BlackBoxEvent')
    pathway_parent_node = reactome_node.find('Pathway')
    if reaction_parent_node is None or pathway_parent_node is None:
        print("Error: tags not found in XML.")
        return None, None

    instance_nodes = reaction_parent_node.findall('instance') + blackboxevent_parent_node.findall('instance') + pathway_parent_node.findall('instance')
    for instance_node in instance_nodes:
        # Reaction DB_ID is typically a direct attribute of the instance
        # or a child attribute named 'DB_ID'. Prioritize child if present.
        current_reaction_id = None
        for attr in instance_node.findall('attribute'):
            if attr.get('name') == 'DB_ID':
                current_reaction_id = attr.get('value')
                break
        if not current_reaction_id:
             current_reaction_id = instance_node.get('DB_ID')


        if current_reaction_id == target_reaction_id:
            # Extract summary
            reaction_summary = ""
            summation_ref_id = None
            for attr in instance_node.findall('attribute'):
                if attr.get('name') == 'summation':
                    summation_ref_id = attr.get('referTo')
                    break
            if summation_ref_id and summation_ref_id in summations_by_id:
                reaction_summary = summations_by_id[summation_ref_id]

            # Extract PubMed IDs
            reaction_pubmed_ids = []
            for attr in instance_node.findall('attribute'):
                if attr.get('name') == 'literatureReference':
                    lit_ref_id = attr.get('referTo')
                    if lit_ref_id and lit_ref_id in literature_refs_by_id:
                        pmid = literature_refs_by_id[lit_ref_id]
                        if pmid:
                            reaction_pubmed_ids.append(pmid)
            
            return reaction_summary, list(set(reaction_pubmed_ids)) # Return unique PubMed IDs

    print(f"Error: Reaction with DB_ID '{target_reaction_id}' not found.")
    return None, None


def run_pdftotext(pdf_path, txt_path):
    """Runs pdftotext to convert a PDF to TXT."""
    try:
        # The -layout option tries to preserve original physical layout.
        # You might prefer no option or other options like -raw for different results.
        result = subprocess.run(['pdftotext', pdf_path, txt_path], 
                                check=False, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running pdftotext for '{pdf_path}':")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
        print(f"Successfully converted '{pdf_path}' to '{txt_path}'.")
        return True
    except FileNotFoundError:
        print("Error: 'pdftotext' command not found. Please ensure it is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running pdftotext for '{pdf_path}': {e}")
        return False

def ensure_text_file_exists_and_get_content(directory, pubmed_id):
    """
    Ensures pubmed_id.txt exists, converting from PDF or prompting user if necessary.
    Returns the content of the .txt file.
    """
    txt_filename = f"{pubmed_id}.txt"
    pdf_filename = f"{pubmed_id}.pdf"
    txt_filepath = os.path.join(directory, txt_filename)
    pdf_filepath = os.path.join(directory, pdf_filename)

    while True: # Loop for retrying after user prompt
        if os.path.exists(txt_filepath):
            try:
                with open(txt_filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except IOError as e:
                print(f"Error reading '{txt_filepath}': {e}")
                return None # Or handle more gracefully
        elif os.path.exists(pdf_filepath):
            print(f"Found '{pdf_filename}', converting to text...")
            if run_pdftotext(pdf_filepath, txt_filepath):
                # Conversion successful, try reading the .txt file again in the next loop iteration
                continue
            else:
                # pdftotext failed, prompt user to fix or provide the .txt file manually
                print(f"Failed to convert '{pdf_filename}'.")
                # Fall through to prompt for manual copy
        
        # If we reach here, either .txt wasn't found, or PDF conversion failed
        print(f"\nFile '{txt_filename}' not found and '{pdf_filename}' either not found or could not be converted.")
        input(f"Please copy '{pdf_filename}' (or '{txt_filename}' directly) into the directory:\n'{directory}'\nThen press Enter to retry...")
        # Loop will restart and re-check conditions


def prepare(reaction_summary, pubmed_ids_list):
    if reaction_summary is None and pubmed_ids_list is None:
        # Error message already printed by find_reaction_details
        sys.exit(1)

    if not pubmed_ids_list:
        print(f"No PubMed IDs found for reaction DB_ID '{args.id}'.")
    
    # --- Write summary.txt ---
    summary_output_path = "short.txt"
    try:
        with open(summary_output_path, 'w', encoding='utf-8') as f:
            
            if reaction_summary:
                f.write(reaction_summary)
            else:
                print("No summary text found for this reaction.")
                exit(0)
        print(f"Reaction summary written to '{summary_output_path}'")
    except IOError as e:
        print(f"Error writing summary file '{summary_output_path}': {e}")

    # --- Process PubMed files and write papers.txt ---
    all_papers_content = []
    if pubmed_ids_list:
        print(f"\nProcessing {len(pubmed_ids_list)} PubMed ID(s): {', '.join(pubmed_ids_list)}")
        for pmid in pubmed_ids_list:
            print(f"\n--- Processing PubMed ID: {pmid} ---")
            paper_text = ensure_text_file_exists_and_get_content(args.directory, pmid)
            if paper_text is not None:
                all_papers_content.append(f"Start of paper with PUBMED_ID: {pmid}\n\n{paper_text}\n\n---END OF PAPER---\n")
            else:
                print(f"Warning: Could not get content for PubMed ID {pmid}. It will be skipped in papers.txt.")
    
    papers_output_path = "papers.txt"
    if all_papers_content:
        try:
            with open(papers_output_path, 'w', encoding='utf-8') as f:
                for content_block in all_papers_content:
                    f.write(content_block)
            print(f"\nConcatenated paper texts written to '{papers_output_path}'")
        except IOError as e:
            print(f"Error writing papers file '{papers_output_path}': {e}")
    elif pubmed_ids_list: # PubMed IDs existed but no content could be retrieved
        print(f"\nNo paper content could be retrieved for the found PubMed IDs. '{papers_output_path}' will not be created or will be empty.")
    else: # No PubMed IDs to begin with
         print(f"\nNo PubMed IDs to process. '{papers_output_path}' will not be created.")

def extract_metadata_from_project_file(project_file_content: str) -> list[dict]:
    """
    MOCK FUNCTION: Extracts metadata from the project file content.
    In a real implementation, this would parse the project file (e.g., XML, JSON).
    For now, it returns a hardcoded metadata set.
    """
    # The project_file_content is ignored in this mock version.
    return [
        {
            "title": "The Reactome pathway knowledgebase",
            "authors": ["Gillespie", "Jassal", "Steadman"]
        },
        {
            "title": "Reactome pathway analysis: a high-performance in-memory approach",
            "authors": ["Fabregat", "Sidiropoulos", "Viteri"]
        },
        {
            "title": "The logic of cancer",
            "authors": ["Vogelstein", "Kinzler"]
        }
    ]
