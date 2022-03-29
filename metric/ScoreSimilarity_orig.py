import music21
import numpy as np
from enum import IntEnum


class ScoreErrors(IntEnum):
    Barline = 0
    Clef = 1
    KeySignature = 2
    TimeSignature = 3
    Note = 4
    NoteSpelling = 5
    NoteDuration = 6
    StemDirection = 7
    Grouping = 8
    Rest = 9
    RestDuration = 10
    StaffAssignment = 11


def scoreAlignment(aScore, bScore):
    """Compare two musical scores.

    Parameters:

    aScore/bScore: music21.stream.Score objects

    Return value:

    (path, d):
           path is a list of tuples containing pairs of matching offsets
           d is the alignment matrix
    """

    def convertScoreToListOfPitches(aScore):
        """Convert a piano score into a list of tuples containing pitches

        Parameter:
            aScore a music21.Stream containing two music21.stream.PartStaff

        Return value:
            list of tuples (offset, pitches)
                offset is a real number indicating the offset of an object in music21 terms 
                pitches is a list of pitches in MIDI numbers
        """

        def getPitches(el):
            if isinstance(el, music21.note.Note):
                return [el.pitch.midi]
            elif isinstance(el, music21.chord.Chord):
                currentList = []
                for pitch in el.pitches:
                    currentList.append(pitch.midi)
                return currentList

        def convertStreamToList(aStream):
            aList = []
            currentOffset = 0.0
            currentList = []
            for el in aStream:
                if el.offset == currentOffset:
                    currentList += getPitches(el)
                else:
                    aList.append((currentOffset, currentList))
                    currentOffset = el.offset
                    currentList = getPitches(el)
            return aList

        aList = convertStreamToList(aScore.flat.notes)
        return aList

    def compareSets(aSet, bSet):
        """Compare two sets of pitches.

        Parameters:

        aSet/bSet: list of pitches

        Return value:

            the number of mismatching objects in the two sets
        """

        a = aSet.copy()
        b = bSet.copy()

        # Remove matching pitches from both sets
        aTemp = []
        for obj in a:
            if obj in b:
                b.remove(obj)
            else:
                aTemp.append(obj)
        a = aTemp

        return len(a) + len(b)

    def costMatrix(s, t):
        m = len(s)
        n = len(t)
        d = np.zeros((m + 1, n + 1))

        for i in range(1, m + 1):
            d[i, 0] = np.inf

        for j in range(1, n + 1):
            d[0, j] = np.inf

        for j in range(1, n + 1):
            for i in range(1, m + 1):
                cost = compareSets(s[i - 1][1], t[j - 1][1])
                idx = np.argmin([d[i - 1, j], d[i, j - 1], d[i - 1, j - 1]])
                if idx == 0:
                    d[i, j] = d[i - 1, j] + cost
                elif idx == 1:
                    d[i, j] = d[i, j - 1] + cost
                else:
                    d[i, j] = d[i - 1, j - 1] + cost

        return d

    # scoreAlignment
    aList = convertScoreToListOfPitches(aScore)
    bList = convertScoreToListOfPitches(bScore)
    d = costMatrix(aList, bList)

    (i,j) = (d.shape[0] - 1, d.shape[1] - 1)
    path = []
    while not (i == 0 and j == 0):
        aOff = aList[i-1][0]
        bOff = bList[j-1][0]
        path = [(aOff,bOff)] + path

        idx = np.argmin([d[i - 1, j], d[i, j - 1], d[i - 1, j - 1]])
        if idx == 0:
            i = i - 1
        elif idx == 1:
            j = j - 1
        else:
            i, j = i - 1, j - 1

    return path, d



