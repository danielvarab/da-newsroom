from argparse import Namespace
from os.path import exists
from urllib.parse import urlparse

import regex as re  # stdlib module doesn't support \p{L}
from tqdm import tqdm

from newsroom import jsonl

#############
# Constants #
#############

ASSET_FILES = set(["css", "js", "png", "eot", "tff", "woff", "svg", "jpg", "bmp"])

#############
# /Constants #
#############


def split_dataset(dataset: str, thin_dev: str, thin_test: str):
    # employing convention to reduce number of arguments
    assert dataset.endswith(".dataset"), "dataset name doesn't follow convention"
    assert thin_dev.endswith(".thin"), "..."
    assert thin_test.endswith(".thin"), "..."

    train_out = f"{dataset[:-8]}.train.dataset"
    dev_out = f"{dataset[:-8]}.dev.dataset"
    test_out = f"{dataset[:-8]}.test.dataset"

    for filename in [train_out, dev_out, test_out]:
        assert not exists(filename), "output file (%s) already exist." % filename

    with jsonl.open(thin_dev, gzip=True) as dev_fh:
        dev_ids = set(doc["archive"] for doc in tqdm(dev_fh))

    with jsonl.open(thin_test, gzip=True) as test_fh:
        test_ids = set(doc["archive"] for doc in tqdm(test_fh))

    # Disable formatter as it messes up formatting below. It's take on it ain't pretty.
    # fmt: off
    with jsonl.open(dataset, gzip=True) as dataset_fh,\
         jsonl.open(train_out, gzip=True) as train_out_fh,\
         jsonl.open(dev_out, gzip=True) as dev_out_fh,\
         jsonl.open(test_out, gzip=True) as test_out_fh:
            for doc in tqdm(dataset_fh):
                if doc["archive"] in dev_ids:
                    dev_out_fh.appendline(doc)
                elif doc["archive"] in test_ids:
                    test_out_fh.appendline(doc)
                else:
                    train_out_fh.appendline(doc)

    # fmt: on


def build_thin_from_dataset(dataset: str, thin: str):
    """
    Builds thin-file from dataset-file for distribution. This is useful when a dataset
    already exists and one wishes distribute it in a appropriately legal manor.

    Recall that a thin-file contains metrics and information to download the dataset.
    """
    desired_cols = set(
        [
            "archive",
            "date",
            "density",
            "coverage",
            "compression",
            "compression_bin",
            "coverage_bin",
            "density_bin",
        ]
    )
    with jsonl.open(dataset, gzip=True) as dataset_fh:
        with jsonl.open(thin, gzip=True) as thin_fh:
            for doc in tqdm(dataset_fh):
                thin_entry = {col: doc[col] for col in desired_cols}
                thin_fh.appendline(thin_entry)


def _is_asset(url):
    """Is string an asset such as css, js, fonts or pictures."""
    parsed_uri = urlparse(url)
    path_name = parsed_uri.path.split("/")[-1]
    idx = path_name.find(".")
    if idx > 0:
        return path_name[idx:] in ASSET_FILES

    return False


def _is_hurl(url):
    """
    Determine whether url is a hURL such as the url below. See definition below.
    
    It's defined by matching the below regex on a sequence of (multilingual) alphabettic
    characters delimited by 3 dashs, e.g:

    https://edition.cnn.com/2020/05/25/asia/hong-kong-china-national-security-law-intl-hnk/index.html
    """
    match = re.search(r"(\p{L}+-){3,}", url)
    if match:
        return True

    return False


def filter_urls(urls_file: str, out: str, prop_name: str = "original"):
    """Simple filter heuristic for noisy articles based on a hURL heuristic."""
    with jsonl.open(urls_file, gzip=True) as urls_file_fh:
        with jsonl.open(out, gzip=True) as output_fh:
            for snapshot_entry in tqdm(urls_file_fh):
                url = snapshot_entry[prop_name]
                is_asset = _is_asset(url)
                is_hurl = _is_hurl(url)

                if not is_asset and is_hurl:
                    output_fh.appendline(snapshot_entry)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    # 1st parser
    thin_parser = subparsers.add_parser(
        "build-thin", help="build thin-file from dataset-file"
    )
    thin_parser.add_argument("--dataset", required=True)
    thin_parser.add_argument("--thin", required=True)

    def cmdline_build_thin_from_dataset(args: Namespace):
        """Small wrapper to keep things clean"""
        build_thin_from_dataset(args.dataset, args.thin)

    thin_parser.set_defaults(func=cmdline_build_thin_from_dataset)

    # 2nd parser
    split_parser = subparsers.add_parser(
        "split-dataset", help="split dataset into dev/test/train"
    )

    split_parser.add_argument("--dataset", required=True)
    split_parser.add_argument("--dev", required=True)
    split_parser.add_argument("--test", required=True)

    def cmdline_split_dataset(args: Namespace):
        """Small wrapper to keep things clean"""
        split_dataset(args.dataset, args.dev, args.test)

    split_parser.set_defaults(func=cmdline_split_dataset)

    # 3rd parser
    filter_url_parser = subparsers.add_parser(
        "filter-urls", help="filter urls using basic heuristics"
    )

    filter_url_parser.add_argument("--urls-file", required=True)
    filter_url_parser.add_argument("--out", required=True)

    def cmdline_filter_urls(args: Namespace):
        """Small wrapper to keep things clean"""
        filter_urls(args.urls_file, args.out)

    filter_url_parser.set_defaults(func=cmdline_filter_urls)

    # ====== #

    args = parser.parse_args()
    args.func(args)
