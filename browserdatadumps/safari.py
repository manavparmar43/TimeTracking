# import logging
# import logging.config
import os
import pwd
import shutil
import sqlite3
from datetime import date, datetime

import common_helper
import requests
from cronendpointconfig import config

# logging.config.fileConfig(
#     "./logging.conf",
#     disable_existing_loggers=False,
#     defaults={"logfilename": f"logs/{date.today()}.log"},
# )
# file_logger = logging.getLogger("simpleFileLogger")
# console_logger = logging.getLogger("simpleConsoleLogger")


def get_db_path():
    os_version = common_helper.sys_info()
    history_file = "History.db"
    default_path = ""

    platform_paths = {
        "Darwin": "/Users/{0}/Library/Safari".format(pwd.getpwuid(os.getuid())[0]),
    }

    if os_version == "macOS":
        default_path = platform_paths["Darwin"]
    else:
        # file_logger.error("Error: Unknown Operating System!")
        pass

    if os.path.isfile(os.path.join(default_path, history_file)):
        return os.path.join(default_path, history_file)
    else:
        # file_logger.error(
        #     f"DB file not found at path : {os.path.join(default_path, history_file)}"
        # )
        return None


def cp_safari_history_db():
    safari_db = get_db_path()
    if safari_db:
        destination_file = "./HistorySafari.db"
        shutil.copy(safari_db, destination_file)
        return destination_file
    else:
        # file_logger.error("safari db path not found, file not copied!")
        return None


def safari_database():
    destination_file = cp_safari_history_db()
    try:
        conn = sqlite3.connect(destination_file)
        return conn
    except sqlite3.Error as err:
        # file_logger.error(f"{err}")
        return None
    except TypeError:
        # file_logger.error("TypeError")
        return None


# to extract domain name
def parse(url):
    try:
        parsed_url_components = url.split("//")
        sub_level_split = parsed_url_components[1].split("/", 1)
        domain = sub_level_split[0].replace("www.", "")
        if domain == "":
            return "offline"
        return domain
    except IndexError:
        # file_logger.error("URL format error!")
        return "offline"


def get_safari_history_data():
    today = date.today()
    conn = safari_database()

    if conn:
        cursor = conn.cursor()
        select_statement = f"""
        SELECT  title, url, datetime(visit_time + 978307200, 'unixepoch', 'localtime') AS LastVisitTime
        FROM history_visits
        INNER JOIN history_items ON history_items.id = history_visits.history_item
        GROUP BY history_visits.id
        HAVING LastVisitTime LIKE '{today}%'
        ORDER BY LastVisitTime DESC
        """
        cursor.execute(select_statement)
        results = cursor.fetchall()
        cursor.close()
        payload = []
        for result in results:
            datetime_object = datetime.strptime(result[2], "%Y-%m-%d %H:%M:%S")
            date_str = datetime_object.date().strftime("%m-%d-%Y")
            datetime_time_obj = datetime.strptime(result[2], "%Y-%m-%d %H:%M:%S")
            time_str = datetime_time_obj.time().strftime("%H:%M:%S")
            _dir = {
                "date": date_str,
                "title": result[0].replace("\\n", "\n").replace("\\t", "\t"),
                "domain": parse(result[1]),
                "url": result[1],
                "last_visit_time": result[2],
                "duration": time_str,
                "browser": "safari",
            }
            payload.append(_dir)
        submit_data(payload=payload)
        # print(payload)
        return None
    else:
        # file_logger.error("something went wrong while getting chrome browser data")
        return None


# print(get_safari_history_data())


def submit_data(payload):
    try:
        conn = sqlite3.connect("user.db")
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM user LIMIT 1 """
        cur.execute(sqlite_select_query)
        record = cur.fetchone()
        conn.commit()
        token = record[4]
        headers = {"Content-type": "application/json", "Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['URLS']}"
        response = requests.post(url, json=payload, headers=headers)
    except sqlite3.Error as err:
        print(err)
    except requests.exceptions.Timeout:
        print("connection timeout")
    except requests.exceptions.RequestException as err:
        print(err)

    return
