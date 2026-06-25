# Scientific PDF Converter

Веб-сервис для разбора научных PDF-статей на структурированные данные: метаданные, секции, таблицы, формулы, изображения и список литературы.

## Стек

- **Backend:** FastAPI
- **Очередь задач:** Celery + Redis
- **Парсинг PDF:** PyMuPDF, pdfminer.six
- **Структура статьи:** GROBID
- **OCR (для сканов):** Tesseract
- **Распознавание формул:** pix2tex (LaTeX OCR)
- **Извлечение таблиц:** Camelot, tabula-py
- **Контейнеризация:** Docker Compose

## Быстрый старт

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Запуск

```bash
docker-compose up --build
```

Сервис будет доступен на `http://localhost:8000`.  
Интерактивная документация API: `http://localhost:8000/docs`

### Остановка

```
Ctrl+C
```

## API

### Загрузить PDF

```
POST /v1/jobs
```

Multipart form upload с параметрами:
- `file` — PDF-файл
- `extract_tables` — извлекать таблицы (по умолчанию `true`)
- `extract_images` — извлекать изображения (по умолчанию `true`)
- `extract_formulas` — извлекать формулы (по умолчанию `true`)
- `ocr_mode` — режим OCR: `auto`, `force`, `off`
- `language_hint` — язык документа (по умолчанию `en`)

### Проверить статус

```
GET /v1/jobs/{job_id}
```

Возвращает статус обработки, прогресс и предупреждения.

### Получить результат

```
GET /v1/jobs/{job_id}/result.json   — структурированный JSON
GET /v1/jobs/{job_id}/result.md     — Markdown
GET /v1/jobs/{job_id}/artifacts.zip — все артефакты (изображения, таблицы, формулы)
```

### Другие операции

```
POST   /v1/jobs/{job_id}/retry   — перезапустить обработку
DELETE /v1/jobs/{job_id}         — удалить задание и все данные
GET    /healthz                  — проверка здоровья сервиса
GET    /readyz                   — проверка готовности
```

## Формат result.json

```json
{
  "document_id": "uuid",
  "source": { "filename": "paper.pdf", "pages": 18, "born_digital": true },
  "metadata": { "title": "...", "authors": ["..."], "abstract": "...", "doi": "..." },
  "sections": [{ "title": "Introduction", "level": 1, "text": "..." }],
  "formulas": [{ "page": 4, "latex": "\\int ...", "confidence": 0.87 }],
  "tables": [{ "page": 6, "markdown": "|...|" }],
  "figures": [{ "page": 5, "image_path": "figures/fig_1.png" }],
  "references": [{ "title": "...", "authors": ["..."], "year": 2024 }],
  "pages": [{ "page": 1, "text": "...", "confidence": 0.95 }],
  "diagnostics": { "ocr_used": false, "grobid_used": true, "formula_engine": "pix2tex" }
}
```

## Архитектура

```
PDF → FastAPI → Celery Queue → Worker Pipeline:
  ├─ PDF Inspection (born-digital vs scan)
  ├─ Text Extraction (PyMuPDF) или OCR (Tesseract)
  ├─ Structure Parsing (GROBID → metadata, sections, references)
  ├─ Table Extraction (Camelot / tabula-py)
  ├─ Image Extraction (PyMuPDF)
  ├─ Formula Detection + Recognition (pix2tex)
  └─ Normalization → result.json + result.md + artifacts.zip
```
