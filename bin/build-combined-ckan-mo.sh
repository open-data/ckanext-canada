#!/bin/bash

set -e

HERE=`dirname $0`
python "$HERE/../setup.py" compile_catalog
