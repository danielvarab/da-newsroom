import typing
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

from gensim.summarization import summarize as gensim_summerizer
from tqdm import tqdm

from icsi.run import make_summary as ilp_summerizer
from newsroom import jsonl
from wrappers import fragments_oracle, lead_3


class SafeSummerizer:
    """Wrap summarizer """

    def __init__(self, callable_model: typing.Callable, budget: int):
        self.model = callable_model
        self.budget = budget

    def __call__(self, text):
        try:
            return self.model(text, word_count=self.budget)
        except:
            return text


##############################################
# Multiprocessing params. Hardcoded for now. #
##############################################
WORKERS = cpu_count()
CHUNK_SIZE = WORKERS * 20


MODELS = {
    # NOTE: Top 4 models used in (Varab & Scluter 2019)
    # stems and splits sentence with porter and simple regex splitter
    "gensim-textrank": gensim_summerizer,
    # ICSI system with gensim sentence splitter
    "ilp": ilp_summerizer,
    "oracle": fragments_oracle,
    "lead-3": lead_3,

    ################

    # NOTE: Below models for future work - WIP.
    # Alt. implementation of above ILP system. Also supports multiple solvers and various greedy aproximations
    # Concept-based Summarization using Integer Linear Programming: From Concept Pruning to Multiple Optimal Solutions
    # https://www.aclweb.org/anthology/D15-1220.pdf
    # uses english (porter) stemmer and english sentence splitting (splitta)
    # "sume_ilp": sume_ilp,
    # generalized gensim implementation with naïve split and lemmatization
    # "textrank": textrank_summarizer,
}


def run(dataset: str, summaries_file: str, model: typing.Callable, budget: int):
    model = SafeSummerizer(model, budget)
    with jsonl.open(dataset, gzip=True) as dataset_fh:
        with jsonl.open(summaries_file, gzip=True) as summaries_fh:
            summaries_fh.delete()  # clean out output file
            progressbar = tqdm()
            for document in dataset_fh:
                summary = model(document)
                summaries_fh.appendline({"system": summary})
                progressbar.update()


def run_parallel(dataset: str, summaries: str, model: typing.Callable, budget: int):
    model = SafeSummerizer(model, budget)
    with jsonl.open(dataset, gzip=True) as dataset_fh:
        with jsonl.open(summaries, gzip=True) as summaries_fh:
            summaries_fh.delete()  # clean out output file
            progressbar = tqdm()

            chunk = []
            for document in dataset_fh:
                chunk.append(document)

                if len(chunk) >= CHUNK_SIZE:
                    with ProcessPoolExecutor(WORKERS) as pool:
                        results = pool.map(model, chunk)
                        results = list(results)
                        for summary in results:
                            summaries_fh.appendline({"system": summary})
                        chunk = []

                    progressbar.update(len(results))


if __name__ == "__main__":
    import argparse

    import os.path

    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, required=True, help="token budget")
    parser.add_argument("--model", help="gensim_textrank/textrank/ilp", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--summaries", required=True)
    parser.add_argument("--parallelize", action="store_true")

    # ILP specific parameters model.
    # Parameters to optimize w.r.t ROUGE properties.
    # parser.add_argument("--unigrams", action="store_true", help="optimize R1")
    # parser.add_argument("--bigrams", action="store_true", help="optimize R2")
    # parser.add_argument("--trigrams", action="store_true", help="optimize R3")
    # parser.add_argument("--fourgrams", action="store_true", help="optimize R4")
    # parser.add_argument("--su4", action="store_true", help="optimising w.r.t. SU4")

    args = parser.parse_args()

    # NOTE: Be weary about the meaning of budget.
    # It refers to the total token count in the summary across sentences.
    # This is noted as older literature refers to this in terms of bytes. Which is at
    # character level, as opposed to token level. This obv. has the implication that
    # we have a common ground for tokenization across models.

    assert os.path.exists(args.dataset), "Dataset file %s doesn't exist" % args.dataset

    model = MODELS[args.model]

    if args.parallelize:
        print(f"running {args.model} in parallelized-mode")
        run_parallel(args.dataset, args.summaries, model, args.budget)
    else:
        run(args.dataset, args.summaries, model, args.budget)
