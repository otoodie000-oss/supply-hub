#!/usr/bin/env bash
# Fetch the open-licensed English dialogue datasets used for stage-1 training.
# All are hosted on GitHub. In the build environment codeload/api.github.com were
# blocked but `git clone` worked, so we use shallow blobless clones + targeted checkouts.
#
#   Topical-Chat                 alexa/Topical-Chat                          CDLA-Sharing-1.0
#   Synthetic-Persona-Chat       google-research-datasets/Synthetic-Persona-Chat   CC BY 4.0
#   Taskmaster-1/2/3             google-research-datasets/Taskmaster         CC BY 4.0
#   Schema-Guided Dialogue       google-research-datasets/dstc8-schema-guided-dialogue  CC BY-SA 4.0
#   MultiWOZ 2.2                 budzianowski/multiwoz                       MIT
set -euo pipefail
DEST="${1:-/home/user/data_raw}"
mkdir -p "$DEST"
cd "$DEST"

clone() {  # repo dir paths...
  local repo="$1" dir="$2"; shift 2
  if [ ! -d "$dir/.git" ]; then
    git clone -q --depth 1 --filter=blob:none --no-checkout "https://github.com/$repo.git" "$dir"
  fi
  (cd "$dir" && git checkout HEAD -- "$@")
}

clone alexa/Topical-Chat Topical-Chat conversations DATALICENSE README.md
clone google-research-datasets/Synthetic-Persona-Chat Synthetic-Persona-Chat data README.md
clone google-research-datasets/Taskmaster Taskmaster \
  TM-1-2019/self-dialogs.json TM-1-2019/woz-dialogs.json TM-1-2019/README.md \
  TM-2-2020/data TM-2-2020/README.md TM-3-2020/data TM-3-2020/README.md
clone google-research-datasets/dstc8-schema-guided-dialogue dstc8-schema-guided-dialogue train dev LICENSE.txt
clone budzianowski/multiwoz multiwoz data/MultiWOZ_2.2/train data/MultiWOZ_2.2/dev LICENSE

du -sh "$DEST"/*
