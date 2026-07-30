from pathlib import Path

from quote_core.drawing_library import extract_part_key, find_drawings, library_roots_from_config


def test_extract_part_key_from_pdf_names():
    assert extract_part_key("80341805.pdf") == "80341805"
    assert extract_part_key("73476047-FAB Packet.pdf") == "73476047"
    assert extract_part_key("23508814 for quoting.pdf") == "23508814"
    assert extract_part_key("35145-1 JIB ARM WELDMENT ALL DRAWINGS.pdf") == "35145-1"


def test_find_mac_assembly_on_shared_drive():
    roots = library_roots_from_config(
        {
            "drawing_library": {
                "roots": [
                    r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings"
                ]
            }
        }
    )
    existing = [r for r in roots if r.exists()]
    if not existing:
        return  # skip when library not synced on this machine

    match = find_drawings("80341805", existing, primary_pdf_name="80341805.pdf")
    assert match.folder is not None
    assert match.stp_path is not None
    assert match.stp_path.name.lower().startswith("80341805")
    assert match.stp_path.suffix.lower() in {".stp", ".step"}
    assert isinstance(match.related_pdfs, list)


def test_find_time_jib_step_beside_folder():
    """Time keeps 35145-1.STEP next to folder Time/35145-1 (PDF-only)."""
    roots = library_roots_from_config(
        {
            "drawing_library": {
                "roots": [
                    r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings"
                ]
            }
        }
    )
    existing = [r for r in roots if r.exists()]
    if not existing:
        return
    step = Path(
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\Time\35145-1.STEP"
    )
    if not step.exists():
        return
    match = find_drawings("35145-1", existing)
    assert match.stp_path is not None
    assert match.stp_path.name.lower() == "35145-1.step"
    assert match.folder is not None
    assert "35145-1" in match.folder.name