def scoreSimilarity(estScore, gtScore):
    """Compare two musical scores.

    Parameters:

    estScore/gtScore: music21.stream.Score objects of piano scores. The scores must contain two
        music21.stream.PartStaff substreams (top and bottom staves)

    estScore is the estimated transcription
    gtScore is the ground truth

    Return value:

    a NumPy array containing the differences between the two scores:

        barlines, clefs, key signatures, time signatures, note, note spelling, 
        note duration, staff assignment, rest, rest duration

    The differences for notes, rests and barlines are normalized with the number of symbols
    in the ground truth
    """

    def isInstanceOfClasses(obj, classes):
        """Helper function to determine if an item is an instance of several classes"""
        for cls in classes:
            if isinstance(obj, cls):
                return True
        return False

    def countSymbols(aScore):
        """Count the number of symbols in a score

        Parameter:
            aScore a music21.Stream

        Return value:
            the number of music symbols (notes, rests, chords, barlines) in the score
        """

        # Classes to consider
        CLASSES = [music21.bar.Barline, music21.note.Note, music21.note.Rest,
                   music21.chord.Chord]

        nSymbols = 0
        for el in aScore.recurse():
            if isInstanceOfClasses(el, CLASSES):
                nSymbols += 1

        return nSymbols

    def convertScoreToList(aScore):
        """Convert a piano score into a list of tuples

        Parameter:
            aScore a music21.Stream containing two music21.stream.PartStaff

        Return value:
            list of tuples (offset, staff, object)
                offset is a real number indicating the offset of an object in music21 terms 
                staff is an integer indicating the staff (0 = top, 1 = bottom)
                object is a music21 object
        """

        # Classes to consider
        CLASSES = [music21.bar.Barline, music21.clef.Clef,
                   music21.key.Key, music21.meter.TimeSignature, music21.note.Note, music21.note.Rest,
                   music21.chord.Chord]

        def convertStreamToList(aStream, staff):
            aList = []
            currentOffset = 0.0
            currentList = []
            for el in aStream.recurse():
                if isInstanceOfClasses(el, CLASSES):
                    if el.getOffsetInHierarchy(aStream) == currentOffset:
                        currentList.append((staff, el))
                    else:
                        aList.append((currentOffset, currentList))
                        currentOffset = el.getOffsetInHierarchy(aStream)
                        currentList = [(staff, el)]
            return aList

        def flattenStream(aStream):
            newStream = music21.stream.Stream()
            for el in aStream.recurse():
                if isInstanceOfClasses(el, CLASSES):
                    newStream.insert(el.getOffsetInHierarchy(aStream), el)
                elif isinstance(el, music21.stream.Measure):
                    newStream.insert(el.getOffsetInHierarchy(aStream), music21.bar.Barline())
            return newStream

        def getNext(iterator):
            try:
                return next(iterator)
            except StopIteration:
                return None

        parts = aScore.getElementsByClass([music21.stream.PartStaff, music21.stream.Part])  # get staves
        topStaffList = convertStreamToList(flattenStream(parts[0]), 0)
        bottomStaffList = convertStreamToList(flattenStream(parts[1]), 1)

        aList = []
        tIterator = iter(topStaffList)
        bIterator = iter(bottomStaffList)
        tEl = getNext(tIterator)
        bEl = getNext(bIterator)

        while tEl or bEl:
            if not tEl:
                aList.append((bEl[0], bEl[1]))
                bEl = getNext(bIterator)
            elif not bEl:
                aList.append((tEl[0], tEl[1]))
                tEl = getNext(tIterator)
            else:
                if tEl[0] < bEl[0]:
                    aList.append((tEl[0], tEl[1]))
                    tEl = getNext(tIterator)
                elif tEl[0] > bEl[0]:
                    aList.append((bEl[0], bEl[1]))
                    bEl = getNext(bIterator)
                else:
                    aList.append((tEl[0], tEl[1] + bEl[1]))
                    tEl = getNext(tIterator)
                    bEl = getNext(bIterator)

        return aList

    def countObjects(aSet):
        """Count objects in a set

        Parameters:

        aSet: list of tuples (staff, object)
            staff is an integer indicating the staff (1 = top, 2 = bottom)
            object is a music21 object

        Return value:

            a tuple with the numbers of objects in the set (see definition of errors below)
        """

        errors = np.zeros((len(ScoreErrors.__members__)), int)

        for obj in aSet:
            if isinstance(obj[1], music21.stream.Measure) or isinstance(obj[1], music21.bar.Barline):
                errors[ScoreErrors.Barline] += 1
            elif isinstance(obj[1], music21.clef.Clef):
                errors[ScoreErrors.Clef] += 1
            elif isinstance(obj[1], music21.key.Key):
                errors[ScoreErrors.KeySignature] += 1
            elif isinstance(obj[1], music21.meter.TimeSignature):
                errors[ScoreErrors.TimeSignature] += 1
            elif isinstance(obj[1], music21.note.Note):
                errors[ScoreErrors.Note] += 1
            elif isinstance(obj[1], music21.chord.Chord):
                errors[ScoreErrors.Note] += len(obj[1].pitches)
            elif isinstance(obj[1], music21.note.Rest):
                errors[ScoreErrors.Rest] += 1
            else:
                print('Class not found:', type(obj[1]))

        return errors

    def compareSets(aSet, bSet):
        """Compare two sets of concurrent musical objects.

        Parameters:

        aSet/bSet: list of tuples (staff, object)
            staff is an integer indicating the staff (1 = top, 2 = bottom)
            object is a music21 object

        Return value:

            a tuple with the differences between the two sets (see definition of errors below)
        """

        def findEnharmonicEquivalent(note, aSet):
            """Find the first enharmonic equivalent in a set

            Parameters:

            note: a music21.note.Note object
            aSet: list of tuples (staff, object)
                staff is an integer indicating the staff (0 = top, 1 = bottom)
                object is a music21 object

            Return value:

                index of the first enharmonic equivalent of note in aSet
                -1 otherwise
            """
            for i, obj in enumerate(aSet):
                if isinstance(obj[1], music21.note.Note) and obj[1].pitch.ps == note.pitch.ps:
                    return i
            return -1

        def splitChords(aSet):
            """Split chords into seperate notes

            Parameters:

            aSet: list of tuples (staff, object)
                staff is an integer indicating the staff (0 = top, 1 = bottom)
                object is a music21 object

            Return value:
                a tuple (newSet, chords)
                newSet: aSet with split chords
                chords: the number of chords in aSet

            """
            newSet = []
            chords = 0
            for obj in aSet:
                if isinstance(obj[1], music21.chord.Chord):
                    chords += 1
                    for pitch in obj[1].pitches:
                        newNote = music21.note.Note()
                        newNote.offset = obj[1].offset
                        newNote.pitch = pitch
                        newNote.duration = obj[1].duration
                        newNote.stemDirection = obj[1].getStemDirection(pitch)
                        newSet.append((obj[0], newNote))
                else:
                    newSet.append(obj)

            return newSet, chords

        def compareObj(aObj, bObj):
            # Compare Music 21 objects
            if aObj == bObj:
                return True
            if type(aObj) != type(bObj):
                return False
            if isinstance(aObj, music21.stream.Measure):
                return True
            if isinstance(aObj, music21.bar.Barline):
                return True
            if isinstance(aObj, music21.clef.Clef):
                if type(aObj) == type(bObj):
                    return True
            if isinstance(aObj, music21.key.Key):
                if aObj.sharps == bObj.sharps:
                    return True
            if isinstance(aObj, music21.meter.TimeSignature):
                if aObj.numerator == bObj.numerator and aObj.beatCount == bObj.beatCount:
                    return True
            if isinstance(aObj, music21.note.Note):
                if aObj.pitch == bObj.pitch and aObj.duration == bObj.duration and aObj.stemDirection == bObj.stemDirection:
                    return True
            if isinstance(aObj, music21.note.Rest):
                if aObj.duration == bObj.duration:
                    return True
            if isinstance(aObj, music21.chord.Chord):
                if aObj.duration == bObj.duration and aObj.pitches == bObj.pitches and aObj.stemDirection == bObj.stemDirection:
                    return True
            return False

        def findObj(aPair, aSet):
            # Find
            for bPair in aSet:
                if aPair[0] == bPair[0]:
                    if compareObj(aPair[1], bPair[1]):
                        return bPair
            return None

        errors = np.zeros((len(ScoreErrors.__members__)), int)

        a = aSet.copy()
        b = bSet.copy()

        # Remove matching pairs from both sets
        # aTemp = []
        # for obj in a:
        #     if obj in b:
        #         b.remove(obj)
        #     else:
        #         aTemp.append(obj)
        # a = aTemp
        aTemp = []
        for pair in a:
            bPair = findObj(pair, b)
            if bPair:
                b.remove(bPair)
            else:
                aTemp.append(pair)
        a = aTemp

        # Find mismatched staff placement
        aTemp = []
        for obj in a:
            bTemp = [o[1] for o in b if o[0] != obj[0]]
            if obj[1] in bTemp:
                idx = b.index((1 - obj[0], obj[1]))
                del b[idx]
                errors[ScoreErrors.StaffAssignment] += 1
            else:
                aTemp.append(obj)
        a = aTemp

        # Split chords and report grouping errors
        a, aChords = splitChords(a)
        b, bChords = splitChords(b)
        errors[ScoreErrors.Grouping] += abs(aChords - bChords)

        # Find mismatches in notes
        aTemp = []
        for obj in a:
            if isinstance(obj[1], music21.note.Note):
                found = False
                for bObj in b:
                    if isinstance(bObj[1], music21.note.Note) and bObj[1].pitch == obj[1].pitch:
                        if bObj[0] != obj[0]:
                            errors[ScoreErrors.StaffAssignment] += 1
                        if bObj[1].duration != obj[1].duration:
                            errors[ScoreErrors.NoteDuration] += 1
                        if bObj[1].stemDirection != obj[1].stemDirection:
                            errors[ScoreErrors.StemDirection] += 1
                        b.remove(bObj)
                        found = True
                        break
                if not found:
                    aTemp.append(obj)
            else:
                aTemp.append(obj)
        a = aTemp

        # Find mismatched duration of rests
        aTemp = []
        for obj in a:
            if isinstance(obj[1], music21.note.Rest):
                for bObj in b:
                    if isinstance(bObj[1], music21.note.Rest) and bObj[1].duration != obj[1].duration:
                        b.remove(bObj)
                        errors[ScoreErrors.RestDuration] += 1
                        break
                aTemp.append(obj)
            else:
                aTemp.append(obj)
        a = aTemp

        # Find enharmonic equivalents and report spelling mistakes and duration mistakes
        aTemp = []
        for obj in a:
            if isinstance(obj[1], music21.note.Note):
                idx = findEnharmonicEquivalent(obj[1], b)
                if idx != -1:
                    if b[idx][0] != obj[0]:
                        errors[ScoreErrors.StaffAssignment] += 1
                    if b[idx][1].duration != obj[1].duration:
                        errors[ScoreErrors.NoteDuration] += 1
                    if b[idx][1].stemDirection != obj[1].stemDirection:
                        errors[ScoreErrors.StemDirection] += 1
                    del b[idx]
                    errors[ScoreErrors.NoteSpelling] += 1
                else:
                    aTemp.append(obj)
            else:
                aTemp.append(obj)
        a = aTemp

        errors += countObjects(a)
        errors += countObjects(b)

        # print()
        # print('aSet =', aSet)
        # print('bSet =', bSet)
        # print('errors =', errors)
        # print()

        return errors

    def errorsToCost(errors):
        cost = errors[ScoreErrors.Barline]
        cost += errors[ScoreErrors.Clef]
        cost += errors[ScoreErrors.KeySignature]
        cost += errors[ScoreErrors.TimeSignature]
        cost += errors[ScoreErrors.Note]
        cost += errors[ScoreErrors.NoteSpelling] * 1 / 4
        cost += errors[ScoreErrors.NoteDuration] * 1 / 4
        cost += errors[ScoreErrors.StemDirection] * 1 / 4
        cost += errors[ScoreErrors.StaffAssignment] * 1 / 2
        cost += errors[ScoreErrors.Grouping]
        cost += errors[ScoreErrors.Rest]
        cost += errors[ScoreErrors.RestDuration] * 1 / 2
        return cost

    def getSet(aList, start, end):
        set = []
        for aTuple in aList:
            if aTuple[0] >= end:
                return set
            if aTuple[0] >= start:
                set += aTuple[1]
        return set

    # scoreSimilarity
    path, _ = scoreAlignment(estScore, gtScore)

    aList = convertScoreToList(estScore)
    bList = convertScoreToList(gtScore)

    nSymbols = countSymbols(gtScore)

    errors = np.zeros((len(ScoreErrors.__members__)), float)

    aStart, aEnd = 0.0, 0.0
    bStart, bEnd = 0.0, 0.0
    for pair in path:
        if pair[0] != aEnd and pair[1] != bEnd:
            aEnd, bEnd = pair[0], pair[1]
            errors += compareSets(getSet(aList, aStart, aEnd), getSet(bList, bStart, bEnd))
            aStart, aEnd = aEnd, aEnd
            bStart, bEnd = bEnd, bEnd
        elif pair[0] == aEnd:
            bEnd = pair[1]
        else:
            aEnd = pair[0]
    errors += compareSets(getSet(aList, aStart, float('inf')), getSet(bList, bStart, float('inf')))
    for aspect in [ScoreErrors.Note, ScoreErrors.NoteSpelling, ScoreErrors.NoteDuration, ScoreErrors.StemDirection,
                   ScoreErrors.StaffAssignment, ScoreErrors.Grouping, ScoreErrors.Rest, ScoreErrors.RestDuration]:
        errors[aspect] /= nSymbols

    return errors
    
