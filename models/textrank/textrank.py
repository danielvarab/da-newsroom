import logging
from typing import List, Callable

from gensim.parsing.preprocessing import (
    preprocess_string,
    remove_stopwords,
    stem_text,
    strip_multiple_whitespaces,
    strip_numeric,
    strip_punctuation,
    strip_short,
    strip_tags,
)
from gensim.summarization.summarizer import (
    _build_corpus,
    _extract_important_sentences,
    _format_results,
    summarize_corpus,
)
from gensim.summarization.textcleaner import (
    clean_text_by_sentences as _clean_text_by_sentences,
    split_sentences
)
from gensim.summarization.textcleaner import merge_syntactic_units, split_sentences


from spacy.lang.da import Danish
nlp = Danish()
INPUT_MIN_LENGTH = 10


# These are the exact same as in
DEFAULT_FILTERS = [
    lambda x: x.lower(),
    strip_tags,
    strip_punctuation,
    strip_multiple_whitespaces,
    strip_numeric,
    remove_stopwords,  # TODO: change to language specific stop words
    strip_short,
    stem_text,  # TODO: change to language specific stemmer
]

logger = logging.getLogger(__name__)


def split_and_preprocess(text: str, token_filters: List[Callable]) -> List[str]:
    # step 1
    original_sentences = split_sentences(text)

    # step two
    filtered_sentences = []
    for sentence in original_sentences:
        processed_sentence = preprocess_string(sentence, filters=token_filters)
        filtered_sentences.append(" ".join(processed_sentence))

    sentences = merge_syntactic_units(original_sentences, filtered_sentences)
    return sentences

def summerize(
    text: str,
    ratio=0.2,
    word_count: int = None,
    split=False,
    token_filters=DEFAULT_FILTERS,
):
    """
    Reimplementation for the textrank algorithm from gensim.

    TODO:
        - language specific stopwords
            - Maybe SpaCy?? e.g. from spacy.lang.X import STOP_WORDS
        - language specific stemmers
        - language specific filters. currently abbrivation merging in split sentences only works on a-zA-Z.
          maybe we can use \\p{L} via https://stackoverflow.com/a/24245331
    
    WARNING: This implementation strategy applies super poorly to Danish abbreviations
             eg. ca.

    DONE:
        - 
    """

    # NOTE: this is the divergence from gensim preprocessing step
    # we replace
    #   > sentences = _clean_text_by_sentences(text)
    # with
    sentences = split_and_preprocess(text, token_filters)

    ###############################
    # everything under this is the same as in the gensim implementation
    ###############################

    # If no sentence could be identified, the function ends.
    if len(sentences) == 0:
        logger.warning("Input text is empty.")
        return [] if split else u""

    # If only one sentence is present, the function raises an error (Avoids ZeroDivisionError).
    if len(sentences) == 1:
        raise ValueError("input must have more than one sentence")

    # Warns if the text is too short.
    if len(sentences) < INPUT_MIN_LENGTH:
        logger.warning(
            "Input text is expected to have at least %d sentences.", INPUT_MIN_LENGTH
        )

    corpus = _build_corpus(sentences)

    most_important_docs = summarize_corpus(
        corpus, ratio=ratio if word_count is None else 1
    )

    # If couldn't get important docs, the algorithm ends.
    if not most_important_docs:
        logger.warning("Couldn't get relevant sentences.")
        return [] if split else u""

    # Extracts the most important sentences with the selected criterion.
    extracted_sentences = _extract_important_sentences(
        sentences, corpus, most_important_docs, word_count
    )

    # Sorts the extracted sentences by apparition order in the original text.
    extracted_sentences.sort(key=lambda s: s.index)

    return _format_results(extracted_sentences, split)


if __name__ == "__main__":
    text = """Rice Pudding - Poem by Alan Alexander Milne
              What is the matter with Mary Jane?
              She's crying with all her might and main,
              And she won't eat her dinner - rice pudding again -
              What is the matter with Mary Jane?
              What is the matter with Mary Jane?
              I've promised her dolls and a daisy-chain,
              And a book about animals - all in vain -
              What is the matter with Mary Jane?
              What is the matter with Mary Jane?
              She's perfectly well, and she hasn't a pain;
              But, look at her, now she's beginning again! -
              What is the matter with Mary Jane?
              What is the matter with Mary Jane?
              I've promised her sweets and a ride in the train,
              And I've begged her to stop for a bit and explain -
              What is the matter with Mary Jane?
              What is the matter with Mary Jane?
              She's perfectly well and she hasn't a pain,
              And it's lovely rice pudding for dinner again!
              What is the matter with Mary Jane?"""
    import sys

    text = sys.argv[1] if len(sys.argv) > 1 else text
    summary = summerize(text)
    print(summary)
