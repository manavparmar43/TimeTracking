import os
import platform
import shutil
import sqlite3
import sys
from datetime import date, datetime

import browserdatadumps.common_helper as common_helper
import requests
from browserdatadumps.cronendpointconfig import config
# from  .cronendpointconfig import config

if sys.platform in ["darwin"]:
    import pwd

# logging.config.fileConfig(
#     "./logging.conf",
#     disable_existing_loggers=False,
#     defaults={"logfilename": f"logs/{date.today()}.log"},
# )
# file_logger = logging.getLogger("simpleFileLogger")
# console_logger = logging.getLogger("simpleConsoleLogger")

def get_platform_path(os_version):
    default_path = ""
    if os_version == "Windows 10":
        default_path = (
            f"C:\\Users\\{os.getlogin()}\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles"
        )
    elif os_version == "Linux":
        platform_detail = platform.version()
        platform_detail_list = platform_detail.split("~")
        _platform_detail_list = platform_detail_list[1].split("-")
        ubuntu_version_string = _platform_detail_list[0]
        ubuntu_version_string_split = ubuntu_version_string.split(".")
        ubuntu_version_prefix = ubuntu_version_string_split[0]
        if int(ubuntu_version_prefix) > 20:
            default_path = (
                f"/home/{os.getlogin()}/snap/firefox/common/.mozilla/firefox/"
            )
        else:
            default_path = f"/home/{os.getlogin()}/.mozilla/firefox/"
    elif os_version == "macOS":
        default_path = f"/Users/{pwd.getpwuid(os.getuid())[0]}/Library/Application Support/Firefox/Profiles"

    return default_path

def get_db_path():
    os_version = common_helper.sys_info()
    history_file = "places.sqlite"
    default_path = ""

    # Dictionary with the platform specific data paths
    # Windows 10 path working fine with Windows 11 as well
    # https://github.com/python/cpython/issues/89545

    # Check the operating system
    default_path = get_platform_path(os_version)

    # Try to find the x.default directory
    # in Firefox' Profiles folder.
    try:
        for item in os.listdir(default_path):
            # Check for the x.default directory
            # and return the database file's path
            if os.path.isdir(os.path.join(default_path, item)) and "default" in item:
                if os.path.isfile(os.path.join(default_path, item, history_file)):
                    # file_logger.debug(
                    #     f"{os.path.join(default_path, item, history_file)}"
                    # )
                    return os.path.join(default_path, item, history_file)
    except FileNotFoundError as err:
        # file_logger.error(f"DB file not found {err}")
        return None


def cp_firefox_history_db():
    history_db = get_db_path()
    if history_db:
        destination_file = "./Database/HistoryFirefox.db"
        shutil.copy(history_db, destination_file)
        return destination_file
    else:
        # file_logger.error("chrome db path not found, file not copied!")
        return None


def firefox_database():
    destination_file = cp_firefox_history_db()
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


def get_firefox_history_data():
    today = date.today()
    conn = firefox_database()
    if conn:
        cursor = conn.cursor()
        select_statement = f"""
        SELECT url, title,datetime(moz_places.last_visit_date / 1000000, 'unixepoch') AS LastVisitTime
        FROM moz_places
        WHERE title != ""
        GROUP BY id
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
            time_str = "00:00:00"
            _dir = {
                "date": date_str,
                "title": result[1].replace("\\n", "\n").replace("\\t", "\t"),
                "domain": parse(result[0]),
                "url": result[0],
                "last_visit_time": result[2],
                "duration": time_str,
                "browser": "firefox",
            }
            payload.append(_dir)
        submit_data(payload=payload)
        return None
    else:
        # file_logger.error("something went wrong while getting firefox browser data")
        return None


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
        print(f"firfox history status: {response.status_code}")
        response.raise_for_status()
    except sqlite3.Error as err:
        print(err)
    except requests.exceptions.Timeout:
        print("connection timeout")
    except requests.exceptions.RequestException as err:
        print(err)
    return
