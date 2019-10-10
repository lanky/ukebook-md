#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:
import os
import sys
import argparse
from glob import glob
import re
from progress.bar import Bar
from bs4 import BeautifulSoup as bs
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

def parse_cmdline(argv):
    parser = argparse.ArgumentParser(description="Convert a multi-page HTML songbook into PDF")
    parser.add_argument("inputdir", help="top-level directory containing HTML")
    parser.add_argument("-o", "--output", default="output.pdf",
        help="Name of PDF file to generate (default: output.pdf). This will be silently replaced if it already exists.")

    opts = parser.parse_args(argv)

    if not os.path.isdir(opts.inputdir):
        print("input dir doesn't appear to exist")
        parser.print_help()
        sys.exit(1)

    return opts

def collate(contentdir, outputfile="output.pdf", fontcfg=FontConfiguration()):

    # the index page will be a string as I need to correct the links
    index = process_links(os.path.join(contentdir, 'index.html'))

    pages = sorted(glob('{}/songs/*.html'.format(contentdir)))

    print ("Rendering index")
    css = [ CSS(os.path.join(contentdir, 'css', 'pdfprint.css')) ]
    documents = [ HTML(string=index).render(stylesheets=css, font_config=fontcfg) ]

    for pg in Bar("Processing HTML").iter(pages):
        try:
            thisdoc = HTML(pg).render(stylesheets=css, font_config=fontcfg)
            documents.append(thisdoc)
        except:
            print ("Failed to render {}".format(pg))

    print("combining pages")
    all_pages = [ page for d in documents for page in d.pages ]
    print("writing PDF to {}".format(outputfile))
    documents[0].copy(all_pages).write_pdf(outputfile)

def process_links(indexhtml):
    """
    ensures all links processed are internal. returns str
    """
    with open(indexhtml) as idx:
        idxsoup = bs(idx, features='lxml')
        for a in idxsoup.findAll('a'):
            if re.match(r'title_\d{3}', a['href']):
                continue
            else:
                linkid = a['id'].split('_')[1]
                a['href'] = '#title_{}'.format(linkid)
        return str(idxsoup)
    return None


if __name__ == "__main__":
    opts = parse_cmdline(sys.argv[1:])

    collate(opts.inputdir, outputfile=opts.output)

