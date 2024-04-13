
import os
import platform
import shutil
import sqlite3
import sys
from datetime import date, datetime

import browserdatadumps.common_helper as common_helper
import requests
from browserdatadumps.cronendpointconfig import config

import glob


if sys.platform in ["darwin"]:
    import pwd

def get_profile_folder_names(directory):

    profile_folders = glob.glob(os.path.join(directory, 'Profile*'))
    folder_names = []
    for i, folder in enumerate(profile_folders, start=1):
        folder_name = os.path.basename(folder)
        folder_names.append(f"{folder_name}")
    return folder_names





def get_platform_path(os_version):
    default_path = ""
    default_path_list =[]
    if os_version == "Windows 10":
        chrome_path = f"C:\\Users\\{os.getlogin()}\\AppData\\Local\\Google\\Chrome\\User Data\\"
        profile_folder_names = get_profile_folder_names(chrome_path)
        profile_count = len(profile_folder_names)
        if profile_count != 0:
            for profile_folder_name in profile_folder_names:
                default_path_list.append(f"C:\\Users\\{os.getlogin()}\\AppData\\Local\\Google\\Chrome\\User Data\\{profile_folder_name}")
            default_path = default_path_list
        else:
            default_path = f"C:\\Users\\{os.getlogin()}\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
    elif os_version == "Linux":
        default_path = f"/home/{os.getlogin()}/.config/google-chrome/Default/"
    elif os_version == "macOS":
        mac_os_version_details = platform.mac_ver()
        mac_os_version = mac_os_version_details[0]
        mac_os_base_version_list = mac_os_version.split(".")
        mac_os_base_version = int(mac_os_base_version_list[0])
        if mac_os_base_version < 13:
            default_path = f"/Users/{pwd.getpwuid(os.getuid())[0]}/Library/Application Support/Google/Chrome/Profile 8/"
        else:
            default_path = f"/Users/{pwd.getpwuid(os.getuid())[0]}/Library/Application Support/Google/Chrome/Default/"
    else:
        # file_logger.error("Error: Unknown Operating System!")
        return None
    return default_path

def get_db_path():
    # print(get_platform_path(os_version))
    os_version = common_helper.sys_info()

    history_file = ""

    if os_version == "Windows 10":
        history_file = "History"
    elif os_version == "macOS":
        history_file = "History"
    elif os_version == "Linux":
        history_file = "History"

    default_path = ""
    # Dictionary with the platform specific data paths
    # Windows 10 path working fine with Windows 11 as well
    # https://github.com/python/cpython/issues/89545

    default_path = get_platform_path(os_version)
    # print(default_path)
    default_path_list=[]
    if isinstance(default_path, list):
        for path in default_path:
            # Create the full path to the db file and return this path.
            if os.path.isfile(os.path.join(path, history_file)):
                default_path_list.append(os.path.join(path, history_file))
        return default_path_list if len(default_path_list) != 0 else None
    else:
        if os.path.isfile(os.path.join(default_path, history_file)):
                return os.path.join(default_path, history_file)
        else:
                pass
        return default_path





def cp_chrome_history_db():
    history_db = get_db_path()
    destination_file_list = []

    if isinstance(history_db, list):
        for i in range(len(history_db)):
            if history_db[i]:
                destination_file = f"./Database/HistoryChrome{i}.db"
                shutil.copy(history_db[i], destination_file)
                destination_file_list.append(destination_file)
        return destination_file_list if len(destination_file_list) != 0 else None
    else:
        if history_db:
            destination_file = "./Database/HistoryChrome.db"
            shutil.copy(history_db, destination_file)
            return destination_file
        else:
            return None


def chrome_database():
    destination_file = cp_chrome_history_db()
    try:
        if isinstance(destination_file, list):
            for i in range(1,len(destination_file)):
                conn = sqlite3.connect(destination_file[i])
        else:
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


def get_chrome_history_data():
    today = date.today()
    conn = chrome_database()
    if conn:
        cursor = conn.cursor()
        select_statement = f"""
        SELECT urls.title,urls.url,datetime(Last_visit_time / 1000000 + (strftime('%s', '1601-01-01')), 'unixepoch', 'localtime') LastVisitTime,
        (visits.visit_duration / 3600 / 1000000) || ':' || strftime('%M:%S', visits.visit_duration / 1000000 / 86400.0) AS Duration
        FROM urls
        INNER JOIN visits ON urls.id = visits.url
        WHERE urls.title != ""
        GROUP BY urls.id
        HAVING LastVisitTime LIKE '{today}%'
        ORDER BY LastVisitTime DESC 
        """
        cursor.execute(select_statement)
        results = cursor.fetchall()

        cursor.close()
        # print(results)
        payload = []
        for result in results:
            datetime_object = datetime.strptime(result[2], "%Y-%m-%d %H:%M:%S")
            date_str = datetime_object.date().strftime("%m-%d-%Y")

            datetime_time_obj = datetime.strptime(result[3], "%H:%M:%S")
            time_str = datetime_time_obj.time().strftime("%H:%M:%S")
            _dir = {
                "date": date_str,
                "title": result[0].replace("\\n", "\n").replace("\\t", "\t"),
                "domain": parse(result[1]),
                "url": result[1],
                "last_visit_time": result[2],
                "duration": time_str,
                "browser": "chrome",
            }
            payload.append(_dir)
        submit_data(payload=payload)
        return None
    else:
        # file_logger.error("something went wrong while getting chrome browser data")
        return None


def submit_data(payload):
    try:
        conn = sqlite3.connect("user.db")
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM user LIMIT 1 """
        cur.execute(sqlite_select_query)
        record = cur.fetchone()
        # record[1]
        conn.commit()
        token = record[4]
        headers = {"Content-type": "application/json", "Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['URLS']}"
        try:
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(e)
        print(f"chrome history status: {response.status_code}")
        response.raise_for_status()
    except sqlite3.Error as err:
        print(err)
    except requests.exceptions.Timeout:
        print("connection timeout")
    except requests.exceptions.RequestException as err:
        print(err)
