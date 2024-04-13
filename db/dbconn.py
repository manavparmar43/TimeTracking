import sqlite3
# from main import resource_path
# import db


def database():
    try:
        conn = sqlite3.connect("user.db")
        cur = conn.cursor()
        cur.execute(
            """ CREATE TABLE IF NOT EXISTS user (id BLOB,first_name TEXT,last_name TEXT,email TEXT,token BLOB) """
        )
        conn.commit()
        return conn
    except sqlite3.Error as er:
        return er




def activity_database():
    try:
        activity_conn = sqlite3.connect("Database/activity_logs.db")
        activity_cur = activity_conn.cursor()
        activity_cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs 
            (
                id BLOB PRIMARY KEY,              
                fk_project BLOB,
                fk_todo BLOB,
                date DATE,
                start_time TIME,
                end_time TIME,
                duration TIME,
                idle_time TEXT,
                screen_activity BLOB,
                image_list BLOB
            )
        """)
        return activity_conn
    except sqlite3.Error as error:
        print("Error creating activity_log table:", error)

def activity_failed_logs_database():
    try:
        activity_failed_logs_conn = sqlite3.connect("Database/activity_failed_logs.db")
        activity_failed_logs_cur = activity_failed_logs_conn.cursor()
        activity_failed_logs_cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_failed_logs 
            (
                id BLOB PRIMARY KEY,              
                fk_project BLOB,
                fk_todo BLOB,
                date DATE,
                start_time TIME,
                end_time TIME,
                duration TIME,
                idle_time TEXT,
                screen_activity BLOB,
                image_list BLOB
            )
        """)
        return activity_failed_logs_conn
    except sqlite3.Error as error:
        print("Error creating activity_failed_logs table:", error)
        pass

def create_task_database():
    try:
        create_task_conn = sqlite3.connect("Database/create_task.db")
        create_task_cur = create_task_conn.cursor()
        create_task_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS create_task 
            (
                id BLOB ,              
                fk_project BLOB,
                fk_todo BLOB,
                task TEXT,
                description TEXT,
                create_task_date DATE,
                create_task_time TEXT,
                update_task_date DATE,
                update_task_time TEXT,
                status TEXT,
                server_status INTEGER
            )
        """
        )
        return create_task_conn
    except sqlite3.Error as error:
        print("Error creating create task database table:", error)
        pass


def create_error_logs_database():
    try:
        error_logs_conn = sqlite3.connect("Database/error_log.db")
        error_logs_cur = error_logs_conn.cursor()
        error_logs_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS error_logs 
            (
                id BLOB ,              
                log_level TEXT,
                file_name TEXT,
                function_name TEXT,
                line_number TEXT,
                error_msg TEXT,
                date TEXT,
                time TEXT

            )
        """
        )
        return error_logs_conn
    except sqlite3.Error as error:
        pass