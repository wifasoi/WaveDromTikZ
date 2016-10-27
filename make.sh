#!/usr/bin/env bash

# Create output directory
mkdir -p bld

# Generate pdf
pdflatex --enable-pipes --shell-escape --output-directory=bld examples/hitchhikers_guide_to_wavedromtikz.tex

