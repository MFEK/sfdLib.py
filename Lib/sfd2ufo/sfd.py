#
# encoding: utf-8

from fontTools.misc.py23 import *

import codecs
import os
import re

from datetime import datetime

from . import parseAltuni, parseAnchorPoint, parseColor, parseVersion
from . import FONTFORGE_PREFIX


LAYER_RE = re.compile('(.)\s+(.)\s+(".*?.")\s+(.?)')
QUOTED_LIST_RE = re.compile('(".*?")')


def toFloat(value):
    """Convert value to integer if possible, else to float."""
    try:
        return int(value)
    except ValueError:
        return float(value)

_INBASE64 = [
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, 63,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1,
    -1,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, -1, -1, -1, -1, -1,
    -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
]

def _SFDReadUTF7(data):
    out = b""

    if data and not isinstance(data[0], int): # Python 2
        data = [ord(c) for c in data]

    prev_cnt = 0
    prev = 0

    ch1 = 0
    ch2 = 0
    ch3 = 0
    ch4 = 0

    i = 0
    inside = False
    while i < len(data):
        ch1 = data[i]
        i += 1

        done = False

        if not done and not inside:
            if ch1 == ord("+"):
                ch1 = data[i]
                i += 1
                if ch1 == ord("-"):
                    ch1 = ord("+")
                    done = True
                else:
                    inside = True
                    prev_cnt = 0
            else:
                done = True

        if not done:
            if ch1 == ord("-"):
                inside = False
            elif _INBASE64[ch1] == -1:
                inside = False
                done = True
            else:
                ch1 = _INBASE64[ch1]
                ch2 = _INBASE64[data[i]]
                i += 1
                if ch2 == -1:
                    i -= 1
                    ch2 = 0
                    ch3 = 0
                    ch4 = 0
                else:
                    ch3 = _INBASE64[data[i]]
                    i += 1
                    if ch3 == -1:
                        i -= 1
                        ch3 = 0
                        ch4 = 0
                    else:
                        ch4 = _INBASE64[data[i]]
                        i += 1
                        if ch4 == -1:
                            i -= 1
                            ch4 = 0

                ch1 = (ch1 << 18) | (ch2 << 12) | (ch3 << 6) | ch4

                if prev_cnt == 0:
                    prev = ch1 & 0xff
                    ch1 >>= 8
                    prev_cnt = 1
                else:
                    ch1 |= (prev << 24)
                    prev = (ch1 & 0xffff)
                    ch1 = (ch1 >> 16) & 0xffff
                    prev_cnt = 2
                done = True

        if done:
            out += unichr(ch1).encode("utf-8")
        if prev_cnt == 2:
            prev_cnt = 0
            if prev != 0:
                out += unichr(prev).encode("utf-8")

    return out.decode("utf-8")


def _sfdUTF7(string):
    return _SFDReadUTF7(string.strip('"').encode("ascii"))#.decode("utf-7")


def _parsePrivateDict(font, data):
    info = font.info
    n = int(data.pop(0))
    assert len(data) == n

    StdHW = StdVW = None

    for line in data:
        key, n, value = [v.strip() for v in line.split(" ", 2)]
        assert len(value) == int(n)

        if value.startswith("[") and value.endswith("]"):
            value = [toFloat(n) for n in value[1:-1].split(" ")]
        else:
            value = toFloat(value)

        if   key == "BlueValues":
            info.postscriptBlueValues = value
        elif key == "OtherBlues":
            info.postscriptOtherBlues = value
        elif key == "FamilyBlues":
            info.postscriptFamilyBlues = value
        elif key == "FamilyOtherBlues":
            info.postscriptFamilyOtherBlues = value
        elif key == "BlueFuzz":
            info.postscriptBlueFuzz = value
        elif key == "BlueShift":
            info.postscriptBlueShift = value
        elif key == "BlueScale":
            info.postscriptBlueScale = value
        elif key == "ForceBold":
            info.postscriptForceBold = value
        elif key == "StemSnapH":
            info.postscriptStemSnapH = value
        elif key == "StemSnapV":
            info.postscriptStemSnapV = value
        elif key == "StdHW":
            StdHW = value[0]
        elif key == "StdVW":
            StdVW = value[0]

    if StdHW:
        if StdHW in info.postscriptStemSnapH:
            info.postscriptStemSnapH.pop(info.postscriptStemSnapH.index(StdHW))
        info.postscriptStemSnapH.insert(0, StdHW)
    if StdVW:
        if StdVW in info.postscriptStemSnapV:
            info.postscriptStemSnapV.pop(info.postscriptStemSnapV.index(StdVW))
        info.postscriptStemSnapV.insert(0, StdVW)


