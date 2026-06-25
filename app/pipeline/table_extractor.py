from pathlib import Path
from app.schemas.job import TableResult


def extract_tables_camelot(pdf_path: str) -> list[TableResult]:
    """Extract tables from text-based PDF using Camelot."""
    try:
        import camelot
    except ImportError:
        return _extract_tables_tabula(pdf_path)

    try:
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
    except Exception:
        try:
            tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
        except Exception:
            return _extract_tables_tabula(pdf_path)

    results = []
    for i, table in enumerate(tables):
        md = table.df.to_markdown(index=False)
        results.append(TableResult(
            page=table.page,
            bbox=list(table._bbox) if hasattr(table, "_bbox") else [0, 0, 0, 0],
            markdown=md,
        ))

    return results


def _extract_tables_tabula(pdf_path: str) -> list[TableResult]:
    """Fallback table extraction using tabula-py."""
    try:
        import tabula
    except ImportError:
        return []

    try:
        dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, silent=True)
    except Exception:
        return []

    results = []
    for i, df in enumerate(dfs):
        if df.empty:
            continue
        md = df.to_markdown(index=False)
        results.append(TableResult(
            page=0,
            bbox=[0, 0, 0, 0],
            markdown=md,
        ))

    return results
