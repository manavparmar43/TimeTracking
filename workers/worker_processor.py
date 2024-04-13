import os, threading
from PyQt5.QtCore import *
import random, json
from PIL import Image
import time
from datetime import datetime, timedelta
import pyautogui
import db.dbconn as dbconn
import db.db_helper as db_helper
import endpoints.requests_helper as reqs
import server_check.server_check as server_check
import dialogbox.error_msg as error_msg
import db.task_db as task_db
import db.error_log as error_log
import db.activity_failed_log as activity_failed_log


def show_error_message(error_message):
    error_dialog = error_msg.Error_window()
    error_dialog.error_msg_lable.setText(error_message)
    error_dialog.exec_()


def activity_payload(payload):
    payload_data = {
        "fk_project": payload[1],
        "fk_todo": payload[2],
        "date": payload[3],
        "start_time": payload[4],
        "end_time": payload[5],
        "duration": payload[6],
        "idle_time": payload[7],
        "screen_activity": json.loads(payload[8]),
    }
    image_list = json.loads(payload[9]) if len(json.loads(payload[9])) > 0 else []
    return payload_data, image_list

def activity_failed_payload(payload):
    payload_data = {
        "fk_project": payload[1],
        "fk_todo": payload[2],
        "date": payload[3],
        "start_time": payload[4],
        "end_time": payload[5],
        "duration": payload[6],
        "idle_time": payload[7],
        "screen_activity": None,
    }
    image_list = json.loads(payload[9]) if len(json.loads(payload[9])) > 0 else []
    return payload_data, image_list


def delete_activity_record_screenshot(id, image_list):
    conn = dbconn.activity_database()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM activity_logs WHERE id = ?", (id,))
        conn.commit()
    except Exception as e:
        error_log.store_error_log(str(e))
        pass
    finally:
        if len(image_list) != 0:
            for image in image_list:
                if os.path.exists(image):
                    os.remove(image)
                else:
                    continue
        if conn:
            conn.close()

def delete_activity_failed_record_screenshot(id, image_list):
    conn = dbconn.activity_failed_logs_database()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM activity_failed_logs WHERE id = ?", (id,))
        conn.commit()
    except Exception as e:
        error_log.store_error_log(str(e))
        pass
    finally:
        if len(image_list) != 0:
            for image in image_list:
                if os.path.exists(image):
                    os.remove(image)
                else:
                    continue
        if conn:
            conn.close()


def delete_create_task(id):
    conn = dbconn.create_task_database()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM create_task WHERE id = ?", (id,))
        conn.commit()
    except Exception as e:
        pass
    finally:
        if conn:
            conn.close()




def compressimages(image_path):
    maxwidth = 1200
    image = Image.open(image_path)

    width, height = image.size
    aspectratio = width / height
    newheight = maxwidth / aspectratio
    image = image.resize((maxwidth, round(newheight)))
    filename = image_path
    image.save(filename, optimize=True, quality=85)


class ScreenshotThread(QThread):
    screenshot_signal = pyqtSignal(str)

    def run(self):
        for _ in range(60):
            self.sleep(random.randint(30, 60))
            screenshot = self.take_screen_shoot()
            self.screenshot_signal.emit(screenshot)

    def take_screen_shoot(self):
        try:
            my_screenshot = pyautogui.screenshot()
            image_date = datetime.now()
            dt_string = image_date.strftime("%d-%m-%Y-%H-%M-%S")
            image_path = os.path.join(os.getcwd(), "screenshots",f"{dt_string}.png")
            my_screenshot.save(image_path)
            compressimages(image_path)
            return image_path
        except Exception as e:
            error_log.store_error_log(str(e))
            pass


class SqlliteCommunication(QThread):
    send_data_sqllite_signal = pyqtSignal()

    def run(self):
        while True:
            self.sleep(63)
            self.send_data_sqllite_signal.emit()


