import sqlite3
import db.dbconn as dbconn
import threading,json

def get_user_token():
    try:
        conn = dbconn.database()
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM user LIMIT 1 """
        cur.execute(sqlite_select_query)
        record = cur.fetchone()
        conn.commit()
        token = record[4]
        return token
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None


def get_user_id():
    try:
        conn = dbconn.database()
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM user LIMIT 1 """
        cur.execute(sqlite_select_query)
        record = cur.fetchone()
        conn.commit()
        id = record[0]
        return id
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None

def get_activity_logs_data():
    try:
        conn =dbconn.activity_database()
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM activity_logs """
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None
    
def get_activity_failed_logs_data():
    try:
        conn =dbconn.activity_failed_logs_database()
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM activity_failed_logs """
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None
    
def get_user_name_email():
    try:
        conn = dbconn.database()
        cur = conn.cursor()
        sqlite_select_query = """ SELECT * FROM user LIMIT 1 """
        cur.execute(sqlite_select_query)
        record = cur.fetchone()
        conn.commit()
        name = record[1] + " " + record[2]
        email = record[3]
        return name, email
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None    


def get_task_list_by_order(order,project_id):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = (
            f""" SELECT * FROM create_task WHERE fk_project='{project_id}' AND status = '{order}' """
        )
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None


def create_task_payload_by_order(order,project_id):
    try:
        data = get_task_list_by_order(order,project_id)

        task_data_list = []
        for task_data in data:
            task_payload = {
                "id": task_data[0],
                "fk_todo": task_data[2],
                "task": task_data[3],
                "description": task_data[4],
                "create_task_date": task_data[5],
                "create_task_time": task_data[6] if len(task_data) > 6 else None,
                "update_task_date": task_data[7] if len(task_data) > 7 else None,
                "update_task_time": task_data[8] if len(task_data) > 8 else None,
            }
            task_data_list.append(task_payload)
        return task_data_list
    except sqlite3.Error as er:
        raise SystemExit("Unable to establish connection with database")
    except TypeError:
        return None


  

def get_create_task_data_by_projectid(id):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = f""" SELECT * FROM create_task WHERE fk_project = '{id}' AND  (status = 'To Do' OR status = 'In progress') """
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        return None
    except TypeError:
        return None


def get_server_status_failed_task():
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = f""" SELECT * FROM create_task WHERE status = 'Completed' AND server_status = 0 """
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        return None
    except TypeError:
        return None


def get_completed_task():
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = f""" SELECT * FROM create_task WHERE status = 'Completed' AND  server_status = 1 """
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        return None
    except TypeError:
        return None


def get_all_completed_list():
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = (
            f""" SELECT * FROM create_task WHERE status = 'Completed' """
        )
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        return None
    except TypeError:
        return None
    
def get_all_uncompleted_list():
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = (
            f""" SELECT * FROM create_task WHERE (status = 'To Do' OR status = 'In progress')"""
        )
        cur.execute(sqlite_select_query)
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        return None
    except TypeError:
        return None    

def get_perticular_project_completed_list(id):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = """
            SELECT * FROM create_task 
            WHERE fk_project = ? AND status = 'Completed'
        """
        cur.execute(sqlite_select_query, (id,))
        record = cur.fetchall()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        return None
    except TypeError:
        return None

def list_completed_data(id):
    data = get_perticular_project_completed_list(id)
    task_data_list = []
    for task_data in data:
        task_payload = {
            "fk_todo": task_data[2],
            "task": task_data[3],
            "description": task_data[4],
            "create_task_date": task_data[5],
            "create_task_time": task_data[6] if len(task_data) > 6 else None,
            "update_task_date": task_data[7] if len(task_data) > 7 else None,
            "update_task_time": task_data[8] if len(task_data) > 8 else None,
        }
        task_data_list.append(task_payload) 
    return task_data_list


def get_perticular_task_by_taskid(id):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        sqlite_select_query = f""" SELECT * FROM create_task WHERE id = '{id}' """
        cur.execute(sqlite_select_query)
        record = cur.fetchone()
        conn.commit()
        conn.close()
        return record
    except sqlite3.Error as er:
        print(er)
        return None
    except TypeError:
        return None


def list_create_task(id):
    try:
        data = []
        payloads = get_create_task_data_by_projectid(id)
        for payload in payloads:
            task_dict = {}
            task_dict["id"] = payload[0]
            task_dict["task"] = {
                "fk_todo": payload[2],
                "task": payload[3],
                "description": payload[4],
                "create_task_date": payload[5],
                "create_task_time": payload[6] if len(payload) > 6 else None,
                "update_task_date": payload[7] if len(payload) > 7 else None,
                "update_task_time": payload[8] if len(payload) > 8 else None,
            }
            data.append(task_dict)
        return data
    except sqlite3.Error as er:
        print("error", er)
    except TypeError:
        return None
