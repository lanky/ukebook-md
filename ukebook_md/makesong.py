#!/usr/bin/env python3
# vim: set ts=4 sts=4 sw=4 et ci ft=python foldmethod=indent:
# -*- coding: utf-8 -*-
"""Render an individual songsheet to PDF."""

import argparse
import datetime
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

import jinja2
import yaml
from bs4 import BeautifulSoup as bs
from weasyprint import CSS, HTML  # type: ignore[import-untyped]
from weasyprint.text.fonts import FontConfiguration  # type: ignore[import-untyped]

from ukebook_md.genbook import parse_song, safe_name

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
    """Process commandline options and arguments.

    parses provided options and sanity-checks them

    Args:
        argv (list[str]): list of options and arguments, e.g. sys.argv[1:]
    """
    parser = argparse.ArgumentParser(
        "render a songsheet to PDF from a ukedown source file"
    )
    parser.add_argument(
        "inputfile", nargs="+", type=Path, help="one or more songsheets to render"
    )
    parser.add_argument(
        "-s",
        "--style",
        default="portrait",
        help="Stylesheet, without extension, or path to a custom file",
    )

    parser.add_argument(
        "-c",
        "--css-dir",
        type=Path,
        default=Path("css"),
        help="Default directory for stylesheets",
    )

    parser.add_argument(
        "-i",
        "--image-dir",
        type=Path,
        help="location of images to include in document",
        default=Path(__file__).parent,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.cwd(),
        help="output directory for rendered PDFs, defaults to current dir",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="print debug info from parsing",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="forcibly overwrite output file if it exists.",
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
        help="Hide diagrams, inline chords and performance notes."
        "Lyrics and headings only",
    )
    fgrp.add_argument(
        "-w",
        "--weds",
        action="store_const",
        dest="format",
        const="ukeweds",
        help="Show diagrams, inline chords and performance notes",
    )
    parser.add_argument(
        "-F",
        "--family-friendly",
        action="store_true",
        default=False,
        help="Clean up nasty swearing",
    )

    opts = parser.parse_args(argv)

    if opts.debug:
        logger.setLevel(logging.DEBUG)

    validfiles = []
    for f in opts.inputfile:
        if not os.path.exists(f):
            logger.warning(f"Ignoring non-existent input file {f}")
        else:
            validfiles.append(f)

    opts.inputfile = validfiles

    # check for existence of CSS
    # if --style = WORD, look for opts.css_dir/WORD.css
    # else, look directly for WORD

    spath = Path(opts.style).with_suffix(".css")
    opts.stylesheet = None
    for ss in [spath, opts.css_dir / spath]:
        if ss.exists():
            opts.stylesheet = ss
            break
    if not opts.stylesheet:
        logger.critical(f"cannot find stylesheet corresponding to {opts.style}")
        sys.exit(1)

    return opts


def main():
    """Run all the pretty things."""
    # generate context for songsheet
    # simplistic as this is for karauke only
    opts = parse_commandline(sys.argv[1:])
    ctx = {
        "book_css": opts.stylesheet.name,
        "css_path": opts.stylesheet.parent,
        "show_diagrams": opts.format == "ukeweds",
        "show_chords": opts.format != "singers",
        "ext_chords": True,
        "show_notes": opts.format != "singers",
        "songbook": "none",
    }

    for song in opts.inputfile:
        ctx["song"] = parse_song(song, family_friendly=opts.family_friendly)
        ctx["image_dir"] = opts.image_dir
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
        # need to fix the title/artist parsing for some songs
        # (Those with '-' in the title)
        if opts.debug:
            print(yaml.safe_dump(ctx, default_flow_style=False))
        # render HTML in a tempdir, which we clean up afterwards
        # with tempfile.TemporaryDirectory() as td:
        td = tempfile.TemporaryDirectory()
        tmppath = Path(td.name)
        # os.makedirs('tmp/test-output-{:Y-%m-%d.%H%M}'.format(datetime.datetime.now()))
        logger.debug(f"creating temp structure in {td.name}")
        css_path = tmppath / "css"
        css_path.mkdir(parents=True, exist_ok=True)
        (tmppath / "chords").mkdir(parents=True, exist_ok=True)

        shutil.copy(opts.stylesheet, css_path)

        fontcfg = FontConfiguration()
        logger.debug(f"using {opts.stylesheet} as stylesheet")
        css = [CSS(opts.stylesheet.resolve())]

        htmlfile = tmppath / ctx["song"]["filename"]

        try:
            content = bs(st.render(ctx), features="lxml")
            # save an HTML version. Is this really needed?
            htmlfile.write_text(str(content))

            # This is a standalone file, remove links to index and prev/next
            # for link in content.find_all('a'):
            #   link.decompose()
            content.find("a", {"class": "left"}).decompose()
            content.find("a", {"class": "right"}).decompose()

            # create a PDF doc from the HTML
            doc = HTML(string=str(content)).render(stylesheets=css, font_config=fontcfg)

            opts.output.mkdir(parents=True, exist_ok=True)

            print(
                f"filename: {ctx['song']['filename']}, {type(ctx['song']['filename'])}"
            )
            print(f"destdir: {opts.output}")

            pdffile = opts.output / ctx["song"]["filename"].with_suffix(".pdf").name

            if pdffile.exists() and not opts.force:
                logger.info(f"backing up existing file {pdffile}")
                ts = datetime.datetime.now()
                backup = Path(
                    pdffile.parent / f"{pdffile.stem}-{ts:%Y%m%d.%H%M}{pdffile.suffix}"
                )

                pdffile.rename(backup)

            print(f"writing PDF to {pdffile}")

            doc.write_pdf(pdffile)
        except jinja2.TemplateError:
            logger.exception(
                f"Failed to render template for {ctx['song']['title']} - "
                f"{ctx['song']['artist']}"
            )
            raise
        if opts.debug:
            shutil.copy(os.path.join(td.name, ctx["song"]["filename"]), ".")

        # parse the songsheet from UDN input to get a context


if __name__ == "__main__":
    main()
