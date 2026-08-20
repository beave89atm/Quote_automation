"""PDF BOM vs synthetic STEP confirmation (no customer files)."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import BomRow
from quote_core.bom_confirm import (
    confirm_flag_text,
    confirm_pdf_bom_against_stp,
    skipped_stp_bom_confirm,
)
from quote_core.weld.takeoff import (
    _normalize_step_part_no,
    _step_keyword,
    extract_step_assembly_part_counts,
    run_weld_takeoff,
)


def _write_minimal_pdf(path: Path, text: str = 'WELDMENT\n1/4" FILLET\n') -> Path:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


def write_synthetic_assembly_step(
    path: Path,
    *,
    assembly: str = "102728-1",
    children: list[tuple[str, int]] | None = None,
    nested: list[tuple[str, str, int]] | None = None,
) -> Path:
    """
    Minimal AP214-style assembly STEP.

    ``children`` are direct instances of ``assembly``: (part_no, qty).
    ``nested`` are children of a sub-assembly already in ``children``:
    (parent_pn, child_pn, qty) — should not be counted as BOM fillers.
    """
    children = list(children or [("102727-4", 2), ("102726-1", 1), ("35121-1", 1)])
    nested = list(nested or [])
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('synthetic assembly'),'2;1');",
        f"FILE_NAME('{path.name}','2026-08-20T00:00:00',('test'),('test'),"
        f"'Quote Automation','','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
        "ENDSEC;",
        "DATA;",
        "#1=APPLICATION_CONTEXT('automotive design');",
        "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);",
        "#3=PRODUCT_CONTEXT('',#1,'mechanical');",
        "#4=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
    ]
    products: dict[str, tuple[int, int]] = {}
    eid = 10

    def add_product(pn: str, desc: str) -> tuple[int, int]:
        nonlocal eid
        if pn in products:
            return products[pn]
        prod, form, defin = eid, eid + 1, eid + 2
        eid += 10
        lines.append(f"#{prod}=PRODUCT('{pn}','{pn}','{desc}',(#3));")
        lines.append(f"#{form}=PRODUCT_DEFINITION_FORMATION('','',#{prod});")
        lines.append(f"#{defin}=PRODUCT_DEFINITION('design','',#{form},#4);")
        products[pn] = (prod, defin)
        return products[pn]

    add_product(assembly, "WELDMENT")
    for pn, _qty in children:
        add_product(pn, "CHILD")
    for parent_pn, child_pn, _qty in nested:
        add_product(parent_pn, "SUB-WELDMENT")
        add_product(child_pn, "NESTED")

    nauo = 100
    _asm_prod, asm_def = products[assembly]
    for pn, qty in children:
        _cprod, cdef = products[pn]
        for i in range(qty):
            lines.append(
                f"#{nauo}=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO{nauo}','{pn}','',#{asm_def},#{cdef},$);"
            )
            nauo += 1
    for parent_pn, child_pn, qty in nested:
        _pprod, pdef = products[parent_pn]
        _cprod, cdef = products[child_pn]
        for _i in range(qty):
            lines.append(
                f"#{nauo}=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO{nauo}','{child_pn}','',#{pdef},#{cdef},$);"
            )
            nauo += 1

    lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def write_synthetic_solidworks_step(
    path: Path,
    *,
    assembly: str = "102728-1",
    children: list[tuple[str, int, str]] | None = None,
    nested: list[tuple[str, str, int, str]] | None = None,
) -> Path:
    """
    SolidWorks-style ISO-10303-21: ``PRODUCT (`` space, FORMATION_WITH_SPECIFIED_SOURCE,
    and Time names like ``102727 Tube, Round -20744_102727-4``.
    """
    children = list(
        children
        or [
            ("102727-4", 2, "102727 Tube, Round -20744_102727-4"),
            ("102726-1", 1, "102726 Plate -1_102726-1"),
        ]
    )
    nested = list(nested or [])
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('synthetic solidworks assembly'),'2;1');",
        f"FILE_NAME('{path.name}','2026-08-20T00:00:00',('test'),('test'),"
        f"'SolidWorks','','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
        "ENDSEC;",
        "DATA;",
        "#1=APPLICATION_CONTEXT('automotive design');",
        "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);",
        "#3=PRODUCT_CONTEXT('',#1,'mechanical');",
        "#4=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
    ]
    products: dict[str, tuple[int, int]] = {}
    eid = 10

    def add_product(pn: str, sw_name: str) -> tuple[int, int]:
        nonlocal eid
        if pn in products:
            return products[pn]
        prod, form, defin = eid, eid + 1, eid + 2
        eid += 10
        lines.append(f"#{prod}=PRODUCT ('{sw_name}','{sw_name}','',(#3));")
        lines.append(
            f"#{form}=PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE "
            f"('','',#{prod},.MADE.);"
        )
        lines.append(f"#{defin}=PRODUCT_DEFINITION ('design','',#{form},#4);")
        products[pn] = (prod, defin)
        return products[pn]

    add_product(assembly, f"102728 Weldment -1_{assembly}")
    for pn, _qty, sw_name in children:
        add_product(pn, sw_name)
    for parent_pn, child_pn, _qty, sw_name in nested:
        add_product(parent_pn, f"{parent_pn} Sub -1_{parent_pn}")
        add_product(child_pn, sw_name)

    nauo = 100
    _asm_prod, asm_def = products[assembly]
    for pn, qty, sw_name in children:
        _cprod, cdef = products[pn]
        for _i in range(qty):
            lines.append(
                f"#{nauo}=NEXT_ASSEMBLY_USAGE_OCCURRENCE "
                f"('NAUO{nauo}','{sw_name}','',#{asm_def},#{cdef},$);"
            )
            nauo += 1
    for parent_pn, child_pn, qty, sw_name in nested:
        _pprod, pdef = products[parent_pn]
        _cprod, cdef = products[child_pn]
        for _i in range(qty):
            lines.append(
                f"#{nauo}=NEXT_ASSEMBLY_USAGE_OCCURRENCE "
                f"('NAUO{nauo}','{sw_name}','',#{pdef},#{cdef},$);"
            )
            nauo += 1

    lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def _rows(*pairs: tuple[str, int]) -> list[BomRow]:
    item = ord("A")
    rows = []
    for pn, qty in pairs:
        rows.append(BomRow(item=chr(item), qty=qty, part_no=pn, description="", source="test"))
        item += 1
        if chr(item) in {"I", "O"}:
            item += 1
    return rows


def test_step_reads_direct_nauo_counts_not_nested(tmp_path: Path):
    stp = write_synthetic_assembly_step(
        tmp_path / "102728-1.STEP",
        children=[("102727-4", 2), ("102726-1", 1), ("99999-1", 1)],
        nested=[("99999-1", "88888-1", 4)],
    )
    parsed = extract_step_assembly_part_counts(stp)
    assert parsed["method"] == "next_assembly_usage_occurrence"
    assert parsed["counts"]["102727-4"] == 2
    assert parsed["counts"]["102726-1"] == 1
    # 99999-1 is a same-file sub-weldment — keep it and count Time-PN children once.
    assert parsed["counts"]["99999-1"] == 1
    assert parsed["counts"]["88888-1"] == 4
    assert parsed["piece_count"] == 8
    assert parsed["part_number_count"] == 4
    assert {r["part_no"] for r in parsed.get("nested") or []} == {"88888-1"}


def test_confirm_match_passes(tmp_path: Path):
    stp = write_synthetic_assembly_step(tmp_path / "102728-1.STEP")
    counts = extract_step_assembly_part_counts(stp)
    pdf = _rows(("102727-4", 2), ("102726-1", 1), ("35121-1", 1))
    snapshot = [(r.part_no, r.qty) for r in pdf]
    result = confirm_pdf_bom_against_stp(pdf, counts)
    assert result["skipped"] is False
    assert result["mismatch"] is False
    assert result["piece_count_agree"] is True
    assert result["unique_pn_count_agree"] is True
    assert {r["part_no"] for r in result["matched"]} == {"102727-4", "102726-1", "35121-1"}
    assert result["pdf_only"] == []
    assert result["stp_only"] == []
    assert result["qty_mismatches"] == []
    assert [(r.part_no, r.qty) for r in pdf] == snapshot
    assert "confirms" in (confirm_flag_text(result) or "").lower()


def test_confirm_extra_pdf_pn_flags(tmp_path: Path):
    stp = write_synthetic_assembly_step(
        tmp_path / "102728-1.STEP",
        children=[("102727-4", 2), ("102726-1", 1)],
    )
    pdf = _rows(("102727-4", 2), ("102726-1", 1), ("35122-1", 1))
    result = confirm_pdf_bom_against_stp(pdf, extract_step_assembly_part_counts(stp))
    assert result["mismatch"] is True
    assert [r["part_no"] for r in result["pdf_only"]] == ["35122-1"]
    assert result["stp_only"] == []
    assert result["piece_count_agree"] is False
    assert "PDF-only 35122-1" in (confirm_flag_text(result) or "")


def test_confirm_extra_stp_pn_flags(tmp_path: Path):
    stp = write_synthetic_assembly_step(
        tmp_path / "102728-1.STEP",
        children=[("102727-4", 2), ("102726-1", 1), ("35122-1", 1)],
    )
    pdf = _rows(("102727-4", 2), ("102726-1", 1))
    result = confirm_pdf_bom_against_stp(pdf, extract_step_assembly_part_counts(stp))
    assert result["mismatch"] is True
    assert [r["part_no"] for r in result["stp_only"]] == ["35122-1"]
    assert result["pdf_only"] == []
    assert "STP-only 35122-1" in (confirm_flag_text(result) or "")


def test_confirm_qty_mismatch_flags(tmp_path: Path):
    stp = write_synthetic_assembly_step(
        tmp_path / "102728-1.STEP",
        children=[("102727-4", 2), ("102726-1", 1)],
    )
    pdf = _rows(("102727-4", 1), ("102726-1", 1))
    result = confirm_pdf_bom_against_stp(pdf, extract_step_assembly_part_counts(stp))
    assert result["mismatch"] is True
    assert result["qty_mismatches"] == [
        {"part_no": "102727-4", "pdf_qty": 1, "stp_qty": 2}
    ]
    assert result["unique_pn_count_agree"] is True
    assert result["piece_count_agree"] is False
    text = confirm_flag_text(result) or ""
    assert "102727-4 PDF 1 vs STP 2" in text


def test_confirm_no_stp_skips():
    result = skipped_stp_bom_confirm("No STP on this job — PDF BOM only")
    assert result["skipped"] is True
    assert result["mismatch"] is False
    assert confirm_flag_text(result) is None


def test_takeoff_without_stp_skips_confirm(tmp_path: Path):
    pdf = _write_minimal_pdf(tmp_path / "102728- Weldment.pdf")
    result = run_weld_takeoff(pdf)
    confirm = result.stp_bom_confirm
    assert confirm.get("skipped") is True
    assert confirm.get("mismatch") is False
    payload = result.to_dict()
    assert payload["stp_bom_confirm"]["skipped"] is True
    assert not any("STP/PDF BOM mismatch" in f for f in result.flags)
    assert not any("STP confirms PDF BOM" in f for f in result.flags)


def test_takeoff_with_stp_surfaces_confirm(tmp_path: Path):
    pdf = _write_minimal_pdf(tmp_path / "102728- Weldment.pdf")
    stp = write_synthetic_assembly_step(
        tmp_path / "102728-1.STEP",
        children=[("102727-4", 2), ("102726-1", 1)],
    )
    result = run_weld_takeoff(pdf, stp)
    confirm = result.stp_bom_confirm
    assert confirm.get("skipped") is False
    # PDF harvest is out of scope here; STEP children must still be reported, not written into BOM.
    assert {r["part_no"] for r in confirm.get("stp_only") or []} >= {"102727-4", "102726-1"}
    assert confirm.get("mismatch") is True
    assert any("STP/PDF BOM mismatch" in f for f in result.flags)
    assert result.to_dict()["stp_bom_confirm"]["stp_only"]


def test_normalize_time_solidworks_product_name():
    assert (
        _normalize_step_part_no("102727 Tube, Round -20744_102727-4") == "102727-4"
    )
    assert _normalize_step_part_no("P102727-4") == "102727-4"
    assert _normalize_step_part_no("102728 Weldment -1_102728-1") == "102728-1"
    assert _normalize_step_part_no("Tube, Round -20744_102727_4") == "102727-4"
    assert _normalize_step_part_no("102727 - 4") == "102727-4"
    assert _normalize_step_part_no("FRONT RIGHT KICK RAIL-4213_460270") == "460270"
    assert _normalize_step_part_no("94560 Gate, Fabrication -20752_94560") == "94560"
    assert _normalize_step_part_no("TUBE CAP 2X1-4229_432710") == "432710"
    # SolidWorks feature ids are not the PN.
    assert _normalize_step_part_no("FRONT RIGHT KICK RAIL-4213_460270") != "4213"
    assert _normalize_step_part_no("94560 Gate, Fabrication -20752_94560") != "20752"
    # Do not invent a dash from the leading word.
    assert _normalize_step_part_no("102727") != "10272-7"
    assert _normalize_step_part_no("HEX BOLT 1/2-13") is None


def test_step_keyword_allows_space_before_paren():
    assert _step_keyword("PRODUCT ('102727 Tube, Round -20744_102727-4','x','',(#3))") == "PRODUCT"
    assert _step_keyword("PRODUCT('102727-4','102727-4','',(#3))") == "PRODUCT"
    assert (
        _step_keyword(
            "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ('','',#20,.MADE.)"
        )
        == "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE"
    )
    assert _step_keyword("PRODUCT_CONTEXT('',#1,'mechanical')") == "PRODUCT_CONTEXT"
    assert _step_keyword("NEXT_ASSEMBLY_USAGE_OCCURRENCE ('NAUO1','x','',#12,#22,$)") == (
        "NEXT_ASSEMBLY_USAGE_OCCURRENCE"
    )


def test_solidworks_spaced_product_and_formation_counts_children(tmp_path: Path):
    stp = write_synthetic_solidworks_step(
        tmp_path / "102728-1.STEP",
        children=[
            ("102727-4", 2, "102727 Tube, Round -20744_102727-4"),
            ("102726-1", 1, "102726 Plate -1_102726-1"),
            ("99999-1", 1, "99999 Sub -1_99999-1"),
        ],
        nested=[("99999-1", "88888-1", 4, "88888 Nested -1_88888-1")],
    )
    parsed = extract_step_assembly_part_counts(stp)
    assert parsed["method"] == "next_assembly_usage_occurrence"
    assert parsed["counts"].get("102727-4") == 2
    assert parsed["counts"].get("102726-1") == 1
    assert parsed["counts"].get("99999-1") == 1
    assert parsed["counts"].get("88888-1") == 4
    assert "102728-1" not in parsed["counts"]
    assert parsed["part_number_count"] == 4
    assert parsed["piece_count"] == 8
    assert {r["part_no"] for r in parsed.get("nested") or []} == {"88888-1"}
    # Must not collapse to filename-only product_names with 0 children.
    assert parsed["part_number_count"] > 0
    assert "10272-7" not in parsed["counts"]


def test_skipped_name_recovery_underscore_and_shape(tmp_path: Path):
    """Recover Time PNs from underscore / SHAPE_REPRESENTATION names; dump skips."""
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('synthetic'),'2;1');",
        "FILE_NAME('102728-1.STEP','2026-08-20T00:00:00',('t'),('t'),'SolidWorks','','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
        "ENDSEC;",
        "DATA;",
        "#1=APPLICATION_CONTEXT('automotive design');",
        "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);",
        "#3=PRODUCT_CONTEXT('',#1,'mechanical');",
        "#4=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
        "#10=PRODUCT ('102728 Weldment -1_102728-1','102728 Weldment -1_102728-1','',(#3));",
        "#11=PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ('','',#10,.MADE.);",
        "#12=PRODUCT_DEFINITION ('design','',#11,#4);",
        # Underscore PN — previously unparseable if dash form is missing.
        "#20=PRODUCT ('Tube, Round -20744_102727_4','Tube, Round -20744_102727_4','',(#3));",
        "#21=PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ('','',#20,.MADE.);",
        "#22=PRODUCT_DEFINITION ('design','',#21,#4);",
        # PRODUCT strings have no PN; SHAPE_REPRESENTATION holds the Time name.
        "#30=PRODUCT ('Imported1','Imported1','',(#3));",
        "#31=PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ('','',#30,.MADE.);",
        "#32=PRODUCT_DEFINITION ('design','',#31,#4);",
        "#33=PRODUCT_DEFINITION_SHAPE ('','',#32);",
        "#34=SHAPE_REPRESENTATION ('102725 Plate -9_102725-1',(#1),#1);",
        "#35=SHAPE_DEFINITION_REPRESENTATION (#33,#34);",
        # Hardware — must stay skipped, not invented.
        "#40=PRODUCT ('HEX BOLT 1/2-13','HEX BOLT 1/2-13','',(#3));",
        "#41=PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ('','',#40,.MADE.);",
        "#42=PRODUCT_DEFINITION ('design','',#41,#4);",
        "#100=NEXT_ASSEMBLY_USAGE_OCCURRENCE ('NAUO1','Tube, Round -20744_102727_4','',#12,#22,$);",
        "#101=NEXT_ASSEMBLY_USAGE_OCCURRENCE ('NAUO2','Tube, Round -20744_102727_4','',#12,#22,$);",
        "#102=NEXT_ASSEMBLY_USAGE_OCCURRENCE ('NAUO3','Imported1','',#12,#32,$);",
        "#103=NEXT_ASSEMBLY_USAGE_OCCURRENCE ('NAUO4','HEX BOLT 1/2-13','',#12,#42,$);",
        "ENDSEC;",
        "END-ISO-10303-21;",
    ]
    stp = tmp_path / "102728-1.STEP"
    stp.write_text("\n".join(lines) + "\n", encoding="ascii")
    parsed = extract_step_assembly_part_counts(stp)
    assert parsed["method"] == "next_assembly_usage_occurrence"
    assert parsed["counts"].get("102727-4") == 2
    assert parsed["counts"].get("102725-1") == 1
    assert "10272-7" not in parsed["counts"]
    assert parsed["skipped_count"] == 1
    raw = parsed["skipped_names"][0]
    assert "HEX BOLT" in (raw.get("product_name") or raw.get("nauo_name") or "")


def test_nested_weldment_children_not_vanished_or_double_counted(tmp_path: Path):
    stp = write_synthetic_solidworks_step(
        tmp_path / "102728-1.STEP",
        children=[
            ("102727-4", 2, "102727 Tube, Round -20744_102727-4"),
            ("102711-1", 1, "102711 Weldment -1_102711-1"),
        ],
        nested=[
            ("102711-1", "102712-1", 2, "102712 Plate -1_102712-1"),
            ("102711-1", "102713-1", 1, "102713 Gusset -1_102713-1"),
        ],
    )
    parsed = extract_step_assembly_part_counts(stp)
    assert parsed["counts"].get("102727-4") == 2
    assert parsed["counts"].get("102711-1") == 1
    assert parsed["counts"].get("102712-1") == 2
    assert parsed["counts"].get("102713-1") == 1
    assert parsed["piece_count"] == 6
    assert parsed["part_number_count"] == 4
    nested_pns = {r["part_no"] for r in parsed.get("nested") or []}
    assert nested_pns == {"102712-1", "102713-1"}
    assert all(r["parent"] == "102711-1" for r in parsed["nested"])
    # Do not treat nested qty as a second copy of the weldment itself.
    assert parsed["counts"]["102711-1"] == 1


def test_trailing_underscore_time_pn_from_live_name_forms(tmp_path: Path):
    """``_460270`` / ``_94560`` are Time PNs; SolidWorks ``-4213`` is not."""
    stp = write_synthetic_solidworks_step(
        tmp_path / "102728-1.STEP",
        children=[
            ("102727-4", 2, "102727 Tube, Round -20744_102727-4"),
            ("460270", 1, "FRONT RIGHT KICK RAIL-4213_460270"),
            ("94560", 2, "94560 Gate, Fabrication -20752_94560"),
        ],
    )
    parsed = extract_step_assembly_part_counts(stp)
    assert parsed["counts"].get("102727-4") == 2
    assert parsed["counts"].get("460270") == 1
    assert parsed["counts"].get("94560") == 2
    assert "4213" not in parsed["counts"]
    assert "20752" not in parsed["counts"]
    assert parsed["skipped_count"] == 0
    pdf = _rows(("102727-4", 2), ("460270", 1), ("94560", 2))
    snapshot = [(r.part_no, r.qty) for r in pdf]
    result = confirm_pdf_bom_against_stp(pdf, parsed)
    assert result["mismatch"] is False
    assert [(r.part_no, r.qty) for r in pdf] == snapshot


def test_solidworks_step_confirm_does_not_pad_pdf(tmp_path: Path):
    stp = write_synthetic_solidworks_step(tmp_path / "102728-1.STEP")
    pdf = _rows(("102727-4", 2), ("102726-1", 1))
    snapshot = [(r.part_no, r.qty) for r in pdf]
    result = confirm_pdf_bom_against_stp(pdf, extract_step_assembly_part_counts(stp))
    assert result["skipped"] is False
    assert {r["part_no"] for r in result["matched"]} == {"102727-4", "102726-1"}
    assert [(r.part_no, r.qty) for r in pdf] == snapshot
    assert not any(r.part_no == "88888-1" for r in pdf)
