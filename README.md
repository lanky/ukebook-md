# ukebook_md

## Intro

A toolset to generate songsheets and indexed songbooks from 
[ukedown](https://github.com/lanky/ukedown)-formatted inputs.

ukedown is a special case of Markdown, with additions for inline chords,
performance notes etc. See the repo linked above for more details

It is intended to be used to manage songbooks for ukulele groups, specifically
[Karauke](https://www.karauke.co.uk), where we have a requirement to produce
both 'band' and 'singers' versions of a given song.

Here you will find tools to convert directories full of 'ukedown' formatted
files to HTML, with index pages and (fairly) responsive CSS.

The end goal will be to build responsive HTML (Supporting rotate and resize)
and PDF documents in both landscape and portrait modes, in a variety of styles,
but initially

  1. karauke band format (inline chords, but no diagrams)
  2. karauke singers' format (no inline chords or diagrams - lyrics only)
  3. Ukulele Wednesdays format (both inline chords and diagrams)

## Contents

### Scripts

| script        | function                                                 |
| :---          | :---                                                     |
| `genbook.py`  | generate HTML structures from directorie(s) of udn files |
| `makepdf.py`  | convert HTML output into PDF songbook                    |
| `chordgen.py` | Generate chord diagrams in SVG format                    |
| `makesong.py` | Generate an individual PDF from a single udn file        |

### configuration files
  `chords.yml` - defines fingering, neck position and barres for known chords.

  These are used to generate SVG chord diagrams (scalable vector diagrams)
  which are inserted into each songsheet

  `fretboard.yml` - defines a standard ukulele fretboard layout

  (for use with an SVG template) - number of strings etc is customisable, so
  could also be used for other instruments (guitar etc)

## Requirements

You'll need a python virtual environment, python 3.5+ - the toolset has only
been tested with that.

There is a `requirements.txt` file in the repo that can be used to generate
this.

Or you can just install all those packages into a system or user directory, of
course.

* markdown (well, obviously)
* jinja2 (for templating) 

## Current Functionality

* Generation of HTML documents, with links to CSS files
* SVG chord diagrams
* HTML docs generated from modular jinja2 templates
* CSS grid used for a flexible layout - text degrades into multiple columns as
     the page gets wider.

## PDF Generation
PDF generation is handled by the [Weasyprint](https://weasyprint.org/) libraries.

A separate tool has been added to build PDFs from web content, but this will
eventually be added to the main book generation tools.

PDF generation has some basic requirements and limitations
* weasyprint doesn't support CSS Grid (yet?)
* It cannot render internal (i.e. directly in HTML) SVG images

To overcome this, for PDF use the `--external` flag to `genbook.py` for content
you intend to render as PDF

The `makepdf.py` tool uses a custom stylesheet without grid

### An example
Generate web content using the PDF stylesheet (it still works as HTML):
```python
./genbook.py --external -o BOOK_DIRECTORY -s pdfprint INPUT_DIRECTORY
```
Then use the included `makepdf.py` script to generate your output PDF

```python
./makepdf.py BOOK_DIRECTORY -o FILENAME.pdf
```