class TimerThread(QThread):
    timer_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.start_time = ""
        self.end_time = ""

    def run(self):
        while True:
            start_time = datetime.now().strftime("%H:%M:%S")
            self.start_time = start_time
            self.timer_signal.emit(start_time, "")
            self.msleep(60000)
            end_time = datetime.now().strftime("%H:%M:%S")
            self.end_time = end_time
            self.timer_signal.emit(self.start_time, self.end_time)
            self.msleep(7000)


class BackendCommunication(QThread):
    send_data_signal = pyqtSignal()

    def run(self):
        while True:
            self.sleep(305)
            self.send_data_signal.emit()


class ActivityLogThread(QThread):
    finished = pyqtSignal()

    def __init__(self, payloads):
        super().__init__()
        self.payloads = payloads

    def run(self):
        token = db_helper.get_user_token()
        if token:
            try:
                if (
                    server_check.check_internet_connection()
                    and server_check.check_server_status()
                ):
                    for payload in self.payloads:
                        payload_data, image_list_data = activity_payload(payload)
                        activity_log = reqs.create_activity_log(
                            token=token,
                            payload=payload_data,
                            image_list=image_list_data,
                        )
                        if activity_log.status_code == 201:
                            delete_activity_record_screenshot(payload[0], image_list_data)
                        if activity_log.status_code in (500,501):
                            payload_data['screen_activity'] = None 
                            activity_failed_log.store_activity_failed_log(payload_data,image_list_data)
                            delete_activity_record_screenshot(payload[0],[])
                        else:
                            delete_activity_record_screenshot(payload[0], image_list_data)


                    self.finished.emit()
                else:
                    pass
            except Exception as e:
                error_log.store_error_log(str(e))
                pass
        else:
            show_error_message("The token provided appears to be invalid..!")

class SendAllActivityLogs(QThread):
    sendallactivitylogs_singal = pyqtSignal()

    def __init__(self):
        super().__init__()
    def run(self):
        try:
            activity_data = db_helper.get_activity_logs_data()
            token = db_helper.get_user_token()
            if server_check.check_server_status():
                if len(activity_data) != 0:
                    for data in activity_data:
                        payload, image_list = activity_payload(data)
                        activity_log = reqs.create_activity_log(
                            token=token, payload=payload, image_list=image_list
                        )
                        if activity_log.status_code == 201:
                                delete_activity_record_screenshot(data[0], image_list)
                        if activity_log.status_code in (500,501):
                            payload['screen_activity'] = None 
                            activity_failed_log.store_activity_failed_log(payload,image_list)
                            delete_activity_record_screenshot(data[0],[])
                        else:
                            continue
                else:
                    pass
            else:
                pass

        except Exception as e:
            error_log.store_error_log(str(e))     

class  SendAllActivityFailedLogs(QThread):
    sendallactivityfailedlogs_singal = pyqtSignal()

    def __init__(self):
        super().__init__() 
    def run(self):
        try:
            activity_data = db_helper.get_activity_failed_logs_data()
            token = db_helper.get_user_token()
            if server_check.check_server_status():
                if len(activity_data) != 0:
                    for data in activity_data:
                        payload, image_list = activity_failed_payload(data)
                        activity_log = reqs.create_activity_log(
                            token=token, payload=payload, image_list=image_list
                        )
                        if activity_log.status_code == 201:
                            delete_activity_failed_record_screenshot(data[0], image_list)
                        else:
                            delete_activity_failed_record_screenshot(data[0], image_list)
                else:
                    pass
            else:
                pass

        except Exception as e:
            error_log.store_error_log(str(e))              


