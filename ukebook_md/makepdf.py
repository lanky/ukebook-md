#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:
import argparse
import os
import re
import sys
from glob import glob
from pathlib import Path

from bs4 import BeautifulSoup as bs
from progress.bar import Bar
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def parse_cmdline(argv):
    parser = argparse.ArgumentParser(
        description="Convert a multi-page HTML songbook into PDF"
    )
    parser.add_argument("inputdir", help="top-level directory containing HTML")
    parser.add_argument(
        "-o",
        "--output",
        default="output.pdf",
        help="""Name of PDF file to generate (default: output.pdf).
                This will be silently replaced if it already exists.""",
    )
    parser.add_argument(
        "-s",
        "--stylesheets",
        default="pdfprint.css",
        help="User stylesheets to apply, must be in the 'css' subdir of the book",
    )

    opts = parser.parse_args(argv)

    opts.inputdir = Path(opts.inputdir)

    if not opts.inputdir.exists():
        print("input dir doesn't appear to exist")
        parser.print_help()
        sys.exit(1)

    return opts


def collate(options: argparse.Namespace, fontcfg=FontConfiguration()):
    """
    put together a PDF, using a directory created by genbook.py
    """
    doclist = []

    css = [
        CSS(os.path.join(options.inputdir, "css", f))
        for f in options.stylesheets.split(",")
    ]

    # the index page will be a string as I need to correct the links
    print("Rendering index")
    index = process_links(options.inputdir / "index.html")

    doclist.append(HTML(string=index).render(stylesheets=css, font_config=fontcfg))

    pages = sorted(options.inputdir.glob("songs/*.html"))

    for pg in Bar("Processing HTML").iter(pages):
        with open(pg) as pagecontent:
            linksoup = bs(pagecontent, features="lxml")
        ilink = linksoup.find("a", {"class": "middle"})
        if ilink is not None:
            ilink["href"] = "#index00"

        linksoup.find("a", {"class": "left"}).decompose()
        linksoup.find("a", {"class": "right"}).decompose()

        thisdoc = HTML(string=str(linksoup)).render(
            stylesheets=css, font_config=fontcfg
        )
        #        thisdoc = HTML(pg).render(stylesheets=css, font_config=fontcfg)
        doclist.append(thisdoc)

    print("combining pages")

    all_pages = [page for d in doclist for page in d.pages]

    print("writing PDF to {}".format(options.output))

    doclist[0].copy(all_pages).write_pdf(options.output, optimize_images=True)


def process_links(index: Path) -> str:
    """
    ensures all links processed are internal. returns str
    """
    with index.open() as idx:
        idxsoup = bs(idx, features="lxml")
        for a in idxsoup.findAll("a"):
            if re.match(r"title_\d{3}", a["href"]):
                continue
            else:
                linkid = a["id"].split("_")[1]
                a["href"] = "#title_{}".format(linkid)
        return str(idxsoup)


def main():
    opts = parse_cmdline(sys.argv[1:])

    collate(opts)


if __name__ == "__main__":
    main()
