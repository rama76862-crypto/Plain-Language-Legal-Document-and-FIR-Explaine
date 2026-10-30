"""Native parsers, source-linked segmentation, and conservative detection."""
import re
import zipfile
from pathlib import Path
from apps.api.schemas import ApiError, Clause, SourceRef
from .ocr import ocr_page

_NUMBERED = re.compile(r'^\s*(?:\d+(?:\.\d+)*[.)]?|[A-Z][.)])\s+')


def _notify(progress, **values):
    if progress:
        progress(values)


def _quality(text):
    letters = sum(character.isalpha() for character in text)
    return letters >= 8 and '\ufffd' not in text and text.count('\x00') == 0


def _detect(text, requested):
    warnings = []
    if requested != 'auto':
        language = requested
        if requested == 'en' and any('\u0900' <= c <= '\u097f' or '\u0a00' <= c <= '\u0a7f' for c in text):
            warnings.append('LANGUAGE_MISMATCH: selected English but non-Latin script was extracted; confirm language.')
        if requested == 'hi' and not any('\u0900' <= c <= '\u097f' for c in text):
            warnings.append('LANGUAGE_MISMATCH: selected Hindi but no Devanagari text was found; confirm language.')
        if requested == 'pa' and not any('\u0a00' <= c <= '\u0a7f' for c in text):
            warnings.append('LANGUAGE_MISMATCH: selected Punjabi but no Gurmukhi text was found; confirm language.')
    else:
        # Script is evidence of a script, not proof of a language.
        language = 'unknown'
        if all(ord(c) < 128 for c in text) and re.search(r'\b(the|shall|agreement|notice|this|and)\b', text, re.I):
            language = 'en'
        warnings.append('CONFIRM_LANGUAGE: automatic language suggestion requires human confirmation.')
    lower = text.lower()
    if 'first information report' in lower:
        document_type = 'fir'
    elif re.search(r'\b(legal notice|notice to|show cause notice)\b', lower):
        document_type = 'notice'
    elif re.search(r'\b(agreement|contract|lease agreement)\b', lower):
        document_type = 'agreement'
    else:
        document_type = 'other'
    warnings.append('CONFIRM_DOCUMENT_TYPE: detected type is a suggestion; confirm during review.')
    return language, document_type, warnings


def _segments(text):
    """Numbered lines begin clauses; sentence windows preserve all nonempty text."""
    groups = []
    current = []
    for line in text.splitlines():
        if not line.strip():
            if current:
                groups.append('\n'.join(current)); current = []
            continue
        if current and _NUMBERED.match(line):
            groups.append('\n'.join(current)); current = []
        current.append(line)
    if current:
        groups.append('\n'.join(current))
    output = []
    for group in groups:
        # Long paragraphs split only at actual sentence boundaries, never truncate.
        if len(group) > 2000:
            output.extend(re.split(r'(?<=[.!?।])\s+(?=\S)', group))
        else:
            output.append(group)
    return [part.strip() for part in output if part.strip()]


def _pdf(path, input_language, settings, progress):
    import pymupdf as fitz
    # MuPDF diagnostics can echo attacker-controlled tokens from a damaged
    # content stream. Disable native stdout/stderr diagnostics process-wide;
    # public errors below remain fixed, content-free messages.
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    fitz.TOOLS.reset_mupdf_warnings()
    clauses, warnings = [], []
    total_chars = 0
    try:
        document = fitz.open(path)
    except Exception:
        raise ApiError('EXTRACTION_FAILED', 'PDF is malformed or unreadable.', 422) from None
    with document:
        if not document.is_pdf or document.needs_pass:
            raise ApiError('EXTRACTION_FAILED', 'Encrypted or unreadable PDF; provide an unlocked PDF.', 422)
        if document.page_count > settings.max_pdf_pages:
            raise ApiError('FILE_TOO_LARGE', 'PDF exceeds the configured page limit.', 413)
        if not document.page_count:
            raise ApiError('EMPTY_DOCUMENT', 'PDF contains no pages.', 422)
        ocr_completed = 0
        for index, page in enumerate(document):
            # Explicit native text path: do not invoke layout/AI helpers, OCR, or
            # preserve image bytes while reading a page's text blocks.
            flags = fitz.TEXTFLAGS_BLOCKS & ~fitz.TEXT_PRESERVE_IMAGES
            blocks = [block for block in page.get_text('blocks', sort=True, flags=flags) if len(block) < 7 or block[6] == 0]
            native = '\n'.join(block[4] for block in blocks).strip()
            method, review = 'text', False
            # A scanned body may coexist with a tiny selectable header/footer.
            # Such a header is not evidence that the scanned body was extracted.
            image_dominant = len(native) < 150 and any(
                fitz.Rect(image['bbox']).get_area() >= page.rect.get_area() * 0.5
                for image in page.get_image_info(hashes=False)
            )
            if not _quality(native) or image_dominant:
                try:
                    text = ocr_page(page, input_language, settings)
                    ocr_completed += 1
                    blocks = [(0, 0, 0, 0, text)]
                    method, review = 'ocr', True
                    warnings.append(f'OCR_REVIEW_REQUIRED: page {index + 1}; verify dates, numbers, names and negation.')
                except ApiError as error:
                    if not native:
                        raise
                    warnings.append(f'{error.code}: page {index + 1}; partial native text retained for review.')
                    review = True
            for block in blocks:
                text = block[4].strip()
                total_chars += len(text)
                if total_chars > settings.max_extracted_chars:
                    raise ApiError('FILE_TOO_LARGE', 'Extracted document exceeds character limit.', 413)
                parts = _segments(text)
                for part in parts:
                    bbox = list(block[:4]) if method == 'text' and len(parts) == 1 else None
                    # Join an unfinished clause at a page boundary, preserving a primary reference.
                    if clauses and clauses[-1].source_ref.page_number != index + 1 and not re.search(r'[.!?।:]\s*$', clauses[-1].source_text) and not _NUMBERED.match(part):
                        previous = clauses[-1]
                        previous.source_text += '\n' + part
                        previous.reviewed_text = previous.source_text
                        previous.source_ref.bbox = None
                        previous.review_required = True
                        warnings.append('CROSS_PAGE_CLAUSE: primary source page retained; inspect the following page too.')
                    else:
                        clauses.append(Clause(clause_id=f'c{len(clauses)+1}', source_text=part, reviewed_text=part,
                                              source_ref=SourceRef(page_number=index+1, bbox=bbox),
                                              extraction_method=method, review_required=review or not _quality(part)))
            _notify(progress, stage='extracting', completed_pages=index+1, total_pages=document.page_count,
                    completed_ocr_pages=ocr_completed)
    return clauses, warnings


