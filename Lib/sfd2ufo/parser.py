#
# encoding: utf-8

from __future__ import print_function, division
from fontTools.misc.py23 import *

import codecs
import math
import os
import re

from collections import OrderedDict
from datetime import datetime

from .utils import parseAltuni, parseAnchorPoint, parseColor, parseVersion, \
                   getFontBounds, processKernClasses, SFDReadUTF7
from .utils import GLYPHCLASS_KEY, DECOMPOSEREMOVEOVERLAP_KEY


QUOTED_RE = re.compile('(".*?")')
NUMBER_RE = re.compile("(-?\d*\.*\d+)")
LAYER_RE = re.compile("(.)\s+(.)\s+" + QUOTED_RE.pattern + "\s+(.?)")
GLYPH_COMMAND_RE = re.compile('(\s[lmc]\s)')
KERNS_RE = re.compile(
    NUMBER_RE.pattern +
    "\s+" +
    NUMBER_RE.pattern +
    "\s+" +
    QUOTED_RE.pattern
)
ANCHOR_RE = re.compile(
    QUOTED_RE.pattern +
    "\s+" +
    NUMBER_RE.pattern +
    "\s+" +
    NUMBER_RE.pattern +
    "\s+(\S+)\s+(\d)"
)
DEVICETABLE_RE = re.compile("\s?{.*?}\s?")
LOOKUP_RE = re.compile(
    "(\d+)\s+(\d+)\s+(\d+)\s+" +
    QUOTED_RE.pattern +
    "\s+" +
    "{(.*?)}" +
    "\s+" +
    "\[(.*?)\]"
)
TAG_RE = re.compile("'(.{,4})'")
FEATURE_RE = re.compile(
    TAG_RE.pattern +
    "\s+" +
    "\((.*.)\)"
)
LANGSYS_RE = re.compile(
    TAG_RE.pattern +
    "\s+" +
    "<(.*?)>" +
    "\s+"
)
SUBPOS_RE = re.compile(QUOTED_RE.pattern + "\s+(.*.)")


