import collections
import os
import re
import typing

from gensim.summarization.textcleaner import split_sentences
from spacy.lang.da import Danish

from .decoder import decode_simple

DANISH_SPACY_TOKENIZER = Danish()


def get_ngrams(sent, n=2, as_string=False):
    """
	Given a sentence (as a string or a list of words), return all ngrams
	of order n in a list of tuples [(w1, w2), (w2, w3), ... ]
	bounds=True includes <start> and <end> tags in the ngram list
	"""

    ngrams = []
    words = sent.split()
    if n == 1:
        return words

    N = len(words)
    for i in range(n - 1, N):
        ngram = words[i - n + 1 : i + 1]
        if as_string:
            ngrams.append("_".join(ngram))
        else:
            ngrams.append(tuple(ngram))
    return ngrams


def get_su4(sent, as_string=False):
    words = get_ngrams(sent, 1, True)
    skipgrams = []

    N = len(words)
    for i in range(0, N):
        for j in range(i + 1, min(i + 5, N)):
            ngram = [words[i], words[j]]
            if as_string:
                skipgrams.append("_".join(ngram))
            else:
                skipgrams.append(tuple(ngram))
    skipgrams.extend(words)
    return skipgrams


class SimpleSentence:
    def __init__(self, n_bytes, sentence_n, text):
        """If you use n_bytes length is modelled as # of chars, otherwise # of tokens."""
        self.id = sentence_n
        self.orig = text
        self.length = len(re.sub("\n", " ", text).split())
        self.tokens = [t.text for t in DANISH_SPACY_TOKENIZER(text)]
        self.tok2 = " ".join(self.tokens)
        self.length = len(self.orig) if n_bytes > -1 else len(self.orig.split())
        # TODO: re-run numbers with the one below (the real number of tokens)
        # self.length = len(self.orig) if n_bytes > -1 else len(self.tokens)

        self.order = 2
        self.doc = ""
        self.unresolved = False
        self.new_par = None == "1"

    def __str__(self):
        return self.orig

    def __repr__(self):
        return str(self)


def get_sentences(n_bytes, text):
    sents = []
    count = 0
    order = 0
    prev_doc = ""
    # split into sentences with gensim splitter
    for line in split_sentences(text):
        doc = line
        orig = line
        tok = line
        sents.append(SimpleSentence(n_bytes, count, text))
        if not (doc or orig or tok):
            break
        if doc != prev_doc:
            order = 0
        text = orig
        count += 1
        order += 1
        prev_doc = doc
    return sents


def create_ilp_output(sents, concepts, path):
    sentence_concepts_file = path + ".sent.tok.concepts"
    length_file = path + ".sent.tok.lengths"
    orig_file = path + ".sent.tok.orig"
    sent_fh = open(sentence_concepts_file, "w")
    length_fh = open(length_file, "w")
    orig_fh = open(orig_file, "w")
    for sent in sents:
        sent_fh.write(" ".join(list(sent.concepts)) + "\n")
        length_fh.write("%d\n" % sent.length)
        orig_fh.write("%s\n" % sent.orig)
    length_fh.close()
    sent_fh.close()
    orig_fh.close()

    concept_weights_file = path + ".concepts"
    concept_fh = open(concept_weights_file, "w")
    for concept, value in concepts.items():
        concept_fh.write("%s %1.7f\n" % (concept, value))
    concept_fh.close()

    return sentence_concepts_file, concept_weights_file, length_file, orig_file


def make_concepts(sents, R1=True, R2=False, R4=False, SU4=False, R3=False) -> tuple:
    concept_files_prefix = f"{os.getpid()}-tmp"
    all_concepts = collections.defaultdict(int)
    for sent in sents:
        # store this sentence's concepts
        sent.concepts = set()
        if R1:
            concepts = set(get_ngrams(sent.tok2, 1, as_string=True))
        elif R2:
            concepts = set(get_ngrams(sent.tok2, 2, as_string=True))
        elif R4:
            concepts = set(get_ngrams(sent.tok2, 4, as_string=True))
        elif R3:
            concepts = set(get_ngrams(sent.tok2, 3, as_string=True))
        elif SU4:
            concepts = set(get_su4(sent.tok2, as_string=True))
        else:
            raise ValueError("no-grams?")

        for concept in concepts:
            all_concepts[concept] += 1
        sent.concepts = concepts

    return sents, all_concepts, concept_files_prefix


def make_summary(doc: dict, word_count: int) -> typing.Optional[str]:
    """Budget dictates the maximum amount of tokens in the summary (across sentences.)"""
    # gensim sentence splitter (not very good)
    sents = get_sentences(n_bytes=-1, text=doc["text"])

    sents, all_concepts, concept_files_prefix = make_concepts(sents, R2=True)

    # TODO: In-memory implementation
    (
        sentence_concepts_file,
        concept_weights_file,
        length_file,
        orig_file,
    ) = create_ilp_output(sents, all_concepts, concept_files_prefix)

    try:
        summ_sent_nums = decode_simple(
            word_count,
            length_file,
            sentence_concepts_file,
            concept_weights_file,
            timelimit=5,  # 5 seconds
        )
        summary = [sents[i] for i in summ_sent_nums]
        summary = " ".join(sent.tok2 for sent in summary)
    except:
        # if no solution could be found, default to empty text.
        # defaulting to entire text should be a decided by consumer.
        summary = None

    # clean up aux. files
    os.remove(sentence_concepts_file)
    os.remove(concept_weights_file)
    os.remove(orig_file)
    os.remove(length_file)
    return summary
