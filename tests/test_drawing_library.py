from pathlib import Path

from quote_core.drawing_library import extract_part_key, find_drawings, library_roots_from_config


def test_extract_part_key_from_pdf_names():
    assert extract_part_key("80341805.pdf") == "80341805"
    assert extract_part_key("73476047-FAB Packet.pdf") == "73476047"
    assert extract_part_key("23508814 for quoting.pdf") == "23508814"
    assert extract_part_key("35145-1 JIB ARM WELDMENT ALL DRAWINGS.pdf") == "35145-1"


def test_extract_part_key_keeps_vendor_dash_and_strips_rev():
    """TYCROP-style DRAWING NUMBER must keep the dash; filename R00 is not part of it."""
    assert extract_part_key("1511-5024.pdf") == "1511-5024"
    assert extract_part_key("1511-5024_R00.pdf") == "1511-5024"
    assert extract_part_key("1511-5024 R00.pdf") == "1511-5024"
    assert extract_part_key("PN 1511-5024_R00.pdf") == "1511-5024"
    assert extract_part_key("1510-9422_R01.pdf") == "1510-9422"
    # Smashed stems cannot invent the dash — still strip R## for Quote Number hygiene.
    assert extract_part_key("15115024R00.pdf") == "15115024"


def test_extract_part_key_strips_idw_and_keeps_hand_suffix():
    """Inventor ``.idw.pdf`` exports must not become MD231703LRidw."""
    assert extract_part_key("MD23-1703LR.idw.pdf") == "MD23-1703LR"
    assert extract_part_key("MD23-1709LR.idw.pdf") == "MD23-1709LR"
    assert extract_part_key("MC31-1699.idw.pdf") == "MC31-1699"
    assert extract_part_key("ME04-2771LR-1.idw.pdf") == "ME04-2771LR-1"
    assert extract_part_key("MD32-1606.pdf") == "MD32-1606"
    assert extract_part_key("MD04-2300.ipt.stp") == "MD04-2300"


def test_stp_name_matches_cummins_prefixed_and_rejects_siblings(tmp_path: Path):
    from quote_core.drawing_library import _pick_stp, _stp_name_matches

    good = tmp_path / "SM - 50 DGEMC31-1699.stp"
    sibling = tmp_path / "SM - 40 DGEMC31-1697R.stp"
    wrong = tmp_path / "MD06-1664.stp"
    exact = tmp_path / "MC31-1699.stp"
    for p in (good, sibling, wrong, exact):
        p.write_bytes(b"ISO")

    assert _stp_name_matches(good, "MC31-1699")
    assert _stp_name_matches(exact, "MC31-1699")
    assert not _stp_name_matches(sibling, "MC31-1699")
    assert not _stp_name_matches(wrong, "MC31-1699")

    picked = _pick_stp(tmp_path, "MC31-1699")
    assert picked is not None
    assert picked.name in {"MC31-1699.stp", "SM - 50 DGEMC31-1699.stp"}


def test_pick_stp_does_not_fallback_to_unrelated_file(tmp_path: Path):
    from quote_core.drawing_library import _pick_stp

    (tmp_path / "MD06-1664.stp").write_bytes(b"ISO")
    (tmp_path / "MD04-2300.ipt.stp").write_bytes(b"ISO")
    assert _pick_stp(tmp_path, "MC31-1699") is None


def test_find_mc31_1699_picks_matching_stp_not_md06():
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
    match = find_drawings("MC31-1699", existing, primary_pdf_name="MC31-1699.idw.pdf")
    if match.stp_path is None:
        return
    assert "MC31-1699" in match.stp_path.name.upper().replace("-", "") or (
        "MC31-1699" in match.stp_path.name.upper()
    )
    assert "MD06-1664" not in match.stp_path.name.upper()


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
