from pathlib import Path

from quote_core.ocr import ocr_available, ocr_pdf_pages, tesseract_cmd


def test_tesseract_available_on_dev_machine():
    # Soft check: if installed, command must resolve to an existing exe.
    cmd = tesseract_cmd()
    if cmd:
        assert Path(cmd).is_file()
        assert ocr_available() is True


def test_ocr_skips_when_native_text_rich(tmp_path: Path):
    import fitz

    pdf = tmp_path / "rich.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "FULL WELD BOTH SIDES 1/4 FILLET TRACE WELD " * 20)
    doc.save(pdf)
    doc.close()
    result = ocr_pdf_pages(pdf, only_when_sparse=True, sparse_text_chars=50)
    assert result.get("used") is False
    assert result.get("skipped") == "native text sufficient"
