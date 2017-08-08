#!/bin/bash
set `date +%m" "%Y`
CURMTH=$1
CURYR=$2

if [ $CURMTH -eq 1 ]
then PRVMTH=12
     PRVYR=`expr $CURYR - 1`
     STARTYR=$PRVYR
else PRVMTH=`expr $CURMTH - 1`
     PRVYR=$CURYR
     STARTYR=`expr $CURYR - 1`
fi


if [ $PRVMTH -lt 10 ]
then PRVMTH="0"$PRVMTH
fi


LASTDY=`cal $PRVMTH $PRVYR | egrep "28|29|30|31" |tail -1 |awk '{print $NF}'`

echo First Day: 01-$PRVMTH-$PRVYR
echo Last Day: $LASTDY-$PRVMTH-$PRVYR

echo Start Day: 01-$CURMTH-$STARTYR

set -e
. /var/www/html/venv/staging-portal/bin/activate

cd /home/odatsrv/tmp
rm -f /tmp/downloads_info.xls
python /home/odatsrv/bin/og_analytics.py  /home/odatsrv/tmp/client_secret_710700207159-chl4rm5p3omk50ssfae1k7bli78m6bhb.apps.googleusercontent.com.json 68455797 /var/www/html/open_gov/staging-portal/ckan/production.ini $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY info > /home/odatsrv/tmp/og_analytics_top20info.log 2>&1
cp /tmp/downloads_info.xls /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.top20Info.xls
