#!/bin/bash
dir=$1
cd $dir
. recipients.config
wget http://open.canada.ca/static/od-do-canada.jl.gz
gzip -d od-do-canada.jl.gz
source $venv
python url_database.py od-do-canada.jl 500 data/url_database_draft.csv
python url_database.py data/url_database_draft.csv 200 data/url_database.csv
rm data/url_database_draft.csv
python url_metadata_match.py od-do-canada.jl data/url_database.csv
rm od-do-canada.jl
the_date=$(date +"%Y-%m-%d")
mail -s "Broken_Resource_Links-$the_date.xlsx" -a reports/Broken_Resource_Links-$the_date.xlsx $recipients < email_message.txt