class GetTaskCompletedData(QThread):
    gettask_completed_signal = pyqtSignal()

    def __init__(self, project_list):
        super().__init__()
        self.project_list = project_list
        self.today_date = datetime.now().date()
        self.previous_three_days = [
            self.today_date - timedelta(days=i) for i in range(3)
        ]
        self.formatted_previous_dates = [
            date.strftime("%d-%m-%Y") for date in self.previous_three_days
        ]

    def run(self):
        try:
            task_data_sqllite = db_helper.get_all_completed_list()
            for project_id in self.project_list:
                tasks_backend = reqs.get_task_completed_list(
                    token=db_helper.get_user_token(),
                    project_id=project_id["id"],
                    user_id=db_helper.get_user_id(),
                )

                for task_data_back in tasks_backend.json()["data"]:
                    _data = json.loads(task_data_back["title"])

                    if _data["create_task_date"] in self.formatted_previous_dates:
                        if all(
                            _data["temp_id"] not in task_tuple
                            for task_tuple in task_data_sqllite
                        ):
                            task_db.store_create_task(
                                _data["temp_id"],
                                project_id["id"],
                                task_data_back["id"],
                                _data["task"],
                                _data["status"],
                                _data["description"],
                                _data["create_task_date"],
                                _data["create_task_time"],
                                _data["update_task_date"],
                                _data["update_task_time"],
                                1,
                            )

                        else:
                            continue
                    else:
                        continue
            self.gettask_completed_signal.emit()

        except Exception as e:
            error_log.store_error_log(str(e))
            pass


class GetTaskData(QThread):
    gettask_signal = pyqtSignal()

    def __init__(self, project_list):
        super().__init__()
        self.project_list = project_list

    def run(self):
        try:
            for project_id in self.project_list:
                tasks_backend = reqs.get_task_list(
                    token=db_helper.get_user_token(),
                    project_id=project_id["id"],
                    user_id=db_helper.get_user_id(),
                )
                task_data_sqllite = db_helper.get_create_task_data_by_projectid(
                    project_id["id"]
                )

                for task_data_back in tasks_backend.json()["data"]:
                    _data = json.loads(task_data_back["title"])
                    if all(
                        _data["temp_id"] not in task_tuple
                        for task_tuple in task_data_sqllite
                    ):
                        task_db.store_create_task(
                            _data["temp_id"],
                            project_id["id"],
                            task_data_back["id"],
                            _data["task"],
                            _data["status"],
                            _data["description"],
                            _data["create_task_date"],
                            _data["create_task_time"],
                            _data["update_task_date"],
                            _data["update_task_time"],
                            0,
                        )

                    else:
                        continue
            self.gettask_signal.emit()

        except Exception as e:
            error_log.store_error_log(str(e))
            pass


class GetUnCompletedTaskData(QThread):
    getuncompletedtask_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            task_data = db_helper.get_all_uncompleted_list()
            today_date = datetime.now().strftime("%d-%m-%Y")

            for data in task_data:
                if data[7] != today_date:
                    payload = {
                        "temp_id": data[0],
                        "task": data[3],
                        "description": data[4],
                        "create_task_date": data[5],
                        "create_task_time": data[6],
                        "update_task_date": today_date,
                        "update_task_time": datetime.now().strftime("%I:%M %p"),
                        "status": data[9],
                    }
                    task_db.update_task_date(
                        data[0], today_date, datetime.now().strftime("%I:%M %p")
                    )
                    reqs.edit_task(
                        db_helper.get_user_token(),
                        data[1],
                        json.dumps(payload),
                        db_helper.get_user_id(),
                        data[2],
                    )
            self.getuncompletedtask_signal.emit()

        except Exception as e:
            error_log.store_error_log(str(e))
            pass


class RemoveTaskDataByDate(QThread):
    removetask_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            while True:
                time.sleep(1800)
                self.today_date = datetime.now().date()
                self.previous_three_days = [
                    self.today_date - timedelta(days=i) for i in range(3)
                ]
                self.formatted_previous_dates = [
                    date.strftime("%d-%m-%Y") for date in self.previous_three_days
                ]
                task_data = db_helper.get_completed_task()
                for data in task_data:
                    if data[5] not in self.formatted_previous_dates:
                        delete_create_task(data[0])
                    else:
                        continue
        except Exception as e:
            error_log.store_error_log(str(e))
            pass
