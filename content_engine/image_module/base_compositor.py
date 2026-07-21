"""
content_engine/image_module/base_compositor.py -- shared font registry
for the two image compositors.

compositor.py (non-IPO articles) and ipo_compositor.py (IPO articles)
each carried their own byte-identical copy of a FONTS dict and
font-loading fallback logic. Consolidated here so the well-known
font-casing bug (FONTS maps 'extrabold'/'regular' to ExtraBold.ttf/
Regular.ttf, but the real files in content_engine/fonts/ are lowercase --
works on case-insensitive filesystems like Windows, silently falls back
to a DejaVu/Liberation font on case-sensitive ones like Linux containers)
only has one place to be fixed, if it's ever fixed.

Deliberately NOT shared here: each file's own compose_image()/
compose_ipo_image() entry points, and their (slightly different)
_save_both_formats() JPEG/WebP save helpers -- compositor.py's applies
subsampling=0 to Instagram JPEGs and ipo_compositor.py's doesn't, a
pre-existing minor inconsistency between the two that this refactor
leaves untouched rather than silently "fixing" (out of scope for a
structural-only change).
"""

import os
from PIL import ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class BaseImageCompositor:
    """Shared font path registry + loader used by both compositors."""

    FONTS = {
        'extrabold': os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf'),
        'bold':      os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf'),
        'regular':   os.path.join(BASE_DIR, '../fonts/Regular.ttf'),
    }

    _FALLBACK_FONTS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    @classmethod
    def get_font(cls, style: str = 'regular', size: int = 24) -> ImageFont.FreeTypeFont:
        """
        Load a TrueType font at the given point size.

        Args:
            style: key into FONTS ('extrabold', 'bold', 'regular'). Unknown
                styles fall straight through to the fallback fonts below.
            size: point size to render at.

        Returns:
            An ImageFont.FreeTypeFont, or ImageFont.load_default() if none
            of the paths (including the DejaVu/Liberation fallbacks) exist.

        Gotcha: see this module's docstring re: the FONTS casing mismatch
            with the actual lowercase filenames in content_engine/fonts/.
        """
        path = cls.FONTS.get(style)
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
        for f in cls._FALLBACK_FONTS:
            if os.path.exists(f):
                print(f"[FONT] Using fallback: {f}")
                return ImageFont.truetype(f, size)
        return ImageFont.load_default()
