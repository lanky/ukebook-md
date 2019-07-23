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

logging.basicConfig(format="%(asctime)s %(levelname)-8s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    filename="bookmaker.log",
                    level=logging.DEBUG)


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
    parser.add_argument("-s", "--style", default='ukebook',
        help="output style, must correspond to a stylesheet in the css dir")
    parser.add_argument("-o", "--output", default="Karauke_{:%Y-%m-%d}".format(datetime.datetime.now()),
        help="Name of Book to build (default is Karauke_YYYY_MM_DD" )
    parser.add_argument("--report", action="store_true", default=False,
        help="Output a report on input directory and available chords. For info only")
    parser.add_argument("--external", action="store_true", default=False,
        help="Use external SVG images (reduces duplication)")
    parser.add_argument("--css-dir", default="css", help="Path to CSS directory")
    parser.add_argument("--template-dir", default="templates", help="path to templates directory")

    cgrp = parser.add_argument_group("content control", "options to control content creation")
    cgrp.add_argument("--no-html", action="store_true", default=False,
        help="Do not rerender HTML pages")
    cgrp.add_argument("--no-css", action="store_true", default=False,
        help="Do not replace CSS files in destination")
    cgrp.add_argument("--exclude", action="append",
        help="exclude the specified paths/files from generated output")
    cgrp.add_argument("--web", "-w", action="store_const", dest="format", const="web",
        help="Generate output suitable for serving as a website")
    cgrp.add_argument("--epub", "-e", action="store_const", dest="format", const="epub",
        help="Generate output suitable for publishing as an EPUB document (default)")
    cgrp.add_argument("--onepage", "-p", action="store_const", dest="format", const="onepage",
        help="Generate output suitable for publishing as a single page HTML document")

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

    if args.style:
        if not os.path.exists('{}/{}.css'.format(args.css_dir, args.style)):
            print ("CSS stylesheet {0.style}.css doesn't exist, perhaps you need to specify --css-dir too?".format(args))
            parser.print_help()
            sys.exit(1)
    args.stylesheet = '{}/{}.css'.format(args.css_dir, args.style)

    if not os.path.isdir(args.css_dir):
        print("CSS directory {0.css_dir} doesn't appear to exist".format(args))
        sys.exit(1)

    if not os.path.isdir(args.template_dir):
        print ("Templates directory {0.template_dir} doesn't appear to exist".format(args))
        sys.exit(1)

    if not args.format:
        args.format = "epub"

    if not args.exclude:
        args.exclude = []
    return args

def safe_name(chord):
    """
    Makes chordnames 'safe' (no shell special chars. Might need expanding for Windows/Mac)

    Args:
        chord(str): a chordname to manipulate

    Returns:
        str: chordname with awkward characters replaced
    """
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

def parse_song(songfile: str, songid: int = 1):
    """
    process an individual songsheet to extract content and metadata

    Args:
        songfile(str): path to songsheet file.
        songid(int): unique identifier

    Returns:
        songdata(dict): dictionary representation of a song for use
                        in templating/reporting
    """
    songdata = {
        'filename': re.sub(r'\.udn$', '.html', os.path.basename(songfile)),
        'chords': [],
        'id': '{:03d}'.format(songid),
        'next_id': '{:03d}'.format(songid + 1),
        'prev_id': '{:03d}'.format(songid - 1),
        }
    # convert ukedown to HTML - this generates a complete document, we only
    # need the HTML <body> element, will extract that later
    content = ukedown_to_html(songfile)

    # process our HTML with BeautifulSoup4
    soup = bs(content, features='lxml')

    # title and artist are in <h1> tags.
    hdr = soup.h1.extract()
    try:
        title, artist = [ i.strip() for i in hdr.text.split('-', 1) ]
    except ValueError:
        title = hdr.text.strip()
        artist = None
    # remove the header from our document
    hdr.decompose()
    # currently all the templates use 'html', so stick to that naming
    songdata['html'] = ''.join([str(x) for x in soup.body.contents ])
    # every valid ukedown songsheet has a title, and possibly an artist
    songdata['title'] = title.strip()
    if artist is not None:
        songdata['artist'] = artist.strip()

    # now get list of chords used in the song
    songdata['chords'] = []
    for c in soup.findAll('span', {'class': 'chord'}):
        cname = c.text.split().pop(0).rstrip('*')
        # don't add repeated chords
        if cname not in songdata['chords']:
            songdata['chords'].append(cname)
    return songdata

def parse_songsheets(inputdirs, exclusions=[]):
    """
    Processes songsheets, returns a context (dict) containing
    song: { id: NNN, title: X, artist: X, chords: [X],

    Args:
        inputdirs(list): list of directories containing input files in
                         ukedown format
        exclusions
    """
    songs = {}
    # will merge dirs together, if a song appears twice, last match wins
    for idir in inputdirs:
        if not os.path.isdir(idir):
            continue
        songs.update({ os.path.basename(s): os.path.realpath(s) for s in glob(os.path.join(idir, '*.udn')) })

    context = {'chords': set([]), 'songs': []}
    # we would like to maintain chord ordering - chords are listed in the order they appear in the song.
    pbar = Bar("Analysing Content: ".ljust(20), max=len(songs))
    # This will sort items across multiple directories
    for sng, path in sorted(songs.items(), key=itemgetter(0)):
        # skip songs/paths we have specifically excluded
        if len(exclusions) and ( sng in exclusions or path in exclusions):
            continue

        # parse the songsheet to get metadata and HTML
        sd = parse_song(path, pbar.index)

        # add any chords from this song to our global chordlist
        context['chords'].update(sd['chords'])

        context['songs'].append(sd)
        pbar.next()
        context['index'] = { s['id']: s['filename'] for s in context['songs'] }
        # index is a mapping of title or title (artist) to song id
    pbar.finish()
    return context


