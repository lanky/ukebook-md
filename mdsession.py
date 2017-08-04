#!/usr/bin/env python 
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import
import markdown
import codecs
import ukedown.udn
from jinja2 import Environment, FileSystemLoader

import sys
import os

def render(template, context):
    j2env = Environment(loader=FileSystemLoader("templates"))

    tpl = j2env.get_template(template)

    return tpl.render(context)

def ukedown_to_html(inputfile):
    
    fh = codecs.open(inputfile, mode="r", encoding="utf-8")
    txt = fh.read()

    return markdown.markdown(txt, extensions=['markdown.extensions.nl2br', 'ukedown.udn'])



if __name__ == "__main__":
    if len(sys.argv[1:]) == 0:
        print ("no filename")
        sys.exit(1)
    else:
        for f in sys.argv[1:]:
            try:
                ud = ukedown_to_html(f)
                out = render("ukesong.j2", {'rendered_text': ud })
                print(out.encode("utf-8", "ignore"))

            except (IOError, OSError), E:
                print ("oops - couldn't render %s (%s)" % (E.filename, E.strerror))

            except:
                # all other errors
                raise


