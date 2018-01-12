#
# encoding: utf-8

from fontTools.misc.py23 import *

import codecs
import os
import re

from datetime import datetime

from . import parseAltuni, parseAnchorPoint, parseColor, parseVersion
from . import FONTFORGE_PREFIX


QUOTED_LIST_RE = re.compile('(".*?")')
LAYER_RE = re.compile("(.)\s+(.)\s+" + QUOTED_LIST_RE.pattern + "\s+(.?)")
GLYPH_COMMAND_RE = re.compile('(\s[lmc]\s)')
KERNS_RE = re.compile("(-?\d+)\s+(-?\d+)\s+" + QUOTED_LIST_RE.pattern)


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

def SFDReadUTF7(data):
    out = b""

    data = data.strip('"').encode("ascii")

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

class SFDParser():
    """Parses an SFD file or SFDIR directory."""

    def __init__(self, path, font):
        self._path = path
        self._font = font
        self._layers = []
        self._layerType = []
        self._glyphRefs = {}
        self._glyphKerns = {}

    def _parsePrivateDict(self, data):
        info = self._font.info
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

    def _parseGaspTable(self, data):
        info = self._font.info

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

    def _parseNames(self, data):
        info = self._font.info

        data = data.split(" ", 1)
        if len(data) < 2:
            return

        langId = int(data[0])
        data = QUOTED_LIST_RE.findall(data[1])

        for nameId, name in enumerate(data):
            name = SFDReadUTF7(name)
            if name:
                if langId == 1033: # English (United States)
                    if self._NAMES[nameId]:
                        setattr(info, self._NAMES[nameId], name)

    def _getSection(self, data, i, end, value=None):
        section = []
        if value is not None:
            section.append(value)

        if not isinstance(end, (list, tuple)):
            end = [end]

        while i < len(data) and data[i].split(":")[0].strip() not in end:
            section.append(data[i])
            i += 1

        return section, i

    def _parseSplineSet(self, glyph, data, quadratic):
        contours = []

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if line == "Spiro":
                spiro, i = self._getSection(data, i, "EndSpiro")
                i += 1
            else:
                points, command, flags = [c.strip() for c in GLYPH_COMMAND_RE.split(line)]
                points = [toFloat(c) for c in points.split(" ")]
                points = [points[j:j + 2] for j in range(0, len(points), 2)]
                if   command == "m":
                    assert len(points) == 1
                    contours.append([(command, points, flags)])
                elif command == "l":
                    assert len(points) == 1
                    contours[-1].append((command, points, flags))
                elif command == "c":
                    assert len(points) == 3
                    contours[-1].append((command, points, flags))

        if contours:
            pen = glyph.getPen()
            for contour in contours:
                for command, points, flags in contour:
                    if   command == "m":
                        pen.moveTo(*points)
                    elif command == "l":
                        pen.lineTo(*points)
                    else:
                        if quadratic:
                            points.pop(0) # XXX I don’t know what I’m doing
                            pen.qCurveTo(*points)
                        else:
                            pen.curveTo(*points)
                pen.closePath()

    def _parseImage(self, glyph, data):
        pass

    def _parseKerns(self, glyph, data):
        assert glyph.name not in self._glyphKerns
        kerns = KERNS_RE.findall(data)
        assert kerns
        self._glyphKerns[glyph.name] = []
        for (gid, kern, subtable) in kerns:
            gid = int(gid)
            kern = toFloat(kern)
            self._glyphKerns[glyph.name].append((gid, kern))

    _LAYER_KEYWORDS = ["Back", "Fore", "Layer"]

    def _parseCharLayer(self, glyph, data):
        font = self._font
        name = glyph.name
        width = glyph.width

        layer = data.pop(0)
        if layer in self._LAYER_KEYWORDS:
            idx = self._LAYER_KEYWORDS.index(layer)
        else:
            idx = int(layer.split(": ")[1])
        layer = self._layers[idx]
        quadratic = self._layerType[idx]

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
                splines, i = self._getSection(data, i, "EndSplineSet")
                self._parseSplineSet(glyph, splines, quadratic)
            elif key == "Image":
                image, i = self._getSection(data, i, "EndImage", value)
                self._parseImage(glyph, image)
            elif key == "Colour":
                glyph.markColor = parseColor(int(value, 16))
            elif key == "Refer":
                # Just collect the refs here, we can’t insert them until all the
                # glyphs are parsed since FontForge uses glyph indices not names.
                # The calling code will process the references at the end.
                if glyph not in self._glyphRefs:
                    self._glyphRefs[glyph] = []
                self._glyphRefs[glyph].append(value)
            elif key == "Kerns2":
                # Technically kerns don’t belong to the layer, but the way we
                # parse layers can lead us to seeing them here.
                self._parseKerns(glyph, value)

           #elif value is not None:
           #    print(key, value)

        return glyph

    def _parseAnchorPoint(self, glyph, data):
        _, name, attrs =  QUOTED_LIST_RE.split(data)
        name = SFDReadUTF7(name)

        attrs = attrs.strip().split(" ")
        assert len(attrs) == 4

        x = toFloat(attrs[0])
        y = toFloat(attrs[1])
        kind = attrs[2]
        index = int(attrs[3])

        glyph.appendAnchor(parseAnchorPoint([name, kind, x, y, index]))


    _GLYPH_CLASSES = [
        "automatic",
        "noclass",
        "baseglyph",
        "baseligature",
        "mark",
        "component",
    ]

    def _parseChar(self, data):
        _, name = data.pop(0).split(": ")
        if name.startswith('"'):
            name = SFDReadUTF7(name)

        glyph = self._font.newGlyph(name)
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
                glyphclass = self._GLYPH_CLASSES[int(value)]
                glyph.lib[FONTFORGE_PREFIX + ".glyphclass"] = glyphclass
            elif key == "AnchorPoint":
                self._parseAnchorPoint(glyph, value)
            elif key in self._LAYER_KEYWORDS:
                layer, i = self._getSection(data, i,
                    self._LAYER_KEYWORDS + ["EndChar"], line)
                layerglyph = self._parseCharLayer(glyph, layer)
            elif key == "Kerns2":
                self._parseKerns(glyph, value)
            elif key == "Comment":
                glyph.note = SFDReadUTF7(value)
            elif key == "Flags":
                pass # XXX
            elif key == "LayerCount":
                pass # XXX

           #elif value is not None:
           #    print(key, value)

        glyph.unicodes = unicodes

        return glyph, order

    def _processReferences(self):
        for glyph, refs in self._glyphRefs.items():
            pen = glyph.getPen()

            for ref in refs:
                ref = ref.split()
                name = self._font.glyphOrder[int(ref[0])]
                matrix = [toFloat(v) for v in ref[3:9]]
                pen.addComponent(name, matrix)

    def _processKerns(self):
        for name1 in self._glyphKerns:
            for gid2, kern in self._glyphKerns[name1]:
                name2 = self._font.glyphOrder[gid2]
                self._font.kerning[name1, name2] = kern

    def _parseChars(self, data):
        font = self._font
        glyphOrderMap = {}

        data = [l.strip() for l in data if l.strip()]

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if line.startswith("StartChar"):
                char, i = self._getSection(data, i, "EndChar", line)
                glyph, order = self._parseChar(char)
                glyphOrderMap[glyph.name] = order

        # Change the glyph order to match FontForge’s, we need this for processing
        # the references below.
        assert len(font.glyphOrder) == len(glyphOrderMap)
        font.glyphOrder = sorted(glyphOrderMap, key=glyphOrderMap.get)

    def parse(self):
        isdir = os.path.isdir(self._path)
        if isdir:
            props = os.path.join(self._path, "font.props")
            if os.path.isfile(props):
                with open(props) as fd:
                    data = fd.readlines()
            else:
                raise Exception("Not an SFD directory")
        else:
            with open(self._path) as fd:
                data = fd.readlines()

        font = self._font
        info = font.info

        charData = None

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
                info.note = SFDReadUTF7(value)
            elif key == "FontLog":
                pass # info.XXX = SFDReadUTF7(value)
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
                self._layers = int(value) * [None]
                self._layerType = int(value) * [None]
            elif key == "Layer":
                m = LAYER_RE.match(value)
                idx = int(m.groups()[0])
                quadratic = bool(int(m.groups()[1]))
                name = SFDReadUTF7(m.groups()[2])
                if idx == 1:
                    self._layers[idx] = font.layers.defaultLayer
                else:
                    self._layers[idx] = name
                self._layerType[idx] = quadratic
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
                self._parseNames(value)
            elif key == "GaspTable":
                self._parseGaspTable(value)
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
                section, i = self._getSection(data, i, "EndPrivate", value)
                self._parsePrivateDict(section)
            elif key == "BeginChars":
                charData, i = self._getSection(data, i, "EndChars")

           #elif value is not None:
           #    print(key, value)


        for idx, name in enumerate(self._layers):
            if not isinstance(name, (str, unicode)):
                continue
            if idx not in (0, 1) and self._layers.count(name) != 1:
                # FontForge layer names are not unique, make sure ours are.
                name += "_%d" % idx
            self._layers[idx] = font.newLayer(name)

        if isdir:
            assert charData is None
            import glob
            charData = []
            for filename in glob.iglob(os.path.join(self._path, '*.glyph')):
                with open(filename) as fp:
                    charData += fp.readlines()

        self._parseChars(charData)

        # We can’t insert the references while parsing the glyphs since
        # FontForge uses glyph indices so we need to know the glyph order
        # first.
        self._processReferences()

        # Same for kerning.
        self._processKerns()

        # FontForge does not have an explicit UPEM setting, it is the sum of its
        # ascender and descender.
        info.unitsPerEm = info.ascender - info.descender
