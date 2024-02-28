#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:
"""Convert a PDF book from an HTML songbook."""

import argparse
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup as bs
from progress.bar import Bar
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def parse_cmdline(argv):
    """Process commandline options and arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a multi-page HTML songbook into PDF"
    )
    parser.add_argument(
        "inputdir", type=Path, help="top-level directory containing HTML"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="""Name of PDF file to generate (default: INPUTDIR.pdf)
                This will be silently replaced if it already exists.""",
    )
    parser.add_argument(
        "-s",
        "--stylesheets",
        default="",
        help="User stylesheets to apply, must be in the 'css' subdir of the book",
    )

    opts = parser.parse_args(argv)

    if not opts.inputdir.exists():
        print("input dir doesn't appear to exist")
        parser.print_help()
        sys.exit(1)

    if not opts.output:
        opts.output = opts.inputdir.with_suffix(".pdf")

    return opts


def parse_song(page: Path) -> str:
    """Parse an individual songsheet.

    - Rewrites links  to  point to IDs not HTML files
    - Removes next & prev links
    """
    with page.open() as content:
        linksoup = bs(content, features="lxml")
        ilink = linksoup.find("a", {"class": "middle"})
        if ilink is not None:
            ilink["href"] = "#index00"

        # remove the forward and back links
        linksoup.find("a", {"class": "left"}).decompose()
        linksoup.find("a", {"class": "right"}).decompose()
        return str(linksoup)


def collate(options: argparse.Namespace, fontcfg=FontConfiguration()):
    """Convert a directory of HTML pages to a PDF document."""
    doclist = []

    if options.stylesheets:
        css = [
            CSS(options.inputdir / "css" / f)
            for f in options.stylesheets.split(",")
            if options.stylesheets
        ]
    else:
        css = None

    # handle a cover page if there is one
    if (options.inputdir / "cover.html").exists():
        print("Parsing cover page")
        cover = parse_cover(options.inputdir / "cover.html")
        doclist.append(
            HTML(string=cover, base_url="").render(stylesheets=css, font_config=fontcfg)
        )

    # the index page will be a string as I need to correct the links
    print("Rendering index")
    index = process_links(options.inputdir / "index.html")

    doclist.append(HTML(string=index).render(stylesheets=css, font_config=fontcfg))

    pages = sorted(options.inputdir.glob("songs/*.html"))

    for pg in Bar("Processing HTML").iter(pages):
        song = HTML(string=parse_song(pg)).render(stylesheets=css, font_config=fontcfg)
        doclist.append(song)

    print("collating pages")

    all_pages = [page for d in doclist for page in d.pages]

    print(f"writing PDF to {options.output}")

    doclist[0].copy(all_pages).write_pdf(options.output, optimize_images=True)


def process_links(index: Path) -> str:
    """Ensure all document links are internal."""
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
    """Run all the pretty things."""
    opts = parse_cmdline(sys.argv[1:])

    collate(opts)


def parse_cover(page: Path) -> str:
    """Process the cover page if there is one."""
    with page.open() as pg:
        content = bs(pg, features="lxml")
        # all links should point to #index00
        for a in content.findAll("a"):
            a["href"] = "#index00"
        for i in content.findAll("img"):
            i["src"] = f"file://{page.parent.resolve()}/{i['src']}"
        print(content)
        return str(content)


if __name__ == "__main__":
    main()
