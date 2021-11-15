## Overview

Detokenizer builds musical scores from token sequences, utilizing [music21](https://web.mit.edu/music21/).

## Usage

#### 1. import "tokens_to_score.py"

```python
from tokens_to_score import *
```

#### 2. pass token sequence (as a string) to "tokens_to_score" function

```Python
s = tokens_to_score(token_sequence)
```

- s : music21 Score object 


#### 3. use ".write" method to write score into a MusicXML file 

```python
s.write('musicxml', 'generated_score')
```

- You'll get the "generated_score.xml" file.

## Specifications

### Supported tokens

- Score tokens (that "[score_to_tokens.py](../tokenizer/)" generates)

### Requirements

Python 3.6+

- music21 (6.7.1)

