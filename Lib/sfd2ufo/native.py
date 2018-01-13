#
# encoding: utf-8

from fontTools.misc.py23 import *

from defcon import Font
import fontforge
import math

from .utils import parseAltuni, parseAnchorPoint, parseColor, parseVersion, \
                   getFontBounds, processKernClasses
from .utils import FONTFORGE_PREFIX


class SFDParser():
    """Parses an SFD file or SFDIR directory, using FontForge’s native python
    extension.
    """

    def __init__(self, path, font, ignore_uvs=False):
        self._path = path
        self._font = font
        self._ignore_uvs = ignore_uvs

        self._sfd = None
        self._layerMap = {}
        self._private = {}

    def parse(self):
        self._sfd = fontforge.open(self._path)

        self._buildLayers()
        self._buildGlyphs()
        self._buildKerning()
        self._buildFeatures()
        self._buildInfo()

    def __del__(self):
        if self._sfd is not None:
            self._sfd.close()

    def _setInfoFromName(self, ufoName, sfdName):
        for name in self._sfd.sfnt_names:
            if name[0] == "English (US)" and name[1] == sfdName:
                setattr(self._font.info, ufoName, name[2])

    def _setInfo(self, ufoName, sfdName):
        value = getattr(self._sfd, sfdName, None)
        if value is not None:
            # UFO's descender is -ve and FontForge's is +ve
            if sfdName in ("descent"):
                value = -value
            # -ve value means computing it failed
            if sfdName in ("capHeight", "xHeight") and value < 0:
                return
            if sfdName == "os2_family_class":
                value = (value >> 8, value & 0xff)
            if sfdName == "os2_fstype":
                fstype = [i for i in range(16) if value & (1 << i)]
                value = fstype

            bb = getFontBounds(self._font.bounds)
            if sfdName == "os2_typoascent" and getattr(self._sfd, sfdName + "_add"):
                value = self._sfd.ascent + value
            if sfdName == "os2_typodescent" and getattr(self._sfd, sfdName + "_add"):
                value = -self._sfd.descent + value

            if sfdName == "os2_winascent" and getattr(self._sfd, sfdName + "_add"):
                value = bb["yMax"] + value
            if sfdName == "os2_windescent" and getattr(self._sfd, sfdName + "_add"):
                value = max(-bb["yMin"] + value, 0)

            if sfdName == "hhea_ascent" and getattr(self._sfd, sfdName + "_add"):
                value = bb["yMax"] + value
            if sfdName == "hhea_descent" and getattr(self._sfd, sfdName + "_add"):
                value = bb["yMin"] + value

            if sfdName == "gasp":
                if not value:
                    return
                records = []
                gaspFlags = ("gridfit", "antialias", "gridfit+smoothing", "symmetric-smoothing")
                for ppem, flags in value:
                    flags = sorted(gaspFlags.index(f) for f in flags)
                    records.append(dict(rangeMaxPPEM=ppem, rangeGaspBehavior=flags))
                value = records

            setattr(self._font.info, ufoName, value)

    def _setPrivate(self, ufoName, sfdName):
        if not self._private:
            for k in self._sfd.private:
                self._private[k] = self._sfd.private[k]

            # UFO is stupid, Std[H|V]W is not explicitly encoded but should be
            # derived from StemSnap[H|V], yet it has to be sorted so Std[H|V]W
            # is not guaranteed to be the first value!
            for k1, k2 in (("StemSnapH", "StdHW"), ("StemSnapV", "StdVW")):
                if k1 in self._private and k2 in self._private:
                    snap = list(self._private[k1])
                    stdw = self._private[k2][0]
                    if snap[0] != stdw:
                        if stdw in snap:
                            snap.pop(snap.index(stdw))
                        self._private[k1] = [stdw] + snap

        if sfdName in self._private:
            setattr(self._font.info, ufoName, self._private[sfdName])

    def _buildInfo(self):
        info = self._font.info

        self._setInfo("familyName", "familyname")
        self._setInfoFromName("styleName", "SubFamily")
        info.versionMajor, info.versionMinor = parseVersion(self._sfd.version)

        self._setInfo("copyright", "copyright")
        self._setInfoFromName("trademark", "Trademark")
        self._setInfo("unitsPerEm", "em")
        self._setInfo("ascender", "ascent")
        self._setInfo("descender", "descent")
        self._setInfo("italicAngle", "italicangle")
        self._setInfo("capHeight", "capHeight")
        self._setInfo("xHeight", "xHeight")
        self._setInfo("note", "comment")

        # head
        self._setInfo("openTypeHeadCreated", "creationtime")

        # hhea
        self._setInfo("openTypeHheaAscender", "hhea_ascent")
        self._setInfo("openTypeHheaDescender", "hhea_descent")
        self._setInfo("openTypeHheaLineGap", "hhea_linegap")

        # OS/2
        self._setInfo("openTypeOS2WidthClass", "os2_width")
        self._setInfo("openTypeOS2WeightClass", "os2_weight")
        self._setInfo("openTypeOS2VendorID", "os2_vendor")
        if any(self._sfd.os2_panose):
            self._setInfo("openTypeOS2Panose", "os2_panose")
        self._setInfo("openTypeOS2FamilyClass", "os2_family_class")
       #self._setInfo("openTypeOS2UnicodeRanges", "os2_unicoderanges")
       #self._setInfo("openTypeOS2CodePageRanges", "os2_codepages")
        self._setInfo("openTypeOS2TypoAscender", "os2_typoascent")
        self._setInfo("openTypeOS2TypoDescender", "os2_typodescent")
        self._setInfo("openTypeOS2TypoLineGap", "os2_typolinegap")
        self._setInfo("openTypeOS2WinAscent", "os2_winascent")
        self._setInfo("openTypeOS2WinDescent", "os2_windescent")
        self._setInfo("openTypeVheaVertTypoLineGap", "vhea_linegap")
        self._setInfo("openTypeOS2Type", "os2_fstype")
        self._setInfo("openTypeGaspRangeRecords", "gasp")

        if any([self._sfd.os2_subxsize, self._sfd.os2_subysize,
                self._sfd.os2_subxoff, self._sfd.os2_subyoff,
                self._sfd.os2_supxsize, self._sfd.os2_supysize,
                self._sfd.os2_supxoff, self._sfd.os2_supyoff,
                self._sfd.os2_strikeysize, self._sfd.os2_strikeypos]):
            self._setInfo("openTypeOS2SubscriptXSize", "os2_subxsize")
            self._setInfo("openTypeOS2SubscriptYSize", "os2_subysize")
            self._setInfo("openTypeOS2SubscriptXOffset", "os2_subxoff")
            self._setInfo("openTypeOS2SubscriptYOffset", "os2_subyoff")
            self._setInfo("openTypeOS2SuperscriptXSize", "os2_supxsize")
            self._setInfo("openTypeOS2SuperscriptYSize", "os2_supysize")
            self._setInfo("openTypeOS2SuperscriptXOffset", "os2_supxoff")
            self._setInfo("openTypeOS2SuperscriptYOffset", "os2_supyoff")
            self._setInfo("openTypeOS2StrikeoutSize", "os2_strikeysize")
            self._setInfo("openTypeOS2StrikeoutPosition", "os2_strikeypos")

        if self._sfd.os2_use_typo_metrics:
            info.openTypeOS2Selection = [7]

        # OpenType names
        self._setInfoFromName("openTypeNameDesigner", "Designer")
        self._setInfoFromName("openTypeNameDesignerURL", "Designer URL")
        self._setInfoFromName("openTypeNameManufacturer", "Manufacturer")
        self._setInfoFromName("openTypeNameManufacturerURL", "Vendor URL")
        self._setInfoFromName("openTypeNameLicense", "License")
        self._setInfoFromName("openTypeNameLicenseURL", "License URL")
        self._setInfoFromName("openTypeNameVersion", "Version")
        self._setInfoFromName("openTypeNameUniqueID", "UniqueID")
        self._setInfoFromName("openTypeNameDescription", "Descriptor")
        self._setInfoFromName("openTypeNamePreferredFamilyName", "Preferred Family")
        self._setInfoFromName("openTypeNamePreferredSubfamilyName", "Preferred Styles")
        self._setInfoFromName("openTypeNameCompatibleFullName", "Compatible Full")
        self._setInfoFromName("openTypeNameSampleText", "Sample Text")
        self._setInfoFromName("openTypeNameWWSFamilyName", "WWS Family")
        self._setInfoFromName("openTypeNameWWSSubfamilyName", "WWS Subfamily")

        # PostScript
        self._setInfo("postscriptFontName", "fontname")
        self._setInfo("postscriptFullName", "fullname")
        info.postscriptSlantAngle = info.italicAngle
        self._setInfo("postscriptWeightName", "weight")
        self._setInfo("postscriptUniqueID", "uniqueid")
        self._setInfo("postscriptUnderlineThickness", "uwidth")
        self._setInfo("postscriptUnderlinePosition", "upos")

        self._setPrivate("postscriptBlueValues", "BlueValues")
        self._setPrivate("postscriptOtherBlues", "OtherBlues")
        self._setPrivate("postscriptFamilyBlues", "FamilyBlues")
        self._setPrivate("postscriptFamilyOtherBlues", "FamilyOtherBlues")
        self._setPrivate("postscriptStemSnapH", "StemSnapH")
        self._setPrivate("postscriptStemSnapV", "StemSnapV")
        self._setPrivate("postscriptBlueFuzz", "BlueFuzz")
        self._setPrivate("postscriptBlueShift", "BlueShift")
        self._setPrivate("postscriptBlueScale", "BlueScale")
        self._setPrivate("postscriptForceBold", "ForceBold")

        # Guidelines
        for c in self._sfd.guide:
            # I suppose this is a line
            if len(c) == 2:
                x = None
                y = None
                angle = None
                name = None

                p0 = c[0]
                p1 = c[1]
                if c.name is not None:
                    name = tounicode(c.name, encoding="utf-8")

                if p0.x == p1.x:
                    x = p0.x
                elif p0.y == p1.y:
                    y = p0.y
                else:
                    x = p0.x
                    y = p0.y
                    angle = math.degrees(math.atan2(p1.x - p0.x, p1.y - p0.y))
                    if angle < 0:
                        angle = 360 + angle
                self._font.info.appendGuideline({"x": x, "y": y, "name": name, "angle": angle})

    def _buildLayers(self):
        for i in range(self._sfd.layer_cnt):
            name = self._sfd.layers[i].name
            if i == self._sfd.activeLayer:
                self._layerMap[name] = self._font.layers.defaultLayer
            else:
                self._layerMap[name] = self._font.newLayer(name)

    def _buildGlyphs(self):
        for sfdGlyph in self._sfd.glyphs():
            name = sfdGlyph.glyphname
            for sfdLayerName in sfdGlyph.layers:
                sfdLayer = sfdGlyph.layers[sfdLayerName]
                sfdLayerRefs = sfdGlyph.layerrefs[sfdLayerName]
                layer = self._layerMap[sfdLayerName]
                if not sfdLayer and not sfdLayerRefs and layer != self._font.layers.defaultLayer:
                    continue
                glyph = layer.newGlyph(name)
                pen = glyph.getPen()
                glyph.width = sfdGlyph.width
                # Hmm, FontForge always reports a vwidth even if the user
                # didn’t set any! The test against UPEM is an attempt to catch
                # this.
                if sfdGlyph.vwidth != self._sfd.em:
                    glyph.height = sfdGlyph.vwidth
                sfdLayer.draw(pen)
                for ref in sfdLayerRefs:
                    pen.addComponent(ref[0], ref[1])
                if sfdGlyph.color >= 0:
                    glyph.markColor = parseColor(sfdGlyph.color)
                if sfdGlyph.glyphclass != "automatic":
                    glyph.lib[FONTFORGE_PREFIX + ".glyphclass"] = sfdGlyph.glyphclass

            glyph = self._font[name]
            unicodes = []
            if sfdGlyph.unicode > 0:
                unicodes.append(sfdGlyph.unicode)
            if sfdGlyph.altuni:
                unicodes += parseAltuni(sfdGlyph.altuni, self._ignore_uvs)
            glyph.unicodes = unicodes

            for anchor in sfdGlyph.anchorPoints:
                glyph.appendAnchor(parseAnchorPoint(anchor))

    def _buildKerning(self):
        sfd = self._sfd

        subtables = []
        for lookup in sfd.gpos_lookups:
            lookpinfo = sfd.getLookupInfo(lookup)
            for subtable in sfd.getLookupSubtables(lookup):
                if sfd.isKerningClass(subtable):
                    # Class kerning.
                    groups1, groups2, kerns = sfd.getKerningClass(subtable)
                    subtables.append((groups1, groups2, kerns))
                    # Delete the kern subtable so that we don’t export it to
                    # the feature file.
                    sfd.removeLookupSubtable(subtable)
                elif lookpinfo[0] == "gpos_pair":
                    # Non-class kerning.
                    for sfdGlyph in sfd.glyphs():
                        name1 = sfdGlyph.glyphname
                        unsupportedPair = False
                        kerning = {}
                        for pos in sfdGlyph.getPosSub(subtable):
                            name2 = pos[2]
                            x1, y1, xoff1, yoff1, x2, y2, xoff2, yoff2 = pos[3:]
                            # UFO kerning is so dumb, so only export the
                            # kerning that changes the x offset of the first
                            # glyph only, otherwise let it be exported to the
                            # feature file.
                            if not all([x1, y1, yoff1, x2, y2, xoff2, yoff2]):
                                kerning[name1, name2] = xoff1
                            else:
                                unsupportedPair = True

                        if kerning and not unsupportedPair:
                            self._font.kerning.update(kerning)
                            # Delete the positioning so that we don’t export it
                            # to the feature file.
                            sfdGlyph.removePosSub(subtable)

        processKernClasses(self._font, subtables)

    def _buildFeatures(self):
        if hasattr(self._sfd, "generateFeatureString"):
            fea = self._sfd.generateFeatureString()
        else:
            from tempfile import NamedTemporaryFile
            with NamedTemporaryFile() as feafile:
                self._sfd.generateFeatureFile(feafile.name)
                feafile.flush()
                fea = feafile.read()
        self._font.features.text = tounicode(fea)
