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
        help="Name of PDF file to generate. Will take its name from source directory if omitted",
    )
    parser.add_argument(
        "-s",
        "--stylesheets",
        help="specify user stylesheets to apply, must be in the 'css' subdir of the book",
    )

    opts = parser.parse_args(argv)

    opts.inputdir = Path(opts.inputdir)

    if not opts.inputdir.exists():
        print("input dir doesn't appear to exist")
        parser.print_help()
        sys.exit(1)

    if not opts.output:
        opts.output = opts.inputdir.with_suffix(".pdf").name

    return opts


def collate(options, fontcfg=FontConfiguration()):
    """
    put together a PDF, using a directory created by genbook.py
    """

    # the index page will be a string as I need to correct the links
    index = process_links(os.path.join(options.inputdir, "index.html"))

    pages = sorted(glob("{}/songs/*.html".format(options.inputdir)))

    print("Rendering index")
    render_args = {
        "font_config": fontcfg,
    }
    if options.stylesheets:
        css = [
            CSS(options.inputdir / "css" / f) for f in options.stylesheets.split(",")
        ]

        render_args["stylesheets"] = css

    documents = [HTML(string=index).render(**render_args)]

    for pg in Bar("Processing HTML").iter(pages):
        with open(pg) as pagecontent:
            linksoup = bs(pagecontent, features="lxml")
        ilink = linksoup.find("a", {"class": "middle"})
        if ilink is not None:
            ilink["href"] = "#title_index"

        linksoup.find("a", {"class": "left"}).decompose()
        linksoup.find("a", {"class": "right"}).decompose()

        thisdoc = HTML(string=str(linksoup)).render(**render_args)
        #        thisdoc = HTML(pg).render(stylesheets=css, font_config=fontcfg)
        documents.append(thisdoc)

    print("combining pages")
    all_pages = [page for d in documents for page in d.pages]
    print("writing PDF to {}".format(opts.output))
    documents[0].copy(all_pages).write_pdf(opts.output)


def process_links(indexhtml):
    """
    ensures all links processed are internal. returns str
    """
    with open(indexhtml) as idx:
        idxsoup = bs(idx, features="lxml")
        for a in idxsoup.findAll("a"):
            if re.match(r"title_\d{3}", a["href"]):
                continue
            else:
                linkid = a["id"].split("_")[1]
                a["href"] = "#title_{}".format(linkid)
        return str(idxsoup)
    return None


if __name__ == "__main__":
    opts = parse_cmdline(sys.argv[1:])

    collate(opts)
