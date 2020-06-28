from setuptools import setup

setup(
    name = "sfdLib",
    version = "1.0.6",
    description = "A simple, quick and dirty, SFD to UFO converter.",
    author = "Khaled Hosny",
    author_email = "khaledhosny@eglug.org",
        url = "https://github.com/khaledhosny/sfdLib",
    license = "OpenSource, BSD-style",
    platforms = ["Any"],

    packages = [
        "sfdLib",
    ],
    entry_points = {
        'console_scripts': ['sfd2ufo = sfdLib.__main__:main'],
    },
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
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
)
