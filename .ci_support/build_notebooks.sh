#!/bin/bash
# Select ipykernelt
if [ "$PYTHONVER" = "2.7" ]; then
    kernel="python2"
else
    kernel="python3"
fi;

# execute notebooks
i=0;
for notebook in $(ls *.ipynb); do 
    papermill ${notebook} ${notebook%.*}-out.${notebook##*.} -k $kernel || i=$((i+1));
done;

# push error to next level
if [ $i -gt 0 ]; then
    exit 1;
fi;
