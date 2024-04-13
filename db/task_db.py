import json
import sqlite3, uuid

import db.dbconn as dbconn


def store_create_task(
    id,
    project_id,
    task_id,
    task,
    status,
    description,
    create_task_date,
    create_task_time,
    update_task_date,
    update_task_time,
    server_status,
):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()

        cur.execute(
            f"""
                INSERT INTO create_task VALUES (
                        '{id}',
                        '{project_id}', 
                        '{task_id}', 
                        '{task}',  
                        '{description}',
                        '{create_task_date}',
                        '{create_task_time}',
                        '{update_task_date}',
                        '{update_task_time}',
                        '{status}',
                        '{server_status}'
                    )
                """
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        print("Error storing create_task log:", error)
        pass
    except Exception as e:
        print(f"Error: {e}")
        pass


def update_create_task_status(task_id, status, server_status):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()

        cur.execute(
            f"""
            UPDATE create_task SET
            server_status=?,status=? WHERE id=?
        """,
            (server_status, status, task_id),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        print("Error update create_task log:", error)
        pass
    except Exception as e:
        print(f"Error: {e}")
        pass


def update_create_task(
    task, description, status, update_task_date, update_task_time, id
):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE create_task SET
            task=?,description=?,update_task_date=?,update_task_time=?,status=? WHERE id=?
        """,
            (task, description, update_task_date, update_task_time, status, id),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        print("Error update create_task log:", error)
        pass
    except Exception as e:
        print(f"Error: {e}")
        pass

def delete_all_create_task():
    try:
        # Connect to the database
        conn = dbconn.create_task_database()
        cur = conn.cursor()

        # Execute the DELETE statement to delete all rows
        cur.execute("DELETE FROM create_task")

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        conn.close()

    except sqlite3.Error as error:
        pass

def update_task_date(id,update_date,update_time):
    try:
        conn = dbconn.create_task_database()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE create_task SET
            update_task_date=?,update_task_time=? WHERE id=?
        """,
            (update_date,update_time,id,),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        print("Error update create_task log:", error)
        pass
    except Exception as e:
        print(f"Error: {e}")
        pass
