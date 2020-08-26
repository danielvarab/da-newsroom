"""DEPRECATED (use newsroom tooling for downloading snapshots)"""
import gzip
import json
import logging
from urllib.parse import urlencode

import requests
import scrapy
from tqdm import tqdm

URL_TEMPLATE = "https://web.archive.org/web/%s_id/%s"
API_ENDPOINT = "https://web.archive.org/cdx/search/cdx?"
DEFAULT_PARAMS = [
    # ("fl", "timestamp,original"),
    ("collapse", "urlkey"),
    ("output", "json"),
    ("filter", "mimetype:text/html"),
    ("filter", "statuscode:200"),
    ("matchType", "domain"),
]
CDX_COLUMN_NAMES = [
    "urlkey",
    "timestamp",
    "original",
    "mimetype",
    "statuscode",
    "digest",
    "length",
]


class CdxSpider(scrapy.Spider):
    name = "archive_spider"

    # Caches results for development
    HTTPCACHE_ENABLED = True

    # Auto throttle will not go below DOWNLOAD_DELAY
    download_delay = 0.25

    USER_AGENT = "NLP Research @ IT University of Copenhagen (djam@itu.dk)"

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)  # python3
        self.domain = kwargs["domain"]
        assert "/" not in self.domain, "domain should be a domain. no paths allowed."

        self.out = f"{self.domain}.jsonl.gz"
        self.start = kwargs.get("start")
        self.logger.setLevel(logging.INFO)

    def start_requests(self):
        parameters = DEFAULT_PARAMS.copy()
        parameters.append(("showNumPages", True))
        parameters.append(("pageSize", 1))
        parameters.append(("url", self.domain))
        url = API_ENDPOINT + urlencode(parameters)

        logging.info("Preparing to scrape the domain: %s" % self.domain)
        try:
            # archive.org's CDX server throws a 445 if User-Agent isn't specified
            response = requests.get(url, headers={"User-Agent": self.USER_AGENT})
            n_pages = int(response.text)
        except:
            self.logger.critical("Couldn't retrieve initial cdx page count.")
            self.logger.critical(url)
            raise

        start = int(self.start) if self.start else 0

        logging.info("Starting scraper from page %d" % start)

        self.pbar = tqdm(total=n_pages, initial=start)

        for page_n in range(start, n_pages + 1):
            page_params = DEFAULT_PARAMS.copy()
            page_params.append(("url", self.domain))
            page_params.append(("page", page_n))
            url = API_ENDPOINT + urlencode(page_params)
            yield scrapy.Request(url=url, callback=self.parse, errback=self.error)

    def parse(self, response):
        self.pbar.update()

        if not response.body:
            return

        body = json.loads(response.body)
        with gzip.open(self.out, mode="at", compresslevel=9) as output_file:
            for entry in body:
                archive_entry = {cn: ec for cn, ec in zip(CDX_COLUMN_NAMES, entry)}
                archive_entry["archive"] = URL_TEMPLATE % (
                    archive_entry["timestamp"],
                    archive_entry["original"],
                )
                output_file.write(json.dumps(archive_entry) + "\n")

    def error(self, response):
        self.logger.critical("Hitting request limit, sleeping for 30 seconds.")
