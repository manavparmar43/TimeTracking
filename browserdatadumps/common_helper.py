import platform
import sqlite3
import sys
from datetime import datetime as dt


def sys_info():
    # check the system
    if platform.system() == "Darwin":
        return "macOS"
    elif platform.system() == "Linux":
        return "Linux"
    elif platform.system() == "Windows":
        version = platform.system() + " " + platform.release()
        return version
    return


def get_db_data(db, command):
    # connect, query db and returning the results
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(command)
        results = cur.fetchall()
        cur.close()
        return results
    except Exception as e:
        sys.exit("Error reading the database: %s" % e)


def convert_date_time(microseconds):
    # convert microseconds to %Y-%m-%d %H:%M:%S [isoformat]
    try:
        return dt.fromtimestamp(microseconds / 1000000).isoformat()
    except Exception as e:
        return None


def convert_epoch(timestamp):
    """
    Convert epoch to human readable date
    :param timestamp: The epoch timestamp.
    :return: The human readable date.
    """
    try:
        rval = dt.fromtimestamp(timestamp / 1000000).ctime()
    except Exception as e:
        rval = "No date available (NULL value in database)."
        print(e)
