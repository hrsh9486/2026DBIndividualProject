"""Generate the maintained architecture and data-lineage guide as a DOCX.

The generator intentionally uses only the Python standard library.  That keeps
the documentation build reproducible in the same minimal environment as the
data pipeline, without making Microsoft Word or python-docx a runtime
dependency.  Coverage and latest-value tables are read from the current
processed artifacts; architectural prose is kept here beside the code it
documents.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from config import PROJECT_ROOT
from config.evidence_specs import (
    EVIDENCE_OUTPUT_PATHS,
    EVIDENCE_SPECS,
    SPECIFICATION_REGISTRY_VERSION,
)
from config.focused_indicators import FOCUSED_BUNDLES
from analysis import prepare_registered_analysis


OUTPUT_PATH = PROJECT_ROOT / "docs" / "architecture" / "FOCUSED_PIPELINE_ARCHITECTURE.docx"
GENERATED_ON = datetime.now(timezone.utc)


def xml_text(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


class DocxBuilder:
    """Small OOXML writer supporting the document elements used in this guide."""

    def __init__(self) -> None:
        self.body: list[str] = []
        self.relationships: list[tuple[str, str]] = []
        self.bookmark_id = 1

    def run(
        self,
        text: object,
        *,
        bold: bool = False,
        italic: bool = False,
        color: str | None = None,
        size: int | None = None,
        font: str | None = None,
        style: str | None = None,
    ) -> str:
        props = []
        if bold:
            props.append("<w:b/>")
        if italic:
            props.append("<w:i/>")
        if color:
            props.append(f'<w:color w:val="{color}"/>')
        if size:
            props.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
        if font:
            props.append(f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>')
        if style:
            props.append(f'<w:rStyle w:val="{style}"/>')
        prop_xml = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
        return f'<w:r>{prop_xml}<w:t xml:space="preserve">{xml_text(text)}</w:t></w:r>'

    def paragraph(
        self,
        text: object = "",
        *,
        style: str | None = None,
        runs: list[str] | None = None,
        align: str | None = None,
        keep_next: bool = False,
        keep_lines: bool = False,
        space_before: int | None = None,
        space_after: int | None = None,
        indent_left: int | None = None,
        border_left: str | None = None,
        shade: str | None = None,
        bookmark: str | None = None,
    ) -> str:
        props = []
        if style:
            props.append(f'<w:pStyle w:val="{style}"/>')
        if align:
            props.append(f'<w:jc w:val="{align}"/>')
        if keep_next:
            props.append("<w:keepNext/>")
        if keep_lines:
            props.append("<w:keepLines/>")
        if space_before is not None or space_after is not None:
            before = f' w:before="{space_before}"' if space_before is not None else ""
            after = f' w:after="{space_after}"' if space_after is not None else ""
            props.append(f"<w:spacing{before}{after}/>")
        if indent_left is not None:
            props.append(f'<w:ind w:left="{indent_left}"/>')
        if border_left:
            props.append(f'<w:pBdr><w:left w:val="single" w:sz="18" w:space="10" w:color="{border_left}"/></w:pBdr>')
        if shade:
            props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
        prop_xml = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
        content = "".join(runs) if runs is not None else self.run(text)
        if bookmark:
            bid = self.bookmark_id
            self.bookmark_id += 1
            content = f'<w:bookmarkStart w:id="{bid}" w:name="{slug(bookmark)}"/>{content}<w:bookmarkEnd w:id="{bid}"/>'
        return f"<w:p>{prop_xml}{content}</w:p>"

    def add_paragraph(self, text: object = "", **kwargs) -> None:
        self.body.append(self.paragraph(text, **kwargs))

    def add_heading(self, text: str, level: int, *, bookmark: str | None = None) -> None:
        self.add_paragraph(text, style=f"Heading{level}", keep_next=True, bookmark=bookmark)

    def add_bullet(self, text: str, *, level: int = 0) -> None:
        self.add_paragraph(
            runs=[self.run("•", bold=True, color="D97706"), self.run(f"  {text}")],
            style="ListParagraph",
            indent_left=360 + level * 360,
            keep_lines=True,
        )

    def add_number(self, number: int, text: str) -> None:
        self.add_paragraph(
            runs=[self.run(f"{number}. ", bold=True, color="1F4E78"), self.run(text)],
            style="ListParagraph",
            indent_left=240,
            keep_lines=True,
        )

    def add_code(self, text: str) -> None:
        self.add_paragraph(text, style="Code", keep_lines=True)

    def add_callout(self, title: str, text: str, *, color: str = "1F4E78", shade: str = "EAF2F8") -> None:
        self.add_paragraph(
            runs=[self.run(f"{title}  ", bold=True, color=color), self.run(text)],
            border_left=color,
            shade=shade,
            indent_left=180,
            keep_lines=True,
            space_before=120,
            space_after=160,
        )

    def add_page_break(self) -> None:
        self.body.append("<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>")

    def hyperlink(self, label: str, url: str) -> str:
        rid = f"rId{20 + len(self.relationships)}"
        self.relationships.append((rid, url))
        return (
            f'<w:hyperlink r:id="{rid}" w:history="1">'
            f'{self.run(label, color="0563C1", style="Hyperlink")}</w:hyperlink>'
        )

    def add_link(self, prefix: str, label: str, url: str, *, suffix: str = "") -> None:
        self.add_paragraph(runs=[self.run(prefix), self.hyperlink(label, url), self.run(suffix)])

    def table(
        self,
        headers: list[str],
        rows: list[list[object]],
        *,
        widths: list[int] | None = None,
        font_size: int = 18,
    ) -> None:
        widths = widths or [int(9000 / len(headers))] * len(headers)
        grid = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
        xml = [
            '<w:tbl><w:tblPr><w:tblStyle w:val="ArchitectureTable"/>'
            '<w:tblW w:w="0" w:type="auto"/><w:tblLayout w:type="fixed"/>'
            '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
            f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
        ]

        def cell(value: object, width: int, *, header: bool = False) -> str:
            cell_props = [f'<w:tcW w:w="{width}" w:type="dxa"/>']
            if header:
                cell_props.append('<w:shd w:val="clear" w:color="auto" w:fill="1F4E78"/>')
            paragraphs = []
            for line in str(value).split("\n") or [""]:
                paragraphs.append(
                    self.paragraph(
                        runs=[self.run(line, bold=header, color="FFFFFF" if header else None, size=font_size)],
                        style="TableText",
                        keep_lines=True,
                    )
                )
            return f"<w:tc><w:tcPr>{''.join(cell_props)}</w:tcPr>{''.join(paragraphs)}</w:tc>"

        xml.append('<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>')
        xml.extend(cell(value, widths[index], header=True) for index, value in enumerate(headers))
        xml.append("</w:tr>")
        for row in rows:
            xml.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
            xml.extend(cell(value, widths[index]) for index, value in enumerate(row))
            xml.append("</w:tr>")
        xml.append("</w:tbl>")
        self.body.append("".join(xml))
        self.add_paragraph("", space_after=80)

    def _document_xml(self) -> str:
        sect = (
            '<w:sectPr><w:headerReference w:type="default" r:id="rId3"/>'
            '<w:footerReference w:type="default" r:id="rId4"/>'
            '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="900" w:bottom="1134" w:left="900" w:header="560" w:footer="560" w:gutter="0"/>'
            '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<w:body>{''.join(self.body)}{sect}</w:body></w:document>"
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        external_rels = "".join(
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target={quoteattr(url)} TargetMode="External"/>'
            for rid, url in self.relationships
        )
        parts = {
            "[Content_Types].xml": CONTENT_TYPES,
            "_rels/.rels": ROOT_RELS,
            "docProps/core.xml": CORE_PROPERTIES,
            "docProps/app.xml": APP_PROPERTIES,
            "word/document.xml": self._document_xml(),
            "word/styles.xml": STYLES,
            "word/settings.xml": SETTINGS,
            "word/fontTable.xml": FONT_TABLE,
            "word/header1.xml": HEADER,
            "word/footer1.xml": FOOTER,
            "word/_rels/document.xml.rels": DOCUMENT_RELS.replace("<!--EXTERNAL-->", external_rels),
        }
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in parts.items():
                archive.writestr(name, content.encode("utf-8"))


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

CORE_PROPERTIES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>Focused India Research Pipeline: Architecture, Data Lineage and Interpretation Guide</dc:title>
<dc:subject>Implemented data architecture, source lineage, transformations, publication, and frontend</dc:subject>
<dc:creator>2026DB project</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">{GENERATED_ON.isoformat()}</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">{GENERATED_ON.isoformat()}</dcterms:modified>
<cp:keywords>India; data pipeline; architecture; lineage; indicators; static frontend</cp:keywords>
</cp:coreProperties>"""

