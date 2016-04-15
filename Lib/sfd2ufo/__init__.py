from defcon import Font
import fontforge

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

    def _setFromSfntName(self, ufoName, sfdName):
        for name in self._sfd.sfnt_names:
            if name[0] == "English (US)" and name[1] == sfdName:
                setattr(self.info, ufoName, name[2])

    def _setFromFont(self, ufoName, sfdName):
        value = getattr(self._sfd, sfdName)
        if value:
            # UFO's descender is -ve and FontForge's is +ve
            if sfdName in ("descent"):
                value = -value
            # -ve value means computing it failed
            if sfdName in ("capHeight", "xHeight") and value < 0:
                return
            setattr(self.info, ufoName, value)

    def _buildInfo(self):
        info = self.info

        self._setFromFont("familyName", "familyname")
        self._setFromSfntName("styleName", "SubFamily")
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

        self._setFromFont("copyright", "copyright")
        self._setFromSfntName("trademark", "Trademark")
        self._setFromFont("unitsPerEm", "em")
        self._setFromFont("ascender", "ascent")
        self._setFromFont("descender", "descent")
        self._setFromFont("italicAngle", "italicangle")
        self._setFromFont("capHeight", "capHeight")
        self._setFromFont("xHeight", "xHeight")
        self._setFromFont("note", "comment")

        # make sure we get absolute values for those
        for attr in ("os2_typoascent", "os2_typodescent", "os2_winascent", "os2_windescent", "hhea_ascent", "hhea_descent"):
            setattr(self._sfd, "%s_add" % attr, False)

        # hhea
        self._setFromFont("openTypeHheaAscender", "hhea_ascent")
        self._setFromFont("openTypeHheaDescender", "hhea_descent")
        self._setFromFont("openTypeHheaLineGap", "hhea_linegap")

        # OS/2
        self._setFromFont("openTypeOS2WidthClass", "os2_width")
        self._setFromFont("openTypeOS2WeightClass", "os2_weight")
       #self._setFromFont("openTypeOS2Selection", "")
        self._setFromFont("openTypeOS2VendorID", "os2_vendor")
        self._setFromFont("openTypeOS2Panose", "os2_panose")
        self._setFromFont("openTypeOS2FamilyClass", "os2_family_class")
       #self._setFromFont("openTypeOS2UnicodeRanges", "os2_unicoderanges")
       #self._setFromFont("openTypeOS2CodePageRanges", "os2_codepages")
        self._setFromFont("openTypeOS2TypoAscender", "os2_typoascent")
        self._setFromFont("openTypeOS2TypoDescender", "os2_typodescent")
        self._setFromFont("openTypeOS2TypoLineGap", "os2_typolinegap")
        self._setFromFont("openTypeOS2WinAscent", "os2_winascent")
        self._setFromFont("openTypeOS2WinDescent", "os2_windescent")
       #self._setFromFont("openTypeOS2Type", "os2_fstype")
        self._setFromFont("openTypeOS2SubscriptXSize", "os2_subxsize")
        self._setFromFont("openTypeOS2SubscriptYSize", "os2_subysize")
        self._setFromFont("openTypeOS2SubscriptXOffset", "os2_subxoff")
        self._setFromFont("openTypeOS2SubscriptYOffset", "os2_subyoff")
        self._setFromFont("openTypeOS2SuperscriptXSize", "os2_supxsize")
        self._setFromFont("openTypeOS2SuperscriptYSize", "os2_supysize")
        self._setFromFont("openTypeOS2SuperscriptXOffset", "os2_supxoff")
        self._setFromFont("openTypeOS2SuperscriptYOffset", "os2_supyoff")
        self._setFromFont("openTypeOS2StrikeoutSize", "os2_strikeysize")
        self._setFromFont("openTypeOS2StrikeoutPosition", "os2_strikeypos")

        # OpenType names
        self._setFromSfntName("openTypeNameDesigner", "Designer")
        self._setFromSfntName("openTypeNameDesignerURL", "Designer URL")
        self._setFromSfntName("openTypeNameManufacturer", "Manufacturer")
        self._setFromSfntName("openTypeNameManufacturerURL", "Vendor URL")
        self._setFromSfntName("openTypeNameLicense", "License")
        self._setFromSfntName("openTypeNameLicenseURL", "License URL")
        self._setFromSfntName("openTypeNameVersion", "Version")
        self._setFromSfntName("openTypeNameUniqueID", "UniqueID")
        self._setFromSfntName("openTypeNameDescription", "Descriptor")
        self._setFromSfntName("openTypeNamePreferredFamilyName", "Preferred Family")
        self._setFromSfntName("openTypeNamePreferredSubfamilyName", "Preferred Styles")
        self._setFromSfntName("openTypeNameCompatibleFullName", "Compatible Full")
        self._setFromSfntName("openTypeNameSampleText", "Sample Text")
        self._setFromSfntName("openTypeNameWWSFamilyName", "WWS Family")
        self._setFromSfntName("openTypeNameWWSSubfamilyName", "WWS Subfamily")

        # PostScript
        self._setFromFont("postscriptFontName", "fontname")
        self._setFromFont("postscriptFullName", "fullname")
        info.postscriptSlantAngle = info.italicAngle
        self._setFromFont("postscriptWeightName", "weight")
        self._setFromFont("postscriptUniqueID", "uniqueid")
        self._setFromFont("postscriptUnderlineThickness", "uwidth")
        self._setFromFont("postscriptUnderlinePosition", "upos")

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
                glyph = layer.newGlyph(sfdGlyph.name)
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
                glyph = self[sfdGlyph.name]
                glyph.unicodes = [sfdGlyph.unicode]
                if sfdGlyph.altuni:
                    for altuni in sfdGlyph.altuni:
                        # TODO: what about variation selectors?
                        if altuni[1] == 0xfe00:
                            glyph.unicodes.append(altuni[0])

