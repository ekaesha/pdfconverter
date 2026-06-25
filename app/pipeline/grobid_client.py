import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from app.config import settings
from app.schemas.job import DocumentMetadata, SectionResult, ReferenceResult

TEI_NS = "{http://www.tei-c.org/ns/1.0}"


def _text_of(el) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def process_fulltext(pdf_path: str) -> Optional[dict]:
    """Send PDF to GROBID and parse TEI XML response."""
    url = f"{settings.grobid_url}/api/processFulltextDocument"
    try:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                url,
                files={"input": f},
                data={"consolidateHeader": "1", "consolidateCitations": "0"},
                timeout=120,
            )
        if resp.status_code == 503:
            return None
        resp.raise_for_status()
    except requests.RequestException:
        return None

    return parse_tei_xml(resp.text)


def parse_tei_xml(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)

    # Metadata
    header = root.find(f".//{TEI_NS}teiHeader")
    title_el = header.find(f".//{TEI_NS}titleStmt/{TEI_NS}title") if header is not None else None
    title = _text_of(title_el)

    authors = []
    if header is not None:
        for author in header.findall(f".//{TEI_NS}author"):
            persname = author.find(f"{TEI_NS}persName")
            if persname is not None:
                forename = _text_of(persname.find(f"{TEI_NS}forename"))
                surname = _text_of(persname.find(f"{TEI_NS}surname"))
                name = f"{forename} {surname}".strip()
                if name:
                    authors.append(name)

    abstract_el = header.find(f".//{TEI_NS}profileDesc/{TEI_NS}abstract") if header is not None else None
    abstract = _text_of(abstract_el)

    keywords = []
    if header is not None:
        kw_el = header.find(f".//{TEI_NS}profileDesc/{TEI_NS}textClass/{TEI_NS}keywords")
        if kw_el is not None:
            for term in kw_el.findall(f"{TEI_NS}term"):
                t = _text_of(term)
                if t:
                    keywords.append(t)

    doi = None
    if header is not None:
        for idno in header.findall(f".//{TEI_NS}idno"):
            if idno.get("type") == "DOI":
                doi = _text_of(idno)
                break

    metadata = DocumentMetadata(
        title=title or None,
        authors=authors,
        abstract=abstract or None,
        keywords=keywords,
        doi=doi,
    )

    # Sections
    sections = []
    body = root.find(f".//{TEI_NS}body")
    if body is not None:
        for div in body.findall(f"{TEI_NS}div"):
            head = div.find(f"{TEI_NS}head")
            sec_title = _text_of(head) if head is not None else ""
            level_str = head.get("n", "1") if head is not None else "1"
            try:
                level = len(level_str.split("."))
            except (ValueError, AttributeError):
                level = 1
            text_parts = []
            for p in div.findall(f"{TEI_NS}p"):
                text_parts.append(_text_of(p))
            sections.append(SectionResult(
                title=sec_title,
                level=level,
                text="\n\n".join(text_parts),
                pages=[],
            ))

    # References
    references = []
    back = root.find(f".//{TEI_NS}back")
    if back is not None:
        for bibl in back.findall(f".//{TEI_NS}biblStruct"):
            raw_parts = []
            ref_title = ""
            ref_authors = []
            ref_year = None

            analytic = bibl.find(f"{TEI_NS}analytic")
            monogr = bibl.find(f"{TEI_NS}monogr")

            source = analytic if analytic is not None else monogr
            if source is not None:
                t = source.find(f"{TEI_NS}title")
                ref_title = _text_of(t)
                for author in source.findall(f"{TEI_NS}author"):
                    pn = author.find(f"{TEI_NS}persName")
                    if pn is not None:
                        fn = _text_of(pn.find(f"{TEI_NS}forename"))
                        sn = _text_of(pn.find(f"{TEI_NS}surname"))
                        ref_authors.append(f"{fn} {sn}".strip())

            if monogr is not None:
                date_el = monogr.find(f".//{TEI_NS}date")
                if date_el is not None:
                    when = date_el.get("when", "")
                    if when and len(when) >= 4:
                        try:
                            ref_year = int(when[:4])
                        except ValueError:
                            pass

            raw_parts.append(_text_of(bibl))
            references.append(ReferenceResult(
                raw=" ".join(raw_parts),
                title=ref_title or None,
                authors=ref_authors,
                year=ref_year,
            ))

    return {
        "metadata": metadata,
        "sections": sections,
        "references": references,
    }
