#!/bin/bash
source $HOME/.bashrc
CONFIG=$1
set -e

ckanapi action resource_patch -c $CONFIG \
        id=12b79506-4d48-484a-9ed2-6e6ea13a08af upload@"./dq170529b-eng.pdf"
ckanapi action resource_patch -c $CONFIG \
        id=0b7d08d3-a6b2-4800-bd15-4b1cac4e4233 upload@"./dq170529a-eng.pdf"
ckanapi action resource_patch -c $CONFIG \
        id=ff58ac0f-f95f-4fb0-8674-f19fa21847ad upload@"./dq170529c-eng.pdf"
ckanapi action resource_patch -c $CONFIG \
        id=758bff28-84fd-4ea7-9b70-5323aec7f61f upload@"./dq170529d-eng.pdf"