APP_PROPERTIES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>2026DB documentation generator</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><Company></Company><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>1.0</AppVersion></Properties>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
<!--EXTERNAL-->
</Relationships>"""

SETTINGS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:zoom w:percent="100"/><w:defaultTabStop w:val="720"/><w:updateFields w:val="true"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>"""

FONT_TABLE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:font w:name="Aptos"/><w:font w:name="Aptos Display"/><w:font w:name="Cascadia Mono"/></w:fonts>"""

HEADER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="right"/><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="5" w:color="CBD5E1"/></w:pBdr></w:pPr><w:r><w:rPr><w:color w:val="64748B"/><w:sz w:val="17"/></w:rPr><w:t>2026DB  |  Architecture and data-lineage guide</w:t></w:r></w:p></w:hdr>"""

FOOTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:color w:val="64748B"/><w:sz w:val="17"/></w:rPr><w:t>Focused research pipeline  •  </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:color w:val="64748B"/><w:sz w:val="17"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/><w:szCs w:val="21"/><w:color w:val="273444"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="140" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/><w:unhideWhenUsed/></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:uiPriority w:val="99"/><w:semiHidden/><w:unhideWhenUsed/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="120" w:after="240"/><w:keepNext/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="17324D"/><w:sz w:val="58"/><w:szCs w:val="58"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="280"/></w:pPr><w:rPr><w:color w:val="64748B"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="300" w:after="160"/><w:outlineLvl w:val="0"/><w:pBdr><w:bottom w:val="single" w:sz="8" w:space="8" w:color="D97706"/></w:pBdr></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="17324D"/><w:sz w:val="38"/><w:szCs w:val="38"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="260" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="1F4E78"/><w:sz w:val="29"/><w:szCs w:val="29"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="220" w:after="90"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:color w:val="2E7D6B"/><w:sz w:val="23"/><w:szCs w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="240" w:right="120"/><w:spacing w:before="80" w:after="120"/><w:shd w:val="clear" w:fill="F1F5F9"/></w:pPr><w:rPr><w:rFonts w:ascii="Cascadia Mono" w:hAnsi="Cascadia Mono"/><w:color w:val="334155"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:basedOn w:val="DefaultParagraphFont"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="ArchitectureTable"><w:name w:val="Architecture Table"/><w:basedOn w:val="TableNormal"/><w:uiPriority w:val="99"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="CBD5E1"/><w:left w:val="single" w:sz="4" w:color="CBD5E1"/><w:bottom w:val="single" w:sz="4" w:color="CBD5E1"/><w:right w:val="single" w:sz="4" w:color="CBD5E1"/><w:insideH w:val="single" w:sz="4" w:color="CBD5E1"/><w:insideV w:val="single" w:sz="4" w:color="CBD5E1"/></w:tblBorders><w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblStylePr w:type="band1Horz"><w:tcPr><w:shd w:val="clear" w:fill="F5F7F9"/></w:tcPr></w:tblStylePr></w:style>
</w:styles>"""


LENS_DETAILS = {
    "digital_integration": {
        "status": "Active — all four registered UPI and GST series have observations.",
        "sources": [
            ("NPCI UPI Product Statistics", "Monthly period, banks live, UPI volume (million transactions), and value (₹ crore). Banks live is retained in raw evidence but is not yet a published series.", "https://www.npci.org.in/product/upi/product-statistics"),
            ("NPCI structured product-statistics APIs", "Product/tab metadata and paginated monthly observations by financial-year range.", "https://www.npci.org.in/api/product-statistic/tabs"),
            ("World Bank Indicators API — SP.POP.TOTL", "Annual India population used as the monthly per-capita denominator.", "https://api.worldbank.org/v2/country/IND/indicator/SP.POP.TOTL?format=json"),
            ("World Bank Indicators API — NY.GDP.MKTP.CN", "Annual nominal GDP in current local currency used for the payment-turnover ratio.", "https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CN?format=json"),
            ("Ministry of Finance / PIB GST history", "Fiscal-year gross GST revenue for FY2020–21 through FY2023–24, reported in lakh crore.", "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/jul/doc202471346101.pdf"),
            ("GST Portal March 2025 collection report", "Exact provisional gross GST totals for FY2023–24 and FY2024–25, including CGST, SGST, IGST and cess.", "https://tutorial.gst.gov.in/downloads/news/approved_monthly_gst_data_for_publishing_mar_2025.pdf"),
            ("RBI Handbook, Table 1", "Matching fiscal-year nominal GDP at current prices, with RBI/NSO observation status retained.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23175"),
        ],
        "method": "The NPCI extractor first obtains the official tab definitions, then requests every advertised year range and page. Calendar-year World Bank denominators are joined without interpolation. For tax capacity, official PDFs are checksum-archived and parsed; fiscal-year gross-GST YoY growth is calculated and matching fiscal-year nominal-GDP YoY growth is subtracted. Exact GST Portal totals supersede rounded PIB totals where both cover the same year, and the provisional label is retained.",
        "interpretation": "UPI series describe payment intensity, ticket size and network turnover relative to the economy. The GST growth gap says whether gross receipts grew faster or slower than nominal GDP in percentage points; it is not a tax-buoyancy estimate because it does not control for rate, base, import, refund, enforcement or timing changes. None of these series identifies a causal effect on formalisation.",
        "special": "UPI value/GDP is a turnover-to-value-added comparison: payments can circulate the same rupee many times. The GST gap is a difference between two growth rates, so +2 means GST grew two percentage points faster than nominal GDP, not that GST revenue equals 2% of GDP.",
    },
    "government_investment": {
        "status": "Active — all six registered series have observations.",
        "sources": [
            ("Union Budget — Budget at a Glance, statement 6", "Across budget editions 2018–19 to 2026–27: actual, original Budget Estimate, Revised Estimate and current Budget Estimate for capital and total expenditure.", "https://www.indiabudget.gov.in/doc/Budget_at_Glance/bag6.pdf"),
            ("RBI Handbook, Table 1: Macro-economic aggregates at current prices", "Annual nominal GDP denominators, including the published observation status.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23175"),
        ],
        "method": "Budget vintages are reconstructed from multiple editions instead of taking only the newest table. In a normal four-column edition, the pipeline associates edition−2 with actual, edition−1 with its original BE and RE, and the current year with BE. This preserves what was originally planned and prevents later estimates from silently replacing it. PDF layout, statement label, year headers and accounting identities are guarded before values are accepted.",
        "interpretation": "The ratios separate scale, composition and execution: CapEx/GDP measures macro effort, CapEx/total expenditure measures budget composition, and actual/BE measures delivery relative to the original plan. None measures asset quality, completion, procurement efficiency or the social return of a project.",
        "special": "An execution ratio above 100% means actual expenditure exceeded the original BE. It may reflect supplementary appropriations or reclassification; it is not automatically evidence of superior administrative efficiency.",
    },
    "private_investment": {
        "status": "Active — national-accounts, lagged public-CapEx and RBI OBICUS capacity-utilisation series are populated.",
        "sources": [
            ("MoSPI new GDP series, base year 2022–23", "Statement 1.1B nominal GDP; Statement 7.1B total GFCF, private non-financial corporation GFCF, and private financial corporation GFCF.", "https://mospi.gov.in/uploads/release_calendar/1772190058170_Press_Note_on_New_Series_of_GDP_Estimates_with_Base_Year_2022-23_27022026.pdf"),
            ("Government-investment processed bundle", "Actual central-government CapEx/GDP, shifted one fiscal year forward for visual comparison.", "https://www.indiabudget.gov.in/"),
            ("RBI OBICUS", "Quarterly number of responding companies plus unadjusted and seasonally adjusted aggregate manufacturing capacity utilisation. The published series uses the unadjusted aggregate.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23808"),
        ],
        "method": "Private corporate GFCF is constructed as private non-financial corporation GFCF plus private financial corporation GFCF. It is divided by nominal GDP or total GFCF from the same release and base-year system. The public-CapEx comparison is an explicit one-fiscal-year lag. The OBICUS extractor discovers RBI's latest quarterly publication, selects Table 1 by title and exact headers, and publishes the unadjusted capacity-utilisation column with fiscal-quarter boundaries.",
        "interpretation": "The investment ratios show how much fixed-capital formation is attributed to private corporations and its share of economy-wide investment. OBICUS adds a survey measure of how intensively responding manufacturers use installed capacity. It is not the investment rate, and changes may reflect demand or production schedules rather than new capacity. A visual association with lagged public CapEx remains hypothesis-generating, not causal.",
        "special": "MoSPI numerators and denominators stay within one base-year vintage. OBICUS is a voluntary survey, its respondent count changes by quarter, and the published unadjusted series can contain seasonality; the seasonally adjusted column is retained in extraction evidence but is not silently substituted.",
    },
    "fiscal_capacity": {
        "status": "Active — all five registered series have observations with actual, revised and budget statuses retained.",
        "sources": [
            ("RBI Handbook, Table 239: Select debt indicators", "Central liabilities/GDP and adjusted combined Centre-plus-states liabilities/GDP.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23413"),
            ("RBI Handbook, Table 236: Select fiscal indicators", "Gross primary deficit/GDP, revenue receipts/GDP, interest payments/GDP and total expenditure/GDP.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23410"),
        ],
        "method": "Published debt ratios are retained directly. The primary balance reverses the sign of RBI’s gross primary deficit so deficits appear negative. Interest burden ratios divide interest-payments/GDP by revenue-receipts/GDP or total-expenditure/GDP; the shared GDP denominator cancels algebraically. Fiscal-year labels and observation statuses are preserved.",
        "interpretation": "Debt/GDP is a stock relative to annual output; the primary balance and interest burden are flows. General-government debt combines Centre and states, while the interest ratios are central-government measures. The dashboard intentionally presents both rather than implying identical institutional coverage.",
        "special": "No universal debt threshold is encoded. Sustainability depends on nominal growth, effective interest rates, maturity, currency denomination, contingent liabilities and expenditure quality as well as the headline debt ratio.",
    },
    "external_competitiveness": {
        "status": "Active — monthly REER/export and quarterly current-account series are populated.",
        "sources": [
            ("RBI Handbook, Table 206: 40-currency NEER/REER", "Monthly trade-weighted REER index, 2015–16=100.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23380"),
            ("RBI Handbook, Table 192: Oil and non-oil trade", "Monthly non-oil exports in US dollars.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23366"),
            ("RBI Handbook, Table 195: Balance of payments", "Quarterly merchandise net and invisibles net, in ₹ crore, used to construct the current account.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23369"),
            ("RBI Handbook, Table 155: Quarterly GDP", "Quarterly nominal GDP at current prices in ₹ crore.", "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23329"),
        ],
        "method": "The REER level is published directly. Its deviation is computed only after a complete trailing 60-month window. Current account equals merchandise net plus invisibles net and is divided by quarterly nominal GDP. Non-oil export growth compares each month with the exact month 12 months earlier; no adjacent-month substitute is used.",
        "interpretation": "The lens combines relative prices, external balances and trade performance. REER is an index, not a currency price forecast. A positive current-account value is a surplus. Nominal export growth contains both quantity and price effects and can be dominated by base effects, as in the early pandemic comparison.",
        "special": "REER above 100 means the index is above its 2015–16 base, not that the rupee is a specific percentage overvalued. Likewise, deviation from the five-year mean is a historical reference rather than an estimate of fair value.",
    },
    "human_capital": {
        "status": "Active — higher-education participation and two PLFS labour-market conversion measures are populated.",
        "sources": [
            ("AISHE Final Report 2023–24, Table 47", "All-India, all-category, both-sex Gross Enrolment Ratio for ages 18–23.", "https://cdnbbsr.s3waas.gov.in/s392049debbe566ca5782a3045cf300a3c/uploads/2026/07/202607131602421770.pdf"),
            ("PLFS Annual Report 2025, Statements 7 and 17", "Rural-plus-urban persons aged 15+, usual status (ps+ss): secondary-and-above unemployment rate and regular wage/salaried share among workers.", "https://www.mospi.gov.in/uploads/publications_reports/publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_PLFS_2025_F_REV_29052026.pdf"),
        ],
        "method": "Published all-India aggregates are extracted with their exact population, age and activity-status definitions. Academic-year GER is represented at the fiscal-style period end while its period label remains explicit. PLFS annual values use the published usual-status definition; the pipeline does not reconstruct an alternative denominator from summary tables.",
        "interpretation": "GER measures participation relative to the official age cohort, not completion or learning. Educated unemployment is conditional on being in the labour force, and regular salaried status is an employment relationship rather than a direct measure of formality, earnings or job quality.",
        "special": "The planning concept initially referred to graduate unemployment. The stable published PLFS series available in the selected report is secondary-and-above. The registry was renamed to match the evidence instead of publishing a more attractive but false label.",
    },
    "capital_resilience": {
        "status": "Partial — two archived NSE trading days are available; rolling windows and shock-event estimates require continued daily accumulation.",
        "sources": [
            ("NSE FII/FPI & DII trading activity report", "Current trading date; DII and FII/FPI gross purchases, gross sales and net activity in ₹ crore.", "https://www.nseindia.com/reports/fii-dii"),
            ("NSE report API", "Structured current-day provisional observations used after establishing the NSE web session.", "https://www.nseindia.com/api/fiidiiTradeReact"),
        ],
        "method": "The extractor loads the official report page to establish the required session and cookies, then fetches the structured endpoint. It verifies buy minus sell against reported net and requires both investor categories. Every day is archived immutably. The builder scans all archived days and chooses the latest retrieval for a duplicated date/category before monthly aggregation.",
        "interpretation": "Monthly net flows show exchange-reported buying minus selling by domestic and foreign institutions. Rolling sums require 12 consecutive months. The offset ratio is defined only when FPI net flow is negative; null in other months is a domain condition, not missing extraction.",
        "special": "The public endpoint is a current-day feed rather than a historical download. The current month is incomplete and provisional. NSE FII/FPI activity also differs in coverage from final NSDL custodial flow data, so the names must not be treated as interchangeable.",
    },
}


def load_artifact(bundle_key: str) -> dict:
    path = PROJECT_ROOT / "data" / "processed" / FOCUSED_BUNDLES[bundle_key].output_path
    return json.loads(path.read_text(encoding="utf-8"))


def availability_for(bundle_key: str) -> str:
    catalogue = json.loads((PROJECT_ROOT / "frontend" / "public" / "data" / "catalogue.json").read_text(encoding="utf-8"))
    return catalogue["assets"][bundle_key.replace("_", "-")]["availability"]


def series_stats(payload: dict, key: str) -> tuple[int, int, str, str, object, str]:
    values = payload["series"][key]["values"]
    populated = [item for item in values if item.get("value") is not None]
    if not values:
        return 0, 0, "—", "—", "—", "—"
    if not populated:
        return len(values), 0, values[0].get("date", "—"), values[-1].get("date", "—"), "—", "—"
    latest = populated[-1]
    return len(values), len(populated), values[0].get("date", "—"), values[-1].get("date", "—"), latest.get("value", "—"), latest.get("date", "—")


def format_value(value: object, unit: str) -> str:
    if not isinstance(value, (float, int)):
        return str(value)
    if unit == "percent":
        return f"{value:,.2f}%"
    if unit == "percentage_points":
        return f"{value:,.2f} pp"
    if unit == "INR":
        return f"₹{value:,.2f}"
    if unit == "INR_crore":
        return f"₹{value:,.2f} crore"
    if unit == "ratio":
        return f"{value:,.3f}"
    if unit == "index":
        return f"{value:,.2f}"
    return f"{value:,.4f}"


def add_title_page(doc: DocxBuilder) -> None:
    doc.add_paragraph("ARCHITECTURE  /  DATA LINEAGE  /  INTERPRETATION", runs=[doc.run("ARCHITECTURE  /  DATA LINEAGE  /  INTERPRETATION", bold=True, color="D97706", size=19)], space_before=720, space_after=300)
    doc.add_paragraph("Focused India Research Pipeline", style="Title")
    doc.add_paragraph("Architecture, data sources, transformations, publication and frontend guide", style="Subtitle")
    doc.add_callout("Purpose", "A technical and analytical account of the architecture as implemented: what is collected, how it is converted into research statistics, how quality gates work, how the static frontend consumes the result, and how every measure should—and should not—be interpreted.")
    doc.add_paragraph("", space_after=600)
    doc.table(
        ["Document control", "Value"],
        [
            ["Version", "1.2"],
            ["Implementation snapshot", GENERATED_ON.strftime("%d %B %Y")],
            ["Repository", str(PROJECT_ROOT)],
            ["Scope", "Seven focused research lenses, registered evidence foundations and retained legacy compatibility"],
            ["Authoritative inputs", "Implemented registry, builders, schemas, processed artifacts and frontend source"],
            ["Intended readers", "Researchers, data engineers, reviewers and frontend maintainers"],
        ],
        widths=[2400, 6600],
    )
    doc.add_paragraph(
        runs=[
            doc.run("This is generated documentation. ", bold=True, color="64748B"),
            doc.run(
                "Coverage counts and latest observations are read from the current processed JSON files; "
                "rerun the generator after a material pipeline change.",
                color="64748B",
            ),
        ]
    )


def add_contents(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("Contents", 1, bookmark="contents")
    contents = [
        "1. Executive summary and current status",
        "2. Architectural principles and system boundaries",
        "3. End-to-end processing pipeline",
        "4. Data contracts, canonical model and quality gates",
        "5–11. The seven research lenses: sources, formulas and meaning",
        "12. Static frontend architecture and user experience",
        "13. Operations, rebuilds, testing and failure behaviour",
        "14. Known gaps and next implementation priorities",
        "15. Source register, glossary and repository map",
    ]
    for item in contents:
        doc.add_bullet(item)
    doc.add_callout("Navigation", "Headings use Word’s outline levels. Word can generate or refresh a detailed table of contents from Heading 1–3 styles if a field-based TOC is preferred.", color="2E7D6B", shade="ECFDF5")


def add_executive_summary(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("1. Executive summary and current status", 1, bookmark="executive_summary")
    doc.add_paragraph("The new architecture is a contract-driven, evidence-preserving publication pipeline. Provider-specific code is confined to acquisition. Every accepted statistic is normalised into a provider-neutral observation with date, entity, unit, frequency, status and provenance. Analytical transforms produce named research series. Only schema-valid, quality-checked bundles are written to the processed layer and promoted into the frontend’s public data directory.")
    doc.add_paragraph("The website is deliberately static at runtime: the browser loads a catalogue and versioned JSON assets rather than querying source institutions or a bespoke application API. This makes deployments cheap and inspectable, while moving strictness to build time. The catalogue defines navigation, availability, component choice, default visible series, formatting, staleness and source/methodology display.")
    doc.add_paragraph("A separate evidence layer now estimates and publishes two fiscal analyses and one UPI trend analysis under versioned specifications. Registered loaders, time-aware alignment and deterministic eligibility gates feed OLS models with Newey–West HAC uncertainty, predeclared diagnostics, robustness checks, Benjamini–Hochberg adjustment and deterministic grading. Source-artifact SHA-256 digests and required code/software versions make each report traceable to its exact inputs.")
    doc.add_callout("Central analytical rule", "The project distinguishes a reported statistic, a derived statistic and an interpretation. A formula can make two inputs comparable; it cannot by itself establish causality, welfare effects, project quality or fair value.")
    doc.add_callout("Evidence milestone", f"Specification registry {SPECIFICATION_REGISTRY_VERSION}, estimation, the evidence-report schema, cross-field validation, atomic export and validated promotion are complete for fiscal capacity and digital integration. Eligibility counts still describe readiness; coefficients and grades appear only in the separate evidence reports.", color="2E7D6B", shade="ECFDF5")

    rows = []
    for key, bundle in FOCUSED_BUNDLES.items():
        payload = load_artifact(key)
        total = len(bundle.series)
        populated = sum(any(v.get("value") is not None for v in payload["series"][series.key]["values"]) for series in bundle.series)
        rows.append([
            bundle.label,
            availability_for(key).upper(),
            f"{populated}/{total}",
            f"{payload['metadata']['start_date']} → {payload['metadata']['end_date']}",
        ])
    doc.table(["Research lens", "Catalogue status", "Series populated", "Published coverage"], rows, widths=[3600, 1500, 1500, 2400])
    doc.add_paragraph("“Active” means every registered series has at least one non-null observation. “Partial” means the artifact is valid and publishable but at least one registered series is not yet populated. “Planned” is used when no promoted artifact exists. These states concern delivery, not analytical confidence.")

    doc.add_heading("What changed from the legacy arrangement", 2)
    for item in [
        "Research lenses and series definitions now live in a typed registry rather than being inferred from filenames or component code.",
        "Raw downloads are immutable, dated and checksum-addressed; processed files are reproducible publications rather than the first place evidence appears.",
        "Actual, provisional, revised, estimate and budget observations are explicit statuses. Indian fiscal years are represented by inclusive start/end dates and an unambiguous FY label.",
        "Transforms, validation, export and promotion are separate layers. A failed run cannot overwrite the last known-good public artifact.",
        "The frontend is catalogue-driven, with one scrollable page per research lens and an always-available sidebar. It has no hard-coded legacy product identity.",
        "Legacy World Bank and market sections remain available for manual review and comparison; they were not deleted and are not silently treated as focused-pipeline outputs.",
    ]:
        doc.add_bullet(item)


def add_architecture(doc: DocxBuilder) -> None:
    doc.add_heading("2. Architectural principles and system boundaries", 1, bookmark="architecture")
    principles = [
        ("Scope before collection", "Each bundle begins with a research question, primary/supporting series, units, frequency, definitions, formulas and limitations in scripts/config/focused_indicators.py."),
        ("Evidence is immutable", "Source responses and PDFs are stored under data/raw/<source>/<retrieval-date-or-period>/ with content checksums. A newer retrieval creates evidence; it does not mutate the old evidence."),
        ("Provider-neutral analysis", "Extractors may understand NPCI APIs, RBI tables, Budget PDFs or NSE sessions; transforms operate on CanonicalRecord objects rather than provider response shapes."),
        ("Null has meaning", "Unavailable denominators, incomplete rolling windows and inapplicable conditional ratios remain null. The pipeline does not interpolate by default, and the chart does not connect gaps."),
        ("Publication is gated", "Record checks, output checks, JSON Schema validation and atomic writes are required before promotion."),
        ("Static delivery, strong build", "Runtime is a catalogue plus JSON assets. TypeScript, schema/adapter compatibility and asset existence are checked during the frontend build."),
        ("Interpretation travels with data", "The asset contains sources, methodology and notes; the catalogue carries definitions, limitations and presentation choices into each metric panel."),
        ("Specify before estimation", "Evidence questions, transformations, lag rules, exceptional periods, uncertainty estimators and robustness checks are versioned before results are calculated."),
    ]
    doc.table(["Principle", "Implemented consequence"], principles, widths=[2200, 6800])

    doc.add_heading("System boundary", 2)
    doc.add_paragraph("Inside the repository boundary are source acquisition, raw archiving, parsing, normalisation, transformations, validation, export, promotion, catalogue generation and static rendering. External institutions remain the systems of record. The pipeline does not modify them, infer unpublished values, or provide a live transactional API.")
    doc.add_callout("Not a real-time system", "A metric is only as current as its source and scheduled build. Staleness badges describe publication recency; they do not guarantee that an institution has released a newer underlying observation.", color="A33D4A", shade="FFF1F2")

    doc.add_heading("Repository responsibility map", 2)
    doc.table(
        ["Location", "Responsibility", "Key rule"],
        [
            ["scripts/config/", "Typed indicator registry, contracts, event definitions and project paths", "Economic meaning is declared before provider details"],
            ["scripts/extractors/", "HTTP/session handling, PDF/table/API parsing, raw snapshot creation", "Provider quirks stay at the edge"],
            ["scripts/models/", "Canonical records, fiscal periods and observation statuses", "One provider-neutral internal language"],
            ["scripts/transforms/", "Ratios, growth, rolling windows, joins and lags", "Formula and missing-data policy are explicit"],
            ["scripts/analysis/", "Registered artifact loading, status-aware alignment and pre-estimation eligibility", "No unregistered series or future-period values enter a sample"],
            ["scripts/build_*.py", "Bundle-specific orchestration from source to candidate payload", "One builder per analytical product"],
            ["scripts/validators/", "Record and payload quality rules plus JSON Schema checks", "Reject before publication"],
            ["scripts/exporters/", "Deterministic, strict, atomic JSON publication", "No NaN; last good file survives failure"],
            ["schemas/", "Backend JSON contracts", "Payload shape is versionable and testable"],
            ["docs/decisions/", "Versioned analytical-policy decisions", "Post-result changes require a new recorded specification version"],
            ["data/raw/", "Immutable source evidence", "Never edit to make a transform pass"],
            ["data/processed/", "Validated research bundles", "Authoritative generated analytical artifacts"],
            ["frontend/public/data/", "Promoted browser assets, schemas and catalogue", "Only validated artifacts reach users"],
            ["frontend/src/", "Navigation, loading, guards, adapters, charts and interpretation UI", "Presentation does not recompute research statistics"],
            ["tests/", "Unit, schema, transformation and regression coverage", "Guard formula and contract behaviour"],
        ],
        widths=[2200, 4000, 2800],
    )


def add_pipeline(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("3. End-to-end processing pipeline", 1, bookmark="pipeline")
    doc.add_paragraph("The full path is shown below. The arrows are publication boundaries, not merely function calls. Each boundary reduces ambiguity and gives failures a defined place to stop.")
    doc.add_code("Research registry → provider extractor → immutable raw snapshot → canonical records → analytical transforms → bundle payload → quality + schema validation → atomic processed JSON → promotion → catalogue → browser guard + adapter → chart and interpretation panels")
    stages = [
        ("1. Register", "Define bundle question, series key, label, unit, frequency, source field, definition, formula, limitation, primary/supporting role and output contract.", "scripts/config/focused_indicators.py"),
        ("2. Acquire", "Call only official institutional sources. Handle API pagination, sessions, table discovery, PDF layout and request metadata.", "scripts/extractors/"),
        ("3. Archive", "Write the unmodified response into a dated source directory with a checksum-bearing filename and retrieval metadata.", "data/raw/"),
        ("4. Parse", "Select named tables/statements and validate structural expectations such as headers, units, categories and accounting identities.", "extractor modules"),
        ("5. Canonicalise", "Convert parsed facts into CanonicalRecord instances with explicit date/entity/indicator/value/unit/frequency/source/status and provenance.", "scripts/models/canonical.py"),
        ("6. Transform", "Join compatible vintages and periods; compute declared ratios, lags, growth rates and complete-window rolling statistics.", "scripts/transforms/"),
        ("7. Assemble", "Create the dated_multi_series payload with metadata, ordered named series and dated values.", "scripts/build_*.py"),
        ("8. Validate", "Check non-emptiness where required, uniqueness, ordering, finiteness, frequency, bounds, coverage metadata and Draft 2020-12 schema.", "scripts/validators/ and schemas/"),
        ("9. Publish", "Serialise with allow_nan=False to a temporary file, flush and fsync it, then atomically replace the target.", "scripts/exporters/json_export.py"),
        ("10. Promote", "Revalidate a processed artifact and atomically copy it to frontend/public/data at the registered path.", "scripts/promote_processed_data.py"),
        ("11. Catalogue", "Insert/update seven lens sections and assets, derive availability and staleness, retain unrelated legacy sections, and validate catalogue schema.", "scripts/sync_focused_catalogue.py"),
        ("12. Deliver", "Load catalogue/assets with React Query, assert schema-to-component compatibility, adapt data to rows, and render chart, latest reading, source and methodology.", "frontend/src/"),
    ]
    doc.table(["Stage", "What happens", "Implementation"], stages, widths=[1500, 5300, 2200], font_size=17)

    doc.add_heading("Registered evidence branch", 2)
    doc.add_paragraph("Evidence production consumes validated processed bundles; it does not bypass the source-to-publication path above. The implemented branch is:")
    doc.add_code("Frozen evidence specification → registered processed-artifact loader → status filtering → transformations and lagging → explicit date alignment → exclusions ledger → eligibility gates → frozen design matrix → OLS + HAC inference → diagnostics + robustness → family adjustment + grading → evidence-report validation → atomic publication")
    doc.add_paragraph("Only an eligible prepared sample reaches estimation. Failed gates become a structured insufficient-data result rather than a best-effort regression. Eligible samples pass through the frozen design, HAC inference, diagnostics, robustness, family adjustment and grading; every completed report then passes the evidence-report schema and semantic validator before atomic export and promotion.")

    doc.add_heading("Acquisition patterns by source type", 2)
    doc.add_heading("Structured APIs: NPCI, World Bank and NSE", 3)
    doc.add_paragraph("NPCI discovery metadata identifies product tabs, year ranges and filters before observations are requested. The World Bank API supplies machine-readable annual denominators; a transient API failure may reuse the newest immutable raw snapshot with an explicit runtime warning. NSE requires a browser-like session established from its official report page before the current-day JSON endpoint is called. Pagination/range completeness, response categories and numerical identities are validated rather than assumed.")
    doc.add_heading("RBI Handbook HTML tables", 3)
    doc.add_paragraph("The RBI Handbook extractor discovers official table links and parses substantive HTML tables. OBICUS uses the same evidence-first pattern against RBI's quarterly-publication index, then selects Table 1 Capacity Utilisation by title and exact headers. A dependency-free XLSX reader also exists, but live unattended builds use official HTML where the rbidocs workbook host may block automated retrieval. Table identity, headers, units and row identity are extraction contracts.")
    doc.add_heading("Official statistical and Budget PDFs", 3)
    doc.add_paragraph("The raw PDF is checksum-archived first. pdftotext -layout creates a stable positional text representation for parsing. Extractors look for exact statement/table labels and expected year columns, then apply table-specific rules. The GST adapter additionally reconciles a rounded historical PIB series with exact provisional totals from the GST Portal. A visually plausible number from the wrong row is a hard extraction error, not an acceptable approximation.")

    doc.add_heading("Raw evidence and reproducibility", 2)
    for item in [
        "The retrieval timestamp says when the project observed a source; it is not the economic reference period.",
        "The content checksum detects changed bytes and prevents ambiguous overwrites.",
        "The raw response is kept even when only a subset of fields is published, allowing later audit or a new transform without redownloading a superseded source.",
        "Repeated NSE daily retrievals may contain revisions; the monthly accumulator deterministically uses the latest retrieval for a duplicated date/category.",
        "Processed artifacts are generated outputs. Corrections belong in extraction/transform logic or source-vintage selection, not hand edits to JSON.",
    ]:
        doc.add_bullet(item)

    doc.add_heading("Dependency ordering", 2)
    doc.add_paragraph("The complete orchestrator runs digital integration, government investment, private investment, fiscal capacity, external competitiveness, human capital and capital resilience in that order. Government investment precedes private investment because the latter consumes the former’s actual CapEx/GDP series to construct the one-year-lag comparison. After requested builders finish, promotion and catalogue synchronisation run once; the optional frontend build is last.")


def add_contracts(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("4. Data contracts, canonical model and quality gates", 1, bookmark="contracts")
    doc.add_heading("Canonical observation", 2)
    fields = [
        ("date", "Normalised observation date; fiscal/academic periods additionally retain labels and boundaries."),
        ("entity", "Country, market or reporting entity identifier; focused India series normally use IND."),
        ("indicator", "Stable machine key from the registry."),
        ("value", "Finite number or null. Null is never encoded as NaN or an invented zero."),
        ("unit / frequency", "Meaning and periodicity required for safe joins and display."),
        ("source / source_url", "Institutional provenance and official location."),
        ("status", "actual, provisional, revised, estimate or budget."),
        ("period_label", "Human-readable FY or academic-year label when a date alone could mislead."),
        ("is_derived / method", "Whether the value was computed and the declared method."),
        ("retrieved_at / vintage", "When the source was collected and which publication vintage supplied it."),
        ("period_start / period_end", "Inclusive bounds for non-calendar reference periods."),
    ]
    doc.table(["Field", "Why it exists"], fields, widths=[2400, 6600])
    doc.add_paragraph("FiscalPeriod treats FY2024–25 as 1 April 2024 through 31 March 2025 and normally uses the period end as the plotted date. The explicit period label prevents the chart date from being mistaken for a calendar-year observation.")

    doc.add_heading("Published dated_multi_series contract", 2)
    doc.add_paragraph("Every focused bundle currently uses the dated_multi_series schema. It has two layers:")
    doc.add_bullet("metadata: generated_at, one or more source objects, frequency, start_date, end_date, indicator_code, label, default_unit, series_order, is_derived, methodology and note.")
    doc.add_bullet("series: a mapping from stable series key to label, entity, unit, is_derived, optional methodology/source note, and an ordered values array. Each value has date, numeric-or-null value, status and optional period label.")
    doc.add_callout("Provenance boundary", "Canonical records are richer than the chart contract. The published bundle preserves source lists, retrieval time, formulas, status, period labels and limitations, while immutable raw snapshots preserve the full response and exact evidence. Not every record-level raw path or vintage is duplicated into every chart point.")

    doc.add_heading("Other recognised contracts", 2)
    doc.table(
        ["Contract", "Current role", "Frontend adapter"],
        [
            ["annual_country_series", "Retained World Bank country/peer indicators. All countries are visualised by default.", "annualCountryToRows"],
            ["dated_multi_series", "All seven focused bundles with multiple named series and mixed status/period semantics.", "datedSeriesToRows"],
            ["market_performance", "Retained equity-market prices, return and risk measures.", "marketPerformanceToRows"],
            ["event_study", "Schema and event configuration prepared; no live artifact until sufficient institutional-flow history exists.", "Not yet wired as a live catalogue asset"],
            ["evidence_report", "Versioned lens-level analyses, source digests, code/software versions, sample/exclusion metadata, estimates, diagnostics, robustness, eligibility and limitations. Fiscal-capacity and digital-integration reports are published.", "EvidencePanel renders the lens-level contract without a chart adapter"],
        ],
        widths=[2100, 4800, 2100],
    )

    doc.add_heading("Evidence specifications and current pre-estimation readiness", 2)
    doc.add_paragraph(
        "The table below is generated by loading the current processed artifacts through the registered "
        "alignment and eligibility pipeline. Passing means only that a model may be attempted under the "
        "frozen specification; it says nothing about coefficient direction, uncertainty or robustness."
    )
    readiness_rows = []
    for spec in EVIDENCE_SPECS.values():
        prepared = prepare_registered_analysis(spec.key)
        readiness_rows.append([
            spec.label,
            spec.formula,
            f"{prepared.sample.start_date} → {prepared.sample.end_date}",
            f"{len(prepared.sample.rows)} / {prepared.eligibility.required_observations}",
            "PASS" if prepared.eligibility.eligible else "FAIL",
        ])
    doc.table(
        ["Registered analysis", "Frozen model", "Aligned coverage", "Available / required", "Gate"],
        readiness_rows,
        widths=[1900, 3100, 1700, 1400, 900],
        font_size=15,
    )
    doc.add_paragraph(
        "Both fiscal specifications accept actual and revised observations, use fiscal-period-safe lags, "
        "require at least 30 complete observations and register HAC uncertainty with maximum lag two. "
        "Focal terms and their expected directions are frozen: positive lagged debt for the interest-burden "
        "change model, negative lagged primary balance for the debt-change model, and a positive annualised "
        "underlying UPI trend. The UPI specification begins in April 2017, log-transforms transactions per capita, registers "
        "calendar-month effects and a pandemic break, requires at least 36 observations and uses HAC "
        "uncertainty with maximum lag twelve. All three are explicitly associational, not causal."
    )
    doc.add_callout(
        "Exclusions are data",
        "Disallowed statuses, unavailable differences or lags, pre-start observations, null values and "
        "non-positive inputs to logarithms are counted by input and reason. Gaps break differences; the "
        "pipeline does not bridge them or pull a later observation backward.",
        color="2E7D6B",
        shade="ECFDF5",
    )

    doc.add_heading("Published evidence results", 2)
    evidence_rows = []
    for lens_key in ("fiscal_capacity", "digital_integration"):
        evidence_path = PROJECT_ROOT / "data" / "processed" / EVIDENCE_OUTPUT_PATHS[lens_key]
        if not evidence_path.is_file():
            continue
        report = json.loads(evidence_path.read_text(encoding="utf-8"))
        for analysis in report["analyses"]:
            focal = next(item for item in analysis["estimates"] if item["is_focal"])
            failed = [
                item["key"]
                for item in analysis["diagnostics"]
                if item["passed"] is False
            ]
            evidence_rows.append([
                analysis["label"],
                f"{analysis['status']} / {analysis['grade']}",
                (
                    f"{focal['value']:.3f} {focal['unit']}\n"
                    f"95% CI {focal['confidence_interval'][0]:.3f} to "
                    f"{focal['confidence_interval'][1]:.3f}\n"
                    f"adjusted p={focal['adjusted_p_value']:.4g}"
                ),
                ", ".join(failed) if failed else "All registered diagnostics passed",
            ])
    doc.table(
        ["Analysis", "Status / grade", "Registered focal estimate", "Failed diagnostics"],
        evidence_rows,
        widths=[2500, 1700, 3000, 1800],
        font_size=15,
    )
    doc.add_callout(
        "Interpretation boundary",
        "The negative debt/interest-burden coefficient is opposite the registered positive direction and is therefore not support for the claim even though its adjusted p-value is below 0.05. The primary-balance model fails the influence diagnostic. The UPI trend is positive in every registered robustness fit but fails the residual-autocorrelation diagnostic. None of these observational results establishes a policy effect.",
        color="A33D4A",
        shade="FFF1F2",
    )

    doc.add_heading("Quality gates", 2)
    checks = [
        ("Record-level", "Non-empty records where required; no duplicate (entity, indicator, date); expected frequency; recognised status and units."),
        ("Series-level", "Chronological ordering; no duplicate dates; finite numerics; required non-empty series; sensible configured bounds; complete-window rules."),
        ("Metadata", "start_date and end_date must exactly match the payload’s true minimum and maximum dates; series_order must match delivered series."),
        ("Schema", "Draft 2020-12 JSON Schema validation of data bundles and the frontend catalogue."),
        ("Evidence semantics", "Registry identity, analysis order, source coverage, sample dates, confidence intervals, adjusted p-values, insufficiency rules and non-causal language are checked across fields."),
        ("Serialisation", "Strict JSON with allow_nan=False. A NaN or infinity fails publication instead of becoming browser-dependent output."),
        ("Atomicity", "Write temporary file → flush → fsync → os.replace. A failed candidate leaves the previous processed/public file intact."),
        ("Promotion", "Processed input is validated again before reaching frontend/public/data."),
        ("Frontend build", "Catalogue schema, referenced assets, schema/component compatibility, metadata coverage and duplicate keys are checked before Vite emits a deployment."),
    ]
    doc.table(["Gate", "Failure prevented"], checks, widths=[1900, 7100])

    doc.add_heading("Missing data and observation status", 2)
    doc.table(
        ["Representation", "Meaning", "Presentation consequence"],
        [
            ["null", "Unavailable denominator, incomplete rolling window, not-yet-implemented input, or a condition where the metric is undefined.", "Chart gap; connectNulls=false prevents a false bridge."],
            ["0", "A measured zero or a value rounded to zero by the provider—not a missing-value substitute.", "Plotted at the zero line."],
            ["actual", "Published out-turn.", "May still be revised by a later institutional release."],
            ["provisional / revised", "Early publication or explicitly revised value.", "Status remains attached to the observation."],
            ["estimate / budget", "Statistical estimate or fiscal plan.", "Must not be described as realised performance."],
        ],
        widths=[1700, 4700, 2600],
    )


def add_lens(doc: DocxBuilder, key: str, number: int) -> None:
    bundle = FOCUSED_BUNDLES[key]
    detail = LENS_DETAILS[key]
    payload = load_artifact(key)
    doc.add_page_break()
    doc.add_heading(f"{number}. {bundle.label}", 1, bookmark=key)
    doc.add_paragraph(bundle.research_question, runs=[doc.run("Research question  ", bold=True, color="D97706"), doc.run(bundle.research_question)])
    doc.add_callout("Implementation status", detail["status"], color="2E7D6B" if availability_for(key) == "active" else "D97706", shade="ECFDF5" if availability_for(key) == "active" else "FFF7ED")
    doc.add_paragraph(f"Published artifact: data/processed/{bundle.output_path}. Contract: {bundle.contract.value}. Declared frequency: {bundle.frequency}. Artifact coverage: {payload['metadata']['start_date']} to {payload['metadata']['end_date']}.")

    doc.add_heading("Official statistics pulled", 2)
    doc.table(["Source", "Raw statistics used"], [[name, stats] for name, stats, _ in detail["sources"]], widths=[3000, 6000])
    for name, _, url in detail["sources"]:
        doc.add_link("Official link: ", name, url)

    doc.add_heading("Extraction and joining method", 2)
    doc.add_paragraph(detail["method"])

    doc.add_heading("Series produced: transformation and meaning", 2)
    rows = []
    for spec in bundle.series:
        total, populated, start, end, latest, latest_date = series_stats(payload, spec.key)
        formula = spec.transformation or "Published directly; no analytical transform."
        rows.append([
            f"{spec.label}\n[{spec.key}]",
            f"{spec.source_field}\nSource: {spec.source}",
            f"{formula}\nUnit: {spec.unit}; frequency: {spec.frequency}",
            f"{spec.definition}\nLIMIT: {spec.limitation}",
        ])
    doc.table(["Published series", "Input statistic(s)", "Transformation", "What it represents"], rows, widths=[2200, 2200, 2300, 2300], font_size=16)

    doc.add_heading("Current artifact coverage and latest populated value", 2)
    coverage_rows = []
    for spec in bundle.series:
        total, populated, start, end, latest, latest_date = series_stats(payload, spec.key)
        coverage_rows.append([
            spec.label,
            f"{populated}/{total}",
            f"{start} → {end}" if total else "No rows yet",
            f"{format_value(latest, spec.unit)} on {latest_date}" if populated else "Not populated",
        ])
    doc.table(["Series", "Non-null / rows", "Stored date span", "Latest non-null observation"], coverage_rows, widths=[2700, 1500, 2300, 2500], font_size=17)

    doc.add_heading("How to interpret the lens", 2)
    doc.add_paragraph(detail["interpretation"])
    doc.add_callout("Critical reading note", detail["special"], color="A33D4A", shade="FFF1F2")
    doc.add_paragraph(bundle.limitation, runs=[doc.run("Bundle-level limitation  ", bold=True), doc.run(bundle.limitation)])


def add_frontend(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("12. Static frontend architecture and user experience", 1, bookmark="frontend")
    doc.add_paragraph("The React/Vite frontend is a reader of published contracts, not a second analytics engine. It never calls NPCI, RBI, MoSPI, NSE or World Bank from the browser and does not recalculate the research metrics. This isolates source instability from user sessions and ensures every viewer sees the same validated artifact version.")
    doc.add_code("Browser → /data/catalogue.json → selected asset path → runtime payload guard → contract adapter → Recharts rows → metric chart + latest reading + source/methodology")

    doc.add_heading("Routes and navigation", 2)
    doc.table(
        ["Route/component", "User experience"],
        [
            ["/  · DashboardPage", "A restrained landing page summarises the available research lenses without slogan-heavy branding."],
            ["/research/:sectionId  · ResearchLensPage", "One page per research lens. All metrics are stacked vertically; users can scroll through them or use metric jump links."],
            ["Layout + Sidebar", "The research-lens sidebar is available from every page. It is generated from catalogue sections, so navigation changes with the data registry rather than a separate menu file."],
            ["EvidencePanel", "For lenses with a valid evidence_asset_id, appears above the metric stack and renders full textual status, focal uncertainty, diagnostics, robustness, method and limitations."],
            ["MetricPanel", "Shows definition, status/staleness, chart, latest selected reading, limitation, sources and methodology."],
            ["Planned/Loading/Error panels", "Catalogue availability and query state are explicit rather than rendered as an empty chart."],
        ],
        widths=[3000, 6000],
    )

    doc.add_heading("Catalogue as the frontend control plane", 2)
    doc.add_paragraph("frontend/public/data/catalogue.json maps a human research hierarchy to physical assets. For every asset it declares the data path, schema path/name, expected frequency, stale-after threshold, cache strategy, version, availability and description. For every indicator view it declares component/chart type, axis, default-visible keys, value formatting, controls, zero line and whether source/methodology panels are shown.")
    doc.table(
        ["Catalogue decision", "Current rule"],
        [
            ["Availability", "active if every registered series has a non-null value; partial if the valid artifact has gaps; planned if no promoted artifact exists."],
            ["Staleness threshold", "Monthly 45 days; annual 450 days; mixed 120 days."],
            ["Focused default visibility", "One registry-configured series for each metric panel, even though the shared artifact contains the other series in that lens."],
            ["Lens evidence", "Only an existing, semantically validated evidence report creates evidence_asset_id. Evidence is not represented as a time-series indicator or recomputed in the browser."],
            ["Country comparison default", "annual_country_series charts select India and every available peer by default, satisfying the all-countries-on-load requirement."],
            ["Zero line", "Enabled for signed balances, deviations, growth and net-flow measures where direction around zero is analytically important."],
            ["Legacy preservation", "Focused sections are inserted first. Unrelated existing sections are retained and their order is shifted; deletion requires an explicit migration decision."],
        ],
        widths=[2600, 6400],
    )

    doc.add_heading("Loading, caching and guards", 2)
    doc.add_paragraph("useCatalogue loads /data/catalogue.json with React Query. useIndicatorData does not issue a request for planned assets. useEvidenceData separately loads lens-level evidence and applies the evidence runtime guard. For a delivered asset, the version is included in the query identity/cache-busting path and the fetch uses revalidation/no-cache semantics. Loading and network/schema failures are rendered in place.")
    doc.add_paragraph("Before rendering, runtimeGuards identifies and checks the supported payload family. assertAdapterMatchesSchema prevents, for example, an annual-country component from receiving a dated-multi-series asset. The three adapters then produce the common row shape expected by ChartView:")
    for item in [
        "annualCountryToRows: pivots annual country observations by year and entity; country labels are resolved for the legend.",
        "datedSeriesToRows: pivots every named series by date, retaining nulls as chart gaps.",
        "marketPerformanceToRows: selects the configured market field and pivots dates by market.",
    ]:
        doc.add_bullet(item)
    doc.add_paragraph("ChartView uses Recharts lines with connectNulls=false. India is visually emphasised in country comparisons; every peer remains visible by default. A focused MetricPanel passes its catalogue default_visible key, so each vertically stacked metric starts with the statistic named by that panel rather than drawing all differently scaled series together.")
    doc.add_paragraph("EvidencePanel deliberately has no chart adapter. Status labels spell out not-supported, mixed, failed-diagnostics or supported states; failed diagnostics are surfaced before the collapsed technical tables. Readers can expand all estimates, confidence intervals, raw/adjusted p-values, diagnostics, robustness fits, formula, causal flag and provenance.")

    doc.add_heading("Build-time validation and deployment", 2)
    doc.add_paragraph("The frontend build validates catalogue structure, every active/partial asset, both evidence reports, schema references, metadata coverage, duplicate identities and component/schema compatibility before TypeScript and Vite compilation. The result is a static dist directory suitable for ordinary static hosting. The previous build completed successfully; the only noted warning was a roughly 655 kB minified JavaScript chunk, a performance optimisation opportunity rather than a correctness failure.")
    doc.add_callout("Why static", "A static site removes database and API availability from the reader’s critical path, makes each publication inspectable, and allows a deployment to be reproduced from committed code plus raw evidence. Its trade-off is that freshness depends on scheduled builds and promotion.")


def add_operations(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("13. Operations, rebuilds, testing and failure behaviour", 1, bookmark="operations")
    doc.add_heading("Standard commands", 2)
    doc.add_paragraph("Run all focused builders, promote their artifacts, refresh the catalogue and compile the frontend:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_focused_pipeline.py --frontend-build")
    doc.add_paragraph("Run only named bundles while retaining dependency order, then promote and refresh the catalogue:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_focused_pipeline.py human_capital capital_resilience")
    doc.add_paragraph("Regenerate this document after architecture or data changes:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 python3 scripts/generate_architecture_docx.py")
    doc.add_paragraph("Backend and frontend verification:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests\ncd frontend && npm run build")
    doc.add_paragraph("Inspect registered samples and eligibility without estimating coefficients:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_evidence_readiness.py")
    doc.add_paragraph("Rebuild, validate and promote the registered evidence reports using the project environment:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/build_evidence_reports.py --promote")
    doc.add_paragraph("Independently reproduce the main estimates, diagnostics and grades through the review code path:")
    doc.add_code("PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/review_evidence_reports.py")

    doc.add_heading("What happens on failure", 2)
    doc.table(
        ["Failure point", "Expected behaviour", "Operator response"],
        [
            ["Network/source unavailable", "Builder fails before candidate publication; existing processed/public asset remains.", "Inspect source availability and raw retrieval logs; do not edit public JSON."],
            ["Source layout changed", "Header/table/identity guard rejects the parse.", "Archive evidence, update parser and add a regression fixture."],
            ["Missing denominator", "Derived observation is null or absent according to the transform contract.", "Confirm the release calendar; never interpolate silently."],
            ["Quality/schema failure", "Atomic exporter does not replace the target.", "Fix contract, transform or source mapping; rerun validation."],
            ["Promotion failure", "Processed candidate may exist, but the browser keeps the last valid promoted artifact.", "Resolve schema/metadata issue before repromotion."],
            ["Frontend build failure", "No deployable static build should be released.", "Correct catalogue path, schema/adapter mismatch or TypeScript error."],
        ],
        widths=[2200, 4200, 2600],
    )

    doc.add_heading("Testing posture", 2)
    doc.add_paragraph("At the implementation snapshot, the complete project environment reported 61 passing backend tests. The frontend TypeScript/Vite build and static-data validation also passed, validating 22 catalogue assets, two evidence reports and 13 sections. Tests cover canonical periods/status, registry contracts, formulas and rolling-window behaviour, schema validation, exporter atomicity, focused builders/catalogue logic, evidence catalogue registration, source-specific GST/OBICUS parsing fixtures, registered evidence loading, no-look-ahead alignment, eligibility gates, OLS/HAC estimation, rank rejection, robustness design, evidence-report semantics and non-destructive promotion. The separate numerical review reproduced every main estimate, interval, p-value adjustment, diagnostic flag, status and grade at tolerance 1e-9. These checks do not replace external peer review.")

    doc.add_heading("Recommended operating cadence", 2)
    for item in [
        "Daily: archive NSE FII/FPI and DII current-day activity after the trading report is available; alert on missing category or accounting mismatch.",
        "Monthly: rebuild NPCI UPI, RBI monthly REER/trade and accumulated institutional-flow bundles; review source revisions and staleness.",
        "Quarterly: rebuild RBI balance-of-payments/GDP and OBICUS capacity utilisation after each official release.",
        "Annual/release-driven: rebuild Budget vintages, RBI fiscal/debt, MoSPI national accounts, GST fiscal-year totals, AISHE and PLFS after official releases.",
        "Before deployment: run backend tests, promote only valid artifacts, synchronise the catalogue and require a clean frontend build.",
        "After a definition or base-year change: update registry wording, parser/transform, tests, artifact methodology and this document together.",
    ]:
        doc.add_bullet(item)


def add_gaps(doc: DocxBuilder) -> None:
    doc.add_heading("14. Known gaps and next implementation priorities", 1, bookmark="gaps")
    doc.table(
        ["Priority", "Missing capability", "Completion criterion"],
        [
            ["1", "External analytical review", "An independent reviewer checks source definitions, specification versions 1.0.0–1.2.0, generated wording and the two diagnostic failures before policy conclusions are drawn."],
            ["2", "Future UPI serial-dependence specification", "If pursued, register a new version before estimation with a model appropriate to the residual dependence; retain the published version-1 result unchanged."],
            ["3", "Historical institutional-flow archive", "Scheduled daily NSE collection has enough consecutive months for complete 12-month windows; month-completeness is explicit."],
            ["4", "Shock-event analysis", "Only after sufficient flow/market history, the configured 2018 EM sell-off, COVID-19 and 2022 tightening windows are populated and validated against event_study.schema.json."],
            ["5", "Longer official GST and OBICUS history", "Additional compatible official vintages extend the short current histories without mixing definitions or overwriting source status."],
            ["6", "Frontend performance and document automation", "Reduce the large JavaScript chunk and generate this guide in a release job without weakening validation."],
            ["7", "Legacy review", "Manually verify retained World Bank/market assets, decide which remain analytically useful, then migrate or delete only with explicit approval."],
        ],
        widths=[900, 3100, 5000],
    )
    doc.add_callout("Immediate next gate", "Keep the version-1 reports visible with their limitations and obtain external analytical review. Any new UPI model must be registered as a new version before its coefficients are inspected; the failed residual-autocorrelation diagnostic must not be erased by retuning the published specification.", color="2E7D6B", shade="ECFDF5")
    doc.add_callout("Event-study readiness", "scripts/config/global_shock_events.py pre-registers the 2018 emerging-market sell-off, COVID-19 and 2022 global tightening windows, and schemas/event_study.schema.json defines the future contract. This is prepared architecture, not currently published evidence.", color="D97706", shade="FFF7ED")


def add_appendix(doc: DocxBuilder) -> None:
    doc.add_page_break()
    doc.add_heading("15. Source register, glossary and repository map", 1, bookmark="appendix")
    doc.add_heading("Consolidated official-source register", 2)
    seen: set[str] = set()
    for key in FOCUSED_BUNDLES:
        for name, stats, url in LENS_DETAILS[key]["sources"]:
            if url in seen:
                continue
            seen.add(url)
            doc.add_link(f"{name} — {stats}  ", url, url)

    doc.add_heading("Exact provenance records embedded in the current artifacts", 2)
    doc.add_paragraph(
        "The entries below are read from each processed artifact, including the retrieval timestamp where the "
        "builder recorded one. This expands aggregated source descriptions into the exact vintages used—for "
        "example, every Union Budget edition used to reconstruct original plans and later out-turns."
    )
    for key, bundle in FOCUSED_BUNDLES.items():
        payload = load_artifact(key)
        doc.add_heading(bundle.label, 3)
        for source in payload["metadata"]["source"]:
            name = source["name"]
            retrieved = source.get("retrieved_at", "retrieval time inherited from validated upstream artifact")
            if source.get("url"):
                doc.add_link(f"{retrieved}  ·  ", name, source["url"])
            else:
                doc.add_paragraph(f"{retrieved}  ·  {name}")

    doc.add_heading("Glossary", 2)
    glossary = [
        ("Actual / BE / RE", "Realised fiscal out-turn / original Budget Estimate / in-year Revised Estimate."),
        ("AISHE", "All India Survey on Higher Education."),
        ("Canonical record", "Provider-neutral internal observation carrying economic identity, time, unit, status and provenance."),
        ("CapEx", "Capital expenditure. In this pipeline, direct central-government CapEx unless a broader concept is explicitly labelled."),
        ("Current account", "Merchandise trade balance plus net invisibles in the implemented RBI construction; positive is surplus."),
        ("DII / FII / FPI", "Domestic institutional investor / foreign institutional investor / foreign portfolio investor. Source-specific coverage matters."),
        ("Fiscal year", "Indian year from 1 April to 31 March; labelled by both years, for example FY2024–25."),
        ("GFCF", "Gross fixed capital formation, a national-accounts measure of investment in fixed assets."),
        ("GER", "Gross Enrolment Ratio: enrolment at a level divided by the population in its official age group; may exceed 100 at some levels because it is gross."),
        ("Immutable raw", "A source response retained without overwriting, identified by retrieval context and checksum."),
        ("Eligibility gate", "A pre-estimation rule on sample size, variation, degrees of freedom, rank and time ordering. Passing authorises estimation; it is not evidence for a claim."),
        ("Evidence grade", "A structured assessment carried by an evidence report after estimation, diagnostics and robustness—not a synonym for statistical significance."),
        ("Nominal GDP", "Gross domestic product at current prices. It is the appropriate denominator for nominal rupee flows in the implemented ratios."),
        ("Null", "Explicit absence or inapplicability; not zero and not an instruction to interpolate."),
        ("OBICUS", "RBI Order Books, Inventories and Capacity Utilisation Survey."),
        ("PLFS usual status (ps+ss)", "Principal plus subsidiary usual activity status used for the selected annual labour-market measures."),
        ("REER", "Real effective exchange rate: a trade-weighted relative-price index adjusted for inflation differentials."),
        ("Rolling 12 months", "A cumulative or average window requiring 12 consecutive monthly observations under this pipeline’s completeness rule."),
        ("UPI", "Unified Payments Interface; NPCI reports transaction volume and value, not unique-user participation."),
        ("Vintage", "The publication edition from which an observation was read. Fiscal and national-accounts values can differ across vintages."),
    ]
    doc.table(["Term", "Meaning in this architecture"], glossary, widths=[2600, 6400])

    doc.add_heading("Key implementation files", 2)
    files = [
        "scripts/config/focused_indicators.py — authoritative focused research registry",
        "scripts/config/evidence_specs.py — frozen evidence questions, inputs, models and decision thresholds",
        "scripts/audit_evidence_readiness.py — read-only registered sample and eligibility audit",
        "scripts/models/canonical.py — canonical observation, status and fiscal-period model",
        "scripts/models/evidence.py — evidence-result, estimate, diagnostic and eligibility models",
        "scripts/analysis/ — registered loading, alignment and pre-estimation eligibility",
        "scripts/analysis/regression.py — explicit statsmodels OLS/HAC boundary and diagnostics",
        "scripts/analysis/estimation.py — registered designs, robustness, adjustment and grading",
        "scripts/build_evidence_reports.py — validated evidence build and promotion orchestrator",
        "scripts/review_evidence_reports.py — independent-code-path numerical reproduction",
        "scripts/build_focused_pipeline.py — seven-bundle orchestrator",
        "scripts/build_<lens>.py — source-to-bundle builders",
        "scripts/extractors/ — provider-specific acquisition and raw archiving",
        "scripts/transforms/ — reusable formulas and time-series transformations",
        "scripts/validators/quality.py — record and output quality gates",
        "scripts/exporters/json_export.py — strict atomic JSON writer",
        "scripts/promote_processed_data.py — validated frontend promotion",
        "scripts/builders/evidence_report.py — registered lens-level evidence report assembly",
        "scripts/validators/evidence.py — schema and cross-field evidence validation",
        "scripts/sync_focused_catalogue.py — catalogue availability and presentation generation",
        "scripts/sync_public_schemas.py — authoritative schema synchronisation to the frontend",
        "schemas/dated_multi_series.schema.json — focused published contract",
        "schemas/evidence_report.schema.json — versioned analytical-evidence contract",
        "docs/decisions/0001-evidence-policy.md — initial evidence-policy decision freeze",
        "docs/reviews/EVIDENCE_REVIEW_2026-07-28.md — internal reproducibility and interpretation review",
        "frontend/public/data/catalogue.json — runtime navigation/asset control plane",
        "frontend/src/pages/ResearchLensPage.tsx — scrollable one-page-per-lens layout",
        "frontend/src/components/MetricPanel.tsx — chart/insight/source composition",
        "frontend/src/components/EvidencePanel.tsx — lens-level status, uncertainty, diagnostics and robustness display",
        "frontend/src/hooks/useEvidenceData.ts — separately guarded evidence loading",
        "frontend/src/components/ChartView.tsx — common chart renderer with explicit null gaps",
        "frontend/src/data/runtimeGuards.ts — runtime schema/component protection",
        "tests/ — transformations, extractors, contracts and publication regression checks",
    ]
    for item in files:
        doc.add_bullet(item)

    doc.add_heading("Maintenance rule", 2)
    doc.add_paragraph("When a statistic, definition, source table, frequency, unit, formula, limitation or frontend contract changes, the smallest complete change set is: registry → extraction/transform → tests → schema or metadata if needed → processed artifact → promotion/catalogue → this architecture guide. Updating only the chart label leaves the data lineage incorrect.")
    doc.add_callout("End state", "A reader should be able to start at any chart, identify the exact published series key and official source statistic, reproduce the formula, understand time/status semantics, locate the immutable evidence, and state what the result does—and does not—support.", color="2E7D6B", shade="ECFDF5")


def build_document() -> DocxBuilder:
    doc = DocxBuilder()
    add_title_page(doc)
    add_contents(doc)
    add_executive_summary(doc)
    add_architecture(doc)
    add_pipeline(doc)
    add_contracts(doc)
    for number, key in enumerate(FOCUSED_BUNDLES, start=5):
        add_lens(doc, key, number)
    add_frontend(doc)
    add_operations(doc)
    add_gaps(doc)
    add_appendix(doc)
    return doc


def main() -> None:
    document = build_document()
    document.save(OUTPUT_PATH)
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
