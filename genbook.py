#!/usr/bin/env python
# -*- coding: utf-8 -*-
# everything but the kitchen sink to ease portability when reqd.

import markdown
import ukedown.udn

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
    parser.add_argument("-o", "--output", help="Name of Book to build (default is Karauke_YYYY_MM_DD", default="Karauke_{:%Y-%m-%d}".format(datetime.datetime.now()))
    parser.add_argument("--stylesheet", help="provide a custom stylesheet to test rendering. Expects to be given a path.")
    parser.add_argument("--template", help="provide a custom template to test rendering. Expects to be given a path")

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

def main(options):
    """
    main script entrypoint, expects an 'options' object from argparse.ArgumentParser
    """
    css_dir = os.path.join(options.output, 'css')
    chord_dir = os.path.join(options.output, 'chords')
    # setup our output directory

    for d in [ css_dir, chord_dir]:
        if not os.path.isdir(d):
            os.makedirs(d)

    for stylesheet in glob('css/*.css'):
        shutil.copy2(stylesheet, css_dir)



    # build an index object
    index = {'songbook': opts.output, 'songlist': []}

    songs = glob("%s/*.udn" % options.input)

    for f in sorted(songs):
        print ("processing ", f)
        try:
            idx_entry = {}
            ctx = {}
            html = ukedown_to_html(f)
            # process that with bs4? Find the classes you require?
            # to generate metadata?
            soup = bs(html, features="lxml")
            # find the chords and associate them with diagrams
            chords = []
            for crd in [c.text.split().pop(0) for c in soup.findAll('span', {'class': 'chord'})]:
                # we only want the first word
                c = crd.split().pop(0)
                # munge filenames, '/' -> 'slash',
                # '#' -> 'sharp'
                if '/' in c:
                    c.replace('/', 'slash')
                if '#' in c:
                    c.replace('#', 'sharp')
                if c not in chords:
                    chords.append(c)
            ctx['chords'] = chords
            for crd in chords:
                crdfile = "{}.gif".format(crd)
                if not os.path.isfile("chords/{}".format(crdfile)):
                    print("Missing chord diagram {}".format(crdfile))
                    continue
                if not os.path.isfile(os.path.join(chord_dir, crdfile)):
                    shutil.copy2("chords/{}".format(crdfile), chord_dir)

            # extract first h1 tag and make it the document title, with optional artist
            # there should only be one of these anyway, even if not, we'll extract the first as song title
            hdr = soup.h1.extract()
            try:
                if '-' in hdr.text:
                    ctx['title'], ctx['artist'] = [i.strip() for i in hdr.text.split('-', 1) ]
                else:
                    ctx['title'] = hdr.text.strip()
            except ValueError:
                print ("Cannot parse {}".format(hdr.text))

            # remove it from the document, we'll render it differently
            hdr.decompose()

            # print(ctx)
            ctx['html'] = str(soup)

            out = render("ukesong.j2", ctx)
            output = "{}.html".format(os.path.splitext(os.path.basename (f))[0])
            idx_entry = { 'filename': output,
                          'artist': ctx.get('artist'),
                          'title': ctx.get('title')
                          }
            with codecs.open(os.path.join(options.output, output), mode='wb', encoding="utf-8") as fd:
                fd.write(out)

        except (IOError, OSError) as E:
            print ("oops - couldn't render %s (%s)" % (E.filename, E.strerror))

        except:
            # all other errors
            raise
        index['songlist'].append(idx_entry)

    indexpg = render('bookindex.j2', index)
    with open(os.path.join(opts.output, 'index.html'), 'w') as index_out:
        index_out.write(indexpg)



if __name__ == "__main__":
    opts = parse_commandline(sys.argv[1:])
    main(opts)


