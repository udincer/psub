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


def get_dict_from_sqlite(
    sqlite_fn,
    table_name="unnamed_table",
    encode=json.dumps,
    decode=json.loads,
) -> dict:
    conn = sqlite3.connect(sqlite_fn)
    cursor = conn.cursor()

    SQL_QUERY_STR = f"SELECT * FROM {table_name}"
    job_statuses = cursor.execute(SQL_QUERY_STR).fetchall()

    status_d = {}
    for job_id, json_str in job_statuses:
        status_d[job_id] = decode(json_str)

    return status_d
