import argparse

from ufoLib2 import Font
from .parser import SFDParser


def main():
    parser = argparse.ArgumentParser(
        prog="sfd2ufo", description="Convert FontForge fonts to UFO.")
    parser.add_argument("sfdfile", metavar="FILE", help="input font to process")
    parser.add_argument("ufofile", metavar="FILE", help="output font to write")
    parser.add_argument("--ignore-uvs", action="store_true",
        help="don’t error if the font uses Unicode variation selectors")
    parser.add_argument("--ufo-anchors", action="store_true",
        help="output UFO anchors instead of writing them to feature file")

    args = parser.parse_args()

    font = Font()
    parser = SFDParser(args.sfdfile, font, args.ignore_uvs, args.ufo_anchors)
    parser.parse()

    font.save(args.ufofile)

if __name__ == "__main__":
    main()
