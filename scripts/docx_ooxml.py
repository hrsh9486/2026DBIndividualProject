"""Minimal standard-library OOXML writer used by the CapEx documentation build."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


def _text(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


class DocxBuilder:
    """Small OOXML writer supporting the elements used in the CapEx guides."""

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
        properties = []
        if bold:
            properties.append("<w:b/>")
        if italic:
            properties.append("<w:i/>")
        if color:
            properties.append(f'<w:color w:val="{color}"/>')
        if size:
            properties.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
        if font:
            properties.append(f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>')
        if style:
            properties.append(f'<w:rStyle w:val="{style}"/>')
        props = f"<w:rPr>{''.join(properties)}</w:rPr>" if properties else ""
        return f'<w:r>{props}<w:t xml:space="preserve">{_text(text)}</w:t></w:r>'

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
        properties = []
        if style:
            properties.append(f'<w:pStyle w:val="{style}"/>')
        if align:
            properties.append(f'<w:jc w:val="{align}"/>')
        if keep_next:
            properties.append("<w:keepNext/>")
        if keep_lines:
            properties.append("<w:keepLines/>")
        if space_before is not None or space_after is not None:
            before = f' w:before="{space_before}"' if space_before is not None else ""
            after = f' w:after="{space_after}"' if space_after is not None else ""
            properties.append(f"<w:spacing{before}{after}/>")
        if indent_left is not None:
            properties.append(f'<w:ind w:left="{indent_left}"/>')
        if border_left:
            properties.append(
                f'<w:pBdr><w:left w:val="single" w:sz="18" w:space="10" w:color="{border_left}"/></w:pBdr>'
            )
        if shade:
            properties.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
        props = f"<w:pPr>{''.join(properties)}</w:pPr>" if properties else ""
        content = "".join(runs) if runs is not None else self.run(text)
        if bookmark:
            bookmark_id = self.bookmark_id
            self.bookmark_id += 1
            content = (
                f'<w:bookmarkStart w:id="{bookmark_id}" w:name="{_slug(bookmark)}"/>'
                f"{content}<w:bookmarkEnd w:id=\"{bookmark_id}\"/>"
            )
        return f"<w:p>{props}{content}</w:p>"

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

    def add_callout(
        self,
        title: str,
        text: str,
        *,
        color: str = "1F4E78",
        shade: str = "EAF2F8",
    ) -> None:
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
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def hyperlink(self, label: str, url: str) -> str:
        relationship_id = f"rId{20 + len(self.relationships)}"
        self.relationships.append((relationship_id, url))
        return (
            f'<w:hyperlink r:id="{relationship_id}" w:history="1">'
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
            '</w:tblPr>'
            f"<w:tblGrid>{grid}</w:tblGrid>"
        ]

        def cell(value: object, width: int, *, header: bool = False) -> str:
            properties = [f'<w:tcW w:w="{width}" w:type="dxa"/>']
            if header:
                properties.append('<w:shd w:val="clear" w:color="auto" w:fill="1F4E78"/>')
            paragraphs = [
                self.paragraph(
                    runs=[self.run(line, bold=header, color="FFFFFF" if header else None, size=font_size)],
                    style="TableText",
                    keep_lines=True,
                )
                for line in str(value).split("\n") or [""]
            ]
            return f"<w:tc><w:tcPr>{''.join(properties)}</w:tcPr>{''.join(paragraphs)}</w:tc>"

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
        section = (
            '<w:sectPr><w:headerReference w:type="default" r:id="rId3"/>'
            '<w:footerReference w:type="default" r:id="rId4"/>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="900" w:bottom="1134" w:left="900" w:header="560" w:footer="560"/>'
            "</w:sectPr>"
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<w:body>{''.join(self.body)}{section}</w:body></w:document>"
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        external = "".join(
            f'<Relationship Id="{relationship_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target={quoteattr(url)} TargetMode="External"/>'
            for relationship_id, url in self.relationships
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
            "word/_rels/document.xml.rels": DOCUMENT_RELS.replace("<!--EXTERNAL-->", external),
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

CORE_PROPERTIES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>India public CapEx documentation</dc:title><dc:creator>2026DB project</dc:creator></cp:coreProperties>"""

APP_PROPERTIES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>2026DB documentation generator</Application></Properties>"""

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
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:updateFields w:val="true"/></w:settings>"""

FONT_TABLE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:font w:name="Aptos"/><w:font w:name="Aptos Display"/><w:font w:name="Cascadia Mono"/></w:fonts>"""

HEADER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>India public CapEx transmission</w:t></w:r></w:p></w:hdr>"""

FOOTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="140"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/></w:style>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="58"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="64748B"/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="38"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="1F4E78"/><w:sz w:val="29"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:color w:val="2E7D6B"/><w:sz w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:shd w:val="clear" w:fill="F1F5F9"/></w:pPr><w:rPr><w:rFonts w:ascii="Cascadia Mono" w:hAnsi="Cascadia Mono"/><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="ArchitectureTable"><w:name w:val="Architecture Table"/><w:basedOn w:val="TableNormal"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="CBD5E1"/><w:left w:val="single" w:sz="4" w:color="CBD5E1"/><w:bottom w:val="single" w:sz="4" w:color="CBD5E1"/><w:right w:val="single" w:sz="4" w:color="CBD5E1"/><w:insideH w:val="single" w:sz="4" w:color="CBD5E1"/><w:insideV w:val="single" w:sz="4" w:color="CBD5E1"/></w:tblBorders></w:tblPr></w:style>
</w:styles>"""
