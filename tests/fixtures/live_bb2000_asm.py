"""BB2000-ASM first /part/create FileList — nested *ASM (ad38881).

Do not PATCH quote a9497a26-cba8-4ec9-a849-cb8bef81cbcc / BB2000-ASM.
Cited live names: 10× BB2000-ASM, 6× BB1000-ASM, 2× BB1010-ASM, Root.
grid_dxf_row_count=19 == FileList 19. Finish was skipped — must invoke
OnAddDXFClick. BB1000-ASM / BB1010-ASM are nested; job-PN BB2000-ASM
leaves are not. Next unused after the page fn fires: EHB3112.
"""

from __future__ import annotations

# Cited live names (order: Root first, then job-PN leaves, then nests).
LIVE_BB2000_ASM_NAMES: list[str] = (
    ["Root"]
    + ["BB2000-ASM"] * 10
    + ["BB1000-ASM"] * 6
    + ["BB1010-ASM"] * 2
)

assert len(LIVE_BB2000_ASM_NAMES) == 19
