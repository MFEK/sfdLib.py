#
# encoding: utf-8

from fontTools.misc.py23 import *

from defcon import Font
import fontforge
import math

class SFDFont(Font):

    def __init__(self, path):
        super(SFDFont, self).__init__()

        self._sfd = fontforge.open(path)
        self._layerMap = {}
        self._bounds = None
        self._private = {}

        self._buildLayers()
        self._buildGlyphs()
        self._buildKerning()
        self._buildFeatures()
        self._buildInfo()

    def __del__(self):
        self._sfd.close()

    def _setInfoFromName(self, ufoName, sfdName):
        for name in self._sfd.sfnt_names:
            if name[0] == "English (US)" and name[1] == sfdName:
                setattr(self.info, ufoName, name[2])

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

            bb = self._getFontBounds()
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

            setattr(self.info, ufoName, value)

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
            setattr(self.info, ufoName, self._private[sfdName])

    def _getVesrsion(self):
        versionMajor = ""
        versionMinor = ""
        version = self._sfd.version
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

    def _getFontBounds(self):
        """Calculate FF font bounds."""

        bbox = [int(round(v)) for v in self.bounds]
        return dict(xMin=bbox[0], yMin=bbox[1], xMax=bbox[2], yMax=bbox[3])

    def _buildInfo(self):
        info = self.info

        self._setInfo("familyName", "familyname")
        self._setInfoFromName("styleName", "SubFamily")
        info.versionMajor, info.versionMinor = self._getVesrsion()

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
        self._setInfo("openTypeOS2Panose", "os2_panose")
        self._setInfo("openTypeOS2FamilyClass", "os2_family_class")
       #self._setInfo("openTypeOS2UnicodeRanges", "os2_unicoderanges")
       #self._setInfo("openTypeOS2CodePageRanges", "os2_codepages")
        self._setInfo("openTypeOS2TypoAscender", "os2_typoascent")
        self._setInfo("openTypeOS2TypoDescender", "os2_typodescent")
        self._setInfo("openTypeOS2TypoLineGap", "os2_typolinegap")
        self._setInfo("openTypeOS2WinAscent", "os2_winascent")
        self._setInfo("openTypeOS2WinDescent", "os2_windescent")
        self._setInfo("openTypeOS2Type", "os2_fstype")
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
                name = c.name

                if p0.x == p1.x:
                    x = p0.x
                elif p0.y == p1.y:
                    y = p0.y
                else:
                    x = p0.x
                    y = p0.y
                    angle = math.degrees(math.atan2(p1.x - p0.x, p1.y - p0.y))
                self.info.appendGuideline({"x": x, "y": y, "name": name, "angle": angle})

    def _buildLayers(self):
        for i in range(self._sfd.layer_cnt):
            name = self._sfd.layers[i].name
            if i == self._sfd.activeLayer:
                self._layerMap[name] = self.layers.defaultLayer
            else:
                self._layerMap[name] = self.newLayer(name)

    def _buildGlyphs(self):
        for sfdGlyph in self._sfd.glyphs():
            name = sfdGlyph.glyphname
            for sfdLayerName in sfdGlyph.layers:
                sfdLayer = sfdGlyph.layers[sfdLayerName]
                sfdLayerRefs = sfdGlyph.layerrefs[sfdLayerName]
                layer = self._layerMap[sfdLayerName]
                if not sfdLayer and not sfdLayerRefs and layer != self.layers.defaultLayer:
                    continue
                glyph = layer.newGlyph(name)
                pen = glyph.getPen()
                glyph.width = sfdGlyph.width
                sfdLayer.draw(pen)
                for ref in sfdLayerRefs:
                    pen.addComponent(ref[0], ref[1])
                if sfdGlyph.color >= 0:
                    r = (sfdGlyph.color & 255) / 255.
                    g = ((sfdGlyph.color >> 8) & 255) / 255.
                    b = ((sfdGlyph.color >> 16) & 255) / 255.
                    a = 1.0
                    glyph.markColor = (r, g, b, a)
                if sfdGlyph.glyphclass != "automatic":
                    glyph.lib["org.fontforge.glyphclass"] = sfdGlyph.glyphclass

            glyph = self[name]
            glyph.unicodes = []
            if sfdGlyph.unicode > 0:
                glyph.unicodes.append(sfdGlyph.unicode)
            if sfdGlyph.altuni:
                for uni, uvs, _ in sfdGlyph.altuni:
                    assert uvs == -1, "Glyph %s uses variation selector "      \
                            "U+%04X, UFO doesn’t support this!" % (name, uvs)
                    glyph.unicodes.append(uni)

            for anchor in sfdGlyph.anchorPoints:
                name, kind, x, y = anchor[:4]
                if kind == "mark":
                    name = "_" + name
                elif kind == "ligature":
                    index = anchor[4]
                    name = "%s_%s" % (name, index)
                elif kind in ["entry", "exit"]:
                    name = "%s_%s" % (name, kind)

                glyph.appendAnchor(dict(name=name, x=x, y=y))

    def _buildKerning(self):
        sfd = self._sfd

        subtables = []
        for lookup in sfd.gpos_lookups:
            for subtable in sfd.getLookupSubtables(lookup):
                if sfd.isKerningClass(subtable):
                    subtables.append(subtable)

        for i, subtable in enumerate(subtables):
            groups1, groups2, kerns = sfd.getKerningClass(subtable)
            for j, group1 in enumerate(groups1):
                for k, group2 in enumerate(groups2):
                    kern = kerns[(j * len(groups2)) + k]
                    if group1 is not None and group2 is not None and kern != 0:
                        name1 = "public.kern1.kc%d_%d" % (i, j)
                        name2 = "public.kern2.kc%d_%d" % (i, k)
                        if name1 not in self.groups:
                            self.groups[name1] = group1
                        if name2 not in self.groups:
                            self.groups[name2] = group2
                        assert self.groups[name1] == group1
                        assert self.groups[name2] == group2
                        self.kerning[name1, name2] = kern

        # Delete the kern subtable so that we don’t export them to the feature
        # file.
        for subtable in subtables:
            sfd.removeLookupSubtable(subtable)

    def _buildFeatures(self):
        if hasattr(self._sfd, "generateFeatureString"):
            fea = self._sfd.generateFeatureString()
        else:
            from tempfile import NamedTemporaryFile
            with NamedTemporaryFile() as feafile:
                self._sfd.generateFeatureFile(feafile.name)
                feafile.flush()
                fea = feafile.read()
        self.features.text = tounicode(fea)
