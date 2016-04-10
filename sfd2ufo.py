#!/usr/bin/python2
from defcon import Font
import fontforge

class SFDFont(Font):

    def __init__(self, path):
        self._sfd = fontforge.open(path)
        self._ufo = Font()

        self._build_info()
        self._build_glyphs()

    def __del__(self):
        self._sfd.close()

    def ufo(self):
        return self._ufo

    def _build_info(self):
        info = self._ufo.info
        info.familyName = self._sfd.familyname
        #info.styleName = self._sfd
        if "." in self._sfd.version:
            info.versionMajor = int(self._sfd.version.split(".")[0])
            info.versionMinor = int(self._sfd.version.split(".")[1])
        else:
            info.versionMajor = int(self._sfd.version)
            info.versionMinor = 0
        #info.year = self._sfd

        info.copyright = self._sfd.copyright
        #info.trademark = self._sfd
        info.unitsPerEm = self._sfd.em
        info.ascender = self._sfd.ascent
        info.descender = -self._sfd.descent
        info.italicAngle = self._sfd.italicangle
        if self._sfd.capHeight > 0:
            info.capHeight = self._sfd.capHeight
        if self._sfd.xHeight > 0:
            info.xHeight = self._sfd.xHeight
        info.note = self._sfd.comment

    def _build_glyphs(self):
        for sfdglyph in self._sfd.glyphs():
            ufoglyph = self._ufo.newGlyph(sfdglyph.name)
            ufopen = ufoglyph.getPen()
            ufoglyph.width = sfdglyph.width
            if sfdglyph.unicode > 0:
                ufoglyph.unicode = sfdglyph.unicode
            sfdglyph.draw(ufopen)

if __name__ == "__main__":
    import sys
    font = SFDFont(sys.argv[1])
    ufo = font.ufo()
    ufo.save(sys.argv[2])