def _validate_docx(path, settings):
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > settings.max_docx_entries or sum(item.file_size for item in entries) > settings.max_docx_expanded_bytes:
                raise ApiError('FILE_TOO_LARGE', 'DOCX expanded size or entry count exceeds configured limits.', 413)
            names = {item.filename for item in entries}
            if len(names) != len(entries) or any(name.startswith(('/', '\\')) or '..' in name.replace('\\', '/').split('/') for name in names):
                raise ApiError('UNSUPPORTED_FILE', 'DOCX archive has ambiguous or unsafe entry names.', 415)
            if not {'[Content_Types].xml', 'word/document.xml'}.issubset(names):
                raise ApiError('UNSUPPORTED_FILE', 'File is not a supported DOCX package.', 415)
            for item in entries:
                if item.flag_bits & 1 or 'vbaproject' in item.filename.lower():
                    raise ApiError('UNSUPPORTED_FILE', 'Encrypted or macro-enabled DOCX is unsupported.', 415)
                if item.filename.lower().endswith('.xml'):
                    data = archive.read(item)
                    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                        raise ApiError('UNSUPPORTED_FILE', 'DOCX XML declarations are unsupported.', 415)
    except ApiError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError, NotImplementedError):
        raise ApiError('EXTRACTION_FAILED', 'DOCX archive is malformed or unreadable.', 422) from None


def _docx(path, settings, progress):
    from docx import Document
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    _validate_docx(path, settings)
    try:
        document = Document(path)
        def paragraphs(parent, element):
            for child in element.iterchildren():
                if child.tag.endswith('}p'):
                    yield Paragraph(child, parent)
                elif child.tag.endswith('}tbl'):
                    table = Table(child, parent)
                    visited = set()
                    for row in table.rows:
                        for cell in row.cells:
                            if cell._tc not in visited:
                                visited.add(cell._tc)
                                yield from paragraphs(cell, cell._tc)
        ordered = list(paragraphs(document, document.element.body))
        clauses, total_chars = [], 0
        for index, paragraph in enumerate(ordered, 1):
            text = paragraph.text.strip()
            total_chars += len(text)
            if total_chars > settings.max_extracted_chars:
                raise ApiError('FILE_TOO_LARGE', 'Extracted document exceeds character limit.', 413)
            for part in _segments(text):
                clauses.append(Clause(clause_id=f'c{len(clauses)+1}', source_text=part, reviewed_text=part,
                                      source_ref=SourceRef(paragraph_index=index), extraction_method='docx',
                                      review_required=not _quality(part)))
            _notify(progress, stage='extracting', completed_paragraphs=index, total_paragraphs=len(ordered))
        return clauses, []
    except ApiError:
        raise
    except Exception:
        raise ApiError('EXTRACTION_FAILED', 'DOCX document is malformed or unreadable.', 422) from None


def extract_document(path: Path, kind: str, input_language: str, settings, progress=None) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ApiError('EMPTY_DOCUMENT', 'Document is empty or unavailable.', 422)
    if path.stat().st_size > settings.max_upload_mb * 1024 * 1024:
        raise ApiError('FILE_TOO_LARGE', 'Upload exceeds configured size limit.', 413)
    try:
        if kind == 'pdf':
            clauses, warnings = _pdf(path, input_language, settings, progress)
        elif kind == 'docx':
            clauses, warnings = _docx(path, settings, progress)
        else:
            raise ApiError('UNSUPPORTED_FILE', 'Only PDF and DOCX are supported.', 415)
    except ApiError:
        raise
    except Exception:
        # Native-library details can include private paths; keep the public
        # error deliberately content-free rather than propagating the exception.
        raise ApiError('EXTRACTION_FAILED', 'Local document parsing failed.', 422) from None
    finally:
        if kind == 'pdf':
            import pymupdf as fitz
            # Native diagnostics also have an in-memory buffer. Do not retain
            # private parser fragments after a successful or failed parse.
            fitz.TOOLS.reset_mupdf_warnings()
    if not clauses:
        raise ApiError('EMPTY_DOCUMENT', 'No usable text was extracted; provide a clearer document.', 422)
    language, document_type, detected_warnings = _detect('\n'.join(c.source_text for c in clauses), input_language)
    return {'clauses': clauses, 'warnings': list(dict.fromkeys(warnings + detected_warnings)),
            'input_language': language, 'document_type': document_type}
