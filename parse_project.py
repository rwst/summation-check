import sys
import xml.etree.ElementTree as ET


def extract_metadata_from_project_file(xml_string):
    """
    Parses an XML string from a Reactome project file to extract literature references.

    Args:
        xml_string: A string containing the XML data.

    Returns:
        A list of dictionaries, where each dictionary represents a literature reference
        and contains 'title' and 'pubMedIdentifier' keys.
        Returns an empty list if no references are found or in case of a parsing error.
    """
    references = []
    try:
        root = ET.fromstring(xml_string)
        # Find all LiteratureReference instances
        for lit_ref_parent in root.findall('.//LiteratureReference'):
            for instance in lit_ref_parent.findall('instance'):
                # Skip shell instances which may not have all attributes
                if instance.get('isShell') == 'true':
                    continue

                title = None
                pub_med_id = None

                # Find title and pubMedIdentifier attributes
                for attr in instance.findall('attribute'):
                    if attr.get('name') == 'title':
                        title = attr.get('value')
                    elif attr.get('name') == 'pubMedIdentifier':
                        pub_med_id = attr.get('value')

                if title and pub_med_id:
                    references.append({
                        'title': title,
                        'pubMedIdentifier': pub_med_id
                    })
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        return []

    return references


def extract_event_data(xml_string):
    """
    Parses an XML string from a Reactome project file to extract data for specific object types.
    The function extracts information for Pathway, BlackBoxEvent, FailedReaction,
    Polymerisation, and Reaction objects.

    Args:
        xml_string: A string containing the XML data of the project file.

    Returns:
        A list of unique dictionaries, where each dictionary contains data for an object.
        The dictionary keys are 'DB_ID', 'name', 'summation_text', and 'literature_references'.
        'literature_references' is a list of lists, with each inner list containing
        [pubMedIdentifier, title].
    """
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        return []

    summations = {}
    for summation_instance in root.findall('.//Summation/instance'):
        db_id = summation_instance.get('DB_ID')
        if not db_id:
            continue
        text_attr = summation_instance.find("attribute[@name='text']")
        if text_attr is not None and text_attr.get('value') is not None:
            summations[db_id] = text_attr.get('value')

    literature_refs = {}
    for lit_ref_instance in root.findall('.//LiteratureReference/instance'):
        db_id = lit_ref_instance.get('DB_ID')
        if not db_id:
            continue

        title_attr = lit_ref_instance.find("attribute[@name='title']")
        pubmed_attr = lit_ref_instance.find("attribute[@name='pubMedIdentifier']")

        title = title_attr.get('value') if title_attr is not None else None
        pubmed_id = pubmed_attr.get('value') if pubmed_attr is not None else None

        if title and pubmed_id:
            literature_refs[db_id] = [pubmed_id, title]

    results = []
    object_types = ['Pathway', 'BlackBoxEvent', 'FailedReaction', 'Polymerisation', 'Reaction']

    for obj_type in object_types:
        for instance in root.findall(f'.//{obj_type}/instance'):
            if instance.get('isShell') == 'true':
                continue

            db_id = instance.get('DB_ID')
            name_attr = instance.find("attribute[@name='name']")

            if not db_id or name_attr is None:
                continue

            name = name_attr.get('value')

            summation_text = None
            summation_attr = instance.find("attribute[@name='summation']")
            if summation_attr is not None:
                summation_id = summation_attr.get('referTo')
                if summation_id in summations:
                    summation_text = summations[summation_id]

            lit_ref_list = []
            for lit_ref_attr in instance.findall("attribute[@name='literatureReference']"):
                lit_ref_id = lit_ref_attr.get('referTo')
                if lit_ref_id in literature_refs:
                    lit_ref_list.append(literature_refs[lit_ref_id])

            try:
                db_id_int = int(db_id)
            except (ValueError, TypeError):
                continue

            results.append({
                'DB_ID': db_id_int,
                'name': name,
                'summation_text': summation_text,
                'literature_references': lit_ref_list
            })

    # Return a list of unique dictionaries, using DB_ID for uniqueness.
    unique_results = {d['DB_ID']: d for d in results}.values()
    return list(unique_results)


def get_summary_for_event(xml_string, db_id):
    """
    Finds the summary text for a specific event DB_ID in the XML data.

    Args:
        xml_string (str): The XML content as a string.
        db_id (int or str): The DB_ID of the event to find.

    Returns:
        str: The summation text for the given event, or None if not found.
    """
    event_data = extract_event_data(xml_string)
    target_db_id = int(db_id)

    for event in event_data:
        if event.get('DB_ID') == target_db_id:
            return event.get('summation_text')

    return None
