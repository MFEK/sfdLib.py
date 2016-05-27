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

    def _sefInfoFromName(self, ufoName, sfdName):
        for name in self._sfd.sfnt_names:
            if name[0] == "English (US)" and name[1] == sfdName:
                setattr(self.info, ufoName, name[2])

    def _sefInfo(self, ufoName, sfdName):
        value = getattr(self._sfd, sfdName)
        if value:
            # UFO's descender is -ve and FontForge's is +ve
            if sfdName in ("descent"):
                value = -value
            # -ve value means computing it failed
            if sfdName in ("capHeight", "xHeight") and value < 0:
                return
            if sfdName == "os2_family_class":
                value = (value >> 8, value & 0xff)
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

    def _buildInfo(self):
        info = self.info

        self._sefInfo("familyName", "familyname")
        self._sefInfoFromName("styleName", "SubFamily")
        info.versionMajor, info.versionMinor = self._getVesrsion()

        self._sefInfo("copyright", "copyright")
        self._sefInfoFromName("trademark", "Trademark")
        self._sefInfo("unitsPerEm", "em")
        self._sefInfo("ascender", "ascent")
        self._sefInfo("descender", "descent")
        self._sefInfo("italicAngle", "italicangle")
        self._sefInfo("capHeight", "capHeight")
        self._sefInfo("xHeight", "xHeight")
        self._sefInfo("note", "comment")

        # make sure we get absolute values for those
        for attr in ("os2_typoascent", "os2_typodescent", "os2_winascent", "os2_windescent", "hhea_ascent", "hhea_descent"):
            setattr(self._sfd, "%s_add" % attr, False)

        # hhea
        self._sefInfo("openTypeHheaAscender", "hhea_ascent")
        self._sefInfo("openTypeHheaDescender", "hhea_descent")
        self._sefInfo("openTypeHheaLineGap", "hhea_linegap")

        # OS/2
        self._sefInfo("openTypeOS2WidthClass", "os2_width")
        self._sefInfo("openTypeOS2WeightClass", "os2_weight")
       #self._sefInfo("openTypeOS2Selection", "")
        self._sefInfo("openTypeOS2VendorID", "os2_vendor")
        self._sefInfo("openTypeOS2Panose", "os2_panose")
        self._sefInfo("openTypeOS2FamilyClass", "os2_family_class")
       #self._sefInfo("openTypeOS2UnicodeRanges", "os2_unicoderanges")
       #self._sefInfo("openTypeOS2CodePageRanges", "os2_codepages")
        self._sefInfo("openTypeOS2TypoAscender", "os2_typoascent")
        self._sefInfo("openTypeOS2TypoDescender", "os2_typodescent")
        self._sefInfo("openTypeOS2TypoLineGap", "os2_typolinegap")
        self._sefInfo("openTypeOS2WinAscent", "os2_winascent")
        self._sefInfo("openTypeOS2WinDescent", "os2_windescent")
       #self._sefInfo("openTypeOS2Type", "os2_fstype")
        self._sefInfo("openTypeOS2SubscriptXSize", "os2_subxsize")
        self._sefInfo("openTypeOS2SubscriptYSize", "os2_subysize")
        self._sefInfo("openTypeOS2SubscriptXOffset", "os2_subxoff")
        self._sefInfo("openTypeOS2SubscriptYOffset", "os2_subyoff")
        self._sefInfo("openTypeOS2SuperscriptXSize", "os2_supxsize")
        self._sefInfo("openTypeOS2SuperscriptYSize", "os2_supysize")
        self._sefInfo("openTypeOS2SuperscriptXOffset", "os2_supxoff")
        self._sefInfo("openTypeOS2SuperscriptYOffset", "os2_supyoff")
        self._sefInfo("openTypeOS2StrikeoutSize", "os2_strikeysize")
        self._sefInfo("openTypeOS2StrikeoutPosition", "os2_strikeypos")

        # OpenType names
        self._sefInfoFromName("openTypeNameDesigner", "Designer")
        self._sefInfoFromName("openTypeNameDesignerURL", "Designer URL")
        self._sefInfoFromName("openTypeNameManufacturer", "Manufacturer")
        self._sefInfoFromName("openTypeNameManufacturerURL", "Vendor URL")
        self._sefInfoFromName("openTypeNameLicense", "License")
        self._sefInfoFromName("openTypeNameLicenseURL", "License URL")
        self._sefInfoFromName("openTypeNameVersion", "Version")
        self._sefInfoFromName("openTypeNameUniqueID", "UniqueID")
        self._sefInfoFromName("openTypeNameDescription", "Descriptor")
        self._sefInfoFromName("openTypeNamePreferredFamilyName", "Preferred Family")
        self._sefInfoFromName("openTypeNamePreferredSubfamilyName", "Preferred Styles")
        self._sefInfoFromName("openTypeNameCompatibleFullName", "Compatible Full")
        self._sefInfoFromName("openTypeNameSampleText", "Sample Text")
        self._sefInfoFromName("openTypeNameWWSFamilyName", "WWS Family")
        self._sefInfoFromName("openTypeNameWWSSubfamilyName", "WWS Subfamily")

        # PostScript
        self._sefInfo("postscriptFontName", "fontname")
        self._sefInfo("postscriptFullName", "fullname")
        info.postscriptSlantAngle = info.italicAngle
        self._sefInfo("postscriptWeightName", "weight")
        self._sefInfo("postscriptUniqueID", "uniqueid")
        self._sefInfo("postscriptUnderlineThickness", "uwidth")
        self._sefInfo("postscriptUnderlinePosition", "upos")

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

