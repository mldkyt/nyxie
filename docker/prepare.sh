#!/bin/bash


GIT_VERSION=$(git describe --long --tags || "dirty")

sed -i "s/@VERSION@/$GIT_VERSION/g" constants.py
