#!/bin/bash
#should run as cront job on 1st day of each month
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

echo First Day: 01-$PRVMTH-$PRVYR > /home/odatsrv/tmp/og_analytics_top20info.log
echo Last Day: $LASTDY-$PRVMTH-$PRVYR >> /home/odatsrv/tmp/og_analytics_top20info.log

echo Start Day: 01-$CURMTH-$STARTYR >> /home/odatsrv/tmp/og_analytics_top20info.log

set -e

CATAFILE=/var/www/html/data/od_catalogue/od-do-canada.$PRVYR$PRVMTH$LASTDY.jl.gz
if [ -f $CATAFILE ]
then
  echo found: $CATAFILE >> /home/odatsrv/tmp/og_analytics_top20info.log
else
  wget -q http://open.canada.ca/static/od-do-canada.jl.gz -O $CATAFILE
fi

. /var/www/html/venv/staging-portal/bin/activate

cd /home/odatsrv/tmp
rm -f /tmp/downloads_info.xls
python /home/odatsrv/bin/og_analytics.py  /home/odatsrv/tmp/client_secret_710700207159-chl4rm5p3omk50ssfae1k7bli78m6bhb.apps.googleusercontent.com.json 68455797 /var/www/html/open_gov/staging-portal/ckan/production.ini $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY info >> /home/odatsrv/tmp/og_analytics_top20info.log 2>&1
cp -f /tmp/downloads_info.xls /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.top20Info.xls

wget -q http://open.canada.ca/static/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv -O /tmp/od_ga_by_org_month.csv
wget -q http://open.canada.ca/static/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv -O /tmp/od_ga_month.csv
python /home/odatsrv/bin/og_analytics.py  /home/odatsrv/tmp/client_secret_710700207159-chl4rm5p3omk50ssfae1k7bli78m6bhb.apps.googleusercontent.com.json 68455797 /var/www/html/open_gov/staging-portal/ckan/production.ini $PRVYR-$PRVMTH-01 $PRVYR-$PRVMTH-$LASTDY dataset >> /home/odatsrv/tmp/og_analytics_top20info.log 2>&1
cp -f /tmp/od_ga_by_org_month.csv /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv
cp -f /tmp/od_ga_month.csv /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv
cp -f /tmp/od_ga_by_org.csv /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.datasetsByOrg.bilingual.csv
cp -f /tmp/od_ga_by_country.csv /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.internationalUsageBreakdown.bilingual.csv
cp -f /tmp/od_ga_by_region.csv /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.provincialUsageBreakdown.bilingual.csv
cp -f /tmp/od_ga_top100.csv /var/www/html/data/ckan/open_data/public/static/openDataPortal.siteAnalytics.top100Datasets.bilingual.csv
echo 'static Done' >> /home/odatsrv/tmp/og_analytics_top20info.log

PORTAL_INI=/var/www/html/open_gov/staging-portal/ckan/production.ini
rm -f /tmp/od_ga_downloads.xls
python /home/odatsrv/bin/og_analytics.py  /home/odatsrv/tmp/client_secret_710700207159-chl4rm5p3omk50ssfae1k7bli78m6bhb.apps.googleusercontent.com.json 68455797 /var/www/html/open_gov/staging-portal/ckan/production.ini $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY visit >> /home/odatsrv/tmp/og_analytics_top20info.log 2>&1
mv /tmp/od_ga_downloads.xls /tmp/visits-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
TMPFILE=/tmp/visits-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
ckanapi action resource_patch -c $PORTAL_INI \
	id=c14ba36b-0af5-4c59-a5fd-26ca6a1ef6db upload@"${TMPFILE}"

rm -f /tmp/od_ga_downloads.xls
python /home/odatsrv/bin/og_analytics.py  /home/odatsrv/tmp/client_secret_710700207159-chl4rm5p3omk50ssfae1k7bli78m6bhb.apps.googleusercontent.com.json 68455797 /var/www/html/open_gov/staging-portal/ckan/production.ini $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY download >> /home/odatsrv/tmp/og_analytics_top20info.log 2>&1
mv /tmp/od_ga_downloads.xls /tmp/downloads-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
TMPFILE=/tmp/downloads-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
ckanapi action resource_patch -c $PORTAL_INI \
	id=4ebc050f-6c3c-4dfd-817e-875b2caf3ec6 upload@"${TMPFILE}"
echo 'visits downloads done' >> /home/odatsrv/tmp/og_analytics_top20info.log

#delete datasets
TMPFILE=/tmp/deletedportalds-$PRVMTH$PRVYR.csv
python /home/odatsrv/bin/get_deleted_datasets.py $PORTAL_INI $TMPFILE
ckanapi action resource_patch -c $PORTAL_INI \
	id=d22d2aca-155b-4978-b5c1-1d39837e1993 upload@"${TMPFILE}"
echo 'deleted datasets done' >> /home/odatsrv/tmp/og_analytics_top20info.log

