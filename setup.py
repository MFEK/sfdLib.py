from setuptools import setup

setup(
    name = "sfd2ufo",
    version = "1.0",
    description = "A simple, quick and dirty, SFD to UFO converter.",
    author = "Khaled Hosny",
    author_email = "khaledhosny@eglug.org",
        url = "https://github.com/khaledhosny/sfd2ufo",
    license = "OpenSource, BSD-style",
    platforms = ["Any"],

    packages = [
        "sfd2ufo",
    ],
    package_dir = {'': 'Lib'},
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
)
