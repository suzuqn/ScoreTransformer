from bs4 import BeautifulSoup
from bs4.element import Tag
from fractions import Fraction
import pretty_midi

def attributes_to_tokens(attributes, staff=None): # tokenize 'attributes' section in MusicXML
    tokens = []
    divisions = None

    for child in attributes.contents:
        type_ = child.name
        if type_ == 'divisions':
            divisions = int(child.text)
        elif type_ in ('clef', 'key', 'time'):
            if staff is not None:
                if 'number' in child.attrs and int(child['number']) != staff:
                    continue
            tokens.append(attribute_to_token(child))

    return tokens, divisions

def attribute_to_token(child): # clef, key signature, and time signature
    type_ = child.name
    if type_ == 'clef':
        if child.sign.text == 'G':
            return 'clef_treble'
        elif child.sign.text == 'F':
            return 'clef_bass'
    elif type_ == 'key':
        key = int(child.fifths.text)
        if key < 0:
            return f'key_flat_{abs(key)}'
        elif key > 0:
            return f'key_sharp_{key}'
        else:
            return f'key_natural_{key}'
    elif type_ == 'time':
        times = [int(c.text) for c in child.contents if isinstance(c, Tag)] # excluding '\n'
        if times[1] == 2:
            return f'time_{times[0]*2}/{times[1]*2}'
        elif times[1] > 4:
            fraction = str(Fraction(times[0], times[1]))
            if int(fraction.split('/')[1]) == 2: # X/2
                return f"time_{int(fraction.split('/')[0])*2}/{int(fraction.split('/')[0])*2}"
            else:
                return 'time_' + fraction
        else:
            return f'time_{times[0]}/{times[1]}'

def aggregate_notes(voice_notes): # notes to chord
    for note in voice_notes[1:]:
        if note.chord is not None:
            last_note = note.find_previous('note')
            last_note.insert(0, note.pitch)
            note.decompose()

def note_to_tokens(note, divisions=8, note_name=True): # notes and rests
    beam_translations = {'begin': 'start', 'end': 'stop', 'forward hook': 'partial-right', 'backward hook': 'partial-left'}

    if note.duration is None: # gracenote
        return []

    duration_in_fraction = str(Fraction(int(note.duration.text), divisions))

    if note.rest:
        return ['rest', f'len_{duration_in_fraction}'] # for rests

    tokens = []

    # pitches
    for pitch in note.find_all('pitch'):
        if note_name:
            if pitch.alter:
                alter_to_symbol= {'-2': 'bb', '-1': 'b', '0':'', '1': '#', '2': '##'}
                tokens.append(f"note_{pitch.step.text}{alter_to_symbol[pitch.alter.text]}{pitch.octave.text}")
            else:
                tokens.append(f"note_{pitch.step.text}{pitch.octave.text}")
        else:
            note_number = pretty_midi.note_name_to_number(pitch.step.text + pitch.octave.text) # 'C4' -> 60
            if pitch.alter:
                note_number += int(pitch.alter.text)
            tokens.append(f'note_{note_number}')

    # len
    tokens.append(f'len_{duration_in_fraction}')

    if note.stem:
        tokens.append(f'stem_{note.stem.text}')

    if note.beam:
        beams = note.find_all('beam')
        tokens.append('beam_' + '_'.join([beam_translations[b.text] if b.text in beam_translations else b.text for b in beams]))

    if note.tied:
        tokens.append('tie_' + note.tied.attrs['type'])

    return tokens

def element_segmentation(measure, soup, staff=None): # divide elements into three sections
    voice_starts, voice_ends = {}, {}
    position = 0
    for element in measure.contents:
        if element.name == 'note':
            if element.duration is None: # gracenote
                continue

            voice = element.voice.text
            duration = int(element.duration.text)
            if element.chord: # rewind for concurrent notes
                position -= last_duration

            if element.staff and int(element.staff.text) == staff:
                voice_starts[voice] = min(voice_starts[voice], position) if voice in voice_starts else position
                start_tag = soup.new_tag('start')
                start_tag.string = str(position)
                element.append(start_tag)

            position += duration

            if element.staff and int(element.staff.text) == staff:
                voice_ends[voice] = max(voice_ends[voice], position) if voice in voice_ends else position
                end_tag = soup.new_tag('end')
                end_tag.string = str(position)
                element.append(end_tag)

            last_duration = duration
        elif element.name == 'backup':
            position -= int(element.duration.text)
        elif element.name == 'forward':
            position += int(element.duration.text)
        else: # other types
            start_tag = soup.new_tag('start')
            end_tag = soup.new_tag('end')

            start_tag.string = str(position)
            end_tag.string = str(position)

            element.append(start_tag)
            element.append(end_tag)

    # voice section
    voice_start = sorted(voice_starts.values())[1] if voice_starts else 0
    voice_end = sorted(voice_ends.values(), reverse=True)[1] if voice_ends else 0

    pre_voice_elements, post_voice_elements, voice_elements = [], [], []
    for element in measure.contents:
        if element.name in ('backup', 'forward'):
            continue
        if element.name == 'note' and element.duration is None: # gracenote
            continue
        if staff is not None:
            if element.staff and int(element.staff.text) != staff:
                continue

        if voice_starts or voice_ends:
            if int(element.end.text) <= voice_start:
                pre_voice_elements.append(element)
            elif voice_end <= int(element.start.text):
                post_voice_elements.append(element)
            else:
                voice_elements.append(element)
        else:
            pre_voice_elements.append(element)

    return pre_voice_elements, voice_elements, post_voice_elements

