#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import yaml
import codecs
from jinja2 import Environment, FileSystemLoader
import argparse
from progress.bar import Bar

# two-way mapping of equivalent non-naturals, to allow a chord to be
# defined in more than one way (possibly to reduce duplication)
alt_names = {
        'A#': 'Bb',
        'Bb': 'A#',
        'C#': 'Db',
        'Db': 'C#',
        'D#': 'Eb',
        'Eb': 'D#',
        'F#': 'Gb',
        'Gb': 'F#',
        'G#': 'Ab',
        'Ab': 'G#',
        }


def parse_cmdline(argv):
    """
    process commandline options and arguments
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("chord", nargs="*", help="chord names (from configuration) to render")
    parser.add_argument("-c", "--chordlist", default="chords.yml", help="chord configuration file (YAML)")
    parser.add_argument("-t", "--template", default="external_chord.svg.j2", help="chord template (jinja2( - used for rendering chords as SVG")
    parser.add_argument("-d", "--destdir", default="chords", help="output directory for chord (SVG) files")

    bgrp = parser.add_argument_group("Fretboard Layout", "Customise frets, strings and spacing")
    bgrp.add_argument("-s", "--strings", help="Number of strings to draw", type=int, default=4)
    bgrp.add_argument("-f", "--frets", help="number of frets to draw (not including nut)", type=int, default=5)
    bgrp.add_argument("-w", "--spacing", help="spacing (fret/string spacing)", type=float, default=18.0)

    opts = parser.parse_args()

    if not os.path.isfile(opts.chordlist):
        raise argparse.ArgumentError("no such file or directory: {}".format(opts.chordlist))

    return opts


def symbolise(name):
    """
    replace pretend symbols with real ones (unicode ftw)
    """
    translations = {
            'b': '&flat;',
            '#': '&sharp;',
            }
    tt = { ord(k): v for k, v in list(translations.items()) }

    return str(name).translate(tt)

def safe_name(chord):
    """
    Translate unsafe characters for filenames (on Linux, at least. May need more for windows)
    """
    transtable = {
            '#': '_sharp_',
            '/': '_on_',
            }

    return chord.translate({ ord(k): v for k, v in transtable.items() })

def merge_ctx(base, **kwargs):
    """
    create a merged context for passing into jinja template

    Args:
        base(dict): basic layout information, fretboard info, diag size etc
    Kwargs:
        name: un-translated name of chord, special symbols and all
    """
    context = {}
    # calculate context settings.
    # need to get fret and string spacing and positions.
    # There are only 3 gaps for 4 strings (etc)
    sgap = ( base['fboard']['right'] - base['fboard']['left'] ) / float( base['fboard']['strings'] - 1 )
    # there will be x+1 fret lines, though, so we need to recognise that
    fgap = ( base['fboard']['bottom'] - base['fboard']['top'] ) / float(base['fboard']['frets'])
    # we only need x positions for strings.
    strings = [ base['fboard']['left'] + (idx * sgap)
                for idx in range(base['fboard']['strings']) ]
    # frets require an extra addition for the 'nut', or 'fret 0'
    frets = [ base['fboard']['top'] + ( idx * fgap )
              for idx in range(base['fboard']['frets']) ]
    # add the baseline
    frets.append(base['fboard']['bottom'])

    context.update(base)
    context['frets'] = frets
    context['strings'] = strings

    # radius for rounding rectangles and sizing finger positions
    # makes circles half a fret gap
    context['radius'] = fgap / 4
    # centre for positioning halfway between frets
    context['centre'] = fgap / 2

    # caculate mid-fret positions to simplify marker stuff
    bpos = kwargs.get('barre', 0)
    if bpos != 0:
        # barre is provided as a fret number
        # we need to calculate offsets
        # barres are wider than the board by radius * 2
        # and offset from position by radius in both x and y axes
        context['barre'] = {
                'position': kwargs['barre'],
                'left': base['fboard']['left'] - context['radius'],
                'top': (frets[bpos] - context['centre']) - context['radius'],
                'width':  base['fboard']['right'] - base['fboard']['left'] +
                          (context['radius'] * 2),
                'height': context['radius'] * 2,
                }

    context['fingers'] = []
    for fpos in kwargs.get('fingers', []):
        if fpos == 0:
            context['fingers'].append(fpos)
        else:
            # we have to be relative to the barre if there is one
            context['fingers'].append(frets[fpos + bpos] - (fgap / 2))

    context['name'] = kwargs.get('name')
    return context


def gen_board(spacing, strings=4, frets=5):
    """
    An attempt to generate an entire chord diagram based on spacing of
    strings and frets.
    Predicated on
    1. width: (strings +1 ) * spacing
    2. height: (frets + 3) * spacing
    3. origin is x: spacing, y: 2* spacing
    4. margins are 1* spacing, except top: 2* spacing

    This should centre the fretboard horizontally
    """
    # margin calculations (used for coords)
    ctx = {}
    # top of fretboard
    tm = 2 * spacing
    # left of board
    lm = spacing
    # right of board ( end of frets)
    rm = strings * spacing
    # bottom of board (end of strings)
    bm = tm + ( frets * spacing )

    ctx['width'] = rm + spacing
    ctx['height'] = bm + spacing

    ctx['top'] = tm
    ctx['bottom'] = bm
    ctx['left'] = lm
    ctx['right'] = rm


    # calculate coords for each string (vertical lines)
    # each one has x1, y1, x2, y2 elements, 2 of which are static.
    ctx['strings'] = [ lm + (spacing * i) for i in range(strings) ]
    # each  string will have coords x1=s, x2=s, y1=top, y2=bottom
    # mark the nut differently, it'll have a thicker line
    # fret 0: [ y1=f, y2=f, x1=left, x2=right]
    ctx['nut'] = tm
    ctx['frets'] = [ tm + (spacing * i) for i in range(frets + 1) ]

    return ctx

def get_alt_name(chord):
    res = re.match(r'^([ABCDEFG][b#]?)(.*)', chord)

    if res is not None:
        root, voicing = res.groups()
        altroot = alt_names.get(root)
        if altroot is not None:
            altname = "{}{}".format(altroot, voicing)
        else:
            return chord

        return altname
    return chord

def generate(chordlist, definitions, destdir="chords", template="external_chord.svg.j2"):
    """
    Generate chord diagrams based on a definitions file

    Args:
        chordlist(list [str]): list of chord names to generate
        definitions(dict): dictionary describing chords (fret positions etc)

    Kwargs:
        destdir(str): output directory  for chord diagrams
    """
    if not os.path.isdir(destdir):
        try:
            os.makedirs(destdir)
        except (IOError, OSError) as E:
            print("Cannot create output directory {0.filename} (0.strerror}".format(E))
            destdir = os.path.realpath(os.curdir)

    cfg = {}


    try:
        with codecs.open('fretboard.yml', mode="r", encoding="utf-8") as cfile:
            cfg.update(yaml.safe_load(cfile))
    except:
        raise

    env = Environment(loader=FileSystemLoader('templates'))
    tpl = env.get_template(template)

    missing = set([])

    print ("progress")
    pbar = Bar("{:20}".format("Rendering Chords:"), max=len(chordlist))
    try:
        for chordname in pbar.iter(chordlist):
            if chordname in definitions:
                ch = definitions.get(chordname)
            else:
                altname = get_alt_name(chordname)
                ch = definitions.get(chordname)

            if ch is None:
                missing.add(chordname)
                continue

            if 'name' not in ch:
                ch['name'] = symbolise(chordname)

            # replaces characters that cause shell problems
            chordfile = safe_name(chordname)

            with codecs.open("{}/{}.svg".format(destdir, chordfile), mode='w', encoding="utf-8") as output:
                output.write(tpl.render(merge_ctx(cfg, **ch)))
    except:
        print("Failed to render {}".format(chordname))
        raise

    return missing



if __name__ == "__main__":
    # we need to load a config for our chord diagram
    opts = parse_cmdline(sys.argv[1:])
    # load out chord definitions to pass into the templates

    if not os.path.isdir(opts.destdir):
        os.makedirs(opts.destdir)
    chorddefs = yaml.load(codecs.open(opts.chordlist, mode="r", encoding="utf-8"))

    if not opts.chord:
        opts.chord = chorddefs.keys()

    print ("generating chords")
    # generate diagrams for the list of provided chords
    # report on any chords that were missing definitions
    missing = generate(opts.chord, chorddefs, destdir=opts.destdir, template=opts.template)

    if len(missing):
        print("Could not find definition for chords: \n", "\n".join(missing) )
