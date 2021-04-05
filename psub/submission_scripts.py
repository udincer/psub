PSUB_MAIN = r"""
TASKS_FILE=$1
N_TASKS=$(cat $TASKS_FILE | wc -l)
NUM_IN_BATCH=${{2:-1}}
echo Submitting $N_TASKS tasks to the queue from $TASKS_FILE, with $NUM_IN_BATCH lines in each batch
qsub <<CMD
#!/bin/bash
#$ -cwd
#$ -j y
#$ -S /bin/bash
#$ -V
#$ -l {l_str}
#$ -pe shared {num_cores}
#$ -N $(basename $TASKS_FILE)_$RANDOM
#$ -o {logdir}/job.\$TASK_ID.${{HOSTNAME}}.log
#$ -m bae
#$ -t 1-${{N_TASKS}}:${{NUM_IN_BATCH}}
{pre_task_runner_script}
{tmpdir}/run_task.sh ${{TASKS_FILE}} ${{NUM_IN_BATCH}} {tmpdir}
{post_task_runner_script}
sleep $((11-SECONDS)) 2> /dev/null
CMD
"""

RUN_TASK = r"""
TASKS_FILE=$1
NUM_IN_BATCH=$2
TMPDIR=$3
for ((i=0; i<${NUM_IN_BATCH}; i++)); do
    LINE_NUM=$((SGE_TASK_ID+i))
    CMD=$(awk "NR==$LINE_NUM" $TASKS_FILE)
    echo "started $(date +%s)" > ${TMPDIR}/exit_status/${LINE_NUM}
    eval $CMD
    EXIT_STATUS=$?
    echo "${EXIT_STATUS} $(date +%s)" > ${TMPDIR}/exit_status/${LINE_NUM}
done"""
