#!/usr/bin/env bash

pandoc -f markdown_github -t rst README.md > README.rst
