# some simple import steps

set -e

ckanapi dump datasets -r https://open.alberta.ca --all -O alberta.jsonl
# 87036365 Jun 12 14:04 alberta.jsonl

jq -c 'select(.type=="opendata")' < alberta.jsonl > opendata_ab.jsonl
# 15711286 Jun 12 15:35 opendata_ab.jsonl


