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
    ${TMPDIR}/status_update.sh ${TMPDIR} ${LINE_NUM} started
    eval $CMD
    EXIT_STATUS=$?
    echo "${EXIT_STATUS} $(date +%s)" > ${TMPDIR}/exit_status/${LINE_NUM}
    ${TMPDIR}/status_update.sh ${TMPDIR} ${LINE_NUM} ${EXIT_STATUS}
done"""


PY_SQLITE_WRITE = r"""
import sys
import json
import sqlite3

# partially based on
# https://github.com/RaRe-Technologies/sqlitedict/blob/master/sqlitedict.py


def add_to_sqlite_from_dict(
    sqlite_fn,
    input_dict,
    table_name="unnamed_table",
    encode=json.dumps,
    decode=json.loads,
):

    conn = sqlite3.connect(sqlite_fn)
    cursor = conn.cursor()

    SQL_MAKE_TABLE = (
        'CREATE TABLE IF NOT EXISTS "%s" (key TEXT PRIMARY KEY, value BLOB)'
        % table_name
    )
    cursor.execute(SQL_MAKE_TABLE)

    for key, value in input_dict.items():
        value_ = encode(value)
        SQL_ADD_ITEM = 'REPLACE INTO "%s" (key, value) VALUES (?,?)' % table_name
        cursor.execute(SQL_ADD_ITEM, (key, value_))

    conn.commit()


sqlite_fn = sys.argv[1]
job_id = sys.argv[2]
exit_code = sys.argv[3]
timestamp = sys.argv[4]

input_dict = {
    job_id: {"job_id": job_id, "exit_code": exit_code, "timestamp": timestamp}
}

add_to_sqlite_from_dict(sqlite_fn, input_dict)
"""


STATUS_UPDATE_SH = r"""
TMPDIR=$1
LINE_NUM=$2
EXIT_STATUS=$3

CURRENT_TIME=$(date +%s)

python {tmpdir}/sqlite_write.py ${{TMPDIR}}/exit_status/exit_status.sqlite ${{LINE_NUM}} ${{EXIT_STATUS}} ${{CURRENT_TIME}}
"""