### MetricForScoreSimilarity
The original implementation is from https://github.com/AndreaCogliati/MetricForScoreSimilarity, which is official implementation for the paper "A metric for Music Notation Transcription Accuracy."

We partially modified this implementation as described in our paper (see Section 5.4):

1. added three musical aspects (*voice*, *beam*, and *tie*) to evaluate our model thoroughly
2. excluded two aspects (*barline* and *note grouping*) that were also measured using other aspects (*time signature* vs. *barline*, and *voice* vs. *note grouping*)
3. separated *insertion* and *deletion* errors

and post-process the result using Pandas in a following way:

4. integrated *note* and *rest* metrics
5. calculated error rates note-wisely