def measures_to_tokens(measures, soup, staff=None, note_name=True):
    divisions = 0
    tokens = []
    for measure in measures:

        tokens.append('bar')
        if staff is not None:
            notes = [n for n in measure.find_all('note') if n.staff and int(n.staff.text) == staff]
        else:
            notes = measure.find_all('note')

        voices = list(set([n.voice.text for n in notes if n.voice]))
        for voice in voices:
            voice_notes = [n for n in notes if n.voice and n.voice.text == voice]
            aggregate_notes(voice_notes)

        if len(voices) > 1:
            pre_voice_elements, voice_elements, post_voice_elements = element_segmentation(measure, soup, staff)

            for element in pre_voice_elements:
                if element.name == 'attributes':
                    attr_tokens, div = attributes_to_tokens(element, staff)
                    tokens += attr_tokens
                    divisions = div if div else divisions
                elif element.name == 'note':
                    if divisions == 0:
                        tokens += note_to_tokens(element, note_name)
                    else:
                        tokens += note_to_tokens(element, divisions, note_name)

            if voice_elements:
                for voice in voices:
                    tokens.append('<voice>')
                    for element in voice_elements:
                        if (element.voice and element.voice.text == voice) or (not element.voice and voice == '1'):
                            if element.name == 'attributes':
                                attr_tokens, div = attributes_to_tokens(element, staff)
                                tokens += attr_tokens
                                divisions = div if div else divisions
                            elif element.name == 'note':
                                if divisions == 0:
                                    tokens += note_to_tokens(element, note_name)
                                else:
                                    tokens += note_to_tokens(element, divisions, note_name)
                    tokens.append('</voice>')

            for element in post_voice_elements:
                if element.name == 'attributes':
                    attr_tokens, div = attributes_to_tokens(element, staff)
                    tokens += attr_tokens
                    divisions = div if div else divisions
                elif element.name == 'note':
                    if divisions == 0:
                        tokens += note_to_tokens(element, note_name)
                    else:
                        tokens += note_to_tokens(element, divisions, note_name)
                        
        else:
            for element in measure.contents:
                if staff is not None:
                    if element.name in ('attributes', 'note') and element.staff and int(element.staff.text) != staff:
                        continue
                if element.name == 'attributes':
                    attr_tokens, div = attributes_to_tokens(element, staff)
                    tokens += attr_tokens
                    divisions = div if div else divisions
                elif element.name == 'note':
                    if divisions == 0:
                        tokens += note_to_tokens(element, note_name)
                    else:
                        tokens += note_to_tokens(element, divisions, note_name)

    return tokens

def load_MusicXML(mxml_path): # load MusicXML contents using BeautifulSoup
    soup = BeautifulSoup(open(mxml_path, encoding='utf-8'), 'lxml-xml', from_encoding='utf-8') # MusicXML
    for tag in soup(string='\n'): # eliminate line breaks
        tag.extract()

    parts = soup.find_all('part')

    return [part.find_all('measure') for part in parts], soup

def MusicXML_to_tokens(soup_or_mxml_path, note_name=True): # use this method
    if type(soup_or_mxml_path) is str:
        parts, soup = load_MusicXML(soup_or_mxml_path)
    else:
        soup = soup_or_mxml_path
        for tag in soup(string='\n'): # eliminate line breaks
            tag.extract()

        parts = [part.find_all('measure') for part in soup.find_all('part')]

    if len(parts) == 1:
        tokens = ['R'] + measures_to_tokens(parts[0], soup, staff=1, note_name=note_name)
        tokens += ['L'] + measures_to_tokens(parts[0], soup, staff=2, note_name=note_name)
    elif len(parts) == 2:
        tokens = ['R'] + measures_to_tokens(parts[0], soup, note_name=note_name)
        tokens += ['L'] + measures_to_tokens(parts[1], soup, note_name=note_name)

    return tokens