def _parseGaspTable(font, data):
    info = font.info

    data = data.split(" ")
    num = int(data.pop(0))
    version = int(data.pop())
    assert len(data) == num * 2
    data = [data[j:j + 2] for j in range(0, len(data), 2)]

    records = []
    for ppem, flag in data:
        ppem = int(ppem)
        flag = int(flag)
        flaglist = []
        for j in range(3):
            if flag & (1 << j):
                flaglist.append(j)
        records.append(dict(rangeMaxPPEM=ppem, rangeGaspBehavior=flaglist))

    if records:
        info.openTypeGaspRangeRecords = records



_NAMES = [
    "copyright",
    None, # styleMapFamily
    None, # styleMapStyle
    "openTypeNameUniqueID",
    None, # styleMapFamily and styleMapStyle
    "openTypeNameVersion",
    "postscriptFontName",
    "trademark",
    "openTypeNameManufacturer",
    "openTypeNameDesigner",
    "openTypeNameDescription",
    "openTypeNameManufacturerURL",
    "openTypeNameDesignerURL",
    "openTypeNameLicense",
    "openTypeNameLicenseURL",
    None,
    "openTypeNamePreferredFamilyName",
    "openTypeNamePreferredSubfamilyName",
    "openTypeNameCompatibleFullName",
    "openTypeNameSampleText",
    None,
    "openTypeNameWWSFamilyName",
    "openTypeNameWWSSubfamilyName",
]

def _parseNames(font, data):
    info = font.info

    data = data.split(" ", 1)
    if len(data) < 2:
        return

    langId = int(data[0])
    data = QUOTED_LIST_RE.findall(data[1])

    for nameId, name in enumerate(data):
        name = _sfdUTF7(name)
        if name:
            if langId == 1033: # English (United States)
                if _NAMES[nameId]:
                    setattr(info, _NAMES[nameId], name)


def _getSction(data, value, i, end):
    section = []
    section.append(value)

    if not isinstance(end, (list, tuple)):
        end = [end]

    while i < len(data) and data[i].split(":")[0].strip() not in end:
        section.append(data[i])
        i += 1

    return section, i


def _parseSplineSet(glyph, data):
    data.pop(0)

    for line in data:
        pass
       #print(line)


def _parseImage(glyph, data):
    pass


LAYER_KEYWORDS = ["Fore", "Back", "Layer"]

def _parseLayer(glyph, data):
    font = glyph.font
    name = glyph.name
    width = glyph.width

    layer = data.pop(0)
    if layer == "Fore":
        layer = font.layers.defaultLayer
    elif layer == "Back":
        layer = font.XXXlayerMap[0]
    else:
        layer = font.XXXlayerMap[int(layer.split(": ")[1])]

    if glyph.name not in layer:
        glyph = layer.newGlyph(name)
        glyph.width = width
    else:
        glyph = layer[name]

    refs = []

    i = 0
    while i < len(data):
        line = data[i]
        i += 1

        if ": " in line:
            key, value = line.split(": ", 1)
        else:
            key = line
            value = None

        if   key == "SplineSet":
            splines, i = _getSction(data, value, i, "EndSplineSet")
            _parseSplineSet(glyph, splines)
        elif key == "Image":
            image, i = _getSction(data, value, i, "EndImage")
            _parseImage(glyph, image)
        elif key == "Colour":
            glyph.markColor = parseColor(int(value, 16))
        elif key == "Refer":
            # Just collect the refs here, we can’t insert them until all the
            # glyphs are parsed since FontForge uses glyph indices not names.
            # The calling code will process the references at the end.
            refs.append(value)

       #elif value is not None:
       #    print(key, value)

    return glyph, refs


