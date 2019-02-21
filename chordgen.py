#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import codecs
from jinja2 import Environment, FileSystemLoader
import argparse


def parse_cmdline(argv):
    """
    process commandline options and arguments
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("chord", nargs="*", help="chord names (from configuration) to render")
    parser.add_argument("-c", "--chordlist", default="chords.yml", help="chord configuration file (YAML)")

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
            'b': '♭',
            '#': '♯'
            }
    tt = { ord(k): v for k, v in list(translations.items()) }

    return str(name).translate(tt)


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

def overlay(base, chord):
    """
    Generates additional context for chords ( fingering, barre, label etc)
    Essentially does a dictionary merge
    """
    # board = { 'top', 'bottom', 'left', 'right', 'nut' ,'strings', 'frets' }
    # we need to add "barre", "fingers",
    # if we have a barre, we need to  define x, y, width, rx, ry
    # barre position is essentially fret + 0.5 fret
    # string[x] - 0.g* spacing, fret[y] + 0.5*spacing,
    # marker and barre width are 0.5 * spacing

if __name__ == "__main__":
    # we need to load a config for our chord diagram
    opts = parse_cmdline(sys.argv[1:])
    cfg = {}

    try:
        with codecs.open('fretboard.yml', mode="r", encoding="utf-8") as cfile:
            cfg.update(yaml.safe_load(cfile))
    except:
        raise

    env = Environment(loader=FileSystemLoader('templates'))
    tpl = env.get_template('fretboard.svg.j2')

    try:
        chords = yaml.load(codecs.open(opts.chordlist, mode="r", encoding="utf-8"))
        for label, ch in list(chords.items()):
            if opts.chord and label not in opts.chord:
                continue
            print("rendering {}".format(label))
            if 'name' not in ch:
                ch['name'] = symbolise(label)
            with codecs.open("chords/{}.svg".format(label), mode='w', encoding="utf-8") as output:
                output.write(tpl.render(merge_ctx(cfg, **ch)))
    except:
        raise

