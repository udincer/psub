TASKS_FILE=$1
NUM_IN_BATCH=$2

for ((i=0; i<${NUM_IN_BATCH}; i++)); do
	LINE_NUM=$((SGE_TASK_ID+i))
	CMD=$(awk "NR==$LINE_NUM" $TASKS_FILE)
	eval $CMD
done