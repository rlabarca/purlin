#!/bin/bash
# stop.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
if [ -f $DIR/software_map.pid ]; then
    PID=$(cat $DIR/software_map.pid)
    kill $PID
    rm $DIR/software_map.pid
    echo "Software Map Viewer stopped (PID: $PID)"
else
    echo "Software Map Viewer is not running (no software_map.pid found)"
fi
