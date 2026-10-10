"""Pure 8x8 LED mapping verification for click-driven physical pixel probe.

Observed coordinates are LEFT->RIGHT and UP->DOWN in the normal viewing
orientation, independent of the USB packet geometry (4 native rows x 16).
This module does not access USB or modify user settings.
"""
from __future__ import annotations

from PIL import Image
from seiren_emote_bridge import TRANSFORMS, transform_frame, inverse_transform

# Eight anchor points across first/second and last/penultimate logical rows.
DEFAULT_PROBE_POINTS = (0, 7, 8, 15, 48, 55, 56, 63)
EXTRA_PROBE_POINTS = (16, 23, 24, 31, 32, 39, 40, 47)


def physical_coordinate_after(transform: str, index: int) -> tuple[int, int]:
    """Where an input pixel lands after a D4 rotation/reflection."""
    if transform not in TRANSFORMS or not 0 <= index < 64:
        raise ValueError('Invalid transform or pixel index')
    marker = Image.new('L', (8, 8), 0)
    marker.putpixel((index % 8, index // 8), 255)
    box = transform_frame(marker, transform).getbbox()
    if box is None:
        raise RuntimeError('Marker disappeared')
    return box[0], box[1]


def infer_orientation(points: dict[int, tuple[int, int] | None]) -> dict:
    """Estimate physical transform and its inverse (GUI correction).

    Results remain tentative until user confirms a real preview image.
    Unknown coordinates are ignored. Duplicate physical coordinates and
    non-D4 mappings are flagged, not silently accepted.
    """
    observed = {}
    for raw_i, position in points.items():
        if position is None:
            continue
        i = int(raw_i)
        if not 0 <= i < 64:
            raise ValueError('Pixel index outside 0..63')
        if len(position) != 2 or any(not isinstance(v, int) or not 0 <= v < 8 for v in position):
            raise ValueError('Coordinates must be integers from 0 to 7')
        observed[i] = tuple(position)
    summary = {'count': len(observed), 'candidates': [], 'physical': None,
               'correction': None, 'duplicates': [], 'message': ''}
    taken = {}
    for index, coord in observed.items():
        if coord in taken:
            summary['duplicates'].append((taken[coord], index))
        else:
            taken[coord] = index
    if summary['duplicates']:
        summary['message'] = 'The same grid position was selected for multiple pixels. Check the highlighted positions if uncertain.'
        return summary
    matches = [t for t in TRANSFORMS if all(physical_coordinate_after(t, i) == pos
                                           for i, pos in observed.items())]
    summary['candidates'] = matches
    if len(observed) < 4:
        summary['message'] = f'At least 4 measurements are needed ({len(observed)}/4).' 
    elif len(matches) == 1:
        physical = matches[0]
        summary['physical'] = physical
        summary['correction'] = inverse_transform(physical)
        summary['message'] = 'Mapping is consistent with rotation/reflection: ' + physical
    elif len(matches) == 0:
        summary['message'] = ('The measurements do not match a simple rotation/mirror correction. '
                              'Recheck the selections. Nothing was saved.')
    else:
        summary['message'] = 'More points are needed to identify the orientation.'
    return summary
