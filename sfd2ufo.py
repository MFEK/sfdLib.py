#!/usr/bin/python2
from defcon import Font
import fontforge
import sys

def fillInfo(sfd, ufo):
    info = ufo.info
    info.familyName = sfd.familyname
    #info.styleName = sfd
    if "." in sfd.version:
        info.versionMajor = int(sfd.version.split(".")[0])
        info.versionMinor = int(sfd.version.split(".")[1])
    else:
        info.versionMajor = int(sfd.version)
        info.versionMinor = 0
    #info.year = sfd

    info.copyright = sfd.copyright
    #info.trademark = sfd
    info.unitsPerEm = sfd.em
    info.ascender = sfd.ascent
    info.descender = -sfd.descent
    info.italicAngle = sfd.italicangle
    if sfd.capHeight > 0:
        info.capHeight = sfd.capHeight
    if sfd.xHeight > 0:
        info.xHeight = sfd.xHeight
    info.note = sfd.comment

def fillGlyphs(sfd, ufo):
    for sfdglyph in sfd.glyphs():
        ufoglyph = ufo.newGlyph(sfdglyph.name)
        ufopen = ufoglyph.getPen()
        ufoglyph.width = sfdglyph.width
        if sfdglyph.unicode > 0:
            ufoglyph.unicode = sfdglyph.unicode
        sfdglyph.draw(ufopen)

sfd = fontforge.open(sys.argv[1])
ufo = Font()

fillInfo(sfd, ufo)
fillGlyphs(sfd, ufo)

ufo.save(sys.argv[2])
