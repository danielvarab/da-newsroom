# DaNewsroom - A Large Scale Summarization Dataset for Danish
A summarization dataset created entirely from archived content hosted at archive.org/web. The goal of this dataset was to 1. create a sizeable dataset with 2. high recall. As result of this precision might be lacking and noise will be present.


## 1. Prerequisits
### Code Dependencies
```bash
# python dependencies
pip install -r requirements.txt

# ilp solver for the ICSI system

# macOS
brew install glpk

# linux
apt-get install -y glpk-utils.

# windows isn't tested
```

### Data
We provide dataset freely through "thin files", which are gzip-compressed jsonl files, where each line consists of a sample's URL and measures (but not the summary and article body). The thin files are:

[danewsroom.dev](https://drive.google.com/file/d/1WJ4_kiqu8o10m0rBeDwA85ZIyjoufPyu/view?usp=sharing)
[danewsroom.thin](https://drive.google.com/file/d/1et6SKCtfs3tWjvZWVQ7x9-4YwwdKRhFb/view?usp=sharing)
[danewsroom.test.thin](https://drive.google.com/file/d/1kmVPnfycPT4lHbpoB_MlAm6IfaDYetq2/view?usp=sharing)

Reach out to djam@itu.dk if you'd like the dataset directly. We can not for legal reasons distribute dataset directly.


## 2. Build DaNewsroom (Scrape and Extract)

Use newsroom tool to scrape news articles from archive.org/web. This should take about about 5 days due to throttling.
```bash
newsroom-scrape --thin distributed-data/danewsroom.thin --archive data/danewsroom.archive
```

Use newsroom tool to extract article content from the HTML dumps. This should takes a few hours with a decent amount of CPUs.
```bash
newsroom-extract --archive distributed-data/danewsroom.archive --dataset data/danewsroom.dataset
```

## 3. Run and Evaluate DaNewsroom (split, run and compute ROUGE scores)

Note that while we do provide predefined-splits, we highly encourage you to create your own splits following recent work.
```bash
# Split dataset into train/dev/test
python build/util.py split-dataset --dataset data/danewsroom.dataset --dev data/dev.thin --test data/test.thin

# Run models

mkdir results

# run below with one of the models [gensim-textrank, ilp, oracle, lead-3].
python models/run_summarizer.py --model MODELNAME --dataset data/test.dataset --summaries results/danewsroom.test.MODELNAME.summaries --budget 35 [--parallelize]

# Compute ROGUE scores (here we continue with the textrank example)
# This produces two files:
#   1. *.scores with ROUGE scores for each system summary
#   2. *.rouge with ROUGE scores across the entire dataset
newsroom-score --dataset data/datanewsroom.test.dataset --summaries results/danewsroom.test.MODELNAME.summaries --scores results/danewsroom.test.MODELNAME.scores --rouge 1,2,L --unstemmed > results/danewsroom.test.MODELNAME.rouge

# Compute table with binned meausures
# This takes the *.scores-file and produces a table with ROUGE scores across binned measures (density, compression and coverage)
newsroom-tables --scores results/danewsroom.test.MODELNAME.scores --rouge 1,2,L --variants fscore --bins density,compression,coverage > results/danewsroom.test.MODELNAME.table
```

## 4. Building a similiar dataset for another language
In addition to the distribution of this dataset, we wished to enable others to create a similar dataset. Following the procedure described in this paper, constructing a dataset consists of 5 steps:
1. Curate a list of sites and collect URLs from archive.org through their CDX server ([link to documentation](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server))
2. Filter out assets and keep hURLs
3. Download snapshots from URL collection and extract article content
4. Domain specific quality control

We distribute tooling for all steps apart from domain specific quality control and describe them below. In the below example we'll consider a single domain dr.dk.

### 4.1. Collect URLs
```bash
# Collect URLs for domain. This outputs to a file called dr.dk.jsonl.gz
scrapy runspider build/snapshots_spider.py -a domain=dr.dk

# Inspect URL count
# MacOS
zcat < dr.dk.jsonl.gz | wc -l

# Linux
zcat dr.dk.jsonl.gz | wc -l
```

### 4.2. Filter URLs
```bash
# basic filtering based on filtering out assets and restricting URLs to hURLs.
# this script assumes no duplicated URLs.
python build/util.py filter-urls --urls-file dr.dk.jsonl.gz --out dr.dr.filtered.jsonl.gz
```

### 4.3 Download snapshots (same as section 2)
```bash
newsroom-scrape --thin dr.dr.filtered.jsonl.gz --archive dr.dk.archive

newsroom-extract --archive dr.dk.archive --dataset dr.dk.dataset
```

### 4.4. Domain specific quality control on extracted articles
As described in the paper, this work filters out documents that have:
- Empty summaries/bodies
- Non-unique summaries/bodies
- Compression measure less than 1.5


# F.A.Q.
## 1. "Cannot open exception db file for reading: data/WordNet-2.0.exc.db"
Check out [https://github.com/masters-info-nantes/ter-resume-auto/blob/master/README.md](https://github.com/masters-info-nantes/ter-resume-auto/blob/master/README.md)

Notice that the ROUGE perl script is embedded in the newsroom distribution which is in this repository (`newsroom-lib/newsroom/analyze/rouge/ROUGE-1.5.5`)

## 2. What are thin/archive/files?
In this repo. we refer to three types of files: thin, archive, and dataset-files. These are all simply compressed JSONL-files wihch can be inspected using `zless` or programmatically:

```python
from newsroom import jsonl
with jsonl.open(FILENAME, gzip=True) as filehandler:
    for row in filehandler:
        # row is dictionary
        ...
```

# Bibtex
```
@inproceedings{varab-schluter-2020-danewsroom,
    title = "{D}a{N}ewsroom: A Large-scale {D}anish Summarisation Dataset",
    author = "Varab, Daniel  and
      Schluter, Natalie",
    booktitle = "Proceedings of The 12th Language Resources and Evaluation Conference",
    month = may,
    year = "2020",
    address = "Marseille, France",
    publisher = "European Language Resources Association",
    url = "https://www.aclweb.org/anthology/2020.lrec-1.831",
    pages = "6731--6739",
    abstract = "Dataset development for automatic summarisation systems is notoriously English-oriented. In this paper we present the first large-scale non-English language dataset specifically curated for automatic summarisation. The document-summary pairs are news articles and manually written summaries in the Danish language. There has previously been no work done to establish a Danish summarisation dataset, nor any published work on the automatic summarisation of Danish. We provide therefore the first automatic summarisation dataset for the Danish language (large-scale or otherwise). To support the comparison of future automatic summarisation systems for Danish, we include system performance on this dataset of strong well-established unsupervised baseline systems, together with an oracle extractive summariser, which is the first account of automatic summarisation system performance for Danish. Finally, we make all code for automatically acquiring the data freely available and make explicit how this technology can easily be adapted in order to acquire automatic summarisation datasets for further languages.",
    language = "English",
    ISBN = "979-10-95546-34-4",
}
```
