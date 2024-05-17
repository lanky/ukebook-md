#!/usr/bin/env python3
# vim: set ts=4 sts=4 sw=4 et ci ft=python foldmethod=indent:
# -*- coding: utf-8 -*-
"""Generate songbook in HTML format from provided ukedown inputs."""

import argparse
import logging
import os
import re
import shutil

# the normal boring stuff
import sys
from datetime import datetime
from glob import glob
from operator import itemgetter
from pathlib import Path, PosixPath
from typing import List, Tuple

# jinja2 templating, originally based on the django model.
import jinja2
import markdown  # type: ignore
import yaml

# for generating summary info
from bs4 import BeautifulSoup as bs
from progress.bar import Bar  # type: ignore

from ukebook_md import chordgen


# local chord generation tool (SVGs)
# from . import chordgen
def path_representer(dumper, data):
    """Create custom representer for pathlib.Path objects."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.representer.SafeRepresenter.add_representer(PosixPath, path_representer)
yaml.representer.SafeRepresenter.add_representer(Path, path_representer)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="bookmaker.log",
    level=logging.DEBUG,
)

SWEARING = {
    "fuck": "forget",
    "shit": "shoot",
    "nigga": "trigger",
}


def parse_commandline(argv: List[str] = sys.argv[1:]) -> argparse.Namespace:
    """Define commandline options and arguments."""
    preamble = """
    Process one or more directories (or files)  containing ukedown-formatted song sheets

    Creates an HTML diretory structure representing a songbook

    * Process all files found in the source directories
    * Parse any metadata
    * Create a directory structure and populate it
    * Render songsheets as HTML
    * Create an index page with links to the songsheets
    * insert chord diagrams / names if desired

    Several built-in formats are available:

    "Karauke": inline chord names, no diagrams
    "Singers": neither chord names  nor diagrams, just lyrics

    Default is to include all of these artifacts
    """

    parser = argparse.ArgumentParser(
        description=preamble, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", type=Path, help="name of input directory", nargs="+")
    parser.add_argument(
        "-s",
        "--style",
        default="ukebook",
        help="output style, must correspond to a stylesheet in the css dir",
    )
    parser.add_argument(
        "-c",
        "--cover",
        type=Path,
        help="cover image, including extension. Must be in 'images' directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default="Karauke_{:%Y-%m-%d}".format(datetime.now()),
        help="Name of Book to build (default is Karauke_YYYY_MM_DD",
    )
    parser.add_argument(
        "-t",
        "--title",
        default="Karauke Songbook",
        help="Title of output document (footers and Index page title)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        default=False,
        help="Output a report on input directory and available chords. For info only",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        default=False,
        help="Use external SVG images (reduces duplication)",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        default=False,
        help="render SVG diagrams to PNG for portability and PDF embedding (TODO)",
    )
    parser.add_argument(
        "--css-dir", default="css", type=Path, help="Path to CSS directory"
    )
    parser.add_argument(
        "--template-dir",
        default="templates",
        type=Path,
        help="path to templates directory",
    )

    cgrp = parser.add_argument_group(
        "Content control", "Options to control content creation. Special cases only."
    )
    cgrp.add_argument(
        "-F",
        "--family-friendly",
        action="store_true",
        default=False,
        help="Clean up the language for sensitive souls",
    )

    cgrp.add_argument(
        "--no-html",
        action="store_true",
        default=False,
        help="Do not regenerate HTML pages (test CSS updates for example)",
    )
    cgrp.add_argument(
        "--no-css",
        action="store_true",
        default=False,
        help="Do not replace CSS files in destination",
    )
    cgrp.add_argument(
        "--no-index",
        action="store_true",
        default=False,
        help="Do not generate an index page",
    )
    cgrp.add_argument(
        "--exclude",
        action="append",
        help="exclude the specified paths/files from generated output",
    )
    cgrp.add_argument(
        "--hide-diagrams",
        action="store_true",
        default=False,
        help="Do not display chord diagrams",
    )
    cgrp.add_argument(
        "--hide-chords",
        action="store_true",
        default=False,
        help="Do mot display inline chords",
    )
    cgrp.add_argument(
        "--hide-notes",
        action="store_true",
        default=False,
        help="Do mot display performance notes",
    )
    cgrp.add_argument(
        "--hide-credits",
        action="store_true",
        default=False,
        help="Do mot display artist/composer credits",
    )
    cgrp.add_argument(
        "--refresh",
        "--update",
        dest="refresh",
        action="store_true",
        default=True,
        help="only update files changed since the last build. If the output directory exists, this is the default behaviour",
    )
    cgrp.add_argument(
        "--clean",
        dest="refresh",
        action="store_true",
        default=False,
        help="remove all files from output dir before building (overrides --update)",
    )

    pgrp = parser.add_argument_group(
        "Pagination and Layout", "options controlling directory structures etc"
    )
    pgrp.add_argument(
        "-w",
        "--web",
        action="store_const",
        dest="layout",
        const="web",
        help="Generate output suitable for serving as a website. This is the default.",
    )
    pgrp.add_argument(
        "-e",
        "--epub",
        action="store_const",
        dest="layout",
        const="epub",
        help="Generate output suitable for publishing as an EPUB document",
    )
    pgrp.add_argument(
        "-p",
        "--onepage",
        action="store_const",
        dest="layout",
        const="onepage",
        help="Generate output suitable for publishing as a single page HTML document",
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
        help="""Hide diagrams, inline chords and performance notes. """
        """Lyrics and headings only""",
    )

    parser.add_argument(
        "--pdf",
        action="store_true",
        default=False,
        help="Generate a PDF document from the generated HTML",
    )

    parser.add_argument(
        "-l",
        "--landscape",
        action="store_const",
        dest="orientation",
        const="landscape",
        help="""This will be a landscape-format book. """
        """You still need to provide a suitable stylesheet""",
    )

    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        help="Produce debug output in songbook directory",
    )

    args = parser.parse_args(argv)

    if not args.output.is_dir():
        try:
            args.output.mkdir(exist_ok=True, parents=True)
        except (IOError, OSError) as E:
            print(
                "Unable to create output directory {0.filename}: {0.strerror}".format(E)
            )
            sys.exit(1)
    else:
        print(
            "Output directory {0.output} already exists. Will replace files in it".format(
                args
            )
        )

    if args.style:
        if not (args.css_dir / f"{args.style}.css").exists():
            print(
                "CSS stylesheet {0.style}.css doesn't exist, perhaps you need to specify --css-dir too?".format(
                    args
                )
            )
            parser.print_help()
            sys.exit(1)
    args.stylesheet = "{}/{}.css".format(args.css_dir, args.style)

    if not os.path.isdir(args.css_dir):
        print("CSS directory {0.css_dir} doesn't appear to exist".format(args))
        sys.exit(1)

    if not os.path.isdir(args.template_dir):
        print(
            "Templates directory {0.template_dir} doesn't appear to exist".format(args)
        )
        sys.exit(1)

    if not args.format:
        args.format = "web"

    if not args.exclude:
        args.exclude = []

    if not args.orientation:
        args.orientation = "portrait"
    return args


def safe_name(chord):
    """Make chordnames 'safe'.

    - removes shell special chars
    - Might need expanding for Windows/Mac

    Args:
        chord(str): a chordname to manipulate

    Returns:
        str: chordname with awkward characters replaced
    """
    # rules:
    # replace '#' with _sharp if at end,
    #                   _sharp_ if not
    # replace '/' with _on_
    return chord.translate({ord("#"): "_sharp_", ord("/"): "_on_"})


def render(template, context, template_dir="templates"):
    """Load and render the provided template.

    Args:
        template(str): name of template file
        context(dict): dictionary of key,value pairs to use inside template

    Kwargs:
        template_dir(str): where to look for templates, default is the local 'templates' directory.

    """
    j2env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

    tpl = j2env.get_template(template)

    return tpl.render(context)


def parse_meta(markup, leader=";"):
    """Parse out metadata from UDN file.

    This MUST be done before passing to markdown
    There doesn't have to be any metadata - should work regardless

    Args:
        markup(str): content of file, which we will manipulate in place
        leader(str): leader character - only process lines that begin with this
    """
    metap = re.compile(r"^{}\s?(.*)".format(leader), re.I | re.U)
    metadata = []
    content = []

    for line in markup.splitlines():
        res = metap.match(line)
        if res is not None:
            metadata.append(res.group(1))
        else:
            content.append(line)
    _markup = "\n".join(content)
    _metadata = yaml.safe_load("\n".join(metadata))

    return _metadata, _markup


def ukedown_to_html(inputfile: Path, family_friendly: bool = False) -> Tuple[str, dict]:
    """Process a file, produce HTML via ukedown."""
    fh = inputfile.open()
    raw_markup = fh.read()
    if family_friendly:
        for k, v in SWEARING.items():
            if raw_markup.find(k):
                raw_markup = raw_markup.replace(k, v)
            if raw_markup.find(k.title()) != -1:
                raw_markup = raw_markup.replace(k.title(), v.title())

    mtime = os.path.getmtime(inputfile)

    meta, markup = parse_meta(raw_markup, leader=";")
    if meta is None:
        meta = {}
    meta["last_modified"] = int(mtime)

    return (
        markdown.markdown(
            markup, extensions=["markdown.extensions.nl2br", "ukedown.udn"]
        ),
        meta,
    )


def create_layout(destdir, *subdirs):
    """Create required directories for output."""
    if not os.path.isdir(destdir):
        try:
            os.makedirs(destdir)
        except (IOError, OSError) as E:
            print("Unable to create dir {0.filename} ({0.strerror}".format(E))
            sys.exit(1)
    for sd in subdirs:
        d = os.path.join(destdir, sd)
        if os.path.isdir(d):
            continue
        print("creating {}".format(d))
        try:
            os.makedirs(d)
        except (IOError, OSError) as E:
            print("Unable to create dir {0.filename} ({0.strerror}".format(E))
            sys.exit(1)


def parse_song(songfile: Path, songid: int = 1, **kwargs) -> dict:
    """Process an individual songsheet to extract content and metadata.

    Args:
        songfile(str): path to songsheet file.
        songid(int): unique identifier

    Returns:
        songdata(dict): dictionary representation of a song for use
                        in templating/reporting
    """
    songdata: dict = {
        "filename": songfile.with_suffix(".html"),
        "chords": [],
        "id": f"{songid:03d}",
        "next_id": f"{songid + 1:03d}",
        "prev_id": f"{songid - 1:03d}",
        "meta": {},
    }
    # convert ukedown to HTML - this generates a complete document, we only
    # need the HTML <body> element, will extract that later
    content, meta = ukedown_to_html(
        songfile, family_friendly=kwargs.get("family_friendly", False)
    )
    if meta is not None:
        songdata["meta"].update(meta)

    # process our HTML with BeautifulSoup4
    soup: bs = bs(content, features="lxml")

    # title and artist are in <h1> tags.
    hdr = soup.h1
    if hdr is not None:
        try:
            title, artist = [i.strip() for i in hdr.text.split("-", 1)]
        except ValueError:
            title = hdr.text.strip()
            artist = None
        # remove the header from our document
        hdr.decompose()
    else:
        title = "Unknown Title"
        artist = "Unknown Artist"
    # currently all the templates use 'html', so stick to that naming
    if soup.body is not None:
        songdata["html"] = "".join([str(x) for x in soup.body.contents]).strip()
        # every valid ukedown songsheet has a title, and possibly an artist
        songdata["title"] = title.strip()
        if artist is not None:
            songdata["artist"] = artist.strip()
    else:
        songdata["html"] = ""

    # now get list of chords used in the song
    songdata["chords"] = []
    for c in soup.findAll("span", {"class": "chord"}):
        cname = c.text.split().pop(0).rstrip("*")
        # don't add repeated chords
        if cname not in songdata["chords"]:
            songdata["chords"].append(cname)
    return songdata


def parse_songsheets(inputs: list, exclusions: list = [], **kwargs) -> dict:
    """Process songsheets.

    Args:
        inputdirs(list): list of directories containing input files in
                         ukedown format
        exclusions(list):
    Returns:
        context(dict): artist, title, chords etc parsed from songsheet
    """
    songs = {}
    # will merge dirs together, if a song appears twice, last match wins
    for src in inputs:
        if src.is_dir():
            songs.update({p.name: p for p in src.glob("*.udn")})
        else:
            # for single songsheets, just the file info
            songs.update({src.name: src})

    context: dict = {"chords": set([]), "songs": []}
    # we would like to maintain chord ordering - chords are listed in the order they appear in the song.
    pbar = Bar("Analysing Content: ".ljust(20), max=len(songs))
    # This will sort items across multiple directories
    for sng, path in sorted(songs.items(), key=itemgetter(0)):
        # skip songs/paths we have specifically excluded
        if len(exclusions) and (sng in exclusions or path in exclusions):
            continue

        # parse the songsheet to get metadata and HTML (sd=songdata)
        sd = parse_song(
            path, pbar.index, family_friendly=kwargs.get("family_friendly", False)
        )

        # add any chords from this song to our global chordlist
        context["chords"].update(sd["chords"])

        context["songs"].append(sd)
        pbar.next()
        context["index"] = {
            s["id"]: Path("../songs") / s["filename"].name for s in context["songs"]
        }
        # index is a mapping of title or title (artist) to song id
    pbar.finish()
    return context


def make_context(ctx: dict, options: argparse.Namespace) -> dict:
    """Generate a template context dict.

    Args:
        ctx(dict): simple context parsed from songsheet
        options(argparse.Namespace): commandline options
    Returns:
        context(dict): updated context ready to pass to a template

    """
    ctx["songbook"] = options.output.name
    ctx["book_type"] = options.format
    ctx["stylesheets"] = []
    ctx["images"] = []
    ctx["scripts"] = []
    ctx["format"] = options.format
    ctx["book_css"] = options.style
    # standard elements on a page if no options selected
    ctx["show_chords"] = True
    ctx["show_diagrams"] = True
    ctx["show_notes"] = True
    ctx["show_credits"] = True
    ctx["ext_chords"] = options.external
    ctx["orientation"] = options.orientation
    if options.hide_diagrams:
        # this is effectively 'karauke band style'
        ctx["show_diagrams"] = False
    elif options.format == "singers":
        ctx["show_diagrams"] = False
        ctx["show_chords"] = False
        ctx["show_notes"] = False
        ctx["show_credits"] = False
    elif options.format == "karauke":
        ctx["show_diagrams"] = False
        ctx["show_credits"] = False
    else:
        ctx["show_credits"] = True
        ctx["show_diagrams"] = True
        ctx["show_chords"] = True
        ctx["show_notes"] = True

    return ctx


def main():  # noqa: C901
    """Run all the pretty things."""
    options = parse_commandline(sys.argv[1:])
    timestamp = datetime.now()
    logging.info("Book Generation Started at {:%Y-%m-%d %H:%M:%S}".format(timestamp))

    if len(options.input) == 1 and options.input[0].is_file():
        options.no_index = True

    # context created by analysing input files and options:
    context = make_context(
        parse_songsheets(
            options.input, options.exclude, family_friendly=options.family_friendly
        ),
        options,
    )

    with open("chords.yml") as cd:
        chord_defs = yaml.safe_load(cd)

    if options.report:
        print(
            """
        Songook Summary for: {0.songbook}
        input directory: {0.input}
        Song Count: {1}
        Chords Used: {2}
        Missing Chord Definitions
        {3}""".format(
                options,
                len(context["songs"]),
                ",".join(context["chordlist"]),
                ",".join(sorted(list(context["missing"]))),
            )
        )

    # now generate the chord images from templates

    # now we need to create our output layout
    # handle any additional layout definitions here
    if options.layout == "epub":
        options.output = options.output / "EPUB"

    coredirs = ["css", "images", "songs"]

    if options.debug:
        coredirs.append("debug")

    if options.external:
        coredirs.append("chords")
        chord_template = "chord_ext.svg.j2"
        chord_dir = options.output / "chords"
        song_template = Path("song.html.j2")
    else:
        chord_template = Path("chord.svg.j2")
        chord_dir = Path("templates/svg")
        song_template = Path("song.html.j2")

    if options.format == "onepage":
        song_template = Path("onepage.html.j2")

    layout = [options.output / c for c in coredirs]

    # create target directories
    create_layout(options.output, *layout)
    tsfile = options.output / ".timestamp"
    tsfile.write_text(timestamp.strftime("%s"))

    # generate all chord diagrams from the songbook context
    missing_chords = chordgen.generate(
        context["chords"], chord_defs, destdir=chord_dir, template=chord_template
    )

    if len(missing_chords):
        print("Cannot find definitions for chords", "\n".join(missing_chords))

    # copy styles and templates in
    if options.format == "epub":
        shutil.copy2("templates/container.xml", options.output / "META-INF")

    def globcp(pattern, dest, key=None):
        for item in glob(pattern):
            if not os.path.isdir(dest):
                os.makedirs(dest)
            shutil.copy2(item, dest)
            if key is not None:
                context[key].append(os.path.basename(item))

    # this section should be refactored to avoid repetition.
    if not options.no_css:
        globcp(
            "{0.css_dir}/*.css".format(options),
            options.output / "css",
            "stylesheets",
        )

    # copy any images we may be using as footers etc
    globcp("images/*", options.output / "images", "images")

    # javascript
    globcp("js/*.js", options.output / "js", "scripts")

    # setup our template environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        lstrip_blocks=True,
        trim_blocks=True,
    )
    env.filters["safe_name"] = safe_name

    # now let's generate our songsheets
    st = env.get_template(song_template.name)
    css_template = env.get_template("song.css.j2")

    failures = []
    if not options.no_html:
        if options.format == "onepage":
            # generate index then all the other things afterwards?
            logging.info("rendering songbook into single-page HTML")
            if not options.no_index:
                (options.output / "index.html").write_text(
                    st.render(context, link_type="internal")
                )

        for songobj in Bar("Rendering Songs:".ljust(20)).iter(context["songs"]):
            logging.info("rendering {title} into {filename}".format(**songobj))
            logging.debug("Chords: {chords!r}".format(**songobj))
            songobj["_prev"] = context["index"].get(songobj["prev_id"], "../index.html")
            songobj["_next"] = context["index"].get(songobj["next_id"], "../index.html")
            songobj["book_css"] = options.style
            songobj["context"] = context
            if (
                "font_size" in songobj["meta"]
                or "landscape_font_size" in songobj["meta"]
            ):
                song_style = (
                    options.output
                    / "css"
                    / songobj["filename"].with_suffix(".css").name
                )
                try:
                    song_style.write_text(
                        css_template.render(
                            orientation=context["orientation"], meta=songobj["meta"]
                        )
                    )
                except jinja2.TemplateError:
                    print(
                        yaml.safe_dump(
                            {
                                "orientation": context["orientation"],
                                "meta": songobj["meta"],
                            }
                        )
                    )
                    raise

            if options.debug:
                dumpfile = (
                    options.output
                    / "debug"
                    / songobj["filename"].with_suffix(".yml").name
                )
                dumpfile.write_text(yaml.safe_dump(songobj))
            try:
                sf = options.output / "songs" / songobj["filename"].name
                content = bs(
                    st.render(
                        song=songobj,
                        **context,
                    ),
                    features="lxml",
                )
                sf.write_text(str(content))
            except jinja2.TemplateError as T:
                logging.exception(
                    "Failed to render template for {title} - {artist}".format(**songobj)
                )
                logging.error("Context: {chords!r}".format(**songobj))
                failures.append((songobj, T))
        for f, err in failures:
            print("{title} - {artist} -> {filename}".format(**f), err.__class__, err)

    # other EPUB structures
    template_maps = {}
    if options.format == "epub":
        template_maps["nav.xhtml"] = "nav.xhtml.j2"
        template_maps["package.opf"] = "package.opf.j2"

    if options.cover:
        template_maps["cover.html"] = "cover.html.j2"
        context["cover"] = options.cover

    if options.format != "onepage" and not options.no_index:
        template_maps["index.html"] = "index.html.j2"

    if len(template_maps):
        for fpath, ftemplate in Bar("Other Templates: ".ljust(20)).iter(
            template_maps.items()
        ):
            t = env.get_template(ftemplate)
            (options.output / fpath).write_text(t.render(context))


if __name__ == "__main__":
    main()
