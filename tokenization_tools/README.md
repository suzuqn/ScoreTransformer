# Tokenization tools

This directory contains the tokenizer and de-tokenizer between **MusicXML** and proposed **score token** representation.

- [**tokenizer**](tokenizer)
  - MusicXML -> Score tokens

- [**de-tokenizer**](detokenizer)
  - Score tokens -> MusicXML

#### requirements

Python 3.6+

- **tokenizer**
  - beautifulsoup4 (4.6.3)
  - lxml (4.9.1)
  - pretty_midi (0.2.9)

- **de-tokenizer**
  - music21 (7.3.3)

Note: The library versions here are not specified ones, but **tested** ones.
