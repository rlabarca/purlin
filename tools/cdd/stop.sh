#!/bin/bash
# stop.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
if [ -f $DIR/cdd.pid ]; then
    PID=$(cat $DIR/cdd.pid)
    kill $PID
    rm $DIR/cdd.pid
    echo "CDD Monitor stopped (PID: $PID)"
else
    echo "CDD Monitor is not running (no cdd.pid found)"
fi
