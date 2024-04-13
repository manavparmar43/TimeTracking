import sqlite3
import db.dbconn as dbconn


def store_user_data(user_id, first_name, last_name, email, access_token):
    try:
        conn = dbconn.database()
        cur = conn.cursor()
        cur.execute(""" DELETE  FROM user """)
        cur.execute(
            f""" INSERT INTO user VALUES ( '{user_id}','{first_name}','{last_name}',"{email}",'{access_token}') """
        )
        conn.commit()
        conn.close()
        return "done"
    except sqlite3.Error as error:
        print(error)
        pass
    except Exception as e:
        print(e)
        pass


def delete_user_data():
    try:
        conn = dbconn.database()
        cur = conn.cursor()
        cur.execute(""" DELETE  FROM user """)
        conn.commit()
        conn.close()
        return "done"
    except sqlite3.Error as error:
        print(error)
        pass
    except Exception as e:
        print(e)
        pass
