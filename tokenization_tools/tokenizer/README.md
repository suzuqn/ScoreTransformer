## Overview

Tokenizer creates token sequences from musical scores, utilizing [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/).

## Usage

#### 1. import

```python
from score_to_tokens import MusicXML_to_tokens
```

#### 2. pass a score path to "MusicXML_to_tokens" function

```Python
tokens = MusicXML_to_tokens('input_score.musicxml')
```

- The list of tokens will be returned.

## Specifications

### Supported scores / formats

- Piano scores (for both hands)
- MusicXML format

### Supported score elements

- Barline
- Clef (treble / bass)
- Key Signature
- Time Signature
- Note
  - note name (+ accidental) / length / stem direction / beam / tie  
- Rest
  - length

### Requirements

Python 3.6+

- beautifulsoup4 (4.6.3)
- pretty_midi (0.2.9)
- lxml (4.9.1)

Note: The library versions here are not specified ones, but **tested** ones.
