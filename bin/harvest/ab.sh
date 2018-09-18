# some simple import steps

set -e

ckanapi dump datasets -r https://open.alberta.ca --all -O alberta.jsonl
# 87036365 Jun 12 14:04 alberta.jsonl
# 92103434 Sep 17 17:50 alberta.jsonl

jq -c 'select(.type=="opendata")' < alberta.jsonl > opendata_ab.jsonl
# 15711286 Jun 12 15:35 opendata_ab.jsonl
# 15785749 Sep 17 14:39 opendata_ab.jsonl

jq -c '.id' < opendata_ab.jsonl | sort > opendata_ab_ids.jsonl
