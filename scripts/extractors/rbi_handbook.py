"""RBI Handbook workbook discovery, immutable landing and XLSX parsing."""

from __future__ import annotations

import hashlib
import posixpath
import re
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from models.capex_sources import RbiHandbookResponse, WorkbookSheet


HANDBOOK_URL = (
    "https://www.rbi.org.in/scripts/AnnualPublications.aspx?"
    "head=Handbook%20of%20Statistics%20on%20Indian%20Economy"
)
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"
_SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DOCUMENT_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((" ".join("".join(self._parts).split()), self._href))
            self._href = None
            self._parts = []


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[tuple[str, ...]]] = []
        self._stack: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._stack.append({"rows": [], "row": None, "cell": None})
        elif self._stack and tag == "tr":
            self._stack[-1]["row"] = []
        elif self._stack and tag in {"td", "th"} and self._stack[-1]["row"] is not None:
            self._stack[-1]["cell"] = []

    def handle_data(self, data: str) -> None:
        if self._stack and self._stack[-1]["cell"] is not None:
            self._stack[-1]["cell"].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self._stack:
            return
        context = self._stack[-1]
        if tag in {"td", "th"} and context["cell"] is not None:
            context["row"].append(" ".join("".join(context["cell"]).split()))
            context["cell"] = None
        elif tag == "tr" and context["row"] is not None:
            if context["row"]:
                context["rows"].append(tuple(context["row"]))
            context["row"] = None
        elif tag == "table":
            completed = self._stack.pop()["rows"]
            if completed:
                self.tables.append(completed)


def _html_value(value: str) -> Any:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", "-", "—", "..", "…"}:
        return None
    parenthesized = cleaned.startswith("(") and cleaned.endswith(")")
    numeric_text = cleaned[1:-1] if parenthesized else cleaned
    try:
        numeric = float(numeric_text)
    except ValueError:
        return value.strip()
    numeric = -numeric if parenthesized else numeric
    return int(numeric) if numeric.is_integer() else numeric


def read_html_tables(content: str, *, table_label: str) -> tuple[WorkbookSheet, ...]:
    """Return substantive data tables from an RBI publication page."""
    parser = _TableParser()
    parser.feed(content)
    if not parser.tables:
        raise ValueError("RBI publication contains no HTML tables")
    substantive = []
    for rows in parser.tables:
        width = max((len(row) for row in rows), default=0)
        contains_year = any(
            re.search(r"(?:19|20)\d{2}", value)
            for row in rows
            for value in row
        )
        if len(rows) >= 3 and width >= 2 and contains_year:
            substantive.append(rows)
    if not substantive:
        raise ValueError("RBI publication contains no substantive data table")
    return tuple(
        WorkbookSheet(
            table_label if len(substantive) == 1 else f"{table_label} — part {index}",
            tuple(tuple(_html_value(value) for value in row) for row in rows),
        )
        for index, rows in enumerate(substantive, start=1)
    )


def read_html_table(content: str, *, table_label: str) -> WorkbookSheet:
    """Select the largest substantive table for simple single-table publications."""
    sheets = read_html_tables(content, table_label=table_label)
    largest = sheets[0]
    for sheet in sheets[1:]:
        if len(sheet.rows) > len(largest.rows):
            largest = sheet
    return largest

def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    if letters is None:
        raise ValueError(f"Invalid XLSX cell reference: {reference}")
    index = 0
    for letter in letters.group(0):
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    namespace = {"s": _SPREADSHEET_NS}
    return [
        "".join(node.text or "" for node in item.findall(".//s:t", namespace))
        for item in root.findall("s:si", namespace)
    ]


def _cell_value(cell, shared: list[str]) -> Any:
    namespace = {"s": _SPREADSHEET_NS}
    value_type = cell.get("t")
    if value_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//s:t", namespace))
    value_node = cell.find("s:v", namespace)
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text
    if value_type == "s":
        return shared[int(raw)]
    if value_type in {"str", "e", "b"}:
        return raw
    try:
        numeric = float(raw)
    except ValueError:
        return raw
    return int(numeric) if numeric.is_integer() else numeric


