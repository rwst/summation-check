"""
Module for downloading PDFs from NCBI PubMed Central (PMC).

Provides functionality to:
- Convert PMIDs to PMCIDs using PMC ID Converter API
- Get PDF download links from PMC OA Service
- Download PDFs with rate limiting
- Background worker for non-blocking downloads
"""

import os
import time
import logging
import tarfile
import tempfile
from threading import Lock
from typing import Optional, Tuple
import xml.etree.ElementTree as ET
from urllib.request import urlretrieve
from urllib.error import URLError

import requests
from pydantic import BaseModel
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class PmcDownloadResult(BaseModel):
    """Result object for PMC download operations."""
    total_requested: int
    successful_downloads: int
    not_available_in_pmc: list[str]  # PMIDs without PMCID
    no_pdf_available: list[str]      # PMCIDs without PDF in OA subset
    errors: dict[str, str]            # {pmid: error_message}
    downloaded_files: list[str]       # List of saved file paths


class PmcApiClient:
    """
    Client for interacting with NCBI PMC APIs.

    Handles:
    - PMC ID Converter API (PMID -> PMCID conversion)
    - PMC OA Service API (PDF link retrieval)
    - Rate limiting (3 req/sec without key, 10 req/sec with key)
    - Error handling and retries
    """

    # Updated API URLs (legacy URLs redirect but use current ones for reliability)
    ID_CONVERTER_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
    PMC_OA_SERVICE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None,
                 tool: str = "SummationCheck"):
        """
        Initialize PMC API client with rate limiting.

        Args:
            email: Optional email for NCBI (improves rate limits)
            api_key: Optional NCBI API key (enables 10 req/sec)
            tool: Tool name for API requests
        """
        self.email = email or ""
        self.api_key = api_key or ""
        self.tool = tool
        self.last_request_time = 0
        self.rate_limit_lock = Lock()

        # Determine rate limit based on API key availability
        if self.api_key:
            self.min_request_interval = 0.1   # 10 req/sec with API key
        else:
            self.min_request_interval = 0.34  # ~3 req/sec without API key

    def _apply_rate_limit(self):
        """Thread-safe rate limiting enforcement."""
        with self.rate_limit_lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
            self.last_request_time = time.time()

    def _make_request_with_retry(self, url: str, params: dict, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: Request URL
            params: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            Response object or None on failure
        """
        for attempt in range(max_retries):
            try:
                self._apply_rate_limit()
                response = requests.get(url, params=params, timeout=30)

                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * self.min_request_interval
                        logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s before retry")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Rate limit exceeded after max retries")
                        return None

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((2 ** attempt) * 0.5)
                else:
                    return None

        return None

    def convert_pmids_to_pmcids(self, pmid_list: list[str]) -> dict[str, Optional[str]]:
        """
        Convert list of PMIDs to PMCIDs using PMC ID Converter API.

        API batches up to 200 IDs per request. This method automatically
        handles batching for larger lists.

        Args:
            pmid_list: List of PubMed IDs

        Returns:
            Dictionary mapping {pmid: pmcid or None}
        """
        result = {}
        batch_size = 200

        for i in range(0, len(pmid_list), batch_size):
            batch = pmid_list[i:i + batch_size]
            batch_str = ",".join(batch)

            params = {
                "ids": batch_str,
                "format": "json",
                "tool": self.tool,
            }
            if self.email:
                params["email"] = self.email
            if self.api_key:
                params["api_key"] = self.api_key

            response = self._make_request_with_retry(self.ID_CONVERTER_URL, params)

            if not response:
                # Mark all PMIDs in this batch as unavailable
                for pmid in batch:
                    result[pmid] = None
                continue

            try:
                data = response.json()
                logger.debug(f"ID Converter response: {data}")
                records = data.get("records", [])

                for record in records:
                    pmid = record.get("pmid")
                    pmcid = record.get("pmcid")
                    if pmid:
                        # Convert pmid to string since API may return int
                        pmid_str = str(pmid)
                        result[pmid_str] = pmcid  # pmcid may be None if not in PMC
                        logger.debug(f"PMID {pmid_str} -> PMCID {pmcid}")

                # Mark any PMIDs not in response as unavailable
                for pmid in batch:
                    if pmid not in result:
                        logger.warning(f"PMID {pmid} not found in ID converter response")
                        result[pmid] = None

            except (ValueError, KeyError) as e:
                logger.error(f"Failed to parse ID converter response: {e}")
                logger.error(f"Response text: {response.text}")
                for pmid in batch:
                    result[pmid] = None

        return result

    def get_pdf_link(self, pmcid: str) -> Optional[Tuple[str, str]]:
        """
        Get PDF download link for a PMCID using PMC OA Service.

        Only works for articles in the PMC Open Access subset.

        Args:
            pmcid: PubMed Central ID (e.g., "PMC1234567")

        Returns:
            Tuple of (link_type, url) where link_type is 'pdf' or 'tgz',
            or None if not available
        """
        params = {
            "id": pmcid,
            "tool": self.tool,
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key

        response = self._make_request_with_retry(self.PMC_OA_SERVICE_URL, params)

        if not response:
            return None

        try:
            # Parse XML response
            logger.debug(f"PMC OA Service response for {pmcid}: {response.text[:500]}")
            root = ET.fromstring(response.content)

            # Look for error element first
            error = root.find(".//error")
            if error is not None:
                logger.warning(f"PMC OA Service error for {pmcid}: {error.text}")
                return None

            # First, try to find direct PDF link
            # XML structure: <OA><records><record><link format="pdf" href="..."/>
            pdf_link = root.find(".//link[@format='pdf']")

            if pdf_link is not None and 'href' in pdf_link.attrib:
                pdf_url = pdf_link.attrib['href']
                logger.info(f"Found direct PDF link for {pmcid}: {pdf_url}")
                return ('pdf', pdf_url)

            # If no direct PDF, look for tar.gz package
            # XML structure: <OA><records><record><link format="tgz" href="..."/>
            tgz_link = root.find(".//link[@format='tgz']")

            if tgz_link is not None and 'href' in tgz_link.attrib:
                tgz_url = tgz_link.attrib['href']
                logger.info(f"Found tar.gz package for {pmcid}: {tgz_url}")
                return ('tgz', tgz_url)

            logger.warning(f"No PDF or tar.gz package found for {pmcid} (may not be in OA subset)")
            logger.debug(f"Full XML response: {response.text}")
            return None

        except ET.ParseError as e:
            logger.error(f"Failed to parse PMC OA Service XML response: {e}")
            logger.error(f"Response content: {response.text}")
            return None

    def download_pdf(self, url: str, save_path: str) -> bool:
        """
        Download PDF from URL to specified path.

        Args:
            url: FTP or HTTP URL to PDF
            save_path: Local file path to save PDF

        Returns:
            True on success, False on failure
        """
        try:
            self._apply_rate_limit()
            urlretrieve(url, save_path)
            return True
        except (URLError, OSError) as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
            return False

    def download_and_extract_pdf_from_tgz(self, tgz_url: str, save_path: str, pmcid: str) -> bool:
        """
        Download tar.gz package from PMC OA Service and extract PDF.

        PMC OA packages typically contain:
        - PMC######.nxml (article XML)
        - PMC######.pdf (the PDF we want)
        - other files (figures, supplements, etc.)

        Args:
            tgz_url: URL to tar.gz package
            save_path: Local file path to save extracted PDF
            pmcid: PMCID for logging (e.g., "PMC1234567")

        Returns:
            True on success, False on failure
        """
        try:
            # Download tar.gz to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_tgz:
                tmp_tgz_path = tmp_tgz.name

            self._apply_rate_limit()
            logger.info(f"Downloading tar.gz package for {pmcid} from {tgz_url}")
            urlretrieve(tgz_url, tmp_tgz_path)

            # Extract PDF from tar.gz
            try:
                with tarfile.open(tmp_tgz_path, 'r:gz') as tar:
                    # Look for PDF file in the archive
                    pdf_member = None
                    for member in tar.getmembers():
                        if member.name.endswith('.pdf'):
                            pdf_member = member
                            logger.info(f"Found PDF in archive: {member.name}")
                            break

                    if pdf_member is None:
                        logger.error(f"No PDF file found in tar.gz package for {pmcid}")
                        return False

                    # Extract PDF to destination
                    with tar.extractfile(pdf_member) as pdf_file:
                        if pdf_file is None:
                            logger.error(f"Could not extract PDF from archive for {pmcid}")
                            return False
                        with open(save_path, 'wb') as output_file:
                            output_file.write(pdf_file.read())

                    logger.info(f"Successfully extracted PDF from tar.gz for {pmcid}")
                    return True

            finally:
                # Clean up temporary tar.gz file
                try:
                    os.remove(tmp_tgz_path)
                except OSError:
                    pass

        except (URLError, OSError, tarfile.TarError) as e:
            logger.error(f"Failed to download/extract PDF from tar.gz for {pmcid}: {e}")
            return False


class PmcDownloadWorker(QObject):
    """
    Background worker for downloading PDFs from PMC.

    Runs in separate QThread to avoid blocking the GUI.
    Emits progress updates and final result.
    """

    finished = pyqtSignal(object)  # Emits PmcDownloadResult
    progress = pyqtSignal(str)     # Emits status message strings

    def __init__(self, pmid_list: list[str], pdf_folder: str,
                 email: str = "", api_key: str = ""):
        """
        Initialize worker with download parameters.

        Args:
            pmid_list: List of PMIDs to download
            pdf_folder: Directory to save PDFs
            email: Optional NCBI email
            api_key: Optional NCBI API key
        """
        super().__init__()
        self.pmid_list = pmid_list
        self.pdf_folder = pdf_folder
        self.email = email
        self.api_key = api_key

    @pyqtSlot()
    def run(self):
        """
        Main download logic. Executes in background thread.

        Flow:
        1. Convert PMIDs to PMCIDs (batched)
        2. For each PMCID, get PDF link or tar.gz package
        3. Download PDFs (direct or extract from tar.gz)
        4. Rename with PMID: prefix
        5. Track success/failure
        6. Emit final result
        """
        logger.info(f"Starting PMC download for {len(self.pmid_list)} PMIDs")

        # Initialize result tracking
        result = PmcDownloadResult(
            total_requested=len(self.pmid_list),
            successful_downloads=0,
            not_available_in_pmc=[],
            no_pdf_available=[],
            errors={},
            downloaded_files=[]
        )

        # Create API client
        client = PmcApiClient(email=self.email, api_key=self.api_key)

        # Step 1: Convert PMIDs to PMCIDs
        self.progress.emit(f"Converting {len(self.pmid_list)} PMIDs to PMCIDs...")
        pmid_to_pmcid = client.convert_pmids_to_pmcids(self.pmid_list)

        # Step 2-4: Process each PMID
        for idx, pmid in enumerate(self.pmid_list, 1):
            self.progress.emit(f"Processing PMID {pmid} ({idx}/{len(self.pmid_list)})...")

            pmcid = pmid_to_pmcid.get(pmid)

            # Check if PMID has PMCID
            if not pmcid:
                logger.info(f"PMID {pmid} not available in PMC")
                result.not_available_in_pmc.append(pmid)
                continue

            # Get PDF link or tar.gz package link
            link_info = client.get_pdf_link(pmcid)

            if not link_info:
                logger.info(f"No PDF available for {pmid} (PMCID: {pmcid})")
                result.no_pdf_available.append(pmid)
                continue

            link_type, link_url = link_info
            temp_filename = f"temp_{pmid}.pdf"
            temp_path = os.path.join(self.pdf_folder, temp_filename)

            # Download based on link type
            if link_type == 'pdf':
                # Direct PDF download
                if not client.download_pdf(link_url, temp_path):
                    result.errors[pmid] = "Failed to download PDF from server"
                    continue
            elif link_type == 'tgz':
                # Download and extract PDF from tar.gz package
                if not client.download_and_extract_pdf_from_tgz(link_url, temp_path, pmcid):
                    result.errors[pmid] = "Failed to extract PDF from tar.gz package"
                    continue
            else:
                result.errors[pmid] = f"Unknown link type: {link_type}"
                continue

            # Rename to PMID: prefix format
            final_filename = f"PMID:{pmid}-downloaded.pdf"
            final_path = os.path.join(self.pdf_folder, final_filename)

            try:
                # Check if file with same PMID already exists
                if os.path.exists(final_path):
                    # Add timestamp to avoid collision
                    timestamp = int(time.time())
                    final_filename = f"PMID:{pmid}-downloaded-{timestamp}.pdf"
                    final_path = os.path.join(self.pdf_folder, final_filename)

                os.rename(temp_path, final_path)
                result.successful_downloads += 1
                result.downloaded_files.append(final_filename)
                logger.info(f"Successfully downloaded and saved: {final_filename}")

            except OSError as e:
                logger.error(f"Failed to rename downloaded file for PMID {pmid}: {e}")
                result.errors[pmid] = f"File system error: {str(e)}"
                # Clean up temp file
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    pass

        # Emit final result
        logger.info(f"PMC download completed: {result.successful_downloads}/{result.total_requested} successful")
        self.progress.emit(f"Download completed: {result.successful_downloads}/{result.total_requested} successful")
        self.finished.emit(result)
