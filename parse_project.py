import xml.etree.ElementTree as ET
import csv
import sys
import os
import argparse
import subprocess


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
