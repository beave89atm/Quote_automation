"""Tests for STEP mm→inch conversion."""

from secturafab.step_units import convert_step_text_mm_to_inch, step_uses_millimetres


def test_step_mm_detection_and_conversion():
    sample = """
ISO-10303-21;
HEADER;ENDSEC;
DATA;
#1=CARTESIAN_POINT('',(25.4,50.8,0.));
#2=(
LENGTH_UNIT()
NAMED_UNIT(*)
SI_UNIT(.MILLI.,.METRE.)
);
#3=LENGTH_MEASURE(25.4);
ENDSEC;
END-ISO-10303-21;
"""
    assert step_uses_millimetres(sample)
    out, changed = convert_step_text_mm_to_inch(sample)
    assert changed
    assert "INCH" in out.upper()
    compact = out.replace(" ", "")
    assert "CARTESIAN_POINT('',(1,2,0.))" in compact or "CARTESIAN_POINT('',(1.,2.,0.))" in compact
