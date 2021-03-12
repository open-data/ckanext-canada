#!/bin/bash

### REQUIRED ENVIRONMENT VARIABLES
#
# Note: Before running this script, the shell following Environment  variables need to be set
#
# GA_CLIENT_SECRET path to GA secrets file
# GA_PORTAL_INI path to the CKAN portal ini file
# GA_ARCHIVE_ROOT path to base archive driectory
# GA_STATIC_DIR path to the directory where static files as stored for the web server
# GA_VENV_SCRIPT path to script to activate the python virtual environment for this script
# GA_OG_ANALYTICS path to the analytics scripts in the CKAN Canada extension
# GA_TMP_DIR temporary directory used by this script and og_analytics.py
# GA_DELETE_DS path to the get_deleted_datasets.py script in the CKAN Canada extension
# GA_LOG_DIR Directory for the og files produced by this script
#
###

GA_LOG_FILE=$GA_LOG_DIR/og_analytics.log

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

LASTDY=$(cal $PRVMTH $PRVYR | egrep "28|29|30|31" |tail -1 |awk '{print $NF}')

echo First Day: 01-$PRVMTH-$PRVYR > $GA_LOG_FILE
echo Last Day: $LASTDY-$PRVMTH-$PRVYR >> $GA_LOG_FILE
echo Start Day: 01-$CURMTH-$STARTYR >> $GA_LOG_FILE

set -e

CATAFILE=$GA_STATIC_DIR/od-do-canada.$PRVYR$PRVMTH$LASTDY.jl.gz
if [ -f $CATAFILE ]
then
  echo found: $CATAFILE >> "$GA_LOG_FILE"
else
  cp $GA_STATIC_DIR/od-do-canada.jl.gz "$CATAFILE"
fi

# backup the file from previous month
GA_ARCHIVE_DIR=$GA_ARCHIVE_ROOT/$PRVYR-$PRVMTH-$LASTDY
mkdir -p $GA_ARCHIVE_DIR
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.top20Info.xls ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.top20Info.xls $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.top20Info.xls
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrg.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrg.bilingual.csv $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.datasetsByOrg.bilingual.csv
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.internationalUsageBreakdown.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.internationalUsageBreakdown.bilingual.csv $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.internationalUsageBreakdown.bilingual.csv
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.provincialUsageBreakdown.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.provincialUsageBreakdown.bilingual.csv $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.provincialUsageBreakdown.bilingual.csv
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.top100Datasets.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.top100Datasets.bilingual.csv $GA_ARCHIVE_DIR/openDataPortal.siteAnalytics.top100Datasets.bilingual.csv
fi

# shellcheck source=venv/bin/activate
source $GA_VENV_SCRIPT

cd $GA_TMP_DIR
rm -f $GA_TMP_DIR/downloads_info.xls
python $GA_OG_ANALYTICS \
    $GA_CLIENT_SECRET 68455797 $GA_PORTAL_INI \
    $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY info #\
#    >> $GA_LOG_FILE 2>&1
cp -f $GA_TMP_DIR/downloads_info.xls $GA_STATIC_DIR/openDataPortal.siteAnalytics.top20Info.xls

# Note, this script will actually fail if these csv files are not present
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv $GA_TMP_DIR/od_ga_by_org_month.csv
else
  echo "Cannot find openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv"
  exit
fi
if [ -f $GA_STATIC_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv ]; then
  cp $GA_STATIC_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv $GA_TMP_DIR/od_ga_month.csv
else
  echo "Cannot find openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv"
  exit
fi

python $GA_OG_ANALYTICS \
    $GA_CLIENT_SECRET 68455797 $GA_PORTAL_INI \
    $PRVYR-$PRVMTH-01 $PRVYR-$PRVMTH-$LASTDY dataset \
    >> $GA_LOG_FILE 2>&1
cp -f $GA_TMP_DIR/od_ga_by_org_month.csv $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrgByMonth.bilingual.csv
cp -f $GA_TMP_DIR/od_ga_month.csv $GA_STATIC_DIR/openDataPortal.siteAnalytics.totalMonthlyUsage.bilingual.csv
cp -f $GA_TMP_DIR/od_ga_by_org.csv $GA_STATIC_DIR/openDataPortal.siteAnalytics.datasetsByOrg.bilingual.csv
cp -f $GA_TMP_DIR/od_ga_by_country.csv $GA_STATIC_DIR/openDataPortal.siteAnalytics.internationalUsageBreakdown.bilingual.csv
cp -f $GA_TMP_DIR/od_ga_by_region.csv $GA_STATIC_DIR/openDataPortal.siteAnalytics.provincialUsageBreakdown.bilingual.csv
cp -f $GA_TMP_DIR/od_ga_top100.csv $GA_STATIC_DIR/openDataPortal.siteAnalytics.top100Datasets.bilingual.csv
echo 'static Done' >> $GA_LOG_FILE

rm -f $GA_TMP_DIR/od_ga_downloads.xls
python $GA_OG_ANALYTICS \
    $GA_CLIENT_SECRET 68455797 $GA_PORTAL_INI \
    $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY visit \
    >> $GA_LOG_FILE 2>&1
mv $GA_TMP_DIR/od_ga_downloads.xls $GA_ARCHIVE_DIR/visits-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
TMPFILE=$GA_TMP_DIR/visits-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
ckanapi action resource_patch -c $GA_PORTAL_INI \
	id=c14ba36b-0af5-4c59-a5fd-26ca6a1ef6db upload@"${TMPFILE}"

rm -f $GA_TMP_DIR/od_ga_downloads.xls
python $GA_OG_ANALYTICS \
    $GA_CLIENT_SECRET 68455797 $GA_PORTAL_INI \
    $STARTYR-$CURMTH-01 $PRVYR-$PRVMTH-$LASTDY download \
    >> $GA_LOG_FILE 2>&1
mv $GA_TMP_DIR/od_ga_downloads.xls $GA_ARCHIVE_DIR/downloads-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
TMPFILE=$GA_TMP_DIR/downloads-$PRVMTH$STARTYR-$PRVMTH$PRVYR.xls
ckanapi action resource_patch -c $GA_PORTAL_INI \
	id=4ebc050f-6c3c-4dfd-817e-875b2caf3ec6 upload@"${TMPFILE}"
echo 'visits downloads done' >> "$GA_LOG_FILE"

#delete datasets
TMPFILE=$GA_TMP_DIR/deletedportalds-$PRVMTH$PRVYR.csv
python $GA_DELETE_DS $GA_PORTAL_INI $TMPFILE
ckanapi action resource_patch -c $GA_PORTAL_INI \
	id=d22d2aca-155b-4978-b5c1-1d39837e1993 upload@"${TMPFILE}"
echo 'deleted datasets done' >> "$GA_LOG_FILE"

