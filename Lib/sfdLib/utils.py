from fontTools.ufoLib.validators import groupsValidator

SFDLIB_PREFIX = "org.sfdlib"
DECOMPOSEREMOVEOVERLAP_KEY = SFDLIB_PREFIX + ".decomposeAndRemoveOverlap"
MATH_KEY = SFDLIB_PREFIX + ".MATH"


def parseVersion(version):
    versionMajor = ""
    versionMinor = ""
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


def parseAltuni(name, altuni, ignore_uvs):

    unicodes = []
    for uni, uvs, _ in altuni:
        if not ignore_uvs:
            assert uvs in (-1, 0xFFFFFFFF), (
                "Glyph %s uses variation selector "
                "U+%04X, UFO doesn’t support this!" % (name, uvs)
            )
        if uvs in (-1, 0xFFFFFFFF):
            unicodes.append(uni)

    return unicodes


def parseAnchorPoint(anchor):
    name, kind, x, y = anchor[:4]
    if kind == "mark":
        name = "_" + name
    elif kind == "ligature":
        index = anchor[4]
        name = "%s_%s" % (name, index)
    elif kind in ["entry", "exit"]:
        name = "%s_%s" % (name, kind)

    return dict(name=name, x=x, y=y)


def parseColor(color):
    r = (color & 255) / 255.0
    g = ((color >> 8) & 255) / 255.0
    b = ((color >> 16) & 255) / 255.0
    a = 1.0
    return f"{r:g},{g:g},{b:g},{a:g}"


def getFontBounds(bounds):
    """Calculate FF font bounds."""

    bbox = [int(round(v)) for v in bounds]
    return dict(xMin=bbox[0], yMin=bbox[1], xMax=bbox[2], yMax=bbox[3])


def kernClassesToUFO(subtables, prefix="public"):
    groups = {}
    kerning = {}

    for i, (groups1, groups2, kerns) in enumerate(subtables):
        for j, group1 in enumerate(groups1):
            for k, group2 in enumerate(groups2):
                kern = kerns[(j * len(groups2)) + k]
                if group1 is not None and group2 is not None and kern != 0:
                    name1 = "%s.kern1.kc%d_%d" % (prefix, i, j)
                    name2 = "%s.kern2.kc%d_%d" % (prefix, i, k)
                    if name1 not in groups:
                        groups[name1] = group1
                    if name2 not in groups:
                        groups[name2] = group2
                    assert groups[name1] == group1
                    assert groups[name2] == group2
                    kerning[name1, name2] = kern

    return groups, kerning


def processKernClasses(font, subtables):
    groups, kerning = kernClassesToUFO(subtables)
    valid, _ = groupsValidator(groups)
    if not valid:
        # If groupsValidator() thinks these groups are invalid, ufoLib will
        # refuse to save the files. Most likely the cause is glyphs
        # appearing in several kerning groups. Since UFO kerning is too
        # dumb to represent this, lets cheat on ufoLib and use our private
        # prefix for group names which would prevent it from attempting to
        # “validate” them.
        groups, kerning = kernClassesToUFO(subtables, SFDLIB_PREFIX)

    font.groups.update(groups)
    font.kerning.update(kerning)


_INBASE64 = [
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    62,
    -1,
    -1,
    -1,
    63,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
]


def SFDReadUTF7(data):
    """Python re-implementation of FontForge’s UTF-7 decoder which does not
    seem to be standards-complaint, so we can’t use Python’s builtin UTF-7
    codec.
    """

    out = b""

    data = data.strip('"').encode("ascii")

    if data and not isinstance(data[0], int):  # Python 2
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
                    prev = ch1 & 0xFF
                    ch1 >>= 8
                    prev_cnt = 1
                else:
                    ch1 |= prev << 24
                    prev = ch1 & 0xFFFF
                    ch1 = (ch1 >> 16) & 0xFFFF
                    prev_cnt = 2
                done = True

        if done:
            out += chr(ch1).encode("utf-8")
        if prev_cnt == 2:
            prev_cnt = 0
            if prev != 0:
                out += chr(prev).encode("utf-8")

    return out.decode("utf-8")


def sortGlyphs(font):
    """Emulate how FontForge orders output glyphs."""
    order = list(font.glyphOrder)

    def sort(name):
        # .notdef, .null, and nonmarkingreturn come first
        if name == ".notdef":
            return 0
        if name in (".null", "uni0000", "glyph1"):
            return 1
        if name in ("nonmarkingreturn", "uni000D", "glyph2"):
            return 2
        # Then encoded glyph in the encoding order (we are assuming Unicode
        # here, because meh).
        g = font[name]
        if g.unicode is not None:
            return g.unicode + 3
        # Then in the font order, we are adding 0x10FFFF here to make sure they
        # sort after Unicode.
        return order.index(name) + 0x10FFFF + 3

    return sorted(font.glyphOrder, key=sort)
