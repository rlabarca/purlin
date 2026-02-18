#!/bin/bash
# start.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_EXE="python3"

# Check if we are in a virtualenv
if [ -d "$DIR/../../.venv" ]; then
    PYTHON_EXE="$DIR/../../.venv/bin/python3"
elif [ -d "$DIR/../../../.venv" ]; then
     PYTHON_EXE="$DIR/../../../.venv/bin/python3"
fi

nohup $PYTHON_EXE $DIR/serve.py > $DIR/software_map.log 2>&1 &
echo $! > $DIR/software_map.pid
echo "Software Map Viewer started (PID: $(cat $DIR/software_map.pid))"
