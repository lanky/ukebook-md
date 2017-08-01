#!/usr/bin/env python 
from __future__ import print_function
import markdown
import codecs
import ukedown_extension
input_file = codecs.open("inputs/dontstrop.txt", mode="r", encoding="utf-8")
txt = input_file.read()

default = markdown.markdown(txt)
# adding BR tags to newlines
br = markdown.markdown(txt, extensions=['markdown.extensions.nl2br'])
# attempting to surround chords with <span class='chord'>XXX</span>
chordext = ukedown_extension.ChordExtension()
blockext = ukedown_extension.BoxExtension()

brcd = markdown.markdown(txt, extensions=['markdown.extensions.nl2br', chordext, blockext])

print(brcd)

