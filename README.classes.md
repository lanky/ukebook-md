# Classes

This is an experimental branch to allow me to wrap the core elements of ukebook into classes.
It's here because eventually it is likely we'll want to marry this with a web framework, which is
almost certainly likely to have an MVC (Model, View, Controller) structure, and these classes could
easily be wrapped into DB models

## items to wrap

### not absolutely certain about these. actually
Fretboard
  strings
  frets

Chord(Fretboard)
  position
  fingering
  barre
  relative

Song - an individual song, with searchable attributes, e.g
  Title: the actual song title
  Artist: the song artist
  ArtistSort: song artist in sort order ("Cure, The", "Tunstall, KT" etc)
  Chords: List of chords used in the song, in the order they appear.
          - in an MVC setup these will probably be references to Chord Objects
  Content: The actual HTML content
  Source: THe original raw UDN
  Tags: a list of tags, used for searching etc. Could be a reference to another model
  Flavour: controls stylesheets, essentially
  Author: the name of the person who created the songsheet. Optional

Songbook - might be as simple as a git tag on a repository of songsheets
  Title
  Songlist
  Index
  Version
  Tag


Songs and Songbooks will need methods that generate HTML sites, PDF, EPUB, whatever

