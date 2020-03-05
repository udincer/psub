# psub
Submit array jobs without all the suffering.

psub provides an intutitive way to submit array jobs on a SGE cluster (particularly UCLA's Hoffman2). Instead of trying to write scripts that generate scripts that in turn gets submitted to the scheduler or dealing with environmental variables, you can do this with psub and forget about the rest:

```
psub --mem 4G --time 12:00:00 "./my_script.py {} {} ::: *.csv ::: arg1 arg2"
```

When run in a folder containing f1.csv, f2.csv and f3.csv, this will submit a job array of 6 jobs for each combination of `arg` and each file, and request 4 GB of memory and 12 hours from the scheduler:
```
./my_script.py f1.csv arg1
./my_script.py f1.csv arg2
./my_script.py f2.csv arg1
./my_script.py f2.csv arg2
./my_script.py f3.csv arg1
./my_script.py f3.csv arg2
```

psub keeps all stdouts and stderrs in a nice tidy directory for each job array. No more accidentally overwriting logs. 

See `psub --help` for all features.

This was psub's command line interface. There is also a Python interface:
```
from psub import Psub
pp = Psub()
for ff, arg in [...]:
  pp.add(f'./my_script.py {ff} {arg}')
pp.submit()
```

psub is still in _alpha_, there will be bugs. 

## Installation:

```
pip install psub
```

psub stands for petko-submit, OG ernstlab member who came up with the core idea.
