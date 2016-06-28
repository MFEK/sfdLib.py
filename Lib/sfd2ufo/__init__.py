#
# encoding: utf-8

from defcon import Font
import fontforge
import math

class SFDFont(Font):

    def __init__(self, path):
        super(SFDFont, self).__init__()

        self._sfd = fontforge.open(path)
        self._layerMap = {}

        self._buildInfo()
        self._buildLayers()
        self._buildGlyphs()

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
            setattr(self.info, ufoName, value)

    def _getVesrsion(self):
        versionMajor = None
        versionMinor = None
        if "." in self._sfd.version:
            versionMajor = self._sfd.version.split(".")[0]
            versionMinor = self._sfd.version.split(".")[1]
        else:
            versionMajor = self._sfd.version
        if versionMajor and versionMajor.isdigit():
            versionMajor = int(versionMajor)
        if versionMinor and versionMinor.isdigit():
            versionMinor = int(versionMinor)

        return versionMajor or None, versionMinor or None

    def _calclauteFontBounds(self):
        """Calculate FF font bounds."""
        bbox = [0, 0, 0, 0]
        for glyph in self._sfd.glyphs():
            gBBox = glyph.boundingBox()
            if bbox == [0, 0, 0, 0]:
                bbox = list(gBBox)
            else:
               if gBBox[0] < bbox[0]: bbox[0] = gBBox[0] # xMin
               if gBBox[1] < bbox[1]: bbox[1] = gBBox[1] # yMin
               if gBBox[2] > bbox[2]: bbox[2] = gBBox[2] # xMax
               if gBBox[3] > bbox[3]: bbox[3] = gBBox[3] # yMax

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

        # make sure we get absolute values for those
        # TODO: Don’t modify values in place
        bb = self._calclauteFontBounds()
        if self._sfd.os2_typoascent_add:
            self._sfd.os2_typoascent_add = False
            self._sfd.os2_typoascent = self._sfd.ascent + self._sfd.os2_typoascent
        if self._sfd.os2_typodescent_add:
            self._sfd.os2_typodescent_add = False
            self._sfd.os2_typodescent = -self._sfd.descent + self._sfd.os2_typodescent

        if self._sfd.os2_winascent_add:
            self._sfd.os2_winascent_add = False
            self._sfd.os2_winascent = bb["yMax"] + self._sfd.os2_winascent
        if self._sfd.os2_windescent_add:
            self._sfd.os2_windescent_add = False
            self._sfd.os2_windescent = -bb["yMin"] + self._sfd.os2_windescent

        if self._sfd.hhea_ascent_add:
            self._sfd.hhea_ascent_add = False
            self._sfd.hhea_ascent = self._sfd.ascent + self._sfd.hhea_ascent
        if self._sfd.hhea_descent_add:
            self._sfd.hhea_descent_add = False
            self._sfd.hhea_descent = -self._sfd.descent + self._sfd.hhea_descent

        # head
        self._setInfo("openTypeHeadCreated", "creationtime")

        # hhea
        self._setInfo("openTypeHheaAscender", "hhea_ascent")
        self._setInfo("openTypeHheaDescender", "hhea_descent")
        self._setInfo("openTypeHheaLineGap", "hhea_linegap")

        # OS/2
        self._setInfo("openTypeOS2WidthClass", "os2_width")
        self._setInfo("openTypeOS2WeightClass", "os2_weight")
       #self._setInfo("openTypeOS2Selection", "")
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
            for sfdLayerName in sfdGlyph.layers:
                sfdLayer = sfdGlyph.layers[sfdLayerName]
                sfdLayerRefs = sfdGlyph.layerrefs[sfdLayerName]
                layer = self._layerMap[sfdLayerName]
                if not sfdLayer and not sfdLayerRefs and layer != self.layers.defaultLayer:
                    continue
                glyph = layer.newGlyph(sfdGlyph.glyphname)
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

            if sfdGlyph.unicode > 0:
                glyph = self[sfdGlyph.glyphname]
                glyph.unicodes = [sfdGlyph.unicode]
                if sfdGlyph.altuni:
                    for altuni in sfdGlyph.altuni:
                        # TODO: what about variation selectors?
                        if altuni[1] == 0xfe00:
                            glyph.unicodes.append(altuni[0])

