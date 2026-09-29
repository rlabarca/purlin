"""The one check of what Purlin prints: no emoji and no pictograph.

`specs/instructions/purlin_output.md` holds one rule: no file under
`scripts/` or `templates/` carries a character with the Unicode property
`Extended_Pictographic`, or U+FE0F, other than `▶`. Python's own `re` cannot
name that property, so the ranges are written out below as a table, taken
from Unicode's `emoji-data.txt`, with adjacent ranges joined.
"""

import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FOLDERS = ('scripts', 'templates')

# Extended_Pictographic, from Unicode's emoji-data.txt: (first, last).
EXTENDED_PICTOGRAPHIC = (
    (0x00A9, 0x00A9), (0x00AE, 0x00AE), (0x203C, 0x203C), (0x2049, 0x2049),
    (0x2122, 0x2122), (0x2139, 0x2139), (0x2194, 0x2199), (0x21A9, 0x21AA),
    (0x231A, 0x231B), (0x2328, 0x2328), (0x2388, 0x2388), (0x23CF, 0x23CF),
    (0x23E9, 0x23F3), (0x23F8, 0x23FA), (0x24C2, 0x24C2), (0x25AA, 0x25AB),
    (0x25B6, 0x25B6), (0x25C0, 0x25C0), (0x25FB, 0x25FE), (0x2600, 0x2605),
    (0x2607, 0x2612), (0x2614, 0x2685), (0x2690, 0x2705), (0x2708, 0x2712),
    (0x2714, 0x2714), (0x2716, 0x2716), (0x271D, 0x271D), (0x2721, 0x2721),
    (0x2728, 0x2728), (0x2733, 0x2734), (0x2744, 0x2744), (0x2747, 0x2747),
    (0x274C, 0x274C), (0x274E, 0x274E), (0x2753, 0x2755), (0x2757, 0x2757),
    (0x2763, 0x2767), (0x2795, 0x2797), (0x27A1, 0x27A1), (0x27B0, 0x27B0),
    (0x27BF, 0x27BF), (0x2934, 0x2935), (0x2B05, 0x2B07), (0x2B1B, 0x2B1C),
    (0x2B50, 0x2B50), (0x2B55, 0x2B55), (0x3030, 0x3030), (0x303D, 0x303D),
    (0x3297, 0x3297), (0x3299, 0x3299), (0x1F000, 0x1F0FF),
    (0x1F10D, 0x1F10F), (0x1F12F, 0x1F12F), (0x1F16C, 0x1F171),
    (0x1F17E, 0x1F17F), (0x1F18E, 0x1F18E), (0x1F191, 0x1F19A),
    (0x1F1AD, 0x1F1E5), (0x1F201, 0x1F20F), (0x1F21A, 0x1F21A),
    (0x1F22F, 0x1F22F), (0x1F232, 0x1F23A), (0x1F23C, 0x1F23F),
    (0x1F249, 0x1F3FA), (0x1F400, 0x1F53D), (0x1F546, 0x1F64F),
    (0x1F680, 0x1F6FF), (0x1F774, 0x1F77F), (0x1F7D5, 0x1F7FF),
    (0x1F80C, 0x1F80F), (0x1F848, 0x1F84F), (0x1F85A, 0x1F85F),
    (0x1F888, 0x1F88F), (0x1F8AE, 0x1F8FF), (0x1F90C, 0x1F93A),
    (0x1F93C, 0x1F945), (0x1F947, 0x1FAFF), (0x1FC00, 0x1FFFD),
)
VARIATION_SELECTOR_16 = 0xFE0F
ALLOWED = {ord('▶')}  # the one glyph Purlin prints that is a pictograph


def is_pictograph(character):
    """True for U+FE0F and any character with Extended_Pictographic."""
    code = ord(character)
    if code == VARIATION_SELECTOR_16:
        return True
    return any(first <= code <= last for first, last in EXTENDED_PICTOGRAPHIC)


def tracked_files(root, folders=FOLDERS):
    """Every file git tracks under `folders`, as paths relative to `root`."""
    listed = subprocess.run(['git', 'ls-files', '-z', '--', *folders],
                            cwd=root, capture_output=True, check=True)
    return [rel for rel in listed.stdout.decode('utf-8').split('\0') if rel]


def pictographs(root, rels):
    """`<path>:<line>: U+XXXX` for each pictograph in the files `rels`."""
    found = []
    for rel in rels:
        with open(os.path.join(root, rel), 'rb') as handle:
            text = handle.read().decode('utf-8', errors='replace')
        for number, line in enumerate(text.splitlines(), 1):
            found += ['%s:%d: U+%04X' % (rel, number, ord(character))
                      for character in line
                      if is_pictograph(character)
                      and ord(character) not in ALLOWED]
    return found


class TestNoPictograph:

    # purlin: purlin_output PROOF-1
    def test_no_tracked_file_under_scripts_or_templates_holds_a_pictograph(
            self, tmp_path):
        rels = tracked_files(ROOT)
        assert any(rel.startswith('scripts/') for rel in rels), rels
        assert any(rel.startswith('templates/') for rel in rels), rels
        assert pictographs(ROOT, rels) == []
        # The glyphs Purlin prints pass; a check mark, a warning sign, an
        # emoji and a bare variation selector are each found.
        assert not any(is_pictograph(c) and ord(c) not in ALLOWED
                       for c in '→▼▲─·←▶')
        (tmp_path / 'out.py').write_text(
            'print("✅ done")\nprint("⚠ careful")\n'
            'print("\U0001f680")\nprint("❤️")\n', encoding='utf-8')
        assert pictographs(str(tmp_path), ['out.py']) == [
            'out.py:1: U+2705', 'out.py:2: U+26A0', 'out.py:3: U+1F680',
            'out.py:4: U+2764', 'out.py:4: U+FE0F']
