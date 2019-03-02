#!/usr/bin/env python
# -*- coding: utf-8 -*-
# everything but the kitchen sink to ease portability when reqd.

import markdown
import ukedown.udn
# local chord generation tool (SVGs)
import chordgen

# jinja2 templating, originially based one the django model.
from jinja2 import Environment, FileSystemLoader

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

from progress.bar import Bar

import argparse
from glob import glob


def parse_commandline(argv):
    """
    Define commandline options and arguments
    """
    preamble = """
    Process a directory of ukedown-formatted song sheets to create an HTML-formatted book.
    This will process all files found in the given directory, converting them to HTML, inserting chord diagrams (can be hidden with CSS)
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="name of input directory")
    parser.add_argument("-s", "--style", help="output style, must correspond to a stylesheet in the css dir", choices=['weds', 'belfast', 'karauke', 'singers'], default='weds')
    parser.add_argument("-o", "--output", default="Karauke_{:%Y-%m-%d}".format(datetime.datetime.now()),
        help="Name of Book to build (default is Karauke_YYYY_MM_DD" )
    parser.add_argument("--stylesheet", help="provide a custom stylesheet to test rendering. Expects to be given a path.")
    parser.add_argument("--template", help="provide a custom template to test rendering. Expects to be given a path")
    parser.add_argument("--report", action="store_true", default=False,
        help="Output a report on input directory and available chords. For info only")

    args = parser.parse_args(argv)

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
    j2env = Environment(loader=FileSystemLoader(template_dir))

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

def analyse_inputs(inputdir):
    """
    Processes songsheets, returns a context (dict) containing
    song: { id: NNN, title: X, artist: X, chords: [X],
    """

    songs = glob(os.path.join(inputdir, "*.udn"))

    context = {'chords': set([]), 'songs': []}
    pbar = Bar("Analysing Content: ", max=len(songs))
    for sng in sorted(songs):
        # index for nav documents/object ids
        song_id = "{:03d}".format(pbar.index + 1)
        # basename of outputfile
        song_dest = os.path.basename(re.sub(r'\.udn$', '.html', sng))

        # convert song body to html
        content = ukedown_to_html(sng)
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
                                  'artist': artist.strip(),
                                  'title': title.strip(),
                                  'chords': [ safe_name(c) for c in songchords],
                                  'html': str(soup)
                                  })
        pbar.next()

    pbar.finish()
    return context


def build_songbook():
    # render templates for songs
    pass

def main(options):
    """
    main script entrypoint, expects an 'options' object from argparse.ArgumentParser
    """
    index = {'songbook': opts.output,
             'songlist': [],
             'chordlist': set([]),
             'stylesheets': [],
             'missing': set([])}


    # context created by analysing input files and options:
    context = analyse_inputs(options.input)
    context['songbook'] = os.path.basename(options.output)
    context['stylesheets'] = []
    context['images'] = []


    # now generate the chord images from templates
    with open('chords.yml') as cd:
        chord_defs = yaml.safe_load(cd)

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

    env = Environment(loader=FileSystemLoader('templates'))

    # now let's generate our songsheets
    tpl = env.get_template('ukesong_inline.j2')
    for songobj in Bar("Rendering").iter(context['songs']):
        with open(os.path.join(options.output, 'EPUB', 'songs', songobj['filename']), 'w') as sf:
            sf.write(tpl.render(songobj))

    # now generate the other templates for epub
    tpl = 'nav.xhtml.j2'
    with open(os.path.join(options.output, 'EPUB', 'nav.xhtml'), 'w') as nav:
        nav.write(tpl.render(context))

    tpl = 'product.opf.j2'
    with open(os.path.join(options.output, 'EPUB', 'product.opf'), 'w') as prod:
        prod.write(tpl.render(context))




    if not options.report:
        try:
            indexpg = render('nav.xhtml.j2', index)
            with open(os.path.join(opts.output, 'EPUB/nav.xhtml'), 'w') as index_out:
                index_out.write(indexpg)
            with open(os.path.join(opts.output, 'EPUB/package.opf'), 'w') as pkgfile:
                pkgfile.write(render('package.opf.j2', index))
            with open(os.path.join(opts.output, 'EPUB/songs/index.html'), 'w') as idxfile:
                idxfile.write(render('bookindex.j2', index))
        except:
            print (yaml.safe_dump(index))
            raise
    if options.report:
        print ("""
        Songook Summary for: {0.output}
        input directory: {0.input}
        Song Count: {1}
        Chords Used: {2}
        Missing Chord Definitions
        {3}""".format(options,
                      len(index['songlist']),
                      ','.join(index['chordlist']),
                      ','.join(sorted(list(index['missing']))) ))







if __name__ == "__main__":
    opts = parse_commandline(sys.argv[1:])
    main(opts)


