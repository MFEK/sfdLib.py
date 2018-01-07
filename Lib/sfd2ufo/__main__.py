import argparse

from . import SFDFont

def main():
    parser = argparse.ArgumentParser(description="Convert FontForge fonts to UFO.")
    parser.add_argument("sfdfile", metavar="FILE", help="input font to process")
    parser.add_argument("ufofile", metavar="FILE", help="output font to write")
    parser.add_argument("--ignore-uvs", action="store_true",
        help="don’t error if the font uses Unicode variation selectors")

    args = parser.parse_args()

    font = SFDFont(args.sfdfile, args.ignore_uvs)
    font.save(args.ufofile)

if __name__ == "__main__":
    main()
