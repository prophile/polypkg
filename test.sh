#!/bin/bash
set -e
if [ -n "$1" ]; then
    echo "Testing package $1..."
    ./polypkg "$1"
    rm -rf components
else
    if [ -e components ]; then
        echo "Aborting, components file exists"
        exit 1
    fi
    PACKAGES=$(grep '^[^ ]' packages.yaml | sed 's/://')
    for PACKAGE in $PACKAGES
    do
        "$0" "$PACKAGE"
    done
fi

