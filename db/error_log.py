
import sqlite3
import json
import uuid
import db.dbconn as dbconn
from datetime import datetime
import inspect
def store_error_log(error):
    
    try:
        conn = dbconn.create_error_logs_database()
        cur = conn.cursor()
        error = error.replace("'", "''")  
        frame = inspect.stack()[1]
        filename = frame.filename
        function_name = frame.function
        line_number = frame.lineno
        cur.execute(f""" INSERT INTO error_logs VALUES ('{str(uuid.uuid4())[0:6]}', 'ERROR','{filename}' ,'{function_name}','{line_number}','{error}','{datetime.now().strftime("%d-%m-%Y")}', '{datetime.now().strftime("%I:%M %p")}') """)
        conn.commit()
        conn.close()
        return "done"
    except sqlite3.Error as error:
        pass
    except Exception as e:
        pass

def delete_all_error_logs():
    try:
        # Connect to the database
        conn = dbconn.create_error_logs_database()
        cur = conn.cursor()

        # Execute the DELETE statement to delete all rows
        cur.execute("DELETE FROM error_logs")

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        conn.close()

    except sqlite3.Error as error:
        pass