# psub
Submit array jobs without all the suffering.

psub provides an intutitive way to submit array jobs on a SGE cluster (particularly UCLA's Hoffman2). Instead of trying to write scripts that generate scripts that in turn gets submitted to the scheduler or dealing with environmental variables, you can do this with psub and forget about the rest:

```
psub --mem 4G --time 12:00:00 "./my_script.py -p {} {} ::: p1 p2 p3 ::: arg1 arg2"
```

This will submit a job array with 6 jobs for each combination of `arg` and `p` and request 4 GB of memory and 12 hours from the scheduler:
```
./my_script.py -p p1 arg1
./my_script.py -p p1 arg2
./my_script.py -p p2 arg1
./my_script.py -p p2 arg2
./my_script.py -p p3 arg1
./my_script.py -p p3 arg2
```

psub keeps all stdouts and stderrs in a nice tidy directory for each job array. 

See `psub --help` for all features.

psub is still in _alpha_, there will be bugs. 

## Installation:

```
pip install psub
```

psub stands for petko-submit, OG ernstlab member who came up with the core idea.