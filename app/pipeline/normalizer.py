import json
from pathlib import Path

from app.schemas.job import DocumentResult, DocumentMetadata


def build_result(
    job_id: str,
    filename: str,
    info: dict,
    pages: list,
    grobid_data: dict | None,
    tables: list,
    figures: list,
    formulas: list,
    diagnostics: dict,
) -> DocumentResult:
    metadata = DocumentMetadata()
    sections = []
    references = []

    if grobid_data:
        metadata = grobid_data["metadata"]
        sections = grobid_data["sections"]
        references = grobid_data["references"]

    return DocumentResult(
        document_id=job_id,
        source={
            "filename": filename,
            "pages": info["total_pages"],
            "born_digital": info["born_digital"],
        },
        metadata=metadata,
        sections=sections,
        formulas=formulas,
        tables=tables,
        figures=figures,
        references=references,
        pages=pages,
        diagnostics=diagnostics,
    )


def save_result_json(result: DocumentResult, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "result.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def save_result_markdown(result: DocumentResult, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = []

    if result.metadata.title:
        lines.append(f"# {result.metadata.title}\n")
    if result.metadata.authors:
        lines.append(f"**Authors:** {', '.join(result.metadata.authors)}\n")
    if result.metadata.abstract:
        lines.append(f"## Abstract\n\n{result.metadata.abstract}\n")
    if result.metadata.keywords:
        lines.append(f"**Keywords:** {', '.join(result.metadata.keywords)}\n")
    if result.metadata.doi:
        lines.append(f"**DOI:** {result.metadata.doi}\n")

    for section in result.sections:
        prefix = "#" * min(section.level + 1, 6)
        lines.append(f"\n{prefix} {section.title}\n\n{section.text}\n")

    if result.tables:
        lines.append("\n## Tables\n")
        for i, table in enumerate(result.tables, 1):
            lines.append(f"\n### Table {i} (page {table.page})\n\n{table.markdown}\n")

    if result.formulas:
        lines.append("\n## Formulas\n")
        for i, formula in enumerate(result.formulas, 1):
            lines.append(f"\n**Formula {i}** (page {formula.page}, confidence {formula.confidence}):\n")
            lines.append(f"$$\n{formula.latex}\n$$\n")

    if result.references:
        lines.append("\n## References\n")
        for i, ref in enumerate(result.references, 1):
            parts = [f"{i}."]
            if ref.authors:
                parts.append(", ".join(ref.authors) + ".")
            if ref.title:
                parts.append(f"*{ref.title}*.")
            if ref.year:
                parts.append(f"({ref.year}).")
            if not ref.title and not ref.authors:
                parts.append(ref.raw)
            lines.append(" ".join(parts) + "\n")

    path = output_dir / "result.md"
    path.write_text("\n".join(lines), encoding="utf-8")
