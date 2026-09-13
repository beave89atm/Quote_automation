"""15911-14 style flat-bar Linear STEP — not strong_plate / Cad Contours.

Live 15911-14 (and 15911-7/9/11, 10289-5) is ~1.75×5×42.5 in flat-bar.
Sectura ProductType=bar. invent=false; do not invent Contours/InternalData.
Q10333/36/38/39/44/46 leftovers stay forbidden/unpatched.
"""

from __future__ import annotations

from typing import Any

# Robust vertex / plane bbox (inches). Hole-axis CARTESIAN_POINTs must not
# expand this into a strong_plate footprint.
FLAT_BAR_15911_DIMS = (42.5, 5.0, 1.75)
# H.6.38-like thin laser plate (Q10333 family). Cad Contours stays valid.
H638_LIKE_PLATE_DIMS = (18.0, 12.0, 0.1875)

LIVE_15911_BAR_VS_PLATE = {
    "part_numbers": ("15911-14", "15911-7", "15911-9", "15911-11", "10289-5"),
    "stock": "flat_bar",
    "product_type": "bar",
    "dims_in": FLAT_BAR_15911_DIMS,
    "bbox_must_use": ("vertex", "plane"),
    "bbox_must_not_use": "all_CARTESIAN_POINT",
    "contours_path": False,
    "invented": False,
}


def live_15911_bar_vs_plate() -> dict[str, Any]:
    return dict(LIVE_15911_BAR_VS_PLATE)


def _box_step(
    *,
    length: float,
    width: float,
    thick: float,
    extra_cartesian: list[tuple[float, float, float]] | None = None,
    name: str = "",
) -> str:
    """Minimal STEP: 8 vertices, 6 opposing PLANEs, optional hole-axis points."""
    corners = (
        (0.0, 0.0, 0.0),
        (length, 0.0, 0.0),
        (length, width, 0.0),
        (0.0, width, 0.0),
        (0.0, 0.0, thick),
        (length, 0.0, thick),
        (length, width, thick),
        (0.0, width, thick),
    )
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION((''),'2;1');",
        f"FILE_NAME('{name or 'box.stp'}','',(''),(''),'','','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
        "ENDSEC;",
        "DATA;",
        "#1=(LENGTH_UNIT()NAMED_UNIT(*)CONVERSION_BASED_UNIT('INCH',#2));",
        "#2=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#3);",
        "#3=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT($,.METRE.));",
        "#10=DIRECTION('x',(1.,0.,0.));",
        "#11=DIRECTION('y',(0.,1.,0.));",
        "#12=DIRECTION('z',(0.,0.,1.));",
    ]
    eid = 20
    corner_ids: list[int] = []
    for i, (x, y, z) in enumerate(corners, start=1):
        lines.append(f"#{eid}=CARTESIAN_POINT('v{i}',({x},{y},{z}));")
        corner_ids.append(eid)
        eid += 1
    vertex_ids: list[int] = []
    for cid in corner_ids:
        lines.append(f"#{eid}=VERTEX_POINT('',#{cid});")
        vertex_ids.append(eid)
        eid += 1
    # Origin + opposite face for each axis.
    plane_origins = (
        (corner_ids[0], 10, "len0"),
        (corner_ids[1], 10, "len1"),
        (corner_ids[0], 11, "wid0"),
        (corner_ids[3], 11, "wid1"),
        (corner_ids[0], 12, "thk0"),
        (corner_ids[4], 12, "thk1"),
    )
    for origin, direction, label in plane_origins:
        axis_id = eid
        lines.append(
            f"#{axis_id}=AXIS2_PLACEMENT_3D('{label}',#{origin},#{direction},#10);"
        )
        eid += 1
        lines.append(f"#{eid}=PLANE('{label}',#{axis_id});")
        eid += 1
    for i, (x, y, z) in enumerate(extra_cartesian or [], start=1):
        lines.append(f"#{eid}=CARTESIAN_POINT('hole_axis_{i}',({x},{y},{z}));")
        eid += 1
    lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
    return "\n".join(lines) + "\n"


def flat_bar_15911_step_text() -> str:
    """1.75×5×42.5 bar plus far hole-axis points (inflate all-CARTESIAN bbox)."""
    l, w, t = FLAT_BAR_15911_DIMS
    return _box_step(
        length=l,
        width=w,
        thick=t,
        extra_cartesian=[
            (l / 2.0, w / 2.0, 80.0),
            (l / 2.0, w / 2.0, -60.0),
            (l / 2.0, 40.0, t / 2.0),
        ],
        name="15911-14.STEP",
    )


def h638_like_plate_step_text() -> str:
    l, w, t = H638_LIKE_PLATE_DIMS
    return _box_step(length=l, width=w, thick=t, name="H.6.38.STEP")
