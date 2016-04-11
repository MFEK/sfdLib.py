#!/usr/bin/python2
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

    def _buildInfo(self):
        info = self.info
        info.familyName = self._sfd.familyname
        #info.styleName = self._sfd
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
        #info.year = self._sfd

        info.copyright = self._sfd.copyright
        #info.trademark = self._sfd
        info.unitsPerEm = self._sfd.em
        info.ascender = self._sfd.ascent
        info.descender = -self._sfd.descent
        info.italicAngle = self._sfd.italicangle
        if self._sfd.capHeight > 0:
            info.capHeight = self._sfd.capHeight
        if self._sfd.xHeight > 0:
            info.xHeight = self._sfd.xHeight
        info.note = self._sfd.comment

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

            if sfdGlyph.unicode > 0:
                glyph = self[sfdGlyph.name]
                glyph.unicode = sfdGlyph.unicode
                glyph.unicodes.append(glyph.unicode)
                if sfdGlyph.altuni:
                    for altuni in sfdGlyph.altuni:
                        # TODO: what about variation selectors?
                        if altuni[1] == 0xfe00:
                            glyph.unicodes.append(altuni[0])