def _parseAnchorPoint(glyph, data):
    _, name, attrs =  QUOTED_LIST_RE.split(data)
    name = _sfdUTF7(name)

    attrs = attrs.strip().split(" ")
    assert len(attrs) == 4

    x = toFloat(attrs[0])
    y = toFloat(attrs[1])
    kind = attrs[2]
    index = int(attrs[3])

    glyph.appendAnchor(parseAnchorPoint([name, kind, x, y, index]))


GLYPH_CLASSES = [
    "automatic",
    "noclass",
    "baseglyph",
    "baseligature",
    "mark",
    "component",
]

def _parseChar(font, data):
    _, name = data.pop(0).split(": ")
    if name.startswith('"'):
        name = _sfdUTF7(name)

    glyph = font.newGlyph(name)
    refs = {}
    unicodes = []

    i = 0
    while i < len(data):
        line = data[i]
        i += 1

        if ": " in line:
            key, value = line.split(": ", 1)
        else:
            key = line
            value = None

        if   key == "Width":
            glyph.width = int(value)
        elif key == "VWidth":
            glyph.height = int(value)
        elif key == "Encoding":
            enc, uni, order = [int(v) for v in value.split()]
            if uni >= 0:
                unicodes.append(uni)
        elif key == "AltUni2":
            altuni = [int(v, 16) for v in value.split(".")]
            altuni = [altuni[j:j + 3] for j in range(0, len(altuni), 3)]
            unicodes += parseAltuni(altuni, True) # XXX
        elif key == "GlyphClass":
            glyphclass = GLYPH_CLASSES[int(value)]
            glyph.lib[FONTFORGE_PREFIX + ".glyphclass"] = glyphclass
        elif key == "AnchorPoint":
            _parseAnchorPoint(glyph, value)
        elif key in LAYER_KEYWORDS:
            layer, i = _getSction(data, line, i, LAYER_KEYWORDS + ["EndChar"])
            layerglyph, layerrefs = _parseLayer(glyph, layer)
            refs[layerglyph] = layerrefs
        elif key == "Comment":
            glyph.note = _sfdUTF7(value)
        elif key == "Flags":
            pass # XXX
        elif key == "LayerCount":
            pass # XXX

       #elif value is not None:
       #    print(key, value)

    glyph.unicodes = unicodes

    return glyph, order, refs


def _processReferences(font, references):
    for glyph, refs in references.items():
        pen = glyph.getPen()

        for ref in refs:
            ref = ref.split()
            name = font.glyphOrder[int(ref[0])]
            matrix = [toFloat(v) for v in ref[3:9]]
            pen.addComponent(name, matrix)


def _parseChars(font, data):
    glyphOrderMap = {}
    references = {}

    data = [l.strip() for l in data if l.strip()]

    i = 0
    while i < len(data):
        line = data[i]
        i += 1

        if line.startswith("StartChar"):
            char, i = _getSction(data, line, i, "EndChar")
            glyph, order, refs = _parseChar(font, char)
            glyphOrderMap[glyph.name] = order
            references.update(refs)

    # Change the glyph order to match FontForge’s, we need this for processing
    # the references below.
    assert len(font.glyphOrder) == len(glyphOrderMap)
    font.glyphOrder = sorted(glyphOrderMap, key=glyphOrderMap.get)

    # We can’t insert the references while parsing the glyphs since FontForge
    # uses glyph indices so we need to know the glyph order first.
    _processReferences(font, references)


