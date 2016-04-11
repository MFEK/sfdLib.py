import sys
from . import SFDFont

font = SFDFont(sys.argv[1])
font.save(sys.argv[2])