def read_xlsx_sheets(content: bytes) -> tuple[WorkbookSheet, ...]:
    """Read values from an XLSX archive without optional dataframe packages."""
    with zipfile.ZipFile(BytesIO(content)) as archive:
        shared = _shared_strings(archive)
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            item.get("Id"): item.get("Target")
            for item in relationships.findall(f"{{{_PACKAGE_REL_NS}}}Relationship")
        }
        sheets: list[WorkbookSheet] = []
        for sheet in workbook.findall(f".//{{{_SPREADSHEET_NS}}}sheet"):
            relationship_id = sheet.get(f"{{{_DOCUMENT_REL_NS}}}id")
            target = targets.get(relationship_id)
            if not target:
                continue
            path = posixpath.normpath(posixpath.join("xl", target))
            root = ElementTree.fromstring(archive.read(path))
            rows: list[tuple[Any, ...]] = []
            for row in root.findall(f".//{{{_SPREADSHEET_NS}}}row"):
                cells: dict[int, Any] = {}
                for cell in row.findall(f"{{{_SPREADSHEET_NS}}}c"):
                    reference = cell.get("r")
                    if reference:
                        cells[_column_index(reference)] = _cell_value(cell, shared)
                if cells:
                    width = max(cells) + 1
                    rows.append(tuple(cells.get(index) for index in range(width)))
            sheets.append(WorkbookSheet(sheet.get("name", "Sheet"), tuple(rows)))
    if not sheets:
        raise ValueError("RBI workbook contains no readable worksheets")
    return tuple(sheets)


class RbiHandbookExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "rbi-handbook",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)
        self.headers = {"User-Agent": _USER_AGENT}

    def _get(self, url: str, *, referer: str | None = None):
        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer
        response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def discover_table(self, table_number: int) -> tuple[str, str, str | None]:
        response = self._get(HANDBOOK_URL)
        parser = _AnchorParser()
        parser.feed(response.text)
        marker = re.compile(rf"^Table\s+{table_number}\s*:", flags=re.IGNORECASE)
        for index, (label, table_href) in enumerate(parser.anchors):
            if not marker.search(label):
                continue
            workbook_url = None
            for _, href in parser.anchors[index + 1:index + 5]:
                if href.lower().endswith((".xlsx", ".xls")):
                    workbook_url = urljoin(response.url, href)
                    break
            return label, urljoin(response.url, table_href), workbook_url
        raise ValueError(f"RBI Handbook table {table_number} was not found")

    def fetch_table(self, table_number: int) -> RbiHandbookResponse:
        label, source_url, _ = self.discover_table(table_number)
        table_response = self._get(source_url, referer=HANDBOOK_URL)
        sheets = read_html_tables(table_response.text, table_label=label)
        retrieved = datetime.now(timezone.utc)
        checksum = hashlib.sha256(table_response.content).hexdigest()
        raw_path = (
            self.raw_root
            / retrieved.date().isoformat()
            / f"table-{table_number}-{checksum[:12]}.html"
        )
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(table_response.content)
        return RbiHandbookResponse(
            table_number=table_number,
            table_label=label,
            sheets=sheets,
            source_url=source_url,
            retrieved_at=retrieved.isoformat(),
            raw_path=raw_path,
            checksum=checksum,
        )

    def fetch_publication(
        self,
        publication_id: int,
        *,
        table_number: int,
        table_label: str,
    ) -> RbiHandbookResponse:
        """Fetch a stable RBI publication page when an archived table is required.

        RBI renumbers some Handbook tables between editions.  The publication ID
        is stable, so research stages that intentionally use a frozen edition can
        retain reproducible source semantics without weakening raw-data landing.
        """
        source_url = (
            "https://www.rbi.org.in/scripts/PublicationsView.aspx?"
            f"id={publication_id}"
        )
        table_response = self._get(source_url, referer=HANDBOOK_URL)
        sheets = read_html_tables(table_response.text, table_label=table_label)
        retrieved = datetime.now(timezone.utc)
        checksum = hashlib.sha256(table_response.content).hexdigest()
        raw_path = (
            self.raw_root
            / retrieved.date().isoformat()
            / f"publication-{publication_id}-{checksum[:12]}.html"
        )
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(table_response.content)
        return RbiHandbookResponse(
            table_number=table_number,
            table_label=table_label,
            sheets=sheets,
            source_url=source_url,
            retrieved_at=retrieved.isoformat(),
            raw_path=raw_path,
            checksum=checksum,
        )