def parse(font, path):
    isdir = os.path.isdir(path)
    if isdir:
        props = os.path.join(path, "font.props")
        if os.path.isfile(props):
            with open(props) as fd:
                data = fd.readlines()
        else:
            raise Exception("Not an SFD directory")
    else:
        with open(path) as fd:
            data = fd.readlines()

    info = font.info

    i = 0
    while i < len(data):
        line = data[i]
        i += 1

        if ":" in line:
            key, value = [v.strip() for v in line.split(":", 1)]
        else:
            key = line.strip()
            value = None

        if i == 1:
            if key != "SplineFontDB":
                raise Exception("Not an SFD file.")
            version = toFloat(value)
            if version != 3.0:
                raise Exception("Unsupported SFD version: %f" % version)

        elif key == "FontName":
            info.postscriptFontName = value
        elif key == "FullName":
            info.postscriptFullName = value
        elif key == "FamilyName":
            info.familyName = value
        elif key == "DefaultBaseFilename":
            pass # info.XXX = value
        elif key == "Weight":
            info.postscriptWeightName = value
        elif key == "Copyright":
            # Decode escape sequences.
            info.copyright = codecs.escape_decode(value)[0].decode("utf-8")
        elif key == "Comments":
            info.note = value
        elif key == "UComments":
            info.note = _sfdUTF7(value)
        elif key == "FontLog":
            pass # info.XXX = _sfdUTF7(value)
        elif key == "Version":
            info.versionMajor, info.versionMinor = parseVersion(value)
        elif key == "ItalicAngle":
            info.italicAngle = info.postscriptSlantAngle = toFloat(value)
        elif key == "UnderlinePosition":
            info.postscriptUnderlinePosition = toFloat(value)
        elif key == "UnderlineWidth":
            info.postscriptUnderlineThickness = toFloat(value)
        elif key in "Ascent":
            info.ascender = toFloat(value)
        elif key in "Descent":
            info.descender = -toFloat(value)
        elif key == "sfntRevision":
            pass # info.XXX = int(value, 16)
        elif key == "WidthSeparation":
            pass # XXX = toFloat(value) # auto spacing
        elif key == "LayerCount":
            font.XXXlayerMap = int(value) * [None]
        elif key == "Layer":
            m = LAYER_RE.match(value)
            idx = int(m.groups()[0])
           # XXX isQuadatic = bool(int(m.groups()[1]))
            name = _sfdUTF7(m.groups()[2])
            if idx == 1:
                font.XXXlayerMap[idx] = font.layers.defaultLayer
            else:
                font.XXXlayerMap[idx] = font.newLayer(name)
        elif key == "DisplayLayer":
            pass # XXX default layer
        elif key == "DisplaySize":
            pass # XXX GUI
        elif key == "AntiAlias":
            pass # XXX GUI
        elif key == "FitToEm":
            pass # XXX GUI
        elif key == "WinInfo":
            pass # XXX GUI
        elif key == "Encoding":
            pass # XXX encoding = value
        elif key == "CreationTime":
            v = datetime.fromtimestamp(int(value))
            info.openTypeHeadCreated = v.strftime("%Y/%m/%d %H:%M:%S")
        elif key == "ModificationTime":
            pass # XXX
        elif key == "FSType":
            v = int(value)
            v = [bit for bit in range(16) if v & (1 << bit)]
            info.openTypeOS2Type = v
        elif key == "PfmFamily":
            pass # info.XXX = value
        elif key in ("TTFWeight", "PfmWeight"):
            info.openTypeOS2WeightClass = int(value)
        elif key == "TTFWidth":
            info.openTypeOS2WidthClass = int(value)
        elif key == "Panose":
            v = value.split()
            info.openTypeOS2Panose = [int(n) for n in v]
        elif key == "LineGap":
            info.openTypeHheaLineGap = int(value)
        elif key == "VLineGap":
            info.openTypeVheaVertTypoLineGap = int(value)
        elif key == "HheadAscent":
            info.openTypeHheaAscender = int(value)
        elif key == "HheadDescent":
            info.openTypeHheaDescender = int(value)
        elif key == "OS2TypoLinegap":
            info.openTypeOS2TypoLineGap = int(value)
        elif key == "OS2Vendor":
            info.openTypeOS2VendorID = value.strip("'")
        elif key == "OS2FamilyClass":
            v = int(value)
            info.openTypeOS2FamilyClass = (v >> 8, v & 0xff)
        elif key == "OS2Version":
            pass # XXX
        elif key == "OS2_WeightWidthSlopeOnly":
            pass # info.XXX = bool(int(value))
        elif key == "OS2_UseTypoMetrics":
            if not info.openTypeOS2Selection:
                info.openTypeOS2Selection = []
            info.openTypeOS2Selection += [7]
        elif key == "OS2CodePages":
            pass # XXX
        elif key == "OS2UnicodeRanges":
            pass # XXX
        elif key == "OS2TypoAscent":
            info.openTypeOS2TypoAscender = int(value)
        elif key == "OS2TypoDescent":
            info.openTypeOS2TypoDescender = int(value)
        elif key == "OS2WinAscent":
            info.openTypeOS2WinAscent = int(value)
        elif key == "OS2WinDescent":
            info.openTypeOS2WinDescent = int(value)
        elif key in ("HheadAOffset", "HheadDOffset", "OS2TypoAOffset",
                     "OS2TypoDOffset", "OS2WinAOffset", "OS2WinDOffset"):
            v = bool(int(value))
       #    assert not v, (key, value) # XXX
        elif key == "OS2SubXSize":
            info.openTypeOS2SubscriptXSize = int(value)
        elif key == "OS2SubYSize":
            info.openTypeOS2SubscriptYSize = int(value)
        elif key == "OS2SubXOff":
            info.openTypeOS2SubscriptXOffset = int(value)
        elif key == "OS2SubYOff":
            info.openTypeOS2SubscriptYOffset = int(value)
        elif key == "OS2SupXSize":
            info.openTypeOS2SuperscriptXSize = int(value)
        elif key == "OS2SupYSize":
            info.openTypeOS2SuperscriptYSize = int(value)
        elif key == "OS2SupXOff":
            info.openTypeOS2SuperscriptXOffset = int(value)
        elif key == "OS2SupYOff":
            info.openTypeOS2SuperscriptYOffset = int(value)
        elif key == "OS2StrikeYSize":
            info.openTypeOS2StrikeoutSize = int(value)
        elif key == "OS2StrikeYPos":
            info.openTypeOS2StrikeoutPosition = int(value)
        elif key == "UniqueID":
            info.postscriptUniqueID = int(value)
        elif key == "LangName":
            _parseNames(font, value)
        elif key == "GaspTable":
            _parseGaspTable(font, value)
        elif key == "XUID":
            pass # XXX
        elif key == "UnicodeInterp":
            pass # XXX
        elif key == "NameList":
            pass # XXX
        elif key == "DEI":
            pass
        elif key == "EndSplineFont":
            break
        elif key == "BeginPrivate":
            section, i = _getSction(data, value, i, "EndPrivate")
            _parsePrivateDict(font, section)
        elif key == "BeginChars":
            chars, i = _getSction(data, value, i, "EndChars")
            chars.pop(0)
            _parseChars(font, chars)

       #elif value is not None:
       #    print(key, value)

    if isdir:
        import glob
        chars = []
        for filename in glob.iglob(os.path.join(path, '*.glyph')):
            with open(filename) as fp:
                chars += fp.readlines()
        _parseChars(font, chars)

    # FontForge does not have an explicit UPEM setting, it is the sum of its
    # ascender and descender.
    info.unitsPerEm = info.ascender - info.descender
