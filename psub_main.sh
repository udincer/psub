# this is the main script to be called (i.e. aliased)
# make sure to change the line that starts with ~/utils to make sure it points 
# to the right thing

TASKS_FILE=$1
N_TASKS=$(cat $TASKS_FILE | wc -l)

NUM_IN_BATCH=${2:-1}

mkdir -p  logs/$(basename $TASKS_FILE)

echo Submitting $N_TASKS tasks to the queue from $TASKS_FILE, with $NUM_IN_BATCH lines in each batch
qsub <<CMD
#!/bin/bash
#$ -cwd
#$ -j y
#$ -S /bin/bash
#$ -V
#$ -l arch=intel*,h_data=8G,h_rt=7:59:00,highp
## -pe shared 1
#$ -N $(basename $TASKS_FILE)_$(date +%s)_$RANDOM
#$ -o logs/$(basename $TASKS_FILE)/job.\$TASK_ID.${HOSTNAME}.log
#$ -m bae
#$ -t 1-${N_TASKS}:${NUM_IN_BATCH}
~/utils/psub/run_task.sh ${TASKS_FILE} ${NUM_IN_BATCH}
sleep 181
CMD
