#
# encoding: utf-8

from fontTools.misc.py23 import *

from ufoLib.validators import groupsValidator

FONTFORGE_PREFIX = "org.fontforge"

def parseVersion(version):
    versionMajor = ""
    versionMinor = ""
    if ";" in version:
        # Some fonts embed stuff after ";" in the version, strip it away.
        version = version.split(";")[0]
    if "." in version:
        versionMajor, versionMinor = version.split(".", 1)
    else:
        versionMajor = version

    versionMajor = int(versionMajor) if versionMajor.isdigit() else None
    versionMinor = int(versionMinor) if versionMinor.isdigit() else None

    return versionMajor, versionMinor


def parseAltuni(altuni, ignore_uvs):
    unicodes = []
    for uni, uvs, _ in altuni:
        if not ignore_uvs:
            assert uvs == -1, "Glyph %s uses variation selector "  \
                "U+%04X, UFO doesn’t support this!" % (name, uvs)
        if uvs in (-1, 0xffffffff):
            unicodes.append(uni)

    return unicodes


def parseAnchorPoint(anchor):
    name, kind, x, y = anchor[:4]
    if kind == "mark":
        name = "_" + name
    elif kind == "ligature":
        index = anchor[4]
        name = "%s_%s" % (name, index)
    elif kind in ["entry", "exit"]:
        name = "%s_%s" % (name, kind)

    return dict(name=name, x=x, y=y)


def parseColor(color):
    r = (color & 255) / 255.
    g = ((color >> 8) & 255) / 255.
    b = ((color >> 16) & 255) / 255.
    a = 1.0
    return (r, g, b, a)


def getFontBounds(bounds):
    """Calculate FF font bounds."""

    bbox = [int(round(v)) for v in bounds]
    return dict(xMin=bbox[0], yMin=bbox[1], xMax=bbox[2], yMax=bbox[3])


def kernClassesToUFO(subtables, prefix="public"):
    groups = {}
    kerning = {}

    for i, (groups1, groups2, kerns) in enumerate(subtables):
        for j, group1 in enumerate(groups1):
            for k, group2 in enumerate(groups2):
                kern = kerns[(j * len(groups2)) + k]
                if group1 is not None and group2 is not None and kern != 0:
                    name1 = "%s.kern1.kc%d_%d" % (prefix, i, j)
                    name2 = "%s.kern2.kc%d_%d" % (prefix, i, k)
                    if name1 not in groups:
                        groups[name1] = group1
                    if name2 not in groups:
                        groups[name2] = group2
                    assert groups[name1] == group1
                    assert groups[name2] == group2
                    kerning[name1, name2] = kern

    return groups, kerning

def processKernClasses(font, subtables):
    groups, kerning = kernClassesToUFO(subtables)
    valid, _ = groupsValidator(groups)
    if not valid:
        # If groupsValidator() thinks these groups are invalid, ufoLib will
        # refuse to save the files. Most likely the cause is glyphs
        # appearing in several kerning groups. Since UFO kerning is too
        # dumb to represent this, lets cheat on ufoLib and use our private
        # prefix for group names which would prevent it from attempting to
        # “validate” them.
        groups, kerning = kernClassesToUFO(subtables, FONTFORGE_PREFIX)

    font.groups.update(groups)
    font.kerning.update(kerning)
