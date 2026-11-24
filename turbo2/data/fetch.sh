#!/usr/bin/env bash
# Fetch all Turbo 2.0 training sources (GitHub + GitHub releases only).
set -uo pipefail
DEST="${1:-/home/user/work/raw}"
mkdir -p "$DEST"; cd "$DEST"
[ -s wiki.gz_00 ] || curl -sSL -C - --max-time 560 -o wiki.gz_00 \
  https://github.com/RaRe-Technologies/gensim-data/releases/download/wiki-english-20171001/wiki-english-20171001.gz_00
clone() {  # repo dir paths...
  local repo="$1" dir="$2"; shift 2
  if [ ! -d "$dir/.git" ]; then
    git clone -q --depth 1 --filter=blob:none --no-checkout "https://github.com/$repo.git" "$dir" || { echo "FAILED $repo"; return; }
  fi
  (cd "$dir" && git checkout HEAD -- "$@") || echo "CHECKOUT FAILED $repo"
}
clone alexa/Topical-Chat Topical-Chat conversations DATALICENSE README.md
clone google-research-datasets/Taskmaster Taskmaster TM-1-2019/self-dialogs.json TM-1-2019/woz-dialogs.json \
  TM-2-2020/data TM-3-2020/data README.md
clone google-research-datasets/dstc8-schema-guided-dialogue dstc8-schema-guided-dialogue train dev LICENSE.txt
clone gururise/AlpacaDataCleaned AlpacaDataCleaned alpaca_data_cleaned.json LICENSE README.md
clone uberspot/OpenTriviaQA OpenTriviaQA categories LICENSE README.md
clone 15Dkatz/official_joke_api official_joke_api jokes LICENCE README.md
clone taivop/joke-dataset joke-dataset stupidstuff.json wocka.json reddit_jokes.json README.md
du -sh "$DEST"/* 
# WordNet: nltk.download refuses proxied fetches, so fetch the same zip nltk uses directly.
mkdir -p "$DEST/../nltk_data/corpora" && (cd "$DEST/../nltk_data/corpora" && [ -d wordnet ] || \
  (curl -sSL -o wordnet.zip https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip && unzip -q -o wordnet.zip))
