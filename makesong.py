#!/usr/bin/env python3
# vim: set ts=4 sts=4 sw=4 et ci ft=python foldmethod=indent:
# -*- coding: utf-8 -*-
# everything but the kitchen sink to ease portability when reqd.
import os
import sys
import argparse
import codecs
import tempfile
import shutil
import yaml
import datetime
import logging


import markdown
import ukedown.udn

import jinja2
from bs4 import BeautifulSoup as bs
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from genbook import parse_song, parse_meta, make_context, ukedown_to_html, safe_name

"""
Separates out the rendering and PDF conversion for an individual
songsheet - allows test rendering and metadata testing without
buggering about with whole songbooks and/or indices
"""


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
f = logging.Formatter(
    "%(asctime)s - %(levelname)-8s - %(message)s", datefmt="%y-%m-%s %H:%M:%S"
)
h = logging.StreamHandler(stream=sys.stdout)
h.setFormatter(f)
logger.addHandler(h)


def parse_commandline(argv: list) -> argparse.Namespace:
    """process commandline options and arguments

    parses provided options and sanity-checks them

    Args:
        argv (list[str]): list of options and arguments, e.g. sys.argv[1:]
    """
    parser = argparse.ArgumentParser(
        "render a songsheet to PDF from a ukedown source file"
    )
    parser.add_argument("inputfile", nargs="+", help="one or more songsheets to render")
    parser.add_argument(
        "-s",
        "--style",
        default="pdfprint",
        help="Stylesheet, without extension, or path to a custom file",
    )

    parser.add_argument(
        "-c", "--css-dir", default="css", help="Default directory for stylesheets",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=os.path.realpath(os.curdir),
        help="output directory for rendered PDFs, defaults to current dir",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="print debug info from parsing",
    )

    fgrp = parser.add_argument_group(
        "Output Formats", "Predefined output formats for simplicity"
    )
    fgrp.add_argument(
        "-k",
        "--karauke",
        action="store_const",
        dest="format",
        const="karauke",
        help="Generate a karauke-style book (no chord diagrams)",
    )
    fgrp.add_argument(
        "-S",
        "--singers",
        action="store_const",
        dest="format",
        const="singers",
        help="Hide diagrams, inline chords and performance notes. Lyrics and headings only",
    )
    fgrp.add_argument(
        "-w",
        "--weds",
        action="store_const",
        dest="format",
        const="ukeweds",
        help="Show diagrams, inline chords and performance notes",
    )

    opts = parser.parse_args(argv)

    if opts.debug:
        logger.setLevel(logging.DEBUG)

    validfiles = []
    for f in opts.inputfile:
        if not os.path.exists(f):
            logger.warning("Ignoring non-existent input file {}".format(f))
        else:
            validfiles.append(f)

    opts.inputfile = validfiles

    # check for existence of CSS
    # if --style = WORD, look for opts.css_dir/WORD.css
    # else, look directly for WORD

    if os.path.exists(opts.style):
        opts.stylesheet = opts.style
    elif os.path.exists(os.path.join(opts.css_dir, opts.style)):
        opts.stylesheet = os.path.join(opts.css_dir, opts.style)
    elif os.path.exists(os.path.join(opts.css_dir, "{0.style}.css".format(opts))):
        opts.stylesheet = os.path.join(opts.css_dir, "{0.style}.css".format(opts))
    elif os.path.exists(opts.style):
        opts.stylesheet = opts.style
    else:
        logger.critical(
            "cannot find stylesheet corresponding to {0.style}".format(opts)
        )
        sys.exit(1)

    return opts


def main(opts: argparse.Namespace):
    """
    [TODO:description]

    :param opts [TODO:type]: [TODO:description]
    """
    # generate context for songsheet
    # simplistic as this is for karauke only
    ctx = {
        "book_css": os.path.basename(opts.stylesheet),
        "css_path": os.path.dirname(opts.stylesheet),
        "show_diagrams": opts.format == "ukeweds",
        "show_chords": opts.format != "singers",
        "ext_chords": True,
        "show_notes": opts.format != "singers",
        "songbook": "none",
    }

    for song in opts.inputfile:
        ctx["song"] = parse_song(song)
        # create tempdir for HTML
        # render HTML to PDF using the appropriate stylesheet
        # remove tempdir
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("templates"),
            lstrip_blocks=True,
            trim_blocks=True,
        )
        env.filters["safe_name"] = safe_name

        st = env.get_template("song.html.j2")
        # need to fix the title/artist parsing for some songs (Those with '-' in the title)
        if opts.debug:
            print(yaml.safe_dump(ctx, default_flow_style=False))
        # render HTML in a tempdir, which we clean up afterwards
        # with tempfile.TemporaryDirectory() as td:
        td = tempfile.TemporaryDirectory()
        # os.makedirs('tmp/test-output-{:Y-%m-%d.%H%M}'.format(datetime.datetime.now()))
        logger.debug("creating temp structure in {0.name}".format(td))
        css_path = os.path.join(td.name, "css")
        os.makedirs(css_path)
        os.makedirs(os.path.join(td.name, "chords"))
        shutil.copy(opts.stylesheet, css_path)

        fontcfg = FontConfiguration()
        logger.debug("using {} as stylesheet".format(os.path.realpath(opts.stylesheet)))
        css = [CSS(os.path.realpath(opts.stylesheet))]

        try:
            with open(os.path.join(td.name, ctx["song"]["filename"]), "w") as sf:
                content = bs(st.render(ctx), features="lxml")
                sf.write(str(content))

            # This is a standalone file, remove links to index and prev/next
            # for link in content.find_all('a'):
            #   link.decompose()
            content.find("a", {"class": "left"}).decompose()
            content.find("a", {"class": "right"}).decompose()

            doc = HTML(string=str(content)).render(stylesheets=css, font_config=fontcfg)

            pdffile = os.path.join(
                opts.output,
                os.path.basename(ctx["song"]["filename"]).replace(".html", ".pdf"),
            )
            if not os.path.isdir(opts.output):
                os.makedirs(opts.output)

            if os.path.exists(pdffile):
                logger.info("backing up existing file {}".format(pdffile))
                os.rename(
                    pdffile,
                    "{}-{:%Y%m%d.%H%M}.pdf".format(
                        os.path.splitext(pdffile)[0], datetime.datetime.now()
                    ),
                )

            print("writing PDF to {}".format(pdffile))

            doc.write_pdf(pdffile)
        except jinja2.TemplateError as T:
            logger.exception(
                "Failed to render template for {title} - {artist}".format(**ctx["song"])
            )
            raise
        if opts.debug:
            shutil.copy(os.path.join(td.name, ctx["song"]["filename"]), ".")

        # parse the songsheet from UDN input to get a context


if __name__ == "__main__":
    options = parse_commandline(sys.argv[1:])
    main(options)