def main(options):
    """
    main script entrypoint, expects an 'options' object from argparse.ArgumentParser
    """
    # handle output options

    logging.info("Book Generation Started at {:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()))
    index = {'songbook': opts.output,
             'songlist': [],
             'chordlist': set([]),
             'stylesheets': [],
             'missing': set([])}

    # context created by analysing input files and options:
    context = parse_songsheets(options.input, options.exclude)
    context['songbook'] = os.path.basename(options.output)
    context['stylesheets'] = []
    context['images'] = []
    context['scripts'] = []
    context['format'] = options.format
    context['book_css'] = options.style

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

    # now we need to create our output layout
    # could do this in option parsing code?
    if options.format == 'epub':
        parent = "EPUB/"
    if options.format == 'web':
        parent = ""
    if options.format == 'onepage':
        parent = ""

    coredirs = ['css', 'images', 'songs' ]

    if options.external:
        coredirs.append('chords')
        chord_template = "chord_ext.svg.j2"
        chord_dir = os.path.join(options.output, parent, 'chords')
        song_template = "song_ext.html.j2"
    else:
        chord_template = "chord.svg.j2"
        chord_dir = "templates/svg"
        song_template = "song.html.j2"

    if options.format == 'onepage':
        song_template = 'onepage.html.j2'

    layout = [ os.path.join(parent, c) for c in coredirs ]
    if len(parent):
        layout.insert(0, parent)

    # create target directories
    create_layout(options.output, *layout)

    # generate all chord diagrams from the songbook context
    missing_chords = chordgen.generate(context['chords'], chord_defs, destdir=chord_dir, template=chord_template)

    # copy styles and templates in
    if options.format == 'epub':
        shutil.copy2('templates/container.xml', os.path.join(options.output, 'META-INF'))

    def globcp(pattern, dest, key=None):
        for item in glob(pattern):
            if not os.path.isdir(dest):
                os.makedirs(dest)
            shutil.copy2(item, dest)
            if key is not None:
                context[key].append(os.path.basename(item))

    # this section should be refactored to avoid repetition.
    if not options.no_css:
        globcp('{0.css_dir}/*.css'.format(opts), os.path.join(options.output, parent, 'css'), 'stylesheets')

    # copy any images we may be using as footers etc
    globcp('images/*', os.path.join(options.output, parent, 'images'), 'images')

    # javascript
    globcp('js/*.js', os.path.join(options.output, parent, 'js'), 'scripts')

    # setup our template environment
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'), trim_blocks=True)
    env.filters['safe_name'] = safe_name

    # now let's generate our songsheets
    st = env.get_template(song_template)

    failures = []
    if not options.no_html:
        if options.format == 'onepage':
            # generate index then all the other things afterwards?
            logging.info("rendering sonbook into single-page HTML")
            with open(os.path.join(options.output, parent, 'index.html'), 'w') as bi:
                bi.write(st.render(context, link_type='internal'))

        for songobj in Bar("Rendering Songs:".ljust(20)).iter(context['songs']):
            logging.info("rendering {title} into {filename}".format(**songobj))
            logging.debug("Chords: {chords!r}".format(**songobj))
            songobj['_prev'] = context['index'].get(songobj['prev_id'], "../index.html")
            songobj['_next'] = context['index'].get(songobj['next_id'], "../index.html")
            songobj['book_css'] = options.style
            try:
                with open(os.path.join(options.output, parent, 'songs', songobj['filename']), 'w') as sf:
                    sf.write(st.render(songobj, songidx=context['index'], book_css=context['book_css']))
            except jinja2.TemplateError as T:
                logging.exception("Failed to render template for {title} - {artist}".format(**songobj))
                logging.error("Context: {chords!r}".format(**songobj))
                failures.append((songobj, T))
        for f, err in failures:
            print ("{title} - {artist} -> {filename}".format(**f), err.__class__, err)


    # other EPUB structures
    template_maps = {}
    if options.format == 'epub':
        template_maps[os.path.join(parent,'nav.xhtml')] = 'nav.xhtml.j2'
        template_mps[os.path.join(parent, 'package.opf')] =  'package.opf.j2'

    if options.format != 'onepage':
        template_maps[os.path.join(parent, 'index.html')] = 'bookindex.j2'

    if len(template_maps):
        for fpath, ftemplate in Bar("Other Templates: ".ljust(20)).iter(template_maps.items()):
            t = env.get_template(ftemplate)
            with open(os.path.join(options.output, fpath), 'w') as dest:
                dest.write(t.render(context))

if __name__ == "__main__":
    opts = parse_commandline(sys.argv[1:])
    main(opts)


