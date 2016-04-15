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

    def _setFromSfntName(self, info, ufoName, sfdName):
        for name in self._sfd.sfnt_names:
            if name[0] == "English (US)" and name[1] == sfdName:
                setattr(info, ufoName, name[2])

    def _setFromFont(self, info, ufoName, sfdName):
        value = getattr(self._sfd, sfdName)
        if value:
            setattr(info, ufoName, value)

    def _buildInfo(self):
        info = self.info

        self._setFromFont(info, "familyName", "familyname")
        self._setFromSfntName(info, "styleName", "SubFamily")
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

        self._setFromFont(info, "copyright", "copyright")
        self._setFromSfntName(info, "trademark", "Trademark")
        self._setFromFont(info, "unitsPerEm", "em")
        self._setFromFont(info, "ascender", "ascent")
        self._setFromFont(info, "descender", "descent")
        if info.descender:
            info.descender = -info.descender
        self._setFromFont(info, "italicAngle", "italicangle")
        if self._sfd.capHeight > 0:
            self._setFromFont(info, "capHeight", "capHeight")
        if self._sfd.xHeight > 0:
            self._setFromFont(info, "xHeight", "xHeight")
        self._setFromFont(info, "note", "comment")

        # make sure we get absolute values for those
        for attr in ("os2_typoascent", "os2_typodescent", "os2_winascent", "os2_windescent", "hhea_ascent", "hhea_descent"):
            setattr(self._sfd, "%s_add" % attr, False)

        # hhea
        self._setFromFont(info, "openTypeHheaAscender", "hhea_ascent")
        self._setFromFont(info, "openTypeHheaDescender", "hhea_descent")
        self._setFromFont(info, "openTypeHheaLineGap", "hhea_linegap")

        # OS/2
        self._setFromFont(info, "openTypeOS2WidthClass", "os2_width")
        self._setFromFont(info, "openTypeOS2WeightClass", "os2_weight")
       #self._setFromFont(info, "openTypeOS2Selection", "")
        self._setFromFont(info, "openTypeOS2VendorID", "os2_vendor")
        self._setFromFont(info, "openTypeOS2Panose", "os2_panose")
        self._setFromFont(info, "openTypeOS2FamilyClass", "os2_family_class")
       #self._setFromFont(info, "openTypeOS2UnicodeRanges", "os2_unicoderanges")
       #self._setFromFont(info, "openTypeOS2CodePageRanges", "os2_codepages")
        self._setFromFont(info, "openTypeOS2TypoAscender", "os2_typoascent")
        self._setFromFont(info, "openTypeOS2TypoDescender", "os2_typodescent")
        self._setFromFont(info, "openTypeOS2TypoLineGap", "os2_typolinegap")
        self._setFromFont(info, "openTypeOS2WinAscent", "os2_winascent")
        self._setFromFont(info, "openTypeOS2WinDescent", "os2_windescent")
       #self._setFromFont(info, "openTypeOS2Type", "os2_fstype")
        self._setFromFont(info, "openTypeOS2SubscriptXSize", "os2_subxsize")
        self._setFromFont(info, "openTypeOS2SubscriptYSize", "os2_subysize")
        self._setFromFont(info, "openTypeOS2SubscriptXOffset", "os2_subxoff")
        self._setFromFont(info, "openTypeOS2SubscriptYOffset", "os2_subyoff")
        self._setFromFont(info, "openTypeOS2SuperscriptXSize", "os2_supxsize")
        self._setFromFont(info, "openTypeOS2SuperscriptYSize", "os2_supysize")
        self._setFromFont(info, "openTypeOS2SuperscriptXOffset", "os2_supxoff")
        self._setFromFont(info, "openTypeOS2SuperscriptYOffset", "os2_supyoff")
        self._setFromFont(info, "openTypeOS2StrikeoutSize", "os2_strikeysize")
        self._setFromFont(info, "openTypeOS2StrikeoutPosition", "os2_strikeypos")

        # OpenType names
        self._setFromSfntName(info, "openTypeNameDesigner", "Designer")
        self._setFromSfntName(info, "openTypeNameDesignerURL", "Designer URL")
        self._setFromSfntName(info, "openTypeNameManufacturer", "Manufacturer")
        self._setFromSfntName(info, "openTypeNameManufacturerURL", "Vendor URL")
        self._setFromSfntName(info, "openTypeNameLicense", "License")
        self._setFromSfntName(info, "openTypeNameLicenseURL", "License URL")
        self._setFromSfntName(info, "openTypeNameVersion", "Version")
        self._setFromSfntName(info, "openTypeNameUniqueID", "UniqueID")
        self._setFromSfntName(info, "openTypeNameDescription", "Descriptor")
        self._setFromSfntName(info, "openTypeNamePreferredFamilyName", "Preferred Family")
        self._setFromSfntName(info, "openTypeNamePreferredSubfamilyName", "Preferred Styles")
        self._setFromSfntName(info, "openTypeNameCompatibleFullName", "Compatible Full")
        self._setFromSfntName(info, "openTypeNameSampleText", "Sample Text")
        self._setFromSfntName(info, "openTypeNameWWSFamilyName", "WWS Family")
        self._setFromSfntName(info, "openTypeNameWWSSubfamilyName", "WWS Subfamily")

        # PostScript
        self._setFromFont(info, "postscriptFontName", "fontname")
        self._setFromFont(info, "postscriptFullName", "fullname")
        info.postscriptSlantAngle = info.italicAngle
        self._setFromFont(info, "postscriptWeightName", "weight")
        self._setFromFont(info, "postscriptUniqueID", "uniqueid")
        self._setFromFont(info, "postscriptUnderlineThickness", "uwidth")
        self._setFromFont(info, "postscriptUnderlinePosition", "upos")

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

