import itertools
import os
import re

from gensim.summarization.textcleaner import get_sentences

from newsroom.analyze import Fragments
from gensim.summarization import summarize as gensim_summerizer


# from sume import ConceptBasedILPSummarizer, Sentence, untokenize
# class MultilingualConceptBasedILPSummarizer(ConceptBasedILPSummarizer):
#     """Extension to accept documents in-memory and to override preprocessing steps."""

#     def read_documents(self, documents: list):
#         """
#         While summarization is often on a single document, this simply supports multiple source documents

#         # step 1 - get sentences
#         # step 2 - get tokens
#         # step 3 - map to sentence-objects
#         """

#         # lines = f.readlines()
#         for doc_id, text in enumerate(documents):
#             infile = doc_id  # this is the name of the document
#             lines = text.split(". ")  # stupid sentence splitter

#             # loop over sentences
#             for i in range(len(lines)):

#                 # stupid tokenizer
#                 tokens = lines[i].strip().split(" ")

#                 # add the sentence
#                 if len(tokens) > 0:
#                     sentence = Sentence(tokens, infile, i)
#                     untokenized_form = untokenize(tokens)
#                     sentence.untokenized_form = untokenized_form
#                     sentence.length = len(untokenized_form.split(" "))
#                     self.sentences.append(sentence)


# def sume_ilp(doc, word_count):
#     s = MultilingualConceptBasedILPSummarizer(str(os.getpid()))
#     documents = [doc["text"]]
#     documents = [re.sub("\n\n", " ", d) for d in documents]
#     s.read_documents(documents)

#     s.extract_ngrams(n=2)

#     # compute document frequency as concept weights
#     s.compute_document_frequency()

#     # prune sentences that are shorter than 10 words, identical sentences and
#     # those that begin and end with a quotation mark
#     s.prune_sentences(
#         mininum_sentence_length=10, remove_citations=True, remove_redundancy=True
#     )

#     # solve ILP problem
#     try:
#         value, subset = s.solve_ilp_problem()
#         # value, subset = s.tabu_search()
#     except:
#         return None

#     # outputs the summary
#     return " ".join([s.sentences[j].untokenized_form for j in subset])


def lead_3(article, word_count):
    """
    Extract lead-3 summary and return as dictionary.

    returns d :: { 'system': ... }
    """
    sentences = get_sentences(article["text"])
    summary = " ".join(itertools.islice(sentences, 3))
    return summary

def fragments_oracle(article, word_count):
    """
    Extract fragment oracle summary and return as dictionary.

    returns d :: { 'system': ... }
    """
    fragments = Fragments(article["summary"], article["text"], "da")
    summary = " ".join(str(f) for f in fragments.strings())
    return summary


def gensim_textrank(article, word_count):
    return gensim_summerizer(article["text"], word_count=word_count)
