#!/bin/bash
for i in {1..5}
do
   echo 'wget' "$@"
   wget "$@"
   if [ $? == 0 ]
   then
     exit 0
   fi
   sleep 1
done
echo 'error wget' "$@"
exit -1
