#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
import codecs
import fnmatch

from chordgen import safe_name
import diagram

def parse_cmdline(argv):
    """
    process commandline options
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("chordname", nargs="?",
        help="names of chords (from provided config) to generate. Can be a shell-style wildcard (e.g. Em* for all chords starting with Em)")
    parser.add_argument("-c", "--config", default="newchords.yml",
        help="path to YAML-format config file defining chord layouts")
    parser.add_argument("-s", "--style", default="chord_diagram.yml",
        help="path to YAML-format config file defining fonts etc for resulting diagrams")
    parser.add_argument("-o", "--output", default=os.path.realpath(os.curdir),
        help="output directory for generated chords (default is CWD)")

    return parser.parse_args(argv)

class ChordConfigError(EnvironmentError):
    pass


class MultiFingerChord(diagram.UkuleleChord):
    """
    A special case of UkuleleChord that can handle
    additional markers (more than one per string)
    """

    def __init__(self, **kwargs):


        # ensure we have only expected args for the parent class
        superargs = {
            'positions': kwargs.get('positions', None),
            'fingers': kwargs.get('fingers', None),
            'barre': kwargs.get('barre', None),
            'title': kwargs.get('title', None),
            'style': kwargs.get('style', None),
            }

        super().__init__(**superargs)

        fretted_positions = list(filter(lambda pos: isinstance(pos, int), self.positions))
        self.maxfret = max(fretted_positions)
        self.minfret = min([p for p in fretted_positions if p > 0 ])
        print("min: {} max: {}".format(self.minfret, self.maxfret))

        # our additional key for extra fingers
        self.extras = kwargs.get('extras')
        fspec = kwargs.get('fret_range')
        # sanity checks
        # 1. is it a 2-tuple or list?
        # 2. arww the values ints
        # 3. is x[0] < x[1]
        if fspec is None:
            self.fretspec = None
        elif not (isinstance(fspec, (tuple,list)) and len(fspec) == 2):
            print("fret range must have 2 entries")
            self.fretspec = None
        elif not all([isinstance(x, int) for x in fspec]):
            print("fret range must consist of integers only")
            self.fretspec = None
        elif not fspec[0] < fspec[1]:
            self.fretspec = None
        elif self.minfret - fspec[0] > 5:
            self.fretspec = None
        elif self.maxfret > fspec[1]:
            print("highest fret is outside fret range")
            self.fretspec = None
        else:
            self.fretspec = fspec


    def get_fret_range(self):
        """
        Work out how many frets to draw and which one to start at
        we want 5 frets, starting at 0 or self.minfret - 1
        """
        # have we overridden this in config?
        if self.fretspec is not None:
            fr = self.fretspec
        # else, calculate based on frets used
        chord_width = self.maxfret - self.minfret
        # the chord fits in the first 5 frets
        if self.maxfret <= 5:
            fr = (0, 5)
        elif chord_width <= 4:
            fr = (self.minfret - 1, self.minfret + 3)
        else:
            fr = (self.minfret, self.maxfret)
        print("{0} fret range: {1}-{2}".format(self.title, *fr))
        return fr


    def draw(self):
        super(MultiFingerChord, self).draw()
        if self.extras is not None:
            for e in self.extras:
                self.fretboard.add_marker(
                        string=e['string'],
                        fret=e['fret'],
                        color=e.get('color'),
                        label=e['finger'],
                        font_color=e.get('font_color')
                        )


# used to test merging. Can probably be removed
def dump(adict):
    print(yaml.safe_dump(dict(adict), default_flow_style=False))


def main():
    options = parse_cmdline(sys.argv[1:])

    if not os.path.isdir(os.path.realpath(options.output)):
        try:
            os.makedirs(os.path.realpath(options.output))
        except (IOError, OSError) as E:
            print("output directory {0.filename} does not exist and I could not create it - {0.strerror}".format(E))
            print("falling back to CWD")
            options.output = os.path.realpath(os.curdir)

    chord_style = None
    chord_defs = {}

    # Attempt to load chord definitions
    try:
        with codecs.open(options.config, mode='r', encoding='utf-8') as defs:
            chord_defs = yaml.safe_load(defs)
    except (IOError, OSError) as E:
        print("Unable to open {0.filename} ({0.strerror})".format(E))
        sys.exit(1)
    except:
        # deal with yaml-specific errors later, when we know what they are
        raise

    # styles (line colours etc)
    try:
        with codecs.open(options.style, mode='r', encoding='utf-8') as styledefs:
            chord_style = yaml.safe_load(styledefs)
    except (IOError, OSError) as E:
        print("Could not open chjord style config {0.filename} ({0.strerror})".format(E))
        print("Falling back to defaults")

    for chordname, cfg in chord_defs.items():
        if options.chordname and not fnmatch.fnmatch(chordname, options.chordname):
            continue
        print(chordname)
        chord = MultiFingerChord(style=chord_style, **cfg)
        chord.save('{}/{}.svg'.format(options.output, safe_name(chordname)))

if __name__ == "__main__":
    main()


