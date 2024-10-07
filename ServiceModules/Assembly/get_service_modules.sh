#!/bin/bash

# Minimal launcher for the Shoestring Assembler

# What version of the Assembler to use
VERSION="v0.4.0"

# Get location of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Download Shoestring Assembler
echo "Downloading Shoestring Assembler" $VERSION
git clone --quiet https://github.com/DigitalShoestringSolutions/ShoestringAssembler -b $VERSION $SCRIPT_DIR/ShoestringAssembler

# Run Shotestring Assembler
echo "Running Shoestring Assembler..."
$SCRIPT_DIR/ShoestringAssembler/assemble.sh
