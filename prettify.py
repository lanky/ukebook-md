#!/usr/bin/env python3
import os
import sys
import codecs
from bs4 import BeautifulSoup as bs

def main():
    for chordfile in sys.argv[1:]:
        try:
            with codecs.open(chordfile, encoding="utf-8", mode="r") as messy:
                soup = bs(messy.read())
                try:
                    with codecs.open('pretty_{}'.format(chordfile), encoding="utf-8", mode="w") as output:
                        output.write(soup.prettify())
                except:
                    print("failed to write output file")
                    pass
        except:
            print("could not open/process {}".format(chordfile))
            raise
            pass

if __name__ == "__main__":
    main()

