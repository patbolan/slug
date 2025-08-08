#!/bin/bash

# Exit on any errror
set -e

############
# Add binary folder (for dcm2niix, etc)
# Get the absolute path to the directory where this script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
############

#source ./venv/bin/activate
source $SCRIPT_DIR/venv/bin/activate

# Run the Python script, passing the file path as an argument
python3 $SCRIPT_DIR/app.py --mode=local --data=live

# Deactivate the  environment
deactivate 

