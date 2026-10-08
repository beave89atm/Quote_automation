"""Kyle's flat-pattern formula. This is the file to edit.

``flat_length_in`` is the only formula. It ships unset: it returns None.
There is no default K-factor and no other math behind it.

When the real formula is ready, make ``flat_length_in`` return the flat
length in inches. Until it does, a formed part stops with
``FLAG: formed part — flat pattern formula not set`` and no quote is created.
"""

from __future__ import annotations


def flat_length_in(
    legs_in: tuple[float, ...],
    thickness_in: float,
    inside_radius_in: float,
    bend_count: int,
) -> float | None:
    """Return the flat length in inches, or None while this is unset.

    legs_in
        Leg lengths in inches, in order along the part.
        A bracket with legs 2.00 and 3.00 is ``(2.0, 3.0)``.
    thickness_in
        Material thickness in inches.
    inside_radius_in
        Inside bend radius in inches.
    bend_count
        How many 90 degree bends are in one plane.

    The flat width comes from the drawing. Do not return the width.

    Example of how a formula would look. This is not shop math, and it
    does not run. Leave the ``return None`` in place until the real
    formula replaces it:

        return sum(legs_in) + (0.1 * bend_count)
    """
    return None
