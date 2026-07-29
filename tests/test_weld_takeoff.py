from pathlib import Path

from quote_core.weld.takeoff import run_weld_takeoff

ROOT = Path(__file__).resolve().parents[1]


def test_takeoff_80341805_if_present():
    pdf = ROOT / "references" / "80341805" / "80341805.pdf"
    stp = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\MAC Manufacturing\80341805\80341805.stp"
    )
    if not pdf.exists():
        # copied earlier in project history; skip if absent
        return
    result = run_weld_takeoff(pdf, stp if stp.exists() else None)
    assert result.sizes_found or result.items
    assert isinstance(result.flags, list)


def test_takeoff_73476047_if_present():
    pdf = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\MAC Manufacturing\73476047\73476047-FAB Packet.pdf"
    )
    stp = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\MAC Manufacturing\73476047\73476047.STEP"
    )
    if not pdf.exists():
        return
    result = run_weld_takeoff(pdf, stp if stp.exists() else None)
    assert "1/4" in result.sizes_found or any(i.size == "1/4" for i in result.items)
    assert result.to_dict()["total_inches"] >= 0
