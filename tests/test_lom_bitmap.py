"""Rendered-grid LOM: cell-by-cell from a bitmap, not whole-page OCR."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import fitz
from PIL import Image, ImageDraw

from quote_core.bom import extract_bom
from quote_core.lom_bitmap import (
    _crop_cell,
    find_grid_lines,
    read_lom_grid_from_bitmap,
)
from quote_core.lom_xlsx import extract_bom_from_lom_xlsx, write_lom_xlsx
from quote_core.weld.takeoff import estimate_fitup_drivers, run_weld_takeoff


def _drawn_grid_image() -> tuple[Image.Image, dict[tuple[int, int], str]]:
    """Black CAD-style table: header at the bottom, Item A at the bottom data row."""
    xs = [20, 90, 160, 300, 520]
    ys = [20, 70, 120, 170, 220, 270, 320]
    im = Image.new("RGB", (540, 340), "white")
    draw = ImageDraw.Draw(im)
    for y in ys:
        draw.line([(xs[0], y), (xs[-1], y)], fill="black", width=3)
    for x in xs:
        draw.line([(x, ys[0]), (x, ys[-1])], fill="black", width=3)

    # rows 0..4 data (top→bottom), row 5 = header (Time prints headers low)
    cells: dict[tuple[int, int], str] = {
        (0, 0): "-",
        (0, 1): "Q",
        (0, 2): "1001908-1",
        (0, 3): "OTHER DASH",
        (1, 0): "8",
        (1, 1): "X",
        (1, 2): "1005940-1",
        (1, 3): "PEDESTAL GUSSET",
        (2, 0): "2",
        (2, 1): "C",
        (2, 2): "29860-4",
        (2, 3): "BRACE ANGLE",
        (3, 0): "1",
        (3, 1): "AB",
        (3, 2): "50029-7",
        (3, 3): "STREET ELBOW",
        (4, 0): "1",
        (4, 1): "A",
        (4, 2): "14500-1",
        (4, 3): "PEDESTAL TOP PLATE",
        (5, 0): "-1",
        (5, 1): "ITEM",
        (5, 2): "PART NO",
        (5, 3): "DESCRIPTION",
    }
    return im, cells


def _ocr_from_boxes(cells: dict[tuple[int, int], str], xs: list[int], ys: list[int]):
    def ocr_cell(cell_im: Image.Image) -> str:
        box = getattr(cell_im, "_lom_box", None)
        if not box:
            return ""
        x0, y0, x1, y1 = box
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        col = min(range(len(xs) - 1), key=lambda i: abs(cx - (xs[i] + xs[i + 1]) / 2.0))
        row = min(range(len(ys) - 1), key=lambda i: abs(cy - (ys[i] + ys[i + 1]) / 2.0))
        return cells.get((row, col), "")

    return ocr_cell


def test_bitmap_reads_printed_cells_not_page_regex():
    im, cells = _drawn_grid_image()
    xs = [20, 90, 160, 300, 520]
    ys = [20, 70, 120, 170, 220, 270, 320]
    orig = _crop_cell

    def tagged(im_, x0, y0, x1, y1, pad=2):
        cell = orig(im_, x0, y0, x1, y1, pad)
        cell._lom_box = (x0, y0, x1, y1)
        return cell

    with patch("quote_core.lom_bitmap._crop_cell", side_effect=tagged):
        grid, meta = read_lom_grid_from_bitmap(im, ocr_cell=_ocr_from_boxes(cells, xs, ys))
    assert meta["grid_found"]
    assert grid[0][:4] == ["-1", "ITEM", "PART NO", "DESCRIPTION"]
    body = [" ".join(r) for r in grid[1:]]
    assert any("14500-1" in row and "A" in row for row in body)
    assert any("50029-7" in row and "AB" in row for row in body)
    assert any("1005940-1" in row and "8" in row for row in body)
    # Other-dash blank / "-" on -1 is kept on the drawn sheet; quote reader drops it.
    assert any("1001908-1" in row for row in body)


def test_bitmap_infers_dash_minus_one_when_headers_unreadable():
    im, cells = _drawn_grid_image()
    xs = [20, 90, 160, 300, 520]
    ys = [20, 70, 120, 170, 220, 270, 320]
    blank_header = {k: ("" if k[0] == 5 else v) for k, v in cells.items()}
    orig = _crop_cell

    def tagged(im_, x0, y0, x1, y1, pad=2):
        cell = orig(im_, x0, y0, x1, y1, pad)
        cell._lom_box = (x0, y0, x1, y1)
        return cell

    with patch("quote_core.lom_bitmap._crop_cell", side_effect=tagged):
        grid, meta = read_lom_grid_from_bitmap(
            im, ocr_cell=_ocr_from_boxes(blank_header, xs, ys)
        )
    assert meta["grid_found"]
    assert grid[0][0] == "-1"
    assert "PART NO" in grid[0]
    assert any("14500-1" in "".join(r) for r in grid[1:])


def _write_drawn_grid_pdf(path: Path, *, with_title: bool = False) -> Path:
    """CAD linework LOM: printed grid, almost no PDF text."""
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    if with_title:
        page.insert_text((420, 40), "LIST OF MATERIAL", fontsize=10)
    x0, y0, x1, y1 = 400.0, 80.0, 780.0, 560.0
    cols, rows = 4, 10
    shape = page.new_shape()
    for i in range(rows + 1):
        y = y0 + i * (y1 - y0) / rows
        shape.draw_line(fitz.Point(x0, y), fitz.Point(x1, y))
    for i in range(cols + 1):
        x = x0 + i * (x1 - x0) / cols
        shape.draw_line(fitz.Point(x, y0), fitz.Point(x, y1))
    shape.finish(color=(0, 0, 0), width=1.2)
    shape.commit()
    doc.save(path)
    doc.close()
    return path


def test_find_grid_lines_on_drawn_pdf(tmp_path: Path):
    pdf = _write_drawn_grid_pdf(tmp_path / "lines.pdf")
    doc = fitz.open(pdf)
    page = doc[0]
    from quote_core.lom_bitmap import candidate_lom_clips, render_page_region

    found = False
    for clip in candidate_lom_clips(page):
        im = render_page_region(page, clip, dpi=140)
        info = find_grid_lines(im, min_h=6, min_v=5)
        if info["found"]:
            found = True
            break
    doc.close()
    assert found, "drawn CAD LOM grid must be visible to the bitmap clipper"


def test_empty_drawn_clip_is_needs_info_never_one_piece(tmp_path: Path):
    pdf = _write_drawn_grid_pdf(tmp_path / "weldment-1.pdf")
    with patch("quote_core.ocr.ocr_available", return_value=False):
        bom = extract_bom(pdf, library_folder=tmp_path, bom_config="1")
        drivers = estimate_fitup_drivers(
            {},
            [],
            pdf_path=pdf,
            library_folder=tmp_path,
            bom_config="1",
        )
    assert bom.method == "lom_clip_empty", bom.notes
    assert bom.piece_count == 0
    assert not list(tmp_path.glob("*LOM.xlsx"))
    assert drivers["needs_info"] is True
    assert drivers["part_count"] != 1
    assert drivers["part_count"] == 0
    assert drivers["piece_count"] == 0


def test_existing_lom_xlsx_is_takeoff_when_drawing_is_vector(tmp_path: Path):
    """Kyle-confirmed sheet wins over a vector drawing that cannot be re-clipped."""
    from tests.test_lom_xlsx import _1001898_lom_rows

    write_lom_xlsx(tmp_path / "1001898-1-LOM.xlsx", _1001898_lom_rows(), part_key="1001898-1")
    pdf = _write_drawn_grid_pdf(tmp_path / "1001898-1.pdf")
    with patch("quote_core.ocr.ocr_available", return_value=False):
        bom = extract_bom(pdf, library_folder=tmp_path, bom_config="1")
        result = run_weld_takeoff(pdf, library_folder=tmp_path, bom_config="1")
    assert bom.method == "lom_xlsx"
    assert bom.part_number_count == 17
    assert bom.piece_count == 27
    assert result.fitup_drivers["part_count"] == 27
    assert result.fitup_drivers["piece_count"] == 27
    assert not result.fitup_drivers.get("needs_info")
