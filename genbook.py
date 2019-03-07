#!/usr/bin/env python
# -*- coding: utf-8 -*-
# everything but the kitchen sink to ease portability when reqd.

import markdown
import ukedown.udn
# local chord generation tool (SVGs)
import chordgen

# jinja2 templating, originially based one the django model.
# from jinja2 import Environment, FileSystemLoader
import jinja2

# for generating summary info
from bs4 import BeautifulSoup as bs

# the normal boring stuff
import sys
import os
import datetime
import shutil
import codecs
import yaml
import re
from operator import itemgetter
import logging

from progress.bar import Bar

import argparse
from glob import glob

logging.basicConfig(format="%(asctime)s %(levelname)-8s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S", filename="bookmaker.log", level=logging.DEBUG)


def parse_commandline(argv):
    """
    Define commandline options and arguments
    """
    preamble = """
    Process a directory of ukedown-formatted song sheets to create an HTML-formatted book.
    This will process all files found in the given directory, converting them to HTML,
    inserting chord diagrams (can be hidden with CSS)
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="name of input directory", nargs="*")
    parser.add_argument("-s", "--style", choices=['weds', 'belfast', 'karauke', 'singers'], default='weds',
        help="output style, must correspond to a stylesheet in the css dir")
    parser.add_argument("-o", "--output", default="Karauke_{:%Y-%m-%d}".format(datetime.datetime.now()),
        help="Name of Book to build (default is Karauke_YYYY_MM_DD" )
    parser.add_argument("--report", action="store_true", default=False,
        help="Output a report on input directory and available chords. For info only")

    args = parser.parse_args(argv)

    if len(args.input) == 0:
        args.input = ['inputs']

    if not os.path.isdir(args.output):
        try:
            os.makedirs(args.output)
        except (IOError, OSError) as E:
            print ("Unable to create output directory {0.filename}: {0.strerror}".format(E))
            sys.exit(1)
    else:
        print("Output directory {0.output} already exists. Will replace files in it".format(args))

    return args

def safe_name(chord):
    # rules:
    # replace '#' with _sharp if at end,
    #                   _sharp_ if not
    # replace '/' with _on_
    return chord.translate({ ord('#'): '_sharp_', ord('/'): '_on_'})



def render(template, context, template_dir="templates"):
    """
    Creates a custom jinja2 environment and generates the provided template - allows for customisation

    Args:
        template(str): name of template file
        context(dict): dictionary of key,value pairs to use inside template

    Kwargs:
        template_dir(str): where to look for templates, default is the local 'templates' directory.

    """
    j2env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

    tpl = j2env.get_template(template)

    return tpl.render(context)

def ukedown_to_html(inputfile):

    fh = codecs.open(inputfile, mode="r", encoding="utf-8")
    txt = fh.read()

    return markdown.markdown(txt, extensions=['markdown.extensions.nl2br', 'ukedown.udn'])

def create_layout(destdir, *subdirs):
    """
    Basic wrapper around os.makedirs to create our cnntainer layout
    """
    if not os.path.isdir(destdir):
        try:
            os.makedirs(destdir)
        except (IOError, OSError) as E:
            print ("Unable to create dir {0.filename} ({0.strerror}".format(E))
            sys.exit(1)
    for sd in subdirs:
        d = os.path.join(destdir, sd)
        if os.path.isdir(d):
            continue
        print ("creating {}".format(d))
        try:
            os.makedirs(d)
        except (IOError, OSError) as E:
            print ("Unable to create dir {0.filename} ({0.strerror}".format(E))
            sys.exit(1)

def parse_songsheets(inputdirs):
    """
    Processes songsheets, returns a context (dict) containing
    song: { id: NNN, title: X, artist: X, chords: [X],
    """
    songs = {}
    # will merge dirs together, if a song appears twice, last match wins
    for idir in inputdirs:
        if not os.path.isdir(idir):
            continue
        songs.update({ os.path.basename(s): os.path.realpath(s) for s in glob(os.path.join(idir, '*.udn')) })

    context = {'chords': set([]), 'songs': []}
    pbar = Bar("Analysing Content: ".ljust(20), max=len(songs))
    # This will sort items across multiple directories
    for sng, path in sorted(songs.items(), key=itemgetter(0)):
        # index for nav documents/object ids
        prev_id = "{:03d}".format(pbar.index)
        song_id = "{:03d}".format(pbar.index + 1)
        next_id = "{:03d}".format(pbar.index + 2)


        # basename of outputfile
        song_dest = re.sub(r'\.udn$', '.html', sng)

        # convert song body to html
        content = ukedown_to_html(path)
        # process with bs4
        soup = bs(content, features="lxml")

        # strip out title/artist, if there is one
        hdr = soup.h1.extract()
        try:
            title, artist = [ i.strip() for i in hdr.text.split('-', 1) ]
        except ValueError:
            title = hdr.text.strip()

        hdr.decompose()

        # Now process chords
        # funky set comprehensions ftw
        songchords = { c.text.split().pop(0) for c in soup.findAll('span', {'class': 'chord'}) }
        # add our chords to the global chordlist
        context['chords'].update(songchords)

        context['songs'].append({ 'filename': song_dest,
                                  'id': song_id,
                                  'prev_id': prev_id,
                                  'next_id': next_id,
                                  'artist': artist.strip(),
                                  'title': title.strip(),
                                  'chords': [ safe_name(c) for c in songchords],
                                  'html': ''.join([str(x) for x in soup.body.contents ])
                                  })
        pbar.next()
        context['index'] = { s['id']: s['filename'] for s in context['songs'] }

    pbar.finish()
    return context


def build_songbook():
    # render templates for songs
    pass

def main(options):
    """
    main script entrypoint, expects an 'options' object from argparse.ArgumentParser
    """
    logging.info("Book Generation Started at {:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()))
    index = {'songbook': opts.output,
             'songlist': [],
             'chordlist': set([]),
             'stylesheets': [],
             'missing': set([])}
    # context  object looks like
    # { chords: set(),
    #   songs: [ { filename: str,
    #              id: 0-padded str(int)
    #              artist
    #              title
    #              chords: list/str
    #              html: body as html
    #            } ]
    #   stylesheets: list, added below
    #   songbook: output dir
    #   images: list of filenames
    #   sources: list of directories containing songsheets
    # }


    # context created by analysing input files and options:
    context = parse_songsheets(options.input)
    context['songbook'] = os.path.basename(options.output)
    context['stylesheets'] = []
    context['images'] = []

    with open('chords.yml') as cd:
        chord_defs = yaml.safe_load(cd)

    if options.report:
        print ("""
        Songook Summary for: {0.songbook}
        input directory: {0.input}
        Song Count: {1}
        Chords Used: {2}
        Missing Chord Definitions
        {3}""".format(options,
                      len(context['songs']),
                      ','.join(context['chordlist']),
                      ','.join(sorted(list(context['missing']))) ))

    # now generate the chord images from templates

    missing_chords = chordgen.generate(context['chords'], chord_defs, destdir="templates/svg", template="inline_svg.j2")

    # now we need to create our EPUB layout
    create_layout(options.output, 'EPUB', 'EPUB/css', 'EPUB/images', 'EPUB/songs', 'META-INF' )
    css_dir = os.path.join(options.output, 'EPUB','css')
    chord_dir = os.path.join(options.output, 'EPUB', 'chords')

    # copy styles and templates in
    shutil.copy2('templates/container.xml', os.path.join(options.output, 'META-INF'))

    for stylesheet in glob('css/*.css'):
        shutil.copy2(stylesheet, css_dir)
        index['stylesheets'].append(os.path.basename(stylesheet))

    for img in glob('images/*'):
        shutil.copy2(img, os.path.join(options.output, 'EPUB', 'images'))
        context['images'].append(img)

    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'), trim_blocks=True)


    # now let's generate our songsheets
    songtemplate = env.get_template('ukesong_inline.j2')
    failures = []
    # so, calc prev and next...
    # simples, generate a   quick index...
    for songobj in Bar("Rendering Songs:".ljust(20)).iter(context['songs']):
        logging.info("rendering {artist} - {title} into {filename}".format(**songobj))
        logging.debug("Chords: {chords!r}".format(**songobj))
        songobj['_prev'] = context['index'].get(songobj['prev_id'], "../index/html")
        songobj['_next'] = context['index'].get(songobj['next_id'], "../index/html")
        try:
            with open(os.path.join(options.output, 'EPUB', 'songs', songobj['filename']), 'w') as sf:
                sf.write(songtemplate.render(songobj, songidx=context['index']))
        except jinja2.TemplateError as T:
            logging.exception("Failed to render template for {title} - {artist}".format(**songobj))
            logging.error("Context: {chords!r}".format(**songobj))
            failures.append((songobj, T))
    for f, err in failures:
        print ("{title} - {artist} -> {filename}".format(**f), err.__class__, err)


    # other EPUB structures
    template_maps = {
        'EPUB/nav.xhtml': 'nav.xhtml.j2',
        'EPUB/index.html': 'bookindex.j2',
        'EPUB/package.opf': 'package.opf.j2'
        }

    for fpath, ftemplate in Bar("EPUB Templates: ".ljust(20)).iter(template_maps.items()):
        t = env.get_template(ftemplate)
        with open(os.path.join(options.output, fpath), 'w') as dest:
            dest.write(t.render(context))

if __name__ == "__main__":
    opts = parse_commandline(sys.argv[1:])
    main(opts)


