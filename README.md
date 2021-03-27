# psub
![badge](https://github.com/udincer/psub/actions/workflows/python-package.yml/badge.svg)

Submit and monitor array jobs on Hoffman2 with minimal configuration and suffering. 

psub provides an intuitive way to submit array jobs on UCLA's Hoffman2 compute cluster and monitor their output logs. Instead of trying to write scripts that generate scripts that in turn gets submitted to the scheduler or dealing with environmental variables, you can do this with psub and forget about the rest:

```bash
psub --mem 4G --time 12:00:00 "./my_script.sh {} --argument {} ::: *.csv ::: arg1 arg2"
```

When run in a folder containing f1.csv, f2.csv and f3.csv, this will submit a job array of 6 jobs for each combination of `arg` and each file, and request 4 GB of memory and 12 hours from the scheduler:
```bash
./my_script.sh f1.csv --argument arg1
./my_script.sh f1.csv --argument arg2
./my_script.sh f2.csv --argument arg1
./my_script.sh f2.csv --argument arg2
./my_script.sh f3.csv --argument arg1
./my_script.sh f3.csv --argument arg2
```

psub keeps all stdouts and stderrs nice and tidy. You can view logs associated with a particular job with the `psub logs` subcommand.

See `psub --help` for all features.

There is also a Python programmatic interface:
```python
from psub import Psub

pp = Psub(name="big_job",
          l_arch="intel*",
          l_mem="4G", 
          l_time="1:00:00", 
          l_highp=True)

for i in range(3):
    pp.add(f"echo hi {i}")  # add individually

# or add parameter combinations in one go
pp.add_parameter_combinations(
    "./my_script.sh {} --argument {}", 
    ["f1.csv", "f2.csv", "f3.csv"], ["arg1", "arg2"]
)

pp.submit()  # submit jobs

pp.status  # view job status
pp.exit_codes  # view exit codes of individual jobs

pp.rerun_failed()  # rerun any failed jobs (TBA)
```

psub is still in alpha, please let me know of any bugs.

psub is for quickly running and monitoring straightforward array jobs. If your workflow has complex interdependencies, you should look into the excellent [snakemake](https://snakemake.readthedocs.io/en/stable/) tool. 

## Installation:

```bash
pip install psub
```

psub stands for petko-submit, the OG ernstlab member who had the core idea.
