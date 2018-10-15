# some simple import steps

set -e

ckanapi dump datasets -r https://open.alberta.ca --all -O alberta.jsonl
# 87036365 Jun 12 14:04 alberta.jsonl
# 92103434 Sep 17 17:50 alberta.jsonl

jq -c 'select(.type=="opendata")' < alberta.jsonl > opendata_ab.jsonl
# 15711286 Jun 12 15:35 opendata_ab.jsonl
# 15785749 Sep 17 14:39 opendata_ab.jsonl


jq -c '.id' < opendata_ab.jsonl | sort > opendata_ab_ids.jsonl
# 95355 Sep 17 14:42 opendata_ab_ids.jsonl


:>results.jsonl
for a in `seq 0 1000 2000`; do
    ckanapi -r https://open.canada.ca/data action package_search q=organization:ab fl=id rows=1000 start=$a -j | jq -c '.results[].id' >> results.jsonl
done
sort < results.jsonl | uniq > existing_ab_ids.jsonl
# 78858 Sep 19 12:29 existing_ab_ids.jsonl


comm -23 existing_ab_ids.jsonl opendata_ab_ids.jsonl > delete_ids.jsonl
# 39 Sep 19 12:34 delete_ids.jsonl

ckanapi delete datasets -I delete_ids.json
