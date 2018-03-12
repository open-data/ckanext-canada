#!/bin/bash
#should run as cront job on 1st day of each month

: ${CLIENT_SECRET:=/project/client_secret.json}
: ${PORTAL_INI:=/project/development.ini}
: ${STATIC_DIR:=/project/public}
: ${LOG_DIR:=/project/ga/logs}
: ${WORK_DIR:=/project/ga/tmp}

set -e

mkdir -p $LOG_DIR
mkdir -p $WORK_DIR

read CURYR CURMTH < <(python -c'from datetime import date; print date.today().strftime("%Y %m")')
read PRVYR PRVMTH LASTDY < <(python -c'from datetime import date,timedelta; print (date(date.today().year, date.today().month, 1) - timedelta(1)).strftime("%Y %m %d")')

echo First Day: 01-$PRVMTH-$PRVYR > $LOG_DIR/og_analytics_top20info.log
echo Last Day: $LASTDY-$PRVMTH-$PRVYR >> $LOG_DIR/og_analytics_top20info.log

echo Start Day: 01-$CURMTH-$STARTYR >> $LOG_DIR/og_analytics_top20info.log

CATAFILE=$STATIC_DIR/od-do-canada.$PRVYR$PRVMTH$LASTDY.jl.gz
if [ -f $CATAFILE ]
then
  echo found: $CATAFILE >> $LOG_DIR/og_analytics_top20info.log
else
  wget -q https://open.canada.ca/static/od-do-canada.jl.gz -O $CATAFILE
fi


rm -f $WORK_DIR/downloads_info.xls
python $(dirname $0)/og_analytics.py $CLIENT_SECRET 68455797 $PORTAL_INI $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY info >> $LOG_DIR/og_analytics_top20info.log 2>&1
cp -f $WORK_DIR/downloads_info.xls $STATIC_DIR/openDataPortal.siteAnalytics.top20Info.xls

wget -q https://open.canada.ca/static/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv -O $WORK_DIR/od_ga_by_org_month.csv
wget -q https://open.canada.ca/static/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv -O $WORK_DIR/od_ga_month.csv
python og_analytics.py  $CLIENT_SECRET 68455797 $PORTAL_INI $PRVYR-$PRVMTH-01 $PRVYR-$PRVMTH-$LASTDY dataset >> $LOG_DIR/og_analytics_top20info.log 2>&1
cp -f $WORK_DIR/od_ga_by_org_month.csv $STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv
cp -f $WORK_DIR/od_ga_month.csv $STATIC_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv
cp -f $WORK_DIR/od_ga_by_org.csv $STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrg.bilingual.csv
cp -f $WORK_DIR/od_ga_by_country.csv $STATIC_DIR/openDataPortal.siteAnalytics.internationalUsageBreakdown.bilingual.csv
cp -f $WORK_DIR/od_ga_by_region.csv $STATIC_DIR/openDataPortal.siteAnalytics.provincialUsageBreakdown.bilingual.csv
cp -f $WORK_DIR/od_ga_top100.csv $STATIC_DIR/openDataPortal.siteAnalytics.top100Datasets.bilingual.csv
echo 'static Done' >> $LOG_DIR/og_analytics_top20info.log

rm -f $WORK_DIR/od_ga_downloads.xls
python $(dirname $0)/og_analytics.py $CLIENT_SECRET 68455797 $PORTAL_INI $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY visit >> $LOG_DIR/og_analytics_top20info.log 2>&1
mv $WORK_DIR/od_ga_downloads.xls $WORK_DIR/visits-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
TMPFILE=$WORK_DIR/visits-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
ckanapi action resource_patch -c $PORTAL_INI \
	id=c14ba36b-0af5-4c59-a5fd-26ca6a1ef6db upload@"${TMPFILE}"

rm -f $WORK_DIR/od_ga_downloads.xls
python $(dirname $0)/og_analytics.py $CLIENT_SECRET 68455797 $PORTAL_INI $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY download >> $LOG_DIR/og_analytics_top20info.log 2>&1
mv $WORK_DIR/od_ga_downloads.xls $WORK_DIR/downloads-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
TMPFILE=$WORK_DIR/downloads-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
ckanapi action resource_patch -c $PORTAL_INI \
	id=4ebc050f-6c3c-4dfd-817e-875b2caf3ec6 upload@"${TMPFILE}"
echo 'visits downloads done' >> $LOG_DIR/og_analytics_top20info.log

#delete datasets
TMPFILE=$WORK_DIR/deletedportalds-$PRVMTH$PRVYR.csv
python $(dirname $0)/get_deleted_datasets.py $PORTAL_INI $TMPFILE
ckanapi action resource_patch -c $PORTAL_INI \
	id=d22d2aca-155b-4978-b5c1-1d39837e1993 upload@"${TMPFILE}"
echo 'deleted datasets done' >> $LOG_DIR/og_analytics_top20info.log

