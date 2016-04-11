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
        versionMajor = ""
        versionMinor = ""
        if "." in self._sfd.version:
            versionMajor, versionMinor = self._sfd.version.split(".")
        else:
            versionMajor = self._sfd.version
        if versionMajor.isdigit():
            info.versionMajor = int(versionMajor)
        if versionMinor.isdigit():
            info.versionMinor = int(versionMinor)
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
            glyph = self._ufo.newGlyph(sfdglyph.name)
            pen = glyph.getPen()
            glyph.width = sfdglyph.width
            if sfdglyph.unicode > 0:
                glyph.unicode = sfdglyph.unicode
                glyph.unicodes.append(glyph.unicode)
                if sfdglyph.altuni:
                    for altuni in sfdglyph.altuni:
                        # TODO: what about variation selectors?
                        if altuni[1] == 0xfe00:
                            glyph.unicodes.append(altuni[0])
            sfdglyph.draw(pen)

if __name__ == "__main__":
    import sys
    font = SFDFont(sys.argv[1])
    ufo = font.ufo()
    ufo.save(sys.argv[2])