class SFDParser():
    """Parses an SFD file or SFDIR directory."""

    def __init__(self, path, font, ignore_uvs=False):
        self._path = path
        self._font = font
        self._ignore_uvs = ignore_uvs
        self._layers = []
        self._layerType = []
        self._glyphRefs = OrderedDict()
        self._glyphKerns = OrderedDict()
        self._glyphPosSub = OrderedDict()
        self._kernClasses = OrderedDict()
        self._gsubLookups = OrderedDict()
        self._gposLookups = OrderedDict()
        self._lookupInfo = OrderedDict()
        self._ligatureCarets = OrderedDict()

    def _parsePrivateDict(self, data):
        info = self._font.info
        n = int(data.pop(0))
        assert len(data) == n

        StdHW = StdVW = None

        for line in data:
            key, n, value = [v.strip() for v in line.split(" ", 2)]
            assert len(value) == int(n)

            if value.startswith("[") and value.endswith("]"):
                value = [float(n) for n in value[1:-1].split(" ")]
            else:
                value = float(value)

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
        for ppem, flags in data:
            ppem = int(ppem)
            flags = int(flags)
            flags = [i for i in range(4) if flags & (1 << i)]
            records.append(dict(rangeMaxPPEM=ppem, rangeGaspBehavior=flags))

        if records:
            info.openTypeGaspRangeRecords = records

    _NAMES = [
        "copyright",
        None, # XXX styleMapFamily
        None, # XXX styleMapStyle
        "openTypeNameUniqueID",
        None, # XXX styleMapFamily and styleMapStyle
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
        None, # Reserved
        "openTypeNamePreferredFamilyName",
        "openTypeNamePreferredSubfamilyName",
        "openTypeNameCompatibleFullName",
        "openTypeNameSampleText",
        None, # XXX
        "openTypeNameWWSFamilyName",
        "openTypeNameWWSSubfamilyName",
    ]

    def _parseNames(self, data):
        info = self._font.info

        data = data.split(" ", 1)
        if len(data) < 2:
            return

        langId = int(data[0])
        data = QUOTED_RE.findall(data[1])

        for nameId, name in enumerate(data):
            name = SFDReadUTF7(name)
            if name:
                if langId == 1033 and self._NAMES[nameId]:
                    # English (United States)
                    setattr(info, self._NAMES[nameId], name)
                else:
                    if not info.openTypeNameRecords:
                        info.openTypeNameRecords = []
                    info.openTypeNameRecords.append(
                        dict(nameID=nameId, languageID=langId, string=name,
                             platformID=3, encodingID=1))

    def _getSection(self, data, i, end, value=None):
        section = []
        if value is not None:
            section.append(value)

        while not data[i].startswith(end):
            section.append(data[i])
            i += 1

        return section, i + 1

    def _parseSplineSet(self, data):
        contours = []

        i = 0
        while i < len(data):
            line = data[i]
            i += 1

            if line == "Spiro":
                spiro, i = self._getSection(data, i, "EndSpiro")
                i += 1
            elif line.startswith("Named"):
                name = SFDReadUTF7(line.split(": ")[1])
                contours[-1].append(name)
            else:
                points, command, flags = [c.strip() for c in GLYPH_COMMAND_RE.split(line)]
                points = [float(c) for c in points.split(" ")]
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

        return contours

    def _drawContours(self, glyph, contours, quadratic):
        pen = glyph.getPen()
        for contour in contours:
            if not isinstance(contour[-1], (tuple, list)):
                name = contour.pop()
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

    def _parseGrid(self, data):
        info = self._font.info

        data = [l.strip() for l in data]
        contours = self._parseSplineSet(data)

        for contour in contours:
            name = None
            p0 = None
            if not isinstance(contour[-1], (tuple, list)):
                name = contour.pop()

            if len(contour) != 2:
                # UFO guidelines are simple straight lines, so I can handle any
                # complex contours here.
                continue

            for command, points, flags in contour:
                if   command == "m":
                    p0 = points[0]
                elif command == "l":
                    p1 = points[0]

                    x = None
                    y = None
                    angle = None

                    if p0[0] == p1[0]:
                        x = p0[0]
                    elif p0[1] == p1[1]:
                        y = p0[1]
                    else:
                        x = p0[0]
                        y = p0[1]
                        angle = math.atan2(p1[0] - p0[0], p1[1] - p0[1])
                        angle = math.degrees(angle)
                        if angle < 0:
                            angle = 360 + angle
                    info.appendGuideline(
                        dict(x=x, y=y, name=name, angle=angle))
                else:
                    p0 = points[0]

    def _parseImage(self, glyph, data):
        pass # XXX

    def _parseKerns(self, glyph, data):
        assert glyph.name not in self._glyphKerns
        kerns = KERNS_RE.findall(data)
        assert kerns
        self._glyphKerns[glyph.name] = []
        for (gid, kern, subtable) in kerns:
            gid = int(gid)
            kern = int(kern)
            self._glyphKerns[glyph.name].append((gid, kern))

    def _parseKernClass(self, data, i, value):
        m = KERNS_RE.match(value)
        n1, n2, name = m.groups()
        n1 = int(n1)
        n2 = int(n2)
        name = SFDReadUTF7(name)

        first = data[i:i + n1 - 1]
        first = [v.split()[1:] for v in first]
        first.insert(0, None)
        i += n1 - 1

        second = data[i:i + n2 - 1]
        second = [v.split()[1:] for v in second]
        second.insert(0, None)
        i += n2 - 1

        kerns = data[i]
        kerns = DEVICETABLE_RE.split(kerns)
        kerns = [int(k) for k in kerns if k]

        self._kernClasses[name] = (first, second, kerns)

        return i + 1

    def _parseAnchorPoint(self, glyph, data):
        m = ANCHOR_RE.match(data)
        assert m
        name, x, y, kind, index = m.groups()
        name = SFDReadUTF7(name)
        x = float(x)
        y = float(y)
        index = int(index)

        glyph.appendAnchor(parseAnchorPoint([name, kind, x, y, index]))

    def _parsePosSub(self, glyph, key, data):
        m = SUBPOS_RE.match(data)
        assert m

        key = key[:-1]

        subtable, possub = m.groups()
        subtable = SFDReadUTF7(subtable)
        possub = possub.strip().split()

        if glyph.name not in self._glyphPosSub:
            self._glyphPosSub[glyph.name] = OrderedDict()

        if  key == "Position":
            possub = [int(p.split("=")[1]) for p in possub]
        elif key == "PairPos":
            possub = possub[:1] + [int(p.split("=")[1]) for p in possub[1:]]

        if key in ("Ligature", "Substitution", "AlternateSubs", "MultipleSubs",
                   "Position", "PairPos"):
            if subtable not in self._glyphPosSub[glyph.name]:
                self._glyphPosSub[glyph.name][subtable] = []
            self._glyphPosSub[glyph.name][subtable].append((key, possub))
        else:
            assert False, (key, possub)

    _LAYER_KEYWORDS = ["Back", "Fore", "Layer"]

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
        layerGlyph = glyph
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
                unicodes += parseAltuni(altuni, self._ignore_uvs)
            elif key == "GlyphClass":
                glyph.lib[GLYPHCLASS_KEY] = self._GLYPH_CLASSES[int(value)]
            elif key == "AnchorPoint":
                self._parseAnchorPoint(glyph, value)
            elif key in self._LAYER_KEYWORDS:
                idx = value and int(value) or self._LAYER_KEYWORDS.index(key)
                layer = self._layers[idx]
                quadratic = self._layerType[idx]
                if glyph.name not in layer:
                    layerGlyph = layer.newGlyph(glyph.name)
                    layerGlyph.width = glyph.width
                else:
                    layerGlyph = layer[glyph.name]
            elif key == "SplineSet":
                splines, i = self._getSection(data, i, "EndSplineSet")
                contours = self._parseSplineSet(splines)
                self._drawContours(layerGlyph, contours, quadratic)
            elif key == "Image":
                image, i = self._getSection(data, i, "EndImage", value)
                self._parseImage(layerGlyph, image)
            elif key == "Colour":
                layerGlyph.markColor = parseColor(int(value, 16))
            elif key == "Refer":
                # Just collect the refs here, we can’t insert them until all the
                # glyphs are parsed since FontForge uses glyph indices not names.
                # The calling code will process the references at the end.
                if layerGlyph not in self._glyphRefs:
                    self._glyphRefs[layerGlyph] = []
                self._glyphRefs[layerGlyph].append(value)
            elif key == "Kerns2":
                self._parseKerns(glyph, value)
            elif key == "Comment":
                glyph.note = SFDReadUTF7(value)
            elif key == "UnlinkRmOvrlpSave":
                glyph.lib[DECOMPOSEREMOVEOVERLAP_KEY] = bool(int(value))
            elif key == "LCarets2":
                v = [int(v) for v in value.split(" ")]
                num = v.pop(0)
                if any(v):
                    assert len(v) == num
                    self._ligatureCarets[glyph.name] = v
            elif key in ("Position2", "PairPos2", "Ligature2", "Substitution2",
                         "AlternateSubs2", "MultipleSubs2"):
                self._parsePosSub(glyph, key, value)
            elif key in ("HStem", "VStem", "DStem2", "CounterMasks"):
                pass # XXX
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
                matrix = [float(v) for v in ref[3:9]]
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

    _LOOKUP_TYPES = {
        0x001: "gsub_single",
        0x002: "gsub_multiple",
        0x003: "gsub_alternate",
        0x004: "gsub_ligature",
        0x005: "gsub_context",
        0x006: "gsub_contextchain",
        # GSUB extension 7
        0x008: "gsub_reversecchain",

        0x0fd: "morx_indic",
        0x0fe: "morx_context",
        0x0ff: "morx_insert",

        0x101: "gpos_single",
        0x102: "gpos_pair",
        0x103: "gpos_cursive",
        0x104: "gpos_mark2base",
        0x105: "gpos_mark2ligature",
        0x106: "gpos_mark2mark",
        0x107: "gpos_context",
        0x108: "gpos_contextchain",
        # GPOS extension 9
        0x1ff: "kern_statemachine",

        # lookup&0xff == lookup type for the appropriate table
        # lookup>>8:     0=>GSUB, 1=>GPOS
    }

    _LOOKUP_FLAGS = {
        1: "RightToLeft",
        2: "IgnoreBaseGlyphs",
        4: "IgnoreLigatures",
        8: "IgnoreMarks",
    }

    def _parseLookup(self, data):
        m = LOOKUP_RE.match(data)
        assert m

        kind, flag, _, lookup, subtables, feature = m.groups()
        kind = int(kind)
        flag = int(flag)
        lookup = SFDReadUTF7(lookup)
        subtables = [SFDReadUTF7(v) for v in QUOTED_RE.findall(subtables)]

        if kind >> 8: # GPOS
            self._gposLookups[lookup] = subtables
        else:
            self._gsubLookups[lookup] = subtables

        flags = []
        for i, name in self._LOOKUP_FLAGS.items():
            if flag & i:
                flags.append(name)

        features = []
        for tag, langsys in FEATURE_RE.findall(feature):
            features.append([tag])
            for script, langs in LANGSYS_RE.findall(langsys):
                features[-1].append((script, TAG_RE.findall(langs)))

        self._lookupInfo[lookup] = (self._LOOKUP_TYPES[kind], flags, features)

    _OFFSET_METRICS = {
        "HheadAOffset": "openTypeHheaAscender",
        "HheadDOffset": "openTypeHheaDescender",
        "OS2TypoAOffset": "openTypeOS2TypoAscender",
        "OS2TypoDOffset": "openTypeOS2TypoDescender",
        "OS2WinAOffset": "openTypeOS2WinAscent",
        "OS2WinDOffset": "openTypeOS2WinDescent",
    }

    def _fixOffsetMetrics(self, metrics):
        info = self._font.info
        bounds = getFontBounds(self._font.bounds)
        for metric in metrics:
            value = getattr(info, metric)

            if   metric == "openTypeOS2TypoAscender":
                value = self._font.ascender + value
            elif metric == "openTypeOS2TypoDescender":
                value = self._font.descender + value
            elif metric == "openTypeOS2WinAscent":
                value = bounds["yMax"] + value
            elif metric == "openTypeOS2WinDescent":
                value = max(-bounds["yMin"] + value, 0)
            elif metric == "openTypeHheaAscender":
                value = bounds["yMax"] + value
            elif metric == "openTypeHheaDescender":
                value = bounds["yMin"] + value

            setattr(info, metric, value)

    def _writeGDEF(self):
        font = self._font
        classNames = OrderedDict()
        classNames["baseglyph"] = "@GDEF_Simple"
        classNames["baseligature"] = "@GDEF_Ligature"
        classNames["mark"] = "@GDEF_Mark"
        classNames["component"] = "@GDEF_Component"
        gdef = {}
        for name in font.glyphOrder:
            glyph = font[name]
            glyphclass = glyph.lib.get(GLYPHCLASS_KEY)
            if glyphclass is None:
                if name == ".notdef":
                    continue
                glyphclass = "baseglyph"
                if name in self._glyphPosSub:
                    for subtable in self._glyphPosSub[name]:
                        for kind, _ in self._glyphPosSub[name][subtable]:
                            if kind == "Ligature":
                                glyphclass = "baseligature"
                                break

            if glyphclass not in gdef:
                gdef[glyphclass] = []
            gdef[glyphclass].append(name)

        # Ugly code to match FontForge output for easy comparison, should be
        # cleaned up once the dust settles.
        lines = []
        lines.append("#Mark attachment classes (defined in GDEF, used in lookupflags)")
        lines.append("")
        for name in classNames:
            if name not in gdef:
                continue
            classname = classNames[name]
            glyphs = gdef[name]
            lines.append("%s = [" % classname)
            n = len(classname) + 8
            for glyph in glyphs:
                if n + len(glyph) + 1 > 80:
                    lines[-1] += "\n\t"
                    n = 8
                lines[-1] += "\\" + glyph + " "
                n += len(glyph) + 1
            lines[-1] += "];"
        names = []
        for name in classNames:
            classname = ""
            if name in gdef:
                classname = classNames[name]
            names.append(classname)
        lines.append("")
        lines.append("table GDEF {")
        lines.append("  GlyphClassDef " + ", ".join(names) + ";")
        lines.append("")
        if self._ligatureCarets:
            for k, v in self._ligatureCarets.items():
                v = [str(i) for i in v]
                lines.append("  LigatureCaretByPos \%s %s;" % (k, " ".join(v)))
        lines.append("} GDEF;")
        lines.append("")
        lines.append("")

        if font.features.text is None:
            font.features.text = ""
        font.features.text += "\n".join(lines)

    def _santizeLookupName(self, name):
        out = ""
        for i, ch in enumerate(name):
            if ord(ch) < 127 and \
              (ch.isalpha() or ch in (".", "_") or (i != 0 and ch.isdigit())):
                out += ch
        return out[:31]

    def _writeGSUBGPOS(self, isgpos=False):
        # Ugly as hell, rewrite later.
        font = self._font

        if isgpos:
            tableLookups = self._gposLookups
        else:
            tableLookups = self._gsubLookups

        # Prune empty lookups
        lookups = OrderedDict()
        for lookup, subtables in tableLookups.items():
            if any(any(s in self._glyphPosSub[g] for s in subtables) for g in self._glyphPosSub):
                lookups[lookup] = subtables

        if not lookups:
            return

        featureSet = []
        scriptSet = set()
        langSet = {}
        for lookup in lookups:
            _, _, fealangsys = self._lookupInfo[lookup]
            for feature in fealangsys:
                if feature[0] not in featureSet:
                    featureSet.append(feature[0])
                for script, languages in feature[1:]:
                    scriptSet.add(script)
                    if script not in langSet:
                        langSet[script] = set()
                    langSet[script].update(languages)

        scriptSet = sorted(scriptSet)
        langSet = {s: sorted(langSet[s], key=lambda l: l == "dflt" and "0" or l) for s in langSet}

        features = OrderedDict()
        for feature in featureSet:
            outf = OrderedDict()
            for script in scriptSet:
                outs = OrderedDict()
                for language in langSet[script]:
                    outl = []
                    for lookup in lookups:
                        _, _, fealangsys = self._lookupInfo[lookup]
                        for fl in fealangsys:
                            if feature == fl[0]:
                                for sl in fl[1:]:
                                    if script == sl[0]:
                                        for ll in sl[1]:
                                            if language == ll:
                                                outl.append(self._santizeLookupName(lookup))
                    if outl:
                        outs[language] = outl
                if outs:
                    outf[script] = outs
            if outf:
                features[feature] = outf

        lines = []
        lines.append("")
        lines.append("# %s " % (isgpos and "GPOS" or "GSUB"))
        lines.append("")

        for lookup in lookups:
            kind, flags, _ = self._lookupInfo[lookup]
            flags = flags and " ".join(flags) or "0"
            lines.append("")
            lines.append("lookup %s {" % self._santizeLookupName(lookup))
            lines.append("  lookupflag %s;" % flags)
            for i, subtable in enumerate(lookups[lookup]):
                for glyph in self._glyphPosSub:
                    if subtable in self._glyphPosSub[glyph]:
                        for _, possub in self._glyphPosSub[glyph][subtable]:
                            if kind.startswith("gsub_"):
                                possub = " \\".join(possub)

                            if   kind in ("gsub_single", "gsub_multiple"):
                                lines.append("    sub \\%s by \\%s ;" % (glyph, possub))
                            elif kind == "gsub_alternate":
                                lines.append("    sub \\%s from [\\%s ];" % (glyph, possub))
                            elif kind == "gsub_ligature":
                                lines.append("    sub \\%s  by \\%s;" % (possub, glyph))
                            elif kind == "gpos_single":
                                possub = " ".join([str(v) for v in possub])
                                lines.append("    pos \\%s <%s>;" % (glyph, possub))
                            elif kind == "gpos_pair":
                                glyph2 = possub.pop(0)
                                pos1 = " ".join([str(v) for v in possub[:4]])
                                pos2 = " ".join([str(v) for v in possub[4:]])
                                lines.append("    pos \\%s <%s> \\%s <%s>;" % (glyph, pos1, glyph2, pos2))
                            else:
                                assert False, (kind, possub)
            lines.append("} %s;" % self._santizeLookupName(lookup))

        for feature in features:
            lines.append("")
            lines.append("feature %s {" % feature)
            for script in features[feature]:
                lines.append("")
                lines.append("  script %s;" % script)
                for language in features[feature][script]:
                    lines.append("     language %s %s;" % (language, language != "dflt" and "exclude_dflt" or ""))
                    for lookup in features[feature][script][language]:
                        lines.append("      lookup %s;" % lookup)
            lines.append("} %s;" % feature)

        lines.append("")

        if font.features.text is None:
            font.features.text = ""
        font.features.text += "\n".join(lines)

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
        offsetMetrics = []

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
                version = float(value)
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
                old = info.note
                info.note = SFDReadUTF7(value)
                if old:
                    info.note += "\n" + old
            elif key == "FontLog":
                if not info.note:
                    info.note = ""
                else:
                    info.note = "\n"
                info.note += "Font log:\n" + SFDReadUTF7(value)
            elif key == "Version":
                info.versionMajor, info.versionMinor = parseVersion(value)
            elif key == "ItalicAngle":
                info.italicAngle = info.postscriptSlantAngle = float(value)
            elif key == "UnderlinePosition":
                info.postscriptUnderlinePosition = float(value)
            elif key == "UnderlineWidth":
                info.postscriptUnderlineThickness = float(value)
            elif key in "Ascent":
                info.ascender = int(value)
            elif key in "Descent":
                info.descender = -int(value)
            elif key == "sfntRevision":
                pass # info.XXX = int(value, 16)
            elif key == "WidthSeparation":
                pass # XXX = float(value) # auto spacing
            elif key == "LayerCount":
                self._layers = int(value) * [None]
                self._layerType = int(value) * [None]
            elif key == "Layer":
                m = LAYER_RE.match(value)
                idx, quadratic, name, _ = m.groups()
                idx = int(idx)
                quadratic = bool(int(quadratic))
                name = SFDReadUTF7(name)
                if idx == 1:
                    self._layers[idx] = font.layers.defaultLayer
                else:
                    self._layers[idx] = name
                self._layerType[idx] = quadratic
            elif key == "DisplayLayer":
                pass # XXX default layer
            elif key == "DisplaySize":
                pass # GUI
            elif key == "AntiAlias":
                pass # GUI
            elif key == "FitToEm":
                pass # GUI
            elif key == "WinInfo":
                pass # GUI
            elif key == "Encoding":
                pass # XXX encoding = value
            elif key == "CreationTime":
                v = datetime.utcfromtimestamp(int(value))
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
                if int(value):
                    if not info.openTypeOS2Selection:
                        info.openTypeOS2Selection = []
                    info.openTypeOS2Selection += [8]
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
            elif key in self._OFFSET_METRICS:
                if int(value):
                    offsetMetrics.append(self._OFFSET_METRICS[key])
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
            elif key == "BeginPrivate":
                section, i = self._getSection(data, i, "EndPrivate", value)
                self._parsePrivateDict(section)
            elif key == "BeginChars":
                charData, i = self._getSection(data, i, "EndChars")
            elif key == "Grid":
                grid, i = self._getSection(data, i, "EndSplineSet")
                self._parseGrid(grid)
            elif key == "KernClass2":
                i = self._parseKernClass(data, i, value)
            elif key == "Lookup":
                self._parseLookup(value)
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

           #else:
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

        # We process all kern classes together so we can detect UFO group
        # overlap issue and act accordingly.
        subtables = []
        for lookup in self._gposLookups:
            for subtable in self._gposLookups[lookup]:
                if subtable in self._kernClasses:
                    subtables.append(self._kernClasses[subtable])
        processKernClasses(self._font, subtables)

        # Need to run after parsing glyphs so that we can calculate font
        # bounding box.
        self._fixOffsetMetrics(offsetMetrics)

        self._writeGSUBGPOS(isgpos=False)
        self._writeGSUBGPOS(isgpos=True)
        self._writeGDEF()

        # FontForge does not have an explicit UPEM setting, it is the sum of its
        # ascender and descender.
        info.unitsPerEm = info.ascender - info.descender