#
# Evaluate dataset
#

from music21 import converter 
import os
import numpy as np
import scipy.io as sio

METHODS = ['F', 'G', 'C', 'M']
METHODS_ORD = [2, 3, 0, 1]
BASEDIR = 'dataset'
N = 19
pieces = list(range(1,N+1))
gt = [None] * N
for piece in pieces:
    filename = os.path.join(BASEDIR, 'K-' + str(piece) + '.mxl')
    try:
        gt[piece - 1] = converter.parse(filename)
    except:
        print("Can't load", filename)
        pass

results = -np.ones((len(METHODS), N, len(ScoreErrors.__members__)))
for piece in pieces:
    if gt[piece - 1] == None:
        continue
    for method in METHODS:
        filename = os.path.join(BASEDIR, method + '-' + str(piece) + '.mxl')
        try:
            comparisonPiece = converter.parse(filename)
            print(filename, end = ' ')
            score = scoreSimilarity(gt[piece - 1], comparisonPiece)
            print(score)
            results[METHODS_ORD[METHODS.index(method)], piece - 1, :] = score
        except music21.converter.ConverterException:
            pass
        except Exception as err:
            print(type(err), err)
     
print('Saving results to MAT file')    
mat_results = {'results' : results}
sio.savemat('resultsWithAlignment', mat_results)
print('Done')