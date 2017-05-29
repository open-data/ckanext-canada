#!/bin/bash
source $HOME/.bashrc

set -e

wget -O /tmp/od-do-canada.jl.gz http://open.canada.ca/static/od-do-canada.jl.gz

rm -rf /tmp/od_linkcheker2.db
TMPDIR="/home/odatsrv/tmp"
(time python3 /home/odatsrv/bin/link_check.py --file=/tmp/od-do-canada.jl.gz ) > "${TMPDIR}/link_check.log" 2>&1
sleep 30
(time python3 /home/odatsrv/bin/link_check.py --file=/tmp/od-do-canada.jl.gz --quick ) > "${TMPDIR}/link_check.log2" 2>&1
sleep 30
(time python3 /home/odatsrv/bin/link_check.py --file=/tmp/od-do-canada.jl.gz --quick ) > "${TMPDIR}/link_check.log3" 2>&1
sleep 30
(time python3 /home/odatsrv/bin/link_check.py --file=/tmp/od-do-canada.jl.gz --quick ) > "${TMPDIR}/link_check.log4" 2>&1

(time python3 /home/odatsrv/bin/link_check.py --file=/tmp/od-do-canada.jl.gz --dump="${TMPDIR}/brokenlink.csv" )  > "${TMPDIR}/link_dump.log" 2>&1
. /var/www/html/venv/rc_reg/bin/activate
ckanapi action resource_patch -c /var/www/html/rc_reg/ckan/production-cli.ini \
	id=1f1b0e53-40cc-4900-a08a-e5595697aaea upload@"${TMPDIR}/brokenlink.csv"
