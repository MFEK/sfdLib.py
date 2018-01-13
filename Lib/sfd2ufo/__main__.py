import argparse

from defcon import Font

from . import SFDFont
from .parser import SFDParser


def main():
    parser = argparse.ArgumentParser(
        prog="sfd2ufo", description="Convert FontForge fonts to UFO.")
    parser.add_argument("sfdfile", metavar="FILE", help="input font to process")
    parser.add_argument("ufofile", metavar="FILE", help="output font to write")
    parser.add_argument("--ignore-uvs", action="store_true",
        help="don’t error if the font uses Unicode variation selectors")

    args = parser.parse_args()

    font = Font()
    parser = SFDParser(args.sfdfile, font, args.ignore_uvs)
    parser.parse()

#   font = SFDFont(args.sfdfile, args.ignore_uvs)
    font.save(args.ufofile)

if __name__ == "__main__":
    main()
