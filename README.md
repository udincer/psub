# psub
Submit array jobs without all the suffering

Stands for petko-submit, OG ernstlab member who came up with the idea.

## New API (alpha):

There's a new (unstable) API that allows submitting jobs directly in Python. 

## Installation:

Must be installed under ~/utils like this:
```
mkdir ~/utils; cd ~/utils
git clone git@github.com:udincer/psub.git
```

Add alias:
```
# Optional: add psub as an alias
# Add the following to .bashrc
alias psub='/u/home/d/<your_username>/utils/psub/psub_main.sh '
```

## How to use:

Make script containing each command you want to run in parallel in exactly one line:
```
# the_jobs.sh
python run_analysis.py theta1
python run_analysis.py theta2
python run_analysis.py theta3
python run_analysis.py theta4
python run_analysis.py theta5
```

Run psub like this, will batch 3 commands to one SGE job (for short jobs):
```
psub the_jobs.py 3
```