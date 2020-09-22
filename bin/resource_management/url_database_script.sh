#!/bin/bash
set `date +%U" "%u`
CURWK=$1
DAY=$2
if [ $(($CURWK%2)) -eq 0 ] && [ $DAY -eq 1 ]
then wget http://open.canada.ca/static/od-do-canada.jl.gz
gzip -d od-do-canada.jl.gz
python url_database.py od-do-canada.jl 500 data/url_database_draft.csv
python url_database.py data/url_database_draft.csv 200 data/url_database.csv
rm data/url_database_draft.csv
python url_metadata_match.py od-do-canada.jl data/url_database.csv
rm od-do-canada.jl
fi
