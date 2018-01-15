`sfd2ufo` — An SFD to UFO converter
===================================

A simple utility to convert FontForge’s SFD fonts to UFO fonts. The main
objective is to create UFO files that are usable in a larger UFO based
workflow, and for that existing UFO libraries are used to generate the UFO
fonts.

There are currently two parsers, a pure Python one that parses a subset of SFD
fonts and a “native” parser that depends on FontForge’s Python module and
supports any font format FontForge supports.

Both parsers try to output UFO fonts that as close as possible, but some
differences are inevitable.
