import os, uuid, json
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
import time as t
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from helpers import get_active_window_title
import db.user_db as user_db
import db.db_helper as db_helper
from models import Activity, TimeEntry
from dialogbox.add_task import Addtask
from dialogbox.edit_task import Edittask
from dialogbox.menu_bar import Menubar
import dialogbox.send_data as send_data 
from dialogbox.open_task import OpenTask
import dialogbox.error_msg as error_msg
import dialogbox.loader2 as loader2
import dialogbox.login as login
import dialogbox.quit as quit
import db.activity_log_db as activity_log_db
import db.task_db as task_db
import db.error_log as error_log
import db.dbconn as dbconn
from endpoints import requests_helper as reqs
from browserdatadumps import chrome, firefox
import workers.worker_processor as workers_processor
import server_check.server_check as server_check
import db.error_log as error_log
import db.activity_failed_log as activity_failed_log

os.chdir(os.path.dirname(os.path.abspath(__file__)))
if sys.platform in ["Windows", "win32", "cygwin"]:
    from ctypes import Structure, byref, c_uint, sizeof, windll

    class LASTINPUTINFO(Structure):
        _fields_ = [
            ("cbSize", c_uint),
            ("dwTime", c_uint),
        ]

    def get_idle_duration(flag):
        if flag:
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = sizeof(lastInputInfo)
            windll.user32.GetLastInputInfo(byref(lastInputInfo))
            millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis / 1000.0
        else:
            return None

elif sys.platform in ["linux", "linux2"]:
    from idle_time import IdleMonitor

    monitor = IdleMonitor.get_monitor()

    def get_idle_duration(flag):
        if flag:
            return monitor.get_idle_time()
        else:
            return None

else:

    def get_idle_duration(flag):
        if flag:
            pass
        return 0


def show_error_message(error_message):
    error_dialog = error_msg.Error_window()
    error_dialog.error_msg_lable.setText(error_message)
    error_dialog.exec_()


class Login(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.ui = login.Login_window()
        self.ui.setupUi(self)
        self.ui.loginbtn.clicked.connect(self.login_function)
        self.ui.error_label.setVisible(False)

    def login_function(self):
        try:
            auth = reqs.authenticate(
                email=self.ui.email_txt.text(), password=self.ui.password_txt.text()
            )
            print(auth.status_code)
            if auth.status_code == 201:
                data = auth.json()
                user_db.store_user_data(
                    data["data"]["user"]["id"],
                    data["data"]["user"]["first_name"],
                    data["data"]["user"]["last_name"],
                    data["data"]["user"]["email"],
                    data["data"]["authentication"]["accessToken"],
                )
                self.dashboard_window = Dashboard()
                self.dashboard_window.show()
                self.close()
            elif auth.status_code == 401:
                self.ui.error_label.setVisible(True)
                self.ui.error_label.setText("Invalid Auth Details")
            else:
                show_error_message("Sorry! Admin does not provide a project")
        except Exception as e:
            error_log.store_error_log(str(e))
            pass


class Dashboard(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        try:
            token = db_helper.get_user_token()
            project_list = reqs.get_project_list(token)
            project_data = project_list.json()

        except Exception as err:
            show_error_message("Something Went Wrong,Please contact the Admin!!")
            sys.exit(app.exec_())

        self.project_list_data = project_data["data"]

        self.setupUi(self)

        self.create_task_btn.clicked.connect(self.show_create_task_dialog)
        self.hour = "00"
        self.minute = "00"
        self.second = "00"
        self.count = "00"
        self.selected_widget = None
        self.startWatch = False
        self.image_list = []
        self.final_payload = {}
        self.project_id = None
        self.project_name = None
        self.completed_task_id = None
        self.task_payloads = []

        self.edit_task_id = ""
        # activity tracker stuff
        self.activities = []
        self.actual_activity = get_active_window_title()
        self.actual_time_entry_start_time = datetime.now()

        self.activity_tracker_flag = True
        self.idleTime = 0
        self.total_idle_time = 0

        self._date_start_time = ""
        self._date_end_time = ""
        self.currant_start_stop_btn = ""
        # self.currant_start_stop_btn_playing=""
        # self.completeTaskButton.clicked.connect(self.on_complete)

        # Create timer object
        self.timer = QTimer(self)
        self.time = QTime(0, 0)
        # self.alert_box = alertbox()
        self.screenshot_thread = workers_processor.ScreenshotThread()
        self.screenshot_thread.screenshot_signal.connect(self.handle_screenshot)

        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        # # Add a method with the timer
        self.backend_thread = workers_processor.BackendCommunication()
        self.backend_thread.send_data_signal.connect(self.send_data_to_backend)

        self.sqllite_thread = workers_processor.SqlliteCommunication()
        self.sqllite_thread.send_data_sqllite_signal.connect(self.send_data_to_sqllite)

        self.timer_thread = workers_processor.TimerThread()
        self.timer_thread.timer_signal.connect(self.handle_time)

        self.gettask_thread = workers_processor.GetTaskData(self.project_list_data)
        self.gettask_thread.gettask_signal.connect(self.gettask_data_finished)
        self.gettask_thread.start()

        self.getcompleted_thread = workers_processor.GetTaskCompletedData(
            self.project_list_data
        )
        self.getcompleted_thread.gettask_completed_signal.connect(
            self.getcompleted_task_data_finished
        )
        self.getcompleted_thread.start()

        self.removetask_thread = workers_processor.RemoveTaskDataByDate()
        self.removetask_thread.removetask_signal.connect(self.removetask_data_finished)
        self.removetask_thread.start()

        self.getuncompletedtask_thread = workers_processor.GetUnCompletedTaskData()
        self.getuncompletedtask_thread.getuncompletedtask_signal.connect(
            self.getuncompletedtask_data_finished
        )
        self.getuncompletedtask_thread.start()
        self.sendallactivitylogs_thread = workers_processor.SendAllActivityLogs()
        self.sendallactivitylogs_thread.sendallactivitylogs_singal.connect(self.sendallactivitylogs_finished)
        
        self.sendallactivityfailedlogs_thread=workers_processor.SendAllActivityFailedLogs()
        self.sendallactivityfailedlogs_thread.sendallactivityfailedlogs_singal.connect(self.sendallactivityfailedlogs_finished)

        self.gettimeduration()
        self.timer.timeout.connect(self.showCounter)
        # self.show_menu_bar_dialog()
        # self.timer.start(1000)

        # self.closeEvent = self.demo()
        # self.clockLabel.setText(self.time.toString("hh:mm:ss"))
        # self.clockLabel.setTe65xt("00:00:00")
        # Call start() method to modify the timer value

        self.idle_time_list = []
        self._tmp_idle_time = []
        self.task_row_widgets = {}
        self.task_list_data = []
        self.project_name_list = []
        self.project_id_list = []
        self.task_names = []
        self.task_ids = []
        self.current_project_detail = {}
        self.current_task_detail = {}
        self.project_current_index = None
        self.task_current_index = None
        self.task_name = None
        self.task_id = None
        self.start_update_duration = None

    def setupUi(self, mainwindow):
        self.project_widgets = []
        self.task_widgets = []
        self.time_left_label_list = []
        self.completed_task_widgets = []
        self.is_playing = False
        self.buttons = []
        self.selected_widgets = {}
        self.startStopButton_flag = "Start"
        mainwindow.setObjectName("mainwindow")
        mainwindow.resize(1408, 812)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(mainwindow.sizePolicy().hasHeightForWidth())
        mainwindow.setSizePolicy(sizePolicy)
        mainwindow.setMinimumSize(QtCore.QSize(3, 0))
        self.exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal", "resource" ,"timeguruz.png")
                # os.path.join(os.getcwd(), "resource/timeguruz.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        mainwindow.setWindowIcon(icon)
        mainwindow.setStyleSheet(
            "background-color: rgb(255, 255, 255);\n"
            "border-right-color: rgb(63, 63, 63);"
        )
        self.centralwidget = QtWidgets.QWidget(mainwindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.leftsidebar = QtWidgets.QWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftsidebar.sizePolicy().hasHeightForWidth())
        self.leftsidebar.setSizePolicy(sizePolicy)
        self.leftsidebar.setMinimumSize(QtCore.QSize(310, 0))
        self.leftsidebar.setMaximumSize(QtCore.QSize(310, 16777215))
        self.leftsidebar.setToolTip("")

        self.leftsidebar.setObjectName("leftsidebar")
        self.leftsidebar.setStyleSheet(
            "#leftsidebar{border-right: 1px solid  rgb(211, 215, 207);\n"
            "border-left: 1px solid  rgb(211, 215, 207);\n"
            "}\n"
            "\n"
            ""
        )
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.leftsidebar)

        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(1, 0, 1, 0)
        self.verticalLayout_5.setSpacing(0)
        self.widget = QtWidgets.QWidget(self.leftsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QtCore.QSize(0, 0))
        self.widget.setMaximumSize(QtCore.QSize(16777215, 270))
        self.widget.setObjectName("widget")
        self.widget_4 = QtWidgets.QWidget(self.widget)
        self.widget_4.setGeometry(QtCore.QRect(0, 0, 311, 43))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_4.sizePolicy().hasHeightForWidth())
        self.widget_4.setSizePolicy(sizePolicy)
        self.widget_4.setObjectName("widget_4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_4)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.clockLabel = QtWidgets.QLabel(self.widget_4)
        self.clockLabel.setMinimumSize(QtCore.QSize(0, 30))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.clockLabel.sizePolicy().hasHeightForWidth())
        self.clockLabel.setSizePolicy(sizePolicy)
        # self.clockLabel.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.clockLabel.setFont(font)
        self.clockLabel.setStyleSheet(
            "\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "#clockLabel{\n"
            "width: 133px;\n"
            "background-color: rgb(46, 52, 54);\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 400;\n"
            "font-size: 25px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(255, 255, 255);\n"
            "}\n"
            "#clockLabel:hover{\n"
            "    background-color: rgb(46, 52, 54);\n"
            "    color: rgb(255, 255, 255);\n"
            "    \n"
            "}"
        )
        self.clockLabel.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.clockLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.clockLabel.setObjectName("clockLabel")
        self.horizontalLayout_2.addWidget(self.clockLabel)
        self.project_title_main = QtWidgets.QLabel(self.widget)
        self.project_title_main.setGeometry(QtCore.QRect(0, 50, 301, 31))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.project_title_main.sizePolicy().hasHeightForWidth()
        )
        self.project_title_main.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.project_title_main.setFont(font)
        self.project_title_main.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size:18px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: #1C1F27;\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.project_title_main.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.project_title_main.setAlignment(QtCore.Qt.AlignCenter)
        self.project_title_main.setObjectName("project_title_main")
        self.task_title_left = QtWidgets.QLabel(self.widget)
        self.task_title_left.setGeometry(QtCore.QRect(0, 80, 301, 31))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.task_title_left.sizePolicy().hasHeightForWidth()
        )
        self.task_title_left.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.task_title_left.setFont(font)
        self.task_title_left.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.task_title_left.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.task_title_left.setAlignment(QtCore.Qt.AlignCenter)
        self.task_title_left.setObjectName("task_title_left")
        self.line_3 = QtWidgets.QFrame(self.widget)
        self.line_3.setGeometry(QtCore.QRect(0, 130, 131, 31))
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_3.setObjectName("line_3")
        self.mainbtn = QtWidgets.QPushButton(self.widget)
        self.mainbtn.setGeometry(QtCore.QRect(130, 110, 51, 51))
        self.mainbtn.setStyleSheet("#mainbtn{\n" "border-radius:10px;}")
        self.mainbtn.setText("")
        self.mainbtn.setEnabled(False)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal","resource" , "play-big@2x.png")
                # os.path.join(os.getcwd(), "resource/play-big@2x.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )

        self.mainbtn.setIcon(icon2)
        self.mainbtn.setIconSize(QtCore.QSize(50, 50))
        self.mainbtn.setObjectName("mainbtn")
        self.line = QtWidgets.QFrame(self.widget)
        self.line.setGeometry(QtCore.QRect(120, 160, 71, 31))
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.line_2 = QtWidgets.QFrame(self.widget)
        self.line_2.setGeometry(QtCore.QRect(180, 130, 131, 31))
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.project_time_lbl = QtWidgets.QLabel(self.widget)
        self.project_time_lbl.setGeometry(QtCore.QRect(40, 150, 71, 21))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.project_time_lbl.sizePolicy().hasHeightForWidth()
        )
        self.project_time_lbl.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.project_time_lbl.setFont(font)
        self.project_time_lbl.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.project_time_lbl.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.project_time_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.project_time_lbl.setObjectName("project_time_lbl")
        self.company_name = QtWidgets.QLabel(self.widget)
        self.company_name.setGeometry(QtCore.QRect(0, 230, 311, 41))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.company_name.sizePolicy().hasHeightForWidth())
        self.company_name.setSizePolicy(sizePolicy)
        self.company_name.setStyleSheet(
            "width: 133px;\n"
            "background-color: rgb(209, 209, 209);\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "padding-left:7px;\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size:15px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: #1C1F27;\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.company_name.setObjectName("company_name")
        self.search_wid = QtWidgets.QWidget(self.widget)
        self.search_wid.setGeometry(QtCore.QRect(0, 190, 307, 41))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.search_wid.sizePolicy().hasHeightForWidth())
        self.search_wid.setSizePolicy(sizePolicy)
        self.search_wid.setAccessibleName("")
        self.search_wid.setStyleSheet(
            "#search_wid{\n" "border-top: 1px solid  rgb(211, 215, 207);\n" "}"
        )
        self.search_wid.setObjectName("search_wid")
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout(self.search_wid)
        self.horizontalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")

        self.search_project = QtWidgets.QLineEdit(self.search_wid)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.search_project.textChanged.connect(self.search_project_list)
        self.search_project.setEnabled(True)
        self.search_project.setMinimumSize(QtCore.QSize(0, 0))
        self.search_project.setStyleSheet("")
        sizePolicy.setHeightForWidth(
            self.search_project.sizePolicy().hasHeightForWidth()
        )
        self.search_project.setInputMask("")
        self.search_project.setFrame(False)
        self.search_project.setObjectName("search_project")
        self.search_project.setStyleSheet(
            """
                                          QLineEdit {
                border: 1px solid #7f7f7f;
                border-radius: 20px;
                padding-left: 2px; /* Adjusted to accommodate the search icon */
                min-width: 10em;
                background-color: #f0f0f0;
                color: #333;
            }
                                          """
        )
        self.horizontalLayout_12.addWidget(self.search_project)

        search_icon = QtGui.QIcon(
            os.path.join(self.exe_dir, "_internal","resource" , "search@2x.png")
            # os.path.join(os.getcwd(), "resource/search@2x.png")
        )
        search_action = QtWidgets.QAction(search_icon, "", self.search_project)
        self.search_project.addAction(
            search_action, QtWidgets.QLineEdit.LeadingPosition
        )
        self.project_duration = QtWidgets.QLabel(self.widget)
        self.project_duration.setGeometry(QtCore.QRect(30, 170, 91, 16))
        self.project_duration.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 10px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.project_duration.setAlignment(QtCore.Qt.AlignCenter)
        self.project_duration.setObjectName("project_duration")
        self.total_time = QtWidgets.QLabel(self.widget)
        self.total_time.setGeometry(QtCore.QRect(180, 150, 111, 21))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.total_time.sizePolicy().hasHeightForWidth())
        self.total_time.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.total_time.setFont(font)
        self.total_time.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.total_time.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.total_time.setAlignment(QtCore.Qt.AlignCenter)
        self.total_time.setObjectName("total_time")
        self.today_duration = QtWidgets.QLabel(self.widget)
        self.today_duration.setGeometry(QtCore.QRect(190, 170, 91, 20))
        self.today_duration.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 10px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.today_duration.setAlignment(QtCore.Qt.AlignCenter)
        self.today_duration.setObjectName("today_duration")
        self.verticalLayout_5.addWidget(self.widget)
        self.scrollArea = QtWidgets.QScrollArea(self.leftsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setMinimumSize(QtCore.QSize(0, 100))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 292, 478))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.scrollArea.setStyleSheet("border: rgb(72, 72, 72);")
        data_to_display = reqs.get_daily_stats(token=db_helper.get_user_token())
        respnse_data_json = data_to_display.json()
        response_data = respnse_data_json["data"]
        for i in range(len(self.project_list_data)):
            self.project_widget = QtWidgets.QWidget(self.scrollAreaWidgetContents)
            self.project_widget.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            sizePolicy = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
            )
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(
                self.project_widget.sizePolicy().hasHeightForWidth()
            )
            self.project_widget.setSizePolicy(sizePolicy)
            self.project_widget.setLayoutDirection(QtCore.Qt.LeftToRight)

            self.project_widget.setObjectName(f"project_widget")

            self.horizontalLayout_13 = QtWidgets.QHBoxLayout(self.project_widget)
            self.horizontalLayout_13.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
            self.horizontalLayout_13.setContentsMargins(0, 8, 2, -1)
            self.horizontalLayout_13.setObjectName("horizontalLayout_13")
            self.project_title_left = QtWidgets.QLabel(self.project_widget)
            sizePolicy = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
            )
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(
                self.project_title_left.sizePolicy().hasHeightForWidth()
            )
            self.project_title_left.setSizePolicy(sizePolicy)
            font = QtGui.QFont()
            font.setFamily("Arial")
            font.setPointSize(-1)
            font.setBold(False)
            font.setItalic(False)
            font.setWeight(50)
            font.setKerning(False)
            self.project_title_left.setFont(font)
            self.project_widget.setStyleSheet(
                "\n"
                f"#project_widget" + "{\n"
                "                background-color: white;\n"
                "                border-bottom: 1px solid rgb(211, 211, 211);\n"
                "            }\n"
                f"#project_widget" + ":hover{\n"
                "                background-color: white;\n"
                "                border: 1px solid rgb(69, 130, 255);\n"
                "            }\n"
                "#btn_left{\n"
                "margin-left:5px;}"
                "#project_title_left{\n"
                "margin-left:1px;}"
            )
            self.project_title_left.setObjectName("project_title_left")
            self.horizontalLayout_13.addWidget(self.project_title_left)
            self.time_left_label = QtWidgets.QLabel(self.project_widget)
            sizePolicy = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
            )
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(
                self.time_left_label.sizePolicy().hasHeightForWidth()
            )
            self.time_left_label.setSizePolicy(sizePolicy)
            self.time_left_label.setStyleSheet(
                "color: rgb(0, 0, 0);\n" "margin-right:3px;"
            )
            self.time_left_label.setAlignment(QtCore.Qt.AlignCenter)
            self.time_left_label.setObjectName("time_left_label")
            self.time_left_label_list.append(self.time_left_label)
            self.time_left_label.setText(
                "00:00"
                if response_data[i]["duration"] is None
                else ":".join(response_data[i]["duration"].split(":")[0:2])
            )
            self.horizontalLayout_13.addWidget(self.time_left_label)
            self.verticalLayout_7.addWidget(self.project_widget)
            self.project_widgets.append(self.project_widget)
            self.project_title_left.setText(
                self.project_list_data[i]["name"]
                if len(self.project_list_data[i]["name"]) <= 12
                else self.project_list_data[i]["name"][
                    0 : (len(self.project_list_data[i]["name"]) - 5)
                ]
                + "..."
            )
            # self.time_left_label.setText("00:00")
            # self.project_widget.mouseReleaseEvent = self.handle_project_widget_click
            self.project_widget.mousePressEvent = (
                lambda event, id=self.project_list_data[i][
                    "id"
                ], title=self.project_list_data[i][
                    "name"
                ]: self.show_rightside_main_win(
                    id, title
                )
            )
        self.widget_5 = QtWidgets.QWidget(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_5.sizePolicy().hasHeightForWidth())
        self.widget_5.setSizePolicy(sizePolicy)
        self.widget_5.setObjectName("widget_5")
        self.verticalLayout_7.addWidget(self.widget_5)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_5.addWidget(self.scrollArea)
        self.horizontalLayout.addWidget(self.leftsidebar)
        self.rightsidebar = QtWidgets.QWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rightsidebar.sizePolicy().hasHeightForWidth())
        self.rightsidebar.setSizePolicy(sizePolicy)
        self.rightsidebar.setMinimumSize(QtCore.QSize(0, 0))
        self.rightsidebar.setStyleSheet(
            "#rightsidebar{\n" "width:auto;\n" "height:auto;}"
        )
        self.rightsidebar.setObjectName("rightsidebar")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.rightsidebar)
        self.verticalLayout.setContentsMargins(1, 0, 1, 0)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget_2 = QtWidgets.QWidget(self.rightsidebar)
        self.widget_2.setVisible(True)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy)
        self.widget_2.setMinimumSize(QtCore.QSize(0, 0))
        self.widget_2.setMaximumSize(QtCore.QSize(16777215, 40))
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_2)

        self.horizontalLayout_3.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.tasks = QtWidgets.QLabel(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tasks.sizePolicy().hasHeightForWidth())
        self.tasks.setSizePolicy(sizePolicy)
        self.tasks.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(15)
        font.setBold(True)
        font.setWeight(75)
        self.tasks.setFont(font)
        self.tasks.setObjectName("tasks")
        self.horizontalLayout_3.addWidget(self.tasks)
        self.menu_btn1 = QtWidgets.QPushButton(self.widget_2)
        self.menu_btn1.setEnabled(False)
        self.menu_btn1.clicked.connect(self.show_menu_bar_dialog)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.menu_btn1.sizePolicy().hasHeightForWidth())
        self.menu_btn1.setSizePolicy(sizePolicy)
        self.menu_btn1.setStyleSheet("#menu_btn1{\n" "border-radius:10px;\n" "}")
        self.menu_btn1.setText("")
        icon5 = QtGui.QIcon()
        icon5.addPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal", "resource" ,"more-menu-v@2x.png")
                # os.path.join(os.getcwd(), "resource/more-menu-v@2x.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.menu_btn1.setIcon(icon5)
        self.menu_btn1.setIconSize(QtCore.QSize(20, 20))
        self.menu_btn1.setObjectName("menu_btn1")
        self.horizontalLayout_3.addWidget(self.menu_btn1)
        self.verticalLayout.addWidget(self.widget_2)
        self.widget_3 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy)
        self.widget_3.setMinimumSize(QtCore.QSize(0, 0))
        self.widget_3.setMaximumSize(QtCore.QSize(16777215, 30))
        self.widget_3.setObjectName("widget_3")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget_3)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.project_title_right = QtWidgets.QLabel(self.widget_3)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.project_title_right.sizePolicy().hasHeightForWidth()
        )
        self.project_title_right.setSizePolicy(sizePolicy)
        self.project_title_right.setMinimumSize(QtCore.QSize(0, 0))
        self.project_title_right.setMaximumSize(QtCore.QSize(16777215, 16777212))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        self.project_title_right.setFont(font)
        self.project_title_right.setLineWidth(0)
        self.project_title_right.setObjectName("project_title_right")
        self.verticalLayout_2.addWidget(self.project_title_right)
        self.verticalLayout.addWidget(self.widget_3)
        self.widget_6 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_6.sizePolicy().hasHeightForWidth())
        self.widget_6.setSizePolicy(sizePolicy)
        self.widget_6.setMinimumSize(QtCore.QSize(0, 0))
        self.widget_6.setObjectName("widget_6")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.widget_6)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 3)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.listbox = QtWidgets.QComboBox(self.widget_6)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listbox.sizePolicy().hasHeightForWidth())
        self.listbox.setSizePolicy(sizePolicy)
        self.listbox.setMinimumSize(QtCore.QSize(0, 0))
        self.listbox.setMaximumSize(QtCore.QSize(100, 100))
        self.listbox.setEditable(False)
        self.listbox.setObjectName("listbox")
        self.listbox.addItem("")
        self.listbox.addItem("")
        self.listbox.setStyleSheet(
            """
                                   QComboBox {
                border: 1px solid #7f7f7f;
                border-radius: 5px;
                padding: 5px;
                min-width: 6em;
                background-color: white;
                color: black;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: darkgray;
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                background-color: #dcdcdc;
            }

            QComboBox::down-arrow {
                image: url("%(image_path)s");
                width: 10px;  
                height: 10px; 
            }
            """
            % {
                "image_path":
                   os.path.join(self.exe_dir, "_internal","resource" , "down_arrow2.png")
                # os.path.join(os.getcwd(), "resource/down_arrow2.png")
            }
        )
        self.listbox.setEnabled(False)
        self.listbox.currentTextChanged.connect(self.on_combo_box_changed)
        self.horizontalLayout_5.addWidget(self.listbox)
        self.comboBox = QtWidgets.QComboBox(self.widget_6)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox.sizePolicy().hasHeightForWidth())
        self.comboBox.setSizePolicy(sizePolicy)
        self.comboBox.setStyleSheet(
            "QComboBox {\n"
            "                border: 1px solid #7f7f7f;\n"
            "                border-radius: 5px;\n"
            "                padding: 5px;\n"
            "                min-width: 4em;\n"
            "                background-color: white;\n"
            "                color: black;\n"
            "            }\n"
            "            \n"
            "            QComboBox::drop-down {\n"
            "                subcontrol-origin: padding;\n"
            "                subcontrol-position: top right;\n"
            "                width: 20px;\n"
            "                border-left-width: 1px;\n"
            "                border-left-color: darkgray;\n"
            "                border-left-style: solid;\n"
            "                border-top-right-radius: 3px;\n"
            "                border-bottom-right-radius: 3px;\n"
            "                background-color: #dcdcdc;\n"
            "            }\n"
            "\n"
            "            QComboBox::down-arrow {\n"
            '                image: url("%(image_path)s");\n'
            "                width: 10px;  \n"
            "                height: 10px; \n"
            "            }"
            % {
                "image_path":
                   os.path.join(self.exe_dir, "_internal","resource" , "down_arrow2.png")
                # os.path.join(os.getcwd(), "resource/down_arrow2.png")
            }
        )
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setVisible(False)
        self.horizontalLayout_5.addWidget(self.comboBox)
        self.checkBox = QtWidgets.QCheckBox(self.widget_6)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkBox.sizePolicy().hasHeightForWidth())
        self.checkBox.setSizePolicy(sizePolicy)
        self.checkBox.setMaximumSize(QtCore.QSize(200, 16777215))
        # self.checkBox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.checkBox.setFont(font)
        self.checkBox.setObjectName("checkBox")
        self.checkBox.stateChanged.connect(self.show_completed_task)
        self.horizontalLayout_5.addWidget(self.checkBox)
        self.refreshbutton = QtWidgets.QPushButton(self.widget_6)
        self.refreshbutton.clicked.connect(self.list_task_widget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.refreshbutton.sizePolicy().hasHeightForWidth()
        )
        self.refreshbutton.setSizePolicy(sizePolicy)
        self.refreshbutton.setStyleSheet(
            "QPushButton {\n"
            "\n"
            "                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,\n"
            "                                                  stop:0 #f0f0f0, stop:1 #c0c0c0); /* Gradient background */\n"
            "                 /* Dark border */\n"
            "                color: #000000; /* Black text */\n"
            "                padding: 5px 6px;\n"
            "                text-align: center;\n"
            "                font-size: 13px;\n"
            "                border-radius: 5px;\n"
            "            }\n"
            "            QPushButton:hover {\n"
            "                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,\n"
            "                                                  stop:0 #e0e0e0, stop:1 #a0a0a0); /* Darker gradient on hover */\n"
            "            }\n"
            "            QPushButton:pressed {\n"
            "                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,\n"
            "                                                  stop:0 #c0c0c0, stop:1 #808080); /* Even darker gradient on press */\n"
            "            }"
        )
        self.refreshbutton.setText("")
        icon6 = QtGui.QIcon()

        icon6.addPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal", "resource" ,"refresh.png")
                # os.path.join(os.getcwd(), "resource/refresh.png")
            )
        )
        self.refreshbutton.setIcon(icon6)
        self.refreshbutton.setObjectName("refreshbutton")
        self.refreshbutton.setEnabled(False)
        self.horizontalLayout_5.addWidget(self.refreshbutton)
        self.widget_12 = QtWidgets.QWidget(self.widget_6)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_12.sizePolicy().hasHeightForWidth())
        self.widget_12.setSizePolicy(sizePolicy)
        self.widget_12.setMinimumSize(QtCore.QSize(100, 0))
        self.widget_12.setObjectName("widget_12")
        self.horizontalLayout_5.addWidget(self.widget_12)
        self.widget_9 = QtWidgets.QWidget(self.widget_6)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_9.sizePolicy().hasHeightForWidth())
        self.widget_9.setSizePolicy(sizePolicy)
        self.widget_9.setObjectName("widget_9")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.widget_9)
        self.horizontalLayout_6.setContentsMargins(3, 3, 0, 3)
        self.horizontalLayout_6.setSpacing(3)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")

        self.search_task = QtWidgets.QLineEdit(self.widget_9)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.search_task.textChanged.connect(self.search_task_list)
        sizePolicy.setHeightForWidth(self.search_task.sizePolicy().hasHeightForWidth())
        self.search_task.setSizePolicy(sizePolicy)
        self.search_task.setObjectName("search_task")
        self.search_task.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #7f7f7f;
                border-radius: 2px;
                padding: 1px;
                padding-left: 2px; /* Adjusted to accommodate the search icon */
                min-width: 10em;
                background-color: #f0f0f0;
                color: #333;
            }
            QLineEdit:focus {
                border-color: #4d90fe;
            }
         
                                       """
        )
        self.horizontalLayout_6.addWidget(self.search_task)

        search_icon = QtGui.QIcon(
            os.path.join(self.exe_dir, "_internal", "resource" ,"search@2x.png")
            #   os.path.join(os.getcwd(), "resource/search@2x.png")
        )
        search_action = QtWidgets.QAction(search_icon, "", self.search_task)
        self.search_task.addAction(search_action, QtWidgets.QLineEdit.LeadingPosition)
        # self.search_task.setEnabled(False)
        self.horizontalLayout_5.addWidget(self.widget_9)
        self.widget_7 = QtWidgets.QWidget(self.widget_6)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_7.sizePolicy().hasHeightForWidth())
        self.widget_7.setSizePolicy(sizePolicy)
        self.widget_7.setMaximumSize(QtCore.QSize(100, 16777215))
        self.widget_7.setStyleSheet("")
        self.widget_7.setObjectName("widget_7")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.widget_7)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalLayout_5.addWidget(self.widget_7)
        self.verticalLayout.addWidget(self.widget_6)
        self.widget_8 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_8.sizePolicy().hasHeightForWidth())
        self.widget_8.setSizePolicy(sizePolicy)
        self.widget_8.setObjectName("widget_8")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.widget_8)
        self.horizontalLayout_7.setContentsMargins(2, 2, 6, 2)
        self.horizontalLayout_7.setSpacing(9)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.create_task = QtWidgets.QLineEdit(self.widget_8)
        # self.create_task.textChanged.connect(self.create_task_append)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.create_task.sizePolicy().hasHeightForWidth())
        self.create_task.setSizePolicy(sizePolicy)
        self.create_task.setObjectName("create_task")
        self.create_task.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #7f7f7f;
                border-radius: 5px;
                padding: 2px;
                min-width: 10em;
                background-color: white;
                color: black;
            }
            QLineEdit:focus {
                border-color: #4d90fe;
            } 
                                       
                                       """
        )
        self.create_task.setEnabled(False)
        self.horizontalLayout_7.addWidget(self.create_task)
        self.create_task_btn = QtWidgets.QPushButton(self.widget_8)
        # self.create_task_btn.clicked.connect(self.show_create_task_dialog)
        self.create_task_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.create_task_btn.sizePolicy().hasHeightForWidth()
        )
        self.create_task_btn.setSizePolicy(sizePolicy)
        self.create_task_btn.setText("")
        icon6 = QtGui.QIcon()

        icon6.addPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal", "resource" ,"add-task-plus@2x.png")
                # os.path.join(os.getcwd(), "resource/add-task-plus@2x.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.create_task_btn.setIcon(icon6)
        self.create_task_btn.setIconSize(QtCore.QSize(14, 14))
        self.create_task_btn.setObjectName("create_task_btn")
        self.create_task_btn.setStyleSheet(
            """
                                           QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #f0f0f0, stop:1 #c0c0c0); /* Gradient background */
                 /* Dark border */
                color: #000000; /* Black text */
                padding: 5px 6px;
                text-align: center;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #e0e0e0, stop:1 #a0a0a0); /* Darker gradient on hover */
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #c0c0c0, stop:1 #808080); /* Even darker gradient on press */
            }
                                           """
        )

        self.horizontalLayout_7.addWidget(self.create_task_btn)
        self.verticalLayout.addWidget(self.widget_8)
        self.widget_10 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_10.sizePolicy().hasHeightForWidth())
        self.widget_10.setSizePolicy(sizePolicy)
        self.widget_10.setMinimumSize(QtCore.QSize(0, 50))
        self.widget_10.setObjectName("widget_10")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.widget_10)
        self.horizontalLayout_8.setContentsMargins(5, 9, 2, 9)
        self.horizontalLayout_8.setSpacing(5)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.task_title = QtWidgets.QLabel(self.widget_10)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.task_title.sizePolicy().hasHeightForWidth())
        self.task_title.setSizePolicy(sizePolicy)
        self.task_title.setMinimumSize(QtCore.QSize(130, 0))
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.task_title.setFont(font)
        self.task_title.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.task_title.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.task_title.setAlignment(QtCore.Qt.AlignCenter)
        self.task_title.setObjectName("task_title")
        self.horizontalLayout_8.addWidget(self.task_title)
        self.line_4 = QtWidgets.QFrame(self.widget_10)
        self.line_4.setMinimumSize(QtCore.QSize(10, 0))
        self.line_4.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_4.setObjectName("line_4")
        self.horizontalLayout_8.addWidget(self.line_4)
        self.des_title = QtWidgets.QLabel(self.widget_10)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.des_title.sizePolicy().hasHeightForWidth())
        self.des_title.setSizePolicy(sizePolicy)
        self.des_title.setMinimumSize(QtCore.QSize(130, 0))
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.des_title.setFont(font)
        self.des_title.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.des_title.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.des_title.setAlignment(QtCore.Qt.AlignCenter)
        self.des_title.setObjectName("des_title")
        self.horizontalLayout_8.addWidget(self.des_title)
        self.line_5 = QtWidgets.QFrame(self.widget_10)
        self.line_5.setMinimumSize(QtCore.QSize(10, 0))
        self.line_5.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_5.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_5.setObjectName("line_5")
        self.horizontalLayout_8.addWidget(self.line_5)
        self.create_at_title = QtWidgets.QLabel(self.widget_10)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.create_at_title.sizePolicy().hasHeightForWidth()
        )
        self.create_at_title.setSizePolicy(sizePolicy)
        self.create_at_title.setMinimumSize(QtCore.QSize(130, 0))
        font = QtGui.QFont()
        font.setFamily("Inter")
        font.setPointSize(-1)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(87)
        self.create_at_title.setFont(font)
        self.create_at_title.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "text-align: center;\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.create_at_title.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.create_at_title.setAlignment(QtCore.Qt.AlignCenter)
        self.create_at_title.setObjectName("create_at_title")
        self.horizontalLayout_8.addWidget(self.create_at_title)
        self.line_6 = QtWidgets.QFrame(self.widget_10)
        self.line_6.setMinimumSize(QtCore.QSize(10, 0))
        self.line_6.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_6.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_6.setObjectName("line_6")
        self.horizontalLayout_8.addWidget(self.line_6)
        self.update_at_title = QtWidgets.QLabel(self.widget_10)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.update_at_title.sizePolicy().hasHeightForWidth()
        )
        self.update_at_title.setSizePolicy(sizePolicy)
        self.update_at_title.setStyleSheet(
            "width: 133px;\n"
            "height: 44px;\n"
            "\n"
            "/* Mobile/Heading H3/Bold */\n"
            "\n"
            "font-family: 'Inter';\n"
            "font-style: normal;\n"
            "font-weight: 700;\n"
            "font-size: 12px;\n"
            "line-height: 44px;\n"
            "/* identical to box height, or 157% */\n"
            "\n"
            "\n"
            "\n"
            "/* Neutral/800 */\n"
            "\n"
            "color: rgb(170, 170, 170);\n"
            "\n"
            "\n"
            "/* Inside auto layout */\n"
            "\n"
            ""
        )
        self.update_at_title.setObjectName("update_at_title")
        self.widget_10.setVisible(False)
        self.horizontalLayout_8.addWidget(self.update_at_title)
        self.verticalLayout.addWidget(self.widget_10)
        self.widget_13 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_13.sizePolicy().hasHeightForWidth())
        self.widget_13.setSizePolicy(sizePolicy)
        self.widget_13.setObjectName("widget_13")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.widget_13)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.task_list_scroll_area = QtWidgets.QScrollArea(self.widget_13)
        self.task_list_scroll_area.setStyleSheet("border: rgb(72, 72, 72);")
        self.task_list_scroll_area.setWidgetResizable(True)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.task_list_scroll_area.sizePolicy().hasHeightForWidth()
        )
        self.task_list_scroll_area.setSizePolicy(sizePolicy)
        self.task_list_scroll_area.setObjectName("task_list_scroll_area")
        self.task_list_scroll_area.setMinimumSize(QtCore.QSize(0, 400))
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 1056, 268))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.addWidget(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.widget2 = QtWidgets.QWidget(self.scrollAreaWidgetContents_2)
        self.widget2.setVisible(True)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget2.sizePolicy().hasHeightForWidth())
        self.widget2.setSizePolicy(sizePolicy)
        self.widget2.setObjectName("widget2")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.widget2)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.widget_19 = QtWidgets.QWidget(self.widget2)
        self.widget_19.setObjectName("widget_19")
        self.horizontalLayout_10.addWidget(self.widget_19)
        self.widget_11 = QtWidgets.QWidget(self.widget2)
        self.widget_11.setObjectName("widget_11")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.widget_11)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.widget_21 = QtWidgets.QWidget(self.widget_11)
        self.widget_21.setObjectName("widget_21")
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout(self.widget_21)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.label = QtWidgets.QLabel(self.widget_21)
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout_11.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.widget_21)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
        )
        self.label_2.setVisible(True)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setText("")
        self.label_2.setPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal","resource" , "no-task@2x.png")
                # os.path.join(os.getcwd(), "resource/no-task@2x.png")
            )
        )
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_11.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.widget_21)
        self.label_3.setVisible(True)
        self.label_3.setText("")
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_11.addWidget(self.label_3)
        self.verticalLayout_8.addWidget(self.widget_21)
        self.widget_22 = QtWidgets.QWidget(self.widget_11)
        self.widget_22.setObjectName("widget_22")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.widget_22)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.label_4 = QtWidgets.QLabel(self.widget_22)
        font = QtGui.QFont()
        font.setFamily("aakar")
        font.setPointSize(12)
        self.label_4.setFont(font)
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.verticalLayout_9.addWidget(self.label_4)
        self.verticalLayout_8.addWidget(self.widget_22)
        self.horizontalLayout_10.addWidget(self.widget_11)
        self.widget_20 = QtWidgets.QWidget(self.widget2)
        self.widget_20.setObjectName("widget_20")
        self.horizontalLayout_10.addWidget(self.widget_20)
        self.verticalLayout_6.addWidget(self.widget2)
        self.task_list_scroll_area.setWidget(self.scrollAreaWidgetContents_2)
        self.verticalLayout_4.addWidget(self.task_list_scroll_area)
        self.verticalLayout.addWidget(self.widget_13)
        self.widget_14 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_14.sizePolicy().hasHeightForWidth())
        self.widget_14.setSizePolicy(sizePolicy)
        self.widget_14.setMinimumSize(QtCore.QSize(0, 10))
        self.widget_14.setStyleSheet("background-color: rgb(209, 209, 209);")
        self.widget_14.setObjectName("widget_14")
        self.verticalLayout.addWidget(self.widget_14)
        self.widget_14.setVisible(False)
        self.widget_15 = QtWidgets.QWidget(self.rightsidebar)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_15.sizePolicy().hasHeightForWidth())
        self.widget_15.setSizePolicy(sizePolicy)
        self.widget_15.setObjectName("widget_15")
        self.widget_15.setMinimumSize(QtCore.QSize(0, 200))
        self.widget_15.setMaximumSize(QtCore.QSize(16777215, 200))
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.widget_15)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.widget_16 = QtWidgets.QWidget(self.widget_15)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_16.sizePolicy().hasHeightForWidth())
        self.widget_16.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.widget_16.setFont(font)
        self.widget_16.setObjectName("widget_16")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout(self.widget_16)
        self.horizontalLayout_9.setContentsMargins(0, 4, 4, 4)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.task_title_1 = QtWidgets.QLabel(self.widget_16)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.task_title_1.sizePolicy().hasHeightForWidth())
        self.task_title_1.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.task_title_1.setFont(font)
        self.task_title_1.setObjectName("task_title_1")
        self.horizontalLayout_9.addWidget(self.task_title_1)
        self.widget_17 = QtWidgets.QWidget(self.widget_16)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_17.sizePolicy().hasHeightForWidth())
        self.widget_17.setSizePolicy(sizePolicy)
        self.widget_17.setObjectName("widget_17")
        self.horizontalLayout_9.addWidget(self.widget_17)
        self.complete = QtWidgets.QPushButton(self.widget_16)
        self.complete.setVisible(False)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.complete.sizePolicy().hasHeightForWidth())
        self.complete.setSizePolicy(sizePolicy)
        self.complete.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.complete.setFont(font)
        self.complete.setObjectName("complete")
        self.complete.setStyleSheet(
            """
            QPushButton {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #f0f0f0, stop:1 #c0c0c0); /* Gradient background */
                /* Dark border */
            color: #000000; /* Black text */
            padding: 5px 18px;
            text-align: center;
            font-size: 13px;
            border-radius: 5px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e0e0e0, stop:1 #a0a0a0); /* Darker gradient on hover */
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #c0c0c0, stop:1 #808080); /* Even darker gradient on press */
            }
            """
        )
        self.horizontalLayout_9.addWidget(self.complete)
        self.menu_btn2 = QtWidgets.QPushButton(self.widget_16)
        self.menu_btn2.setVisible(False)
        self.menu_btn2.clicked.connect(self.show_open_task_dialog)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.menu_btn2.sizePolicy().hasHeightForWidth())
        self.menu_btn2.setSizePolicy(sizePolicy)
        self.menu_btn2.setStyleSheet("border-radius:10px;")
        self.menu_btn2.setText("")
        self.menu_btn2.setIcon(icon5)
        self.menu_btn2.setObjectName("menu_btn2")
        self.horizontalLayout_9.addWidget(self.menu_btn2)
        self.verticalLayout_3.addWidget(self.widget_16)
        # self.widget_16.setVisible(False)
        self.update_at_bottom = QtWidgets.QLabel(self.widget_15)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.update_at_bottom.sizePolicy().hasHeightForWidth()
        )
        self.update_at_bottom.setSizePolicy(sizePolicy)
        self.update_at_bottom.setStyleSheet("color: rgb(179, 179, 179);")
        self.update_at_bottom.setObjectName("update_at_bottom")
        self.verticalLayout_3.addWidget(self.update_at_bottom)
        self.task_title_2 = QtWidgets.QLabel(self.widget_15)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.task_title_2.sizePolicy().hasHeightForWidth())
        self.task_title_2.setSizePolicy(sizePolicy)
        self.task_title_2.setStyleSheet("color: rgb(0, 0, 0);")
        self.task_title_2.setObjectName("task_title_2")
        self.verticalLayout_3.addWidget(self.task_title_2)
        self.widget_18 = QtWidgets.QWidget(self.widget_15)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_18.sizePolicy().hasHeightForWidth())
        self.widget_18.setSizePolicy(sizePolicy)
        self.widget_18.setObjectName("widget_18")
        self.horizontalLayout_14 = QtWidgets.QHBoxLayout(self.widget_18)
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        self.widget_24 = QtWidgets.QWidget(self.widget_18)
        self.widget_24.setObjectName("widget_24")
        self.verticalLayout_10 = QtWidgets.QVBoxLayout(self.widget_24)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.no_task_lbl_3 = QtWidgets.QLabel(self.widget_24)
        self.no_task_lbl_3.setText("")
        self.no_task_lbl_3.setPixmap(
            QtGui.QPixmap(
                os.path.join(self.exe_dir, "_internal", "resource" ,"no-task@2x.png")
                # os.path.join(os.getcwd(), "resource/no-task@2x.png")
            )
        )
        self.no_task_lbl_3.setAlignment(QtCore.Qt.AlignCenter)
        self.no_task_lbl_3.setObjectName("no_task_lbl_3")
        self.verticalLayout_10.addWidget(self.no_task_lbl_3)
        self.no_task_lbl_2 = QtWidgets.QLabel(self.widget_24)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.no_task_lbl_2.sizePolicy().hasHeightForWidth()
        )
        self.no_task_lbl_2.setSizePolicy(sizePolicy)
        self.no_task_lbl_2.setAlignment(QtCore.Qt.AlignCenter)
        self.no_task_lbl_2.setObjectName("no_task_lbl_2")
        self.verticalLayout_10.addWidget(self.no_task_lbl_2)
        self.horizontalLayout_14.addWidget(self.widget_24)
        self.verticalLayout_3.addWidget(self.widget_18)
        self.verticalLayout.addWidget(self.widget_15)
        self.no_task_lbl_2.setVisible(False)
        self.no_task_lbl_3.setVisible(False)
        self.horizontalLayout.addWidget(self.rightsidebar)
        mainwindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(mainwindow)
        self.statusbar.setObjectName("statusbar")
        mainwindow.setStatusBar(self.statusbar)

        self.retranslateUi(mainwindow)
        QtCore.QMetaObject.connectSlotsByName(mainwindow)

    def on_combo_box_changed(self, text):
        if self.checkBox.isChecked():
            self.checkBox.setChecked(False)
        if text == "All Task":
            self.search_task.setEnabled(True)
            self.refreshbutton.setEnabled(True)
            self.checkBox.setEnabled(True)
            self.comboBox.setVisible(False)
            self.create_task.setEnabled(True)
            self.create_task_btn.setEnabled(True)
            self.list_task_widget()
        else:
            self.search_task.setEnabled(False)
            self.refreshbutton.setEnabled(False)
            self.comboBox.setVisible(True)
            self.checkBox.setEnabled(False)
            self.create_task.setEnabled(False)
            self.create_task_btn.setEnabled(False)
            self.comboBox.currentTextChanged.connect(self.list_task_by_order)

    def list_task_by_order(self, text):
        try:
            payload_data = db_helper.create_task_payload_by_order(text, self.project_id)
            self.task_widgets.clear()
            for i in reversed(range(1, self.verticalLayout_6.count())):
                widget = self.verticalLayout_6.itemAt(i).widget()
                if widget is not None:
                    self.verticalLayout_6.removeWidget(widget)
                    widget.setParent(None)
            if len(payload_data) == 0:
                self.refreshbutton.setEnabled(False)
                self.checkBox.setEnabled(False)
                self.widget_10.setVisible(False)
                self.widget2.setVisible(True)
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)
                self.task_title_2.setVisible(False)
                self.update_at_bottom.setVisible(False)
                self.task_title_1.setVisible(False)
                self.widget_16.setVisible(False)
                self.widget_14.setVisible(False)
                self.no_task_lbl_3.setVisible(False)
                self.no_task_lbl_2.setVisible(False)
                self.search_task.setEnabled(False)
                self.create_task.setEnabled(False)
                self.create_task_btn.setEnabled(False)
            elif text == "Completed":
                self.widget_10.setVisible(True)
                self.widget2.setVisible(False)
                self.checkBox.setEnabled(False)
                self.create_task.setEnabled(False)
                self.create_task_btn.setEnabled(False)
                for widget in self.completed_task_widgets[:]:
                    self.verticalLayout_6.removeWidget(widget)
                    widget.deleteLater()
                self.completed_task_widgets.clear()
                if hasattr(self, "blanck_box_right"):
                    self.blanck_box_right.setVisible(False)

                self.verticalLayout_6.setSpacing(2)
                for payload in db_helper.list_completed_data(self.project_id):
                    completed_task_row = QtWidgets.QWidget(
                        self.scrollAreaWidgetContents_2
                    )
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        completed_task_row.sizePolicy().hasHeightForWidth()
                    )

                    completed_task_row.setCursor(
                        QtGui.QCursor(QtCore.Qt.ForbiddenCursor)
                    )
                    completed_task_row.setSizePolicy(sizePolicy)
                    completed_task_row.setMinimumSize(QtCore.QSize(0, 40))
                    # self.create_task_row.setStyleSheet("background-color: rgb(46, 140, 255);")
                    completed_task_row.setStyleSheet(
                        "background-color: rgb(143, 255, 169);"
                    )
                    completed_task_row.setObjectName(f"completed_task_row")
                    task_row_layout = QtWidgets.QHBoxLayout(completed_task_row)
                    # task_row_layout.setContentsMargins(0, 0, 0, 0)
                    btn_right = QtWidgets.QPushButton()
                    btn_right.setStyleSheet(
                        "#btn_right{\n" "border-radius:30px;\n" "\n" "}"
                    )
                    btn_right.setText("")
                    icon4 = QtGui.QIcon()
                    icon4.addPixmap(
                        QtGui.QPixmap(
                            os.path.join(self.exe_dir, "_internal", "resource" ,"play-big@2x.png")
                            # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                        ),
                        QtGui.QIcon.Normal,
                        QtGui.QIcon.Off,
                    )
                    btn_right.setIcon(icon4)
                    btn_right.setIconSize(QtCore.QSize(20, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        btn_right.sizePolicy().hasHeightForWidth()
                    )
                    btn_right.setSizePolicy(sizePolicy)
                    btn_right.setObjectName(f"btn_right_{str(uuid.uuid4)[0:4]}")
                    btn_right.setContentsMargins(0, 0, 0, 0)
                    btn_right.setEnabled(False)
                    task_row_layout.addWidget(btn_right)
                    task_des_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(task_des_text)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        task_des_text.sizePolicy().hasHeightForWidth()
                    )
                    task_des_text.setSizePolicy(sizePolicy)
                    task_des_text.setMaximumSize(QtCore.QSize(100, 16777215))
                    task_des_text.setMinimumSize(QtCore.QSize(100, 16777215))
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    task_des_text.setFont(font)
                    task_des_text.setStyleSheet(
                        "#task_des_text{\n" "color: rgb(0, 0, 0);\n" "margin-left:5px;}"
                    )
                    task_des_text.setObjectName("task_des_text")
                    widget_11 = QtWidgets.QWidget(completed_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        widget_11.sizePolicy().hasHeightForWidth()
                    )
                    widget_11.setSizePolicy(sizePolicy)
                    widget_11.setMinimumSize(QtCore.QSize(10, 16777215))
                    widget_11.setObjectName("widget_11")
                    task_row_layout.addWidget(widget_11)
                    description_text = QtWidgets.QLabel()

                    task_row_layout.addWidget(description_text)
                    self.verticalLayout_6.addWidget(completed_task_row)
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        description_text.sizePolicy().hasHeightForWidth()
                    )
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    description_text.setSizePolicy(sizePolicy)
                    description_text.setMinimumSize(QtCore.QSize(120, 0))
                    description_text.setMaximumSize(QtCore.QSize(120, 16777215))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    description_text.setFont(font)
                    description_text.setStyleSheet(" color: rgb(0, 0, 0);")
                    # self.description_text.setStyleSheet("color: rgb(255, 255, 255); ") # white color
                    description_text.setAlignment(
                        QtCore.Qt.AlignLeading
                        | QtCore.Qt.AlignLeft
                        | QtCore.Qt.AlignVCenter
                    )
                    description_text.setObjectName("description_text")
                    blanck_widget_box1 = QtWidgets.QWidget(completed_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box1.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box1.setSizePolicy(sizePolicy)
                    blanck_widget_box1.setMinimumSize(QtCore.QSize(4, 16777215))
                    blanck_widget_box1.setObjectName("blanck_widget_box1")
                    task_row_layout.addWidget(blanck_widget_box1)
                    create_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(create_at_text)
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_at_text.sizePolicy().hasHeightForWidth()
                    )
                    create_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    create_at_text.setFont(font)
                    create_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    create_at_text.setObjectName("create_at_text")
                    create_at_text.setMinimumSize(QtCore.QSize(110, 0))
                    create_at_text.setMaximumSize(QtCore.QSize(180, 16777215))
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    blanck_widget_box3 = QtWidgets.QWidget(completed_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box3.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box3.setSizePolicy(sizePolicy)
                    blanck_widget_box3.setObjectName("blanck_widget_box3")
                    blanck_widget_box3.setMinimumSize(QtCore.QSize(0, 16777215))
                    task_row_layout.addWidget(blanck_widget_box3)
                    blanck_widget_box2 = QtWidgets.QWidget(completed_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box2.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box2.setSizePolicy(sizePolicy)
                    blanck_widget_box2.setObjectName("blanck_widget_box2")
                    task_row_layout.addWidget(blanck_widget_box2)
                    update_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(update_at_text)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        update_at_text.sizePolicy().hasHeightForWidth()
                    )
                    update_at_text.setMaximumSize(QtCore.QSize(16777215, 16777215))
                    update_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    update_at_text.setFont(font)
                    update_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    update_at_text.setObjectName("update_at_text")
                    blanck_widget_box5 = QtWidgets.QWidget(completed_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box5.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box5.setSizePolicy(sizePolicy)
                    blanck_widget_box5.setObjectName("blanck_widget_box5")
                    task_row_layout.addWidget(blanck_widget_box5)
                    self.verticalLayout_6.addWidget(completed_task_row)
                    task_des_text.setText(payload["task"])
                    description_text.setText(payload["description"])
                    create_at_text.setText(
                        f"{payload['create_task_date']}"
                        + " "
                        + f"{payload['create_task_time']}"
                    )
                    update_at_text.setText(
                        f"{payload['update_task_date']}"
                        + " "
                        + f"{payload['update_task_time']}"
                    )
                    self.completed_task_widgets.append(completed_task_row)
                self.blanck_box_right = QtWidgets.QWidget(
                    self.scrollAreaWidgetContents_2
                )
                self.blanck_box_right.setObjectName("blanck_box_right")
                self.verticalLayout_6.addWidget(self.blanck_box_right)
                self.widget_14.setVisible(True)
                self.widget_16.setVisible(True)
                self.no_task_lbl_2.setVisible(True)
                self.no_task_lbl_3.setVisible(True)

            else:
                self.create_task.setEnabled(False)
                self.create_task_btn.setEnabled(False)
                self.comboBox.setEnabled(True)
                self.listbox.setEnabled(True)
                self.checkBox.setEnabled(False)
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)
                self.task_title_2.setVisible(False)
                self.update_at_bottom.setVisible(False)
                self.task_title_1.setVisible(False)
                self.widget_16.setVisible(False)
                self.widget_14.setVisible(False)
                self.no_task_lbl_3.setVisible(True)
                self.no_task_lbl_2.setVisible(True)
                self.search_task.setEnabled(True)
                self.widget_10.setVisible(True)
                self.widget2.setVisible(False)
                self.verticalLayout_6.setSpacing(2)
                if hasattr(self, "blanck_box_right"):
                    self.blanck_box_right.setVisible(False)
                self.verticalLayout_6.setSpacing(2)
                for payload in payload_data:
                    create_task_row = QtWidgets.QWidget(self.scrollAreaWidgetContents_2)
                    self.create_task_dynamic_row = create_task_row
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_task_row.sizePolicy().hasHeightForWidth()
                    )
                    self.create_task_dynamic_row.mousePressEvent = (
                        lambda event, task=payload["task"], update_date=payload[
                            "update_task_date"
                        ], update_time=payload["update_task_time"], description=payload[
                            "description"
                        ]: self.show_task_data_footer(
                            payload["id"], task, update_date, update_time, description
                        )
                    )
                    self.create_task_dynamic_row.setCursor(
                        QtGui.QCursor(QtCore.Qt.PointingHandCursor)
                    )
                    create_task_row.setSizePolicy(sizePolicy)
                    create_task_row.setMinimumSize(QtCore.QSize(0, 40))
                    # self.create_task_row.setStyleSheet("background-color: rgb(46, 140, 255);")
                    create_task_row.setStyleSheet(
                        "background-color: rgb(238, 238, 236);"
                    )
                    create_task_row.setObjectName(f"create_task_row")
                    task_row_layout = QtWidgets.QHBoxLayout(create_task_row)
                    # task_row_layout.setContentsMargins(0, 0, 0, 0)
                    btn_right = QtWidgets.QPushButton()
                    btn_right.setStyleSheet(
                        "#btn_right{\n" "border-radius:30px;\n" "\n" "}"
                    )
                    btn_right.setText("")
                    icon4 = QtGui.QIcon()
                    icon4.addPixmap(
                        QtGui.QPixmap(
                            os.path.join(self.exe_dir, "_internal","resource" , "play-big@2x.png")
                            # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                        ),
                        QtGui.QIcon.Normal,
                        QtGui.QIcon.Off,
                    )
                    btn_right.setIcon(icon4)
                    btn_right.setEnabled(False)
                    btn_right.setIconSize(QtCore.QSize(20, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        btn_right.sizePolicy().hasHeightForWidth()
                    )
                    btn_right.setSizePolicy(sizePolicy)
                    btn_right.setObjectName(f"btn_right_{str(uuid.uuid4)[0:4]}")
                    btn_right.clicked.connect(self.handle_task_play_button)
                    # btn_right.setGeometry(QtCore.QRect(10, 10, 21, 20))
                    btn_right.setContentsMargins(0, 0, 0, 0)

                    task_row_layout.addWidget(btn_right)
                    # task_row_layout.setSpacing(10)  # 10 pixels between widgets
                    # task_row_layout.setContentsMargins(5, 5, 5, 5)
                    task_des_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(task_des_text)
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        task_des_text.sizePolicy().hasHeightForWidth()
                    )
                    task_des_text.setSizePolicy(sizePolicy)
                    task_des_text.setMaximumSize(QtCore.QSize(100, 16777215))
                    task_des_text.setMinimumSize(QtCore.QSize(100, 16777215))
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    task_des_text.setFont(font)
                    task_des_text.setStyleSheet(
                        "#task_des_text{\n" "color: rgb(0, 0, 0);\n" "margin-left:5px;}"
                    )
                    task_des_text.setObjectName("task_des_text")
                    widget_11 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        widget_11.sizePolicy().hasHeightForWidth()
                    )
                    widget_11.setSizePolicy(sizePolicy)
                    widget_11.setMinimumSize(QtCore.QSize(10, 16777215))
                    widget_11.setObjectName("widget_11")
                    task_row_layout.addWidget(widget_11)
                    description_text = QtWidgets.QLabel()

                    task_row_layout.addWidget(description_text)
                    self.verticalLayout_6.addWidget(create_task_row)
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        description_text.sizePolicy().hasHeightForWidth()
                    )
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    description_text.setSizePolicy(sizePolicy)
                    description_text.setMinimumSize(QtCore.QSize(120, 0))
                    description_text.setMaximumSize(QtCore.QSize(120, 16777215))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    description_text.setFont(font)
                    description_text.setStyleSheet(" color: rgb(0, 0, 0);")
                    # self.description_text.setStyleSheet("color: rgb(255, 255, 255); ") # white color
                    description_text.setAlignment(
                        QtCore.Qt.AlignLeading
                        | QtCore.Qt.AlignLeft
                        | QtCore.Qt.AlignVCenter
                    )
                    description_text.setObjectName("description_text")
                    blanck_widget_box1 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box1.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box1.setSizePolicy(sizePolicy)
                    blanck_widget_box1.setMinimumSize(QtCore.QSize(4, 16777215))
                    blanck_widget_box1.setObjectName("blanck_widget_box1")
                    task_row_layout.addWidget(blanck_widget_box1)
                    create_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(create_at_text)
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_at_text.sizePolicy().hasHeightForWidth()
                    )
                    create_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    create_at_text.setFont(font)
                    create_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    create_at_text.setObjectName("create_at_text")
                    create_at_text.setMinimumSize(QtCore.QSize(110, 0))
                    create_at_text.setMaximumSize(QtCore.QSize(180, 16777215))
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    blanck_widget_box3 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box3.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box3.setSizePolicy(sizePolicy)
                    blanck_widget_box3.setObjectName("blanck_widget_box3")
                    blanck_widget_box3.setMinimumSize(QtCore.QSize(0, 16777215))
                    task_row_layout.addWidget(blanck_widget_box3)
                    blanck_widget_box2 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box2.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box2.setSizePolicy(sizePolicy)
                    blanck_widget_box2.setObjectName("blanck_widget_box2")
                    task_row_layout.addWidget(blanck_widget_box2)
                    update_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(update_at_text)
                    # update_at_text.setGeometry(QtCore.QRect(450, 10, 121, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        update_at_text.sizePolicy().hasHeightForWidth()
                    )
                    update_at_text.setMaximumSize(QtCore.QSize(16777215, 16777215))
                    update_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    update_at_text.setFont(font)
                    update_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    update_at_text.setObjectName("update_at_text")
                    blanck_widget_box5 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box5.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box5.setSizePolicy(sizePolicy)
                    blanck_widget_box5.setObjectName("blanck_widget_box5")
                    task_row_layout.addWidget(blanck_widget_box5)
                    # update_at_text.setGeometry(QtCore.QRect(450, 10, 121, 21))
                    self.verticalLayout_6.addWidget(create_task_row)
                    task_des_text.setText(payload["task"])
                    description_text.setText(payload["description"])
                    create_at_text.setText(
                        f"{payload['create_task_date']}"
                        + " "
                        + f"{payload['create_task_time']}"
                    )
                    update_at_text.setText(
                        f"{payload['update_task_date']}"
                        + " "
                        + f"{payload['update_task_time']}"
                    )
                    self.task_widgets.append(create_task_row)
                    
                    btn_right.clicked.connect(
                        lambda: self.start(payload["fk_todo"], payload["task"])
                    )
                self.blanck_box_right = QtWidgets.QWidget(
                    self.scrollAreaWidgetContents_2
                )
                self.blanck_box_right.setObjectName("blanck_box_right")
                self.verticalLayout_6.addWidget(self.blanck_box_right)
                self.widget_16.setVisible(True)
                self.widget_14.setVisible(True)
        except Exception as e:
            error_log.store_error_log(str(e))
            pass

    def show_completed_task(self, state):
        if state == 2:
            try:
                if self.project_id == None:
                    show_error_message("Please select Project..!")
                    if self.checkBox.isChecked():
                        self.checkBox.setChecked(False)

                else:
                    self.complete.setVisible(False)
                    self.menu_btn2.setVisible(False)
                    self.task_title_2.setVisible(False)
                    self.update_at_bottom.setVisible(False)
                    self.task_title_1.setVisible(False)
                    self.search_task.setEnabled(False)
                    self.widget_10.setVisible(True)
                    self.widget2.setVisible(False)
                    for widget in self.completed_task_widgets[:]:
                        self.verticalLayout_6.removeWidget(widget)
                        widget.deleteLater()
                    self.completed_task_widgets.clear()
                    if hasattr(self, "blanck_box_right"):
                        self.blanck_box_right.setVisible(False)
                    self.verticalLayout_6.setSpacing(2)
                    for payload in db_helper.list_completed_data(self.project_id):
                        completed_task_row = QtWidgets.QWidget(
                            self.scrollAreaWidgetContents_2
                        )
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            completed_task_row.sizePolicy().hasHeightForWidth()
                        )

                        completed_task_row.setCursor(
                            QtGui.QCursor(QtCore.Qt.ForbiddenCursor)
                        )
                        completed_task_row.setSizePolicy(sizePolicy)
                        completed_task_row.setMinimumSize(QtCore.QSize(0, 40))
                        # self.create_task_row.setStyleSheet("background-color: rgb(46, 140, 255);")
                        completed_task_row.setStyleSheet(
                            "background-color: rgb(143, 255, 169);"
                        )
                        completed_task_row.setObjectName(f"completed_task_row")
                        task_row_layout = QtWidgets.QHBoxLayout(completed_task_row)
                        # task_row_layout.setContentsMargins(0, 0, 0, 0)
                        btn_right = QtWidgets.QPushButton()
                        btn_right.setStyleSheet(
                            "#btn_right{\n" "border-radius:30px;\n" "\n" "}"
                        )
                        btn_right.setText("")
                        icon4 = QtGui.QIcon()
                        icon4.addPixmap(
                            QtGui.QPixmap(
                                os.path.join(self.exe_dir, "_internal","resource" , "play-big@2x.png")
                                # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                            ),
                            QtGui.QIcon.Normal,
                            QtGui.QIcon.Off,
                        )
                        btn_right.setIcon(icon4)
                        btn_right.setIconSize(QtCore.QSize(20, 20))
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            btn_right.sizePolicy().hasHeightForWidth()
                        )
                        btn_right.setSizePolicy(sizePolicy)
                        btn_right.setObjectName(f"btn_right_{str(uuid.uuid4)[0:4]}")
                        btn_right.setContentsMargins(0, 0, 0, 0)
                        btn_right.setEnabled(False)
                        task_row_layout.addWidget(btn_right)
                        task_des_text = QtWidgets.QLabel()
                        task_row_layout.addWidget(task_des_text)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            task_des_text.sizePolicy().hasHeightForWidth()
                        )
                        task_des_text.setSizePolicy(sizePolicy)
                        task_des_text.setMaximumSize(QtCore.QSize(100, 16777215))
                        task_des_text.setMinimumSize(QtCore.QSize(100, 16777215))
                        # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                        font = QtGui.QFont()
                        font.setPointSize(8)
                        task_des_text.setFont(font)
                        task_des_text.setStyleSheet(
                            "#task_des_text{\n"
                            "color: rgb(0, 0, 0);\n"
                            "margin-left:5px;}"
                        )
                        task_des_text.setObjectName("task_des_text")
                        widget_11 = QtWidgets.QWidget(completed_task_row)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            widget_11.sizePolicy().hasHeightForWidth()
                        )
                        widget_11.setSizePolicy(sizePolicy)
                        widget_11.setMinimumSize(QtCore.QSize(10, 16777215))
                        widget_11.setObjectName("widget_11")
                        task_row_layout.addWidget(widget_11)
                        description_text = QtWidgets.QLabel()

                        task_row_layout.addWidget(description_text)
                        self.verticalLayout_6.addWidget(completed_task_row)
                        # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Preferred,
                            QtWidgets.QSizePolicy.Expanding,
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            description_text.sizePolicy().hasHeightForWidth()
                        )
                        # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                        description_text.setSizePolicy(sizePolicy)
                        description_text.setMinimumSize(QtCore.QSize(120, 0))
                        description_text.setMaximumSize(QtCore.QSize(120, 16777215))
                        font = QtGui.QFont()
                        font.setPointSize(8)
                        description_text.setFont(font)
                        description_text.setStyleSheet(" color: rgb(0, 0, 0);")
                        # self.description_text.setStyleSheet("color: rgb(255, 255, 255); ") # white color
                        description_text.setAlignment(
                            QtCore.Qt.AlignLeading
                            | QtCore.Qt.AlignLeft
                            | QtCore.Qt.AlignVCenter
                        )
                        description_text.setObjectName("description_text")
                        blanck_widget_box1 = QtWidgets.QWidget(completed_task_row)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            blanck_widget_box1.sizePolicy().hasHeightForWidth()
                        )
                        blanck_widget_box1.setSizePolicy(sizePolicy)
                        blanck_widget_box1.setMinimumSize(QtCore.QSize(4, 16777215))
                        blanck_widget_box1.setObjectName("blanck_widget_box1")
                        task_row_layout.addWidget(blanck_widget_box1)
                        create_at_text = QtWidgets.QLabel()
                        task_row_layout.addWidget(create_at_text)
                        # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            create_at_text.sizePolicy().hasHeightForWidth()
                        )
                        create_at_text.setSizePolicy(sizePolicy)
                        font = QtGui.QFont()
                        font.setPointSize(8)
                        create_at_text.setFont(font)
                        create_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                        create_at_text.setObjectName("create_at_text")
                        create_at_text.setMinimumSize(QtCore.QSize(110, 0))
                        create_at_text.setMaximumSize(QtCore.QSize(180, 16777215))
                        # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                        blanck_widget_box3 = QtWidgets.QWidget(completed_task_row)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            blanck_widget_box3.sizePolicy().hasHeightForWidth()
                        )
                        blanck_widget_box3.setSizePolicy(sizePolicy)
                        blanck_widget_box3.setObjectName("blanck_widget_box3")
                        blanck_widget_box3.setMinimumSize(QtCore.QSize(0, 16777215))
                        task_row_layout.addWidget(blanck_widget_box3)
                        blanck_widget_box2 = QtWidgets.QWidget(completed_task_row)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            blanck_widget_box2.sizePolicy().hasHeightForWidth()
                        )
                        blanck_widget_box2.setSizePolicy(sizePolicy)
                        blanck_widget_box2.setObjectName("blanck_widget_box2")
                        task_row_layout.addWidget(blanck_widget_box2)
                        update_at_text = QtWidgets.QLabel()
                        task_row_layout.addWidget(update_at_text)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            update_at_text.sizePolicy().hasHeightForWidth()
                        )
                        update_at_text.setMaximumSize(QtCore.QSize(16777215, 16777215))
                        update_at_text.setSizePolicy(sizePolicy)
                        font = QtGui.QFont()
                        font.setPointSize(8)
                        update_at_text.setFont(font)
                        update_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                        update_at_text.setObjectName("update_at_text")
                        blanck_widget_box5 = QtWidgets.QWidget(completed_task_row)
                        sizePolicy = QtWidgets.QSizePolicy(
                            QtWidgets.QSizePolicy.Expanding,
                            QtWidgets.QSizePolicy.Preferred,
                        )
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(
                            blanck_widget_box5.sizePolicy().hasHeightForWidth()
                        )
                        blanck_widget_box5.setSizePolicy(sizePolicy)
                        blanck_widget_box5.setObjectName("blanck_widget_box5")
                        task_row_layout.addWidget(blanck_widget_box5)
                        self.verticalLayout_6.addWidget(completed_task_row)
                        task_des_text.setText(payload["task"])
                        description_text.setText(payload["description"])
                        create_at_text.setText(
                            f"{payload['create_task_date']}"
                            + " "
                            + f"{payload['create_task_time']}"
                        )
                        update_at_text.setText(
                            f"{payload['update_task_date']}"
                            + " "
                            + f"{payload['update_task_time']}"
                        )
                        self.completed_task_widgets.append(completed_task_row)
                    self.blanck_box_right = QtWidgets.QWidget(
                        self.scrollAreaWidgetContents_2
                    )
                    self.blanck_box_right.setObjectName("blanck_box_right")
                    self.verticalLayout_6.addWidget(self.blanck_box_right)
                    self.widget_14.setVisible(True)
                    self.widget_16.setVisible(True)
                    self.no_task_lbl_2.setVisible(True)
                    self.no_task_lbl_3.setVisible(True)
            except Exception as e:
                error_log.store_error_log(str(e))
                pass

        else:
            if self.project_id != None:
                self.refreshbutton.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.widget_10.setVisible(True)
                self.widget2.setVisible(False)
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)
                self.task_title_2.setVisible(False)
                self.update_at_bottom.setVisible(False)
                self.task_title_1.setVisible(False)
                self.widget_16.setVisible(True)
                self.widget_14.setVisible(True)
                self.no_task_lbl_3.setVisible(True)
                self.no_task_lbl_2.setVisible(True)
                self.search_task.setEnabled(False)
                for widget in self.completed_task_widgets[:]:
                    self.verticalLayout_6.removeWidget(widget)
                    widget.deleteLater()
                self.completed_task_widgets.clear()
                self.search_task.setEnabled(True)

    def show_menu_bar_dialog(self):
        self.menu_bar_dialog = QtWidgets.QDialog()
        self.menu_bar_ui = Menubar()
        self.menu_bar_ui.setupUi(self.menu_bar_dialog)
        name, email = db_helper.get_user_name_email()
        self.menu_bar_ui.label_2.setText(f"Sign in {name.capitalize()}")
        self.menu_bar_ui.label.setText(f"{email}")
        self.menu_bar_ui.quit.clicked.connect(self.show_quit_dialog)
        self.menu_bar_ui.open_dash.clicked.connect(self.open_dashboard)
        self.menu_bar_ui.sign_out_btn.clicked.connect(self.logout_clicked)
        self.menu_bar_ui.add_edit_time.clicked.connect(self.add_edit_time_dialog)
        self.menu_bar_dialog.exec_()

    def open_dashboard(self):
        webbrowser.open("http://192.168.68.80:3000/#/signin")

    def add_edit_time_dialog(self):
        webbrowser.open("http://192.168.68.80:3000/#/signin")

    def logout_clicked(self):
        if self.startStopButton_flag == "Stop":
            show_error_message(
                "The Task is in progress. \n Please stop it after click on Exit..!"
            )
        else:
            # Start the send_all_task_data_to_server thread
            send_to_server_thread = threading.Thread(
                target=self.send_all_task_data_to_server
            )
            send_to_server_thread.start()
            send_to_server_thread.join()
            threading.Thread(target=chrome.get_chrome_history_data).start()
            threading.Thread(target=firefox.get_firefox_history_data).start()
            threading.Thread(target=task_db.delete_all_create_task).start()
            threading.Thread(target=error_log.delete_all_error_logs).start()
            threading.Thread(target=user_db.delete_user_data).start()
            
            
            self.menu_bar_dialog.close()
            self.close()

    def closeEvent(self, event):
        if self.startStopButton_flag == "Stop":
            show_error_message(
                "The Task is in progress. \n Please stop it after click on Exit..!"
            )
            event.ignore()
        else:
            quit_dialog = quit.Quitalert()
            quit_dialog.setupUi(quit_dialog)
            result = quit_dialog.exec_()
            if result == QtWidgets.QDialog.Accepted:
                threading.Thread(target=self.send_all_task_data_to_server).start()
                threading.Thread(target=chrome.get_chrome_history_data).start()
                threading.Thread(target=firefox.get_firefox_history_data).start()
                # threading.Thread(target=safari.get_safari_history_data).start()
                self.removetask_thread.terminate()
                sys.exit(app.exec_())
            else:
                event.ignore()

    def show_quit_dialog(self):
        self.show_quitbox_dialog = QtWidgets.QDialog()
        self.show_quitbox_ui = quit.Quitalert()
        self.show_quitbox_ui.setupUi(self.show_quitbox_dialog)
        self.show_quitbox_ui.buttonBox.accepted.connect(self.exit_system)
        self.show_quitbox_dialog.exec_()

    def exit_system(self):
        if self.startStopButton_flag == "Stop":
            show_error_message(
                "The Task is in progress. \n Please stop it after click on Exit..!"
            )
        else:
            threading.Thread(target=chrome.get_chrome_history_data).start()
            threading.Thread(target=firefox.get_firefox_history_data).start()
            # threading.Thread(target=safari.get_safari_history_data).start()
            self.removetask_thread.terminate()
            sys.exit(app.exec_())

    def show_open_task_dialog(self):
        self.open_task_dialog = QtWidgets.QDialog()
        self.open_task_ui = OpenTask()
        self.open_task_ui.setupUi(self.open_task_dialog)
        self.open_task_ui.open_task_btn.clicked.connect(self.show_edit_task_dialog)
        self.open_task_dialog.exec_()

    def show_edit_task_dialog(self):
        try:
            self.edit_task_dialog = QtWidgets.QDialog()
            self.edit_task_ui = Edittask()
            payload = db_helper.get_perticular_task_by_taskid(self.edit_task_id)
            self.edit_task_ui.setupUi(self.edit_task_dialog)
            self.edit_task_ui.task_txt.setText(payload[3])
            self.edit_task_ui.textedit.setText(payload[4])
            if payload[9] == "To Do":
                self.edit_task_ui.list.setCurrentIndex(0)
            elif payload[9] == "In progress":
                self.edit_task_ui.list.setCurrentIndex(1)
            elif payload[9] == "Completed":
                self.edit_task_ui.list.setCurrentIndex(2)
            self.edit_task_dialog.setWindowTitle(
                f"Edit task to project {self.project_name}"
            )
            self.edit_task_ui.buttonBox.accepted.connect(self.edit_task_data)
            self.edit_task_dialog.exec_()
        except Exception as e:
            show_error_message("Please select task after you can edit")

    def show_create_task_dialog(self):
        if self.startStopButton_flag == "Stop":
            show_error_message(
                "The Task is in progress. \n Please stop it after click on Create..!"
            )
        else:
            self.create_task_dialog = QtWidgets.QDialog()
            self.create_task_ui = Addtask()
            self.create_task_ui.setupUi(self.create_task_dialog)
            self.create_task_ui.task_txt.setText(self.create_task.text())
            self.create_task.setText("")
            self.create_task_dialog.setWindowTitle(
                f"Add task to project {self.project_name}"
            )
            self.create_task_ui.buttonBox.accepted.connect(self.create_task_data)
            self.create_task_dialog.exec_()

    def show_rightside_main_win(self, id, project_title):
        try:
            self.project_id = id
            self.project_name = project_title
            self.widget_10.setVisible(False)
            self.project_title_right.setText(project_title)
            self.project_title_main.setText(self.project_name.upper())
            self.widget2.setVisible(True)
            self.label_2.setVisible(True)
            self.label_4.setVisible(True)
            self.menu_btn1.setEnabled(True)
            self.create_task.setEnabled(True)
           
            # self.clockLabel.setText(self.time.toString("hh:mm:ss"))
            self.list_task_widget()
            threading.Thread(target=self.gettimeduration).start()
            if hasattr(self, "create_task_row"):
                self.create_task_dynamic_row.setVisible(False)
            if len(db_helper.list_create_task(self.project_id)) == 0:
                self.listbox.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.refreshbutton.setEnabled(True)
                self.comboBox.setEnabled(True)
                self.search_task.setEnabled(False)
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)
                self.task_title_2.setVisible(False)
                self.update_at_bottom.setVisible(False)
                self.task_title_1.setVisible(False)
                self.widget_16.setVisible(False)
                self.widget_14.setVisible(False)
                self.no_task_lbl_3.setVisible(False)
                self.no_task_lbl_2.setVisible(False)
            else:
                self.listbox.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.comboBox.setEnabled(True)
                self.refreshbutton.setEnabled(True)
                self.search_task.setEnabled(True)
                self.no_task_lbl_3.setVisible(True)
                self.no_task_lbl_2.setVisible(True)
                self.widget_14.setVisible(True)
                self.widget_16.setVisible(True)
                self.task_title_1.setText("")
                self.task_title_2.setText("")
                self.update_at_bottom.setText("")
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)

        except Exception as e:
            error_log.store_error_log(str(e))
            pass

    def search_update_list(self, items):
        for i, widget in enumerate(self.project_widgets):
            if i < len(items):
                widget.setVisible(True)
                widget.findChild(QtWidgets.QLabel, "project_title_left").setText(
                    items[i]["name"]
                    if len(items[i]["name"]) <= 12
                    else items[i]["name"][
                        0 : (len(items[i]["name"]) - 5)
                    ]
                    + "..."
                )
            else:
                widget.setVisible(False)

    def search_project_list(self, text):
        if text:
            filtered_data = [
                item
                for item in self.project_list_data
                if text.lower() in item["name"].lower()
            ]
        else:
            filtered_data = self.project_list_data

        self.search_update_list(filtered_data)

    def search_update_task_list(self, items):
        for i, widget in enumerate(self.task_widgets):
            if items:
                if i < len(items):
                    widget.setVisible(True)  # Make sure the widget is visible
                    task_label = widget.findChild(QtWidgets.QLabel, "task_des_text")
                    if isinstance(items[i]["task"], dict):
                        task_label.setText(items[i]["task"]["task"])
                    else:
                        task_label.setText(
                            str(items[i]["task"])
                        )  # Convert task to string
            else:
                widget.setVisible(False)

    def search_task_list(self, text):
        if self.project_id == None:
            self.search_task.setText("")
            show_error_message("Please Select Project..!")
            self.search_task.setEnabled(False)
        else:
            if text:
                filtered_data = [
                    item
                    for item in self.task_payloads
                    if isinstance(item["task"], dict)
                    and text.lower() in item["task"]["task"].lower()
                ]
            else:
                filtered_data = self.task_payloads
            self.search_update_task_list(filtered_data)

    def create_task_widget(self, id, fk_todo_id, payload_data):
        try:
            if len(payload_data) != 0:
                self.refreshbutton.setEnabled(True)
                self.comboBox.setEnabled(True)
                self.listbox.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.search_task.setEnabled(True)
                self.widget_10.setVisible(True)
                self.widget2.setVisible(False)
                if hasattr(self, "blanck_box_right"):
                    self.blanck_box_right.setVisible(False)
                self.verticalLayout_6.setSpacing(2)
                for payload in payload_data:
                    create_task_row = QtWidgets.QWidget(self.scrollAreaWidgetContents_2)
                    self.create_task_dynamic_row = create_task_row
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_task_row.sizePolicy().hasHeightForWidth()
                    )
                    self.create_task_dynamic_row.setCursor(
                        QtGui.QCursor(QtCore.Qt.PointingHandCursor)
                    )
                    create_task_row.setSizePolicy(sizePolicy)
                    create_task_row.setMinimumSize(QtCore.QSize(0, 40))
                    # self.create_task_row.setStyleSheet("background-color: rgb(46, 140, 255);")
                    create_task_row.setStyleSheet(
                        "background-color: rgb(238, 238, 236);"
                    )
                    create_task_row.setObjectName(f"create_task_row")
                    task_row_layout = QtWidgets.QHBoxLayout(create_task_row)
                    # task_row_layout.setContentsMargins(0, 0, 0, 0)
                    btn_right = QtWidgets.QPushButton()
                    btn_right.setStyleSheet(
                        "#btn_right{\n" "border-radius:30px;\n" "\n" "}"
                    )
                    btn_right.setText("")
                    icon4 = QtGui.QIcon()
                    icon4.addPixmap(
                        QtGui.QPixmap(
                            # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                            os.path.join(self.exe_dir, "_internal","resource" , "play-big@2x.png")
                        ),
                        QtGui.QIcon.Normal,
                        QtGui.QIcon.Off,
                    )
                    btn_right.setIcon(icon4)
                    btn_right.setIconSize(QtCore.QSize(20, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        btn_right.sizePolicy().hasHeightForWidth()
                    )
                    btn_right.setSizePolicy(sizePolicy)
                    btn_right.setObjectName(f"btn_right_{str(uuid.uuid4)[0:4]}")
                    # btn_right.clicked.connect(self.handle_task_play_button)
                    # btn_right.setGeometry(QtCore.QRect(10, 10, 21, 20))
                    btn_right.setContentsMargins(0, 0, 0, 0)
                    btn_right.playing = False
                    self.buttons.append(btn_right)

                    task_row_layout.addWidget(btn_right)
                    # task_row_layout.setSpacing(10)  # 10 pixels between widgets
                    # task_row_layout.setContentsMargins(5, 5, 5, 5)
                    task_des_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(task_des_text)
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        task_des_text.sizePolicy().hasHeightForWidth()
                    )
                    task_des_text.setSizePolicy(sizePolicy)
                    task_des_text.setMaximumSize(QtCore.QSize(100, 16777215))
                    task_des_text.setMinimumSize(QtCore.QSize(100, 16777215))
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    task_des_text.setFont(font)
                    task_des_text.setStyleSheet(
                        "#task_des_text{\n" "color: rgb(0, 0, 0);\n" "margin-left:5px;}"
                    )
                    task_des_text.setObjectName("task_des_text")
                    widget_11 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        widget_11.sizePolicy().hasHeightForWidth()
                    )
                    widget_11.setSizePolicy(sizePolicy)
                    widget_11.setMinimumSize(QtCore.QSize(10, 16777215))
                    widget_11.setObjectName("widget_11")
                    task_row_layout.addWidget(widget_11)
                    description_text = QtWidgets.QLabel()

                    task_row_layout.addWidget(description_text)
                    self.verticalLayout_6.addWidget(create_task_row)
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        description_text.sizePolicy().hasHeightForWidth()
                    )
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    description_text.setSizePolicy(sizePolicy)
                    description_text.setMinimumSize(QtCore.QSize(120, 0))
                    description_text.setMaximumSize(QtCore.QSize(120, 16777215))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    description_text.setFont(font)
                    description_text.setStyleSheet(" color: rgb(0, 0, 0);")
                    # self.description_text.setStyleSheet("color: rgb(255, 255, 255); ") # white color
                    description_text.setAlignment(
                        QtCore.Qt.AlignLeading
                        | QtCore.Qt.AlignLeft
                        | QtCore.Qt.AlignVCenter
                    )
                    description_text.setObjectName("description_text")
                    blanck_widget_box1 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box1.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box1.setSizePolicy(sizePolicy)
                    blanck_widget_box1.setMinimumSize(QtCore.QSize(4, 16777215))
                    blanck_widget_box1.setObjectName("blanck_widget_box1")
                    task_row_layout.addWidget(blanck_widget_box1)
                    create_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(create_at_text)
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_at_text.sizePolicy().hasHeightForWidth()
                    )
                    create_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    create_at_text.setFont(font)
                    create_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    create_at_text.setObjectName("create_at_text")
                    create_at_text.setMinimumSize(QtCore.QSize(110, 0))
                    create_at_text.setMaximumSize(QtCore.QSize(180, 16777215))
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    blanck_widget_box3 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box3.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box3.setSizePolicy(sizePolicy)
                    blanck_widget_box3.setObjectName("blanck_widget_box3")
                    blanck_widget_box3.setMinimumSize(QtCore.QSize(0, 16777215))
                    task_row_layout.addWidget(blanck_widget_box3)
                    blanck_widget_box2 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box2.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box2.setSizePolicy(sizePolicy)
                    blanck_widget_box2.setObjectName("blanck_widget_box2")
                    task_row_layout.addWidget(blanck_widget_box2)
                    update_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(update_at_text)
                    # update_at_text.setGeometry(QtCore.QRect(450, 10, 121, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        update_at_text.sizePolicy().hasHeightForWidth()
                    )
                    update_at_text.setMaximumSize(QtCore.QSize(16777215, 16777215))
                    update_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    update_at_text.setFont(font)
                    update_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    update_at_text.setObjectName("update_at_text")
                    create_task_row_id = QtWidgets.QLabel()
                    task_row_layout.addWidget(create_task_row_id)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_task_row_id.sizePolicy().hasHeightForWidth()
                    )
                    create_task_row_id.setGeometry(QtCore.QRect(590, 10, 71, 21))
                    create_task_row_id.setObjectName("create_task_row_id")
                    create_task_row_id.setText(id)
                    create_task_row_id.setVisible(False)
                    blanck_widget_box5 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box5.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box5.setSizePolicy(sizePolicy)
                    blanck_widget_box5.setObjectName("blanck_widget_box5")
                    task_row_layout.addWidget(blanck_widget_box5)
                    # update_at_text.setGeometry(QtCore.QRect(450, 10, 121, 21))
                    self.verticalLayout_6.addWidget(create_task_row)
                    task_des_text.setText(payload["task"])
                    description_text.setText(payload["description"])
                    create_at_text.setText(
                        f"{payload['create_task_date']}"
                        + " "
                        + f"{payload['create_task_time']}"
                    )
                    update_at_text.setText(
                        f"{payload['update_task_date']}"
                        + " "
                        + f"{payload['update_task_time']}"
                    )
                    self.task_widgets.append(create_task_row)
                   
                    btn_right.clicked.connect(
                        lambda _, description_text=description_text, task_des_text=task_des_text, create_at_text=create_at_text, update_at_text=update_at_text, create_task_row=create_task_row: self.handle_task_play_button(
                            create_task_row,
                            description_text,
                            task_des_text,
                            create_at_text,
                            update_at_text,
                        )
                    )
                    btn_right.clicked.connect(
                        lambda: self.start(fk_todo_id, payload["task"])
                    )
                    create_task_row.mousePressEvent = (
                        lambda event, task=payload["task"], update_date=payload[
                            "update_task_date"
                        ], update_time=payload["update_task_time"], description=payload[
                            "description"
                        ]: self.show_task_data_footer(
                            id,
                            task,
                            update_date,
                            update_time,
                            description,
                        )
                    )
                    
            self.blanck_box_right = QtWidgets.QWidget(self.scrollAreaWidgetContents_2)
            self.blanck_box_right.setObjectName("blanck_box_right")
            self.verticalLayout_6.addWidget(self.blanck_box_right)
            self.widget_14.setVisible(True)
            self.widget_16.setVisible(True)
            self.update_at_bottom.setVisible(True)
            self.task_title_2.setVisible(True)
            self.complete.setVisible(True)
            self.menu_btn2.setVisible(True)
            self.no_task_lbl_2.setVisible(False)
            self.no_task_lbl_3.setVisible(False)
            self.task_title_1.setVisible(True)
            self.task_title_1.setText(payload["task"])
            self.update_at_bottom.setText(
                f"Update at: {payload['create_task_date']}"
                + " "
                + f"{payload['create_task_time'][0:3]}....."
            )
            self.task_title_2.setText(payload["task"])
            if hasattr(self, "bottom_blanck_label_1"):
                self.bottom_blanck_label_1.setVisible(True)
            if not hasattr(self, "bottom_blanck_label_1"):
                self.bottom_blanck_label_1 = QtWidgets.QWidget(self.widget_15)
                sizePolicy = QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
                )
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(
                    self.bottom_blanck_label_1.sizePolicy().hasHeightForWidth()
                )
                self.bottom_blanck_label_1.setSizePolicy(sizePolicy)
                self.bottom_blanck_label_1.setObjectName("bottom_blanck_label_1")
                self.verticalLayout_3.addWidget(self.bottom_blanck_label_1)
        except Exception as e:
            error_log.store_error_log(str(e))
            pass

    def list_task_widget(self):
        try:
            if self.checkBox.isChecked():
                self.checkBox.setChecked(False)
            if self.startStopButton_flag == "Stop":
                self.project_widget.setEnabled(False)
            self.task_widgets.clear()
            self.task_payloads.clear()
            self.buttons.clear()
            self.task_payloads.extend(
                payload for payload in db_helper.list_create_task(self.project_id)
            )
            for i in reversed(range(1, self.verticalLayout_6.count())):
                widget = self.verticalLayout_6.itemAt(i).widget()
                if widget is not None:
                    self.verticalLayout_6.removeWidget(widget)
                    widget.setParent(None)
            if len(db_helper.list_create_task(self.project_id)) == 0:
                self.refreshbutton.setEnabled(True)
                self.comboBox.setEnabled(True)
                self.listbox.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.widget_10.setVisible(False)
                self.widget2.setVisible(True)
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)
                self.task_title_2.setVisible(False)
                self.update_at_bottom.setVisible(False)
                self.task_title_1.setVisible(False)
                self.widget_16.setVisible(False)
                self.widget_14.setVisible(False)
                self.no_task_lbl_3.setVisible(False)
                self.no_task_lbl_2.setVisible(False)
                self.search_task.setEnabled(False)
            else:
                self.refreshbutton.setEnabled(True)
                self.comboBox.setEnabled(True)
                self.listbox.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.complete.setVisible(False)
                self.menu_btn2.setVisible(False)
                self.task_title_2.setVisible(False)
                self.update_at_bottom.setVisible(False)
                self.task_title_1.setVisible(False)
                self.widget_16.setVisible(False)
                self.widget_14.setVisible(False)
                self.no_task_lbl_3.setVisible(True)
                self.no_task_lbl_2.setVisible(True)
                self.search_task.setEnabled(True)
                self.widget_10.setVisible(True)
                self.widget2.setVisible(False)
                if hasattr(self, "blanck_box_right"):
                    for i in reversed(range(1, self.verticalLayout_6.count())):
                        blanck_box_right = self.verticalLayout_6.itemAt(i).widget()
                        if blanck_box_right is not None:
                            self.verticalLayout_6.removeWidget(blanck_box_right)
                            blanck_box_right.setParent(None)
                self.verticalLayout_6.setSpacing(2)
                for payload in db_helper.list_create_task(self.project_id):
                    create_task_row = QtWidgets.QWidget(self.scrollAreaWidgetContents_2)
                    self.create_task_dynamic_row = create_task_row
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
                    )

                    self.create_task_dynamic_row.setCursor(
                        QtGui.QCursor(QtCore.Qt.PointingHandCursor)
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_task_row.sizePolicy().hasHeightForWidth()
                    )
                    create_task_row.setSizePolicy(sizePolicy)
                    create_task_row.setMinimumSize(QtCore.QSize(0, 40))
                    # self.create_task_row.setStyleSheet("background-color: rgb(46, 140, 255);")
                    create_task_row.setStyleSheet(
                        "background-color: rgb(238, 238, 236);"
                    )

                    create_task_row.setObjectName(f"create_task_row")
                    task_row_layout = QtWidgets.QHBoxLayout(create_task_row)
                    # task_row_layout.setContentsMargins(0, 0, 0, 0)
                    btn_right = QtWidgets.QPushButton()
                    btn_right.setStyleSheet("#btn_right{\n" "border-radius:30px;\n" "}")
                    btn_right.setText("")
                    icon4 = QtGui.QIcon()
                    icon4.addPixmap(
                        QtGui.QPixmap(
                            # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                            os.path.join(self.exe_dir, "_internal", "resource" ,"play-big@2x.png")
                        ),
                        QtGui.QIcon.Normal,
                        QtGui.QIcon.Off,
                    )
                    btn_right.setIcon(icon4)
                    btn_right.setIconSize(QtCore.QSize(20, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        btn_right.sizePolicy().hasHeightForWidth()
                    )
                    btn_right.setSizePolicy(sizePolicy)
                    btn_right.setObjectName(f"btn_right_{str(uuid.uuid4())[0:4]}")

                    # btn_right.setGeometry(QtCore.QRect(10, 10, 21, 20))
                    btn_right.setContentsMargins(0, 0, 0, 0)
                    btn_right.playing = False
                    self.buttons.append(btn_right)
                    task_row_layout.addWidget(btn_right)
                    # task_row_layout.setSpacing(10)  # 10 pixels between widgets
                    # task_row_layout.setContentsMargins(5, 5, 5, 5)
                    task_des_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(task_des_text)
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        task_des_text.sizePolicy().hasHeightForWidth()
                    )
                    task_des_text.setSizePolicy(sizePolicy)
                    task_des_text.setMaximumSize(QtCore.QSize(100, 16777215))
                    task_des_text.setMinimumSize(QtCore.QSize(100, 16777215))
                    # task_des_text.setGeometry(QtCore.QRect(30, 10, 111, 20))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    task_des_text.setFont(font)
                    task_des_text.setStyleSheet(
                        "#task_des_text{\n" "color: rgb(0, 0, 0);\n" "margin-left:5px;}"
                    )
                    task_des_text.setObjectName("task_des_text")
                    widget_11 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        widget_11.sizePolicy().hasHeightForWidth()
                    )
                    widget_11.setSizePolicy(sizePolicy)
                    widget_11.setMinimumSize(QtCore.QSize(10, 16777215))
                    widget_11.setObjectName("widget_11")
                    task_row_layout.addWidget(widget_11)
                    description_text = QtWidgets.QLabel()

                    task_row_layout.addWidget(description_text)
                    self.verticalLayout_6.addWidget(create_task_row)
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        description_text.sizePolicy().hasHeightForWidth()
                    )
                    # description_text.setGeometry(QtCore.QRect(157, 10, 141, 21))
                    description_text.setSizePolicy(sizePolicy)
                    description_text.setMinimumSize(QtCore.QSize(120, 0))
                    description_text.setMaximumSize(QtCore.QSize(120, 16777215))
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    description_text.setFont(font)
                    description_text.setStyleSheet(" color: rgb(0, 0, 0);")
                    # self.description_text.setStyleSheet("color: rgb(255, 255, 255); ") # white color
                    description_text.setAlignment(
                        QtCore.Qt.AlignLeading
                        | QtCore.Qt.AlignLeft
                        | QtCore.Qt.AlignVCenter
                    )
                    description_text.setObjectName("description_text")
                    blanck_widget_box1 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box1.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box1.setSizePolicy(sizePolicy)
                    blanck_widget_box1.setMinimumSize(QtCore.QSize(5, 16777215))
                    blanck_widget_box1.setObjectName("blanck_widget_box1")
                    task_row_layout.addWidget(blanck_widget_box1)
                    create_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(create_at_text)
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_at_text.sizePolicy().hasHeightForWidth()
                    )
                    create_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    create_at_text.setFont(font)
                    create_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    create_at_text.setObjectName("create_at_text")
                    create_at_text.setMinimumSize(QtCore.QSize(110, 0))
                    create_at_text.setMaximumSize(QtCore.QSize(180, 16777215))
                    # create_at_text.setGeometry(QtCore.QRect(310, 10, 131, 20))
                    blanck_widget_box3 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box3.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box3.setSizePolicy(sizePolicy)
                    blanck_widget_box3.setObjectName("blanck_widget_box3")
                    blanck_widget_box3.setMinimumSize(QtCore.QSize(0, 16777215))
                    task_row_layout.addWidget(blanck_widget_box3)
                    blanck_widget_box2 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box2.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box2.setSizePolicy(sizePolicy)
                    blanck_widget_box2.setObjectName("blanck_widget_box2")
                    task_row_layout.addWidget(blanck_widget_box2)
                    update_at_text = QtWidgets.QLabel()
                    task_row_layout.addWidget(update_at_text)
                    # update_at_text.setGeometry(QtCore.QRect(450, 10, 121, 21))
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        update_at_text.sizePolicy().hasHeightForWidth()
                    )
                    update_at_text.setMaximumSize(QtCore.QSize(16777215, 16777215))
                    update_at_text.setSizePolicy(sizePolicy)
                    font = QtGui.QFont()
                    font.setPointSize(8)
                    update_at_text.setFont(font)
                    update_at_text.setStyleSheet("color: rgb(0, 0, 0);")
                    update_at_text.setObjectName("update_at_text")
                    create_task_row_id = QtWidgets.QLabel()
                    task_row_layout.addWidget(create_task_row_id)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        create_task_row_id.sizePolicy().hasHeightForWidth()
                    )
                    create_task_row_id.setGeometry(QtCore.QRect(590, 10, 71, 21))
                    create_task_row_id.setObjectName("create_task_row_id")
                    create_task_row_id.setText(payload["id"])
                    create_task_row_id.setVisible(False)
                    blanck_widget_box5 = QtWidgets.QWidget(create_task_row)
                    sizePolicy = QtWidgets.QSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
                    )
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(
                        blanck_widget_box5.sizePolicy().hasHeightForWidth()
                    )
                    blanck_widget_box5.setSizePolicy(sizePolicy)
                    blanck_widget_box5.setObjectName("blanck_widget_box5")
                    task_row_layout.addWidget(blanck_widget_box5)
                    # update_at_text.setGeometry(QtCore.QRect(450, 10, 121, 21))
                    self.verticalLayout_6.addWidget(create_task_row)
                    task_des_text.setText(payload["task"]["task"])
                    description_text.setText(payload["task"]["description"])
                    create_at_text.setText(
                        f"{payload['task']['create_task_date']}"
                        + " "
                        + f"{payload['task']['create_task_time']}"
                    )
                    update_at_text.setText(
                        f"{payload['task']['update_task_date']}"
                        + " "
                        + f"{payload['task']['update_task_time']}"
                    )
                    self.task_widgets.append(create_task_row)
                   
                    btn_right.clicked.connect(
                        lambda _, description_text=description_text, task_des_text=task_des_text, create_at_text=create_at_text, update_at_text=update_at_text, create_task_row=create_task_row: self.handle_task_play_button(
                            create_task_row,
                            description_text,
                            task_des_text,
                            create_at_text,
                            update_at_text,
                        )
                    )
                    btn_right.clicked.connect(
                        lambda: self.start(
                            payload["task"]["fk_todo"], payload["task"]["task"]
                        )
                    )
                    create_task_row.mousePressEvent = (
                        lambda event, id=payload["id"], task=payload["task"][
                            "task"
                        ], update_date=payload["task"][
                            "update_task_date"
                        ], update_time=payload[
                            "task"
                        ][
                            "update_task_time"
                        ], description=payload[
                            "task"
                        ][
                            "description"
                        ]: self.show_task_data_footer(
                            id, task, update_date, update_time, description
                        )
                    )
                if hasattr(self, "bottom_blanck_label_1"):
                    self.bottom_blanck_label_1.setVisible(False)
                self.blanck_box_right = QtWidgets.QWidget(
                    self.scrollAreaWidgetContents_2
                )
                self.blanck_box_right.setObjectName("blanck_box_right")
                self.verticalLayout_6.addWidget(self.blanck_box_right)
                self.widget_16.setVisible(True)
                self.widget_14.setVisible(True)
        except Exception as e:
            error_log.store_error_log(str(e))
            pass

    def show_task_data_footer(self, id, task, update_date, update_time, description):
        self.edit_task_id = id
        self.widget_16.setVisible(True)
        self.widget_14.setVisible(True)
        self.update_at_bottom.setVisible(True)
        self.task_title_2.setVisible(True)
        self.complete.setVisible(True)
        self.completed_task_id = id 
        self.complete.clicked.connect(lambda: self.on_complete(id))
        self.menu_btn2.setVisible(True)
        self.no_task_lbl_3.setVisible(False)
        self.no_task_lbl_2.setVisible(False)
        self.task_title_1.setVisible(True)
        self.task_title_1.setText(task)
        self.update_at_bottom.setText(
            f"Update at: {update_date}" + " " + f"{update_time[0:3]}....."
        )
        self.task_title_2.setText(
            description
            if len(description) <= 8
            else description[0 : (len(description) - 5)] + "..."
        )
        if hasattr(self, "bottom_blanck_label_1"):
            self.bottom_blanck_label_1.setVisible(True)
        if not hasattr(self, "bottom_blanck_label_1"):
            self.bottom_blanck_label_1 = QtWidgets.QWidget(self.widget_15)
            sizePolicy = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(
                self.bottom_blanck_label_1.sizePolicy().hasHeightForWidth()
            )
            self.bottom_blanck_label_1.setSizePolicy(sizePolicy)
            self.bottom_blanck_label_1.setObjectName("bottom_blanck_label_1")
            self.verticalLayout_3.addWidget(self.bottom_blanck_label_1)

    def handle_task_play_button(
        self,
        create_task_row,
        description_text,
        task_des_text,
        create_at_text,
        update_at_text,
    ):
        sender_button = self.sender()
        sender_button.playing = not sender_button.playing
        buttons_copy = self.buttons.copy()

        if sender_button.playing:
            icon1 = QtGui.QIcon()
            icon1.addPixmap(
                QtGui.QPixmap(os.path.join(self.exe_dir, "_internal", "resource" ,"stop-big@2x.png")),
                # QtGui.QPixmap(os.path.join(os.getcwd(), "resource/stop-big@2x.png")),
                QtGui.QIcon.Normal,
                QtGui.QIcon.Off,
            )
            sender_button.setIcon(icon1)
            self.mainbtn.setIcon(icon1)
            self.mainbtn.setEnabled(False)
            create_task_row.setStyleSheet("background-color: rgb(46, 140, 255);")

            description_text.setStyleSheet("color: rgb(255, 255, 255);")
            task_des_text.setStyleSheet(
                "#task_des_text{\n"
                "    color: rgb(255, 255, 255);\n"
                "margin-left:5px;\n"
                "}"
            )
            create_at_text.setStyleSheet("color: rgb(255, 255, 255);")
            update_at_text.setStyleSheet("color: rgb(255, 255, 255);")
            self.clockLabel.setStyleSheet(
                "/* Inside auto layout */\n"
                "#clockLabel{\n"
                "width: 133px;\n"
                "background-color: rgb(46, 140, 255);\n"
                "height: 44px;\n"
                "\n"
                "/* Mobile/Heading H3/Bold */\n"
                "\n"
                "font-family: 'Inter';\n"
                "font-style: normal;\n"
                "font-weight: 400;\n"
                "font-size: 25px;\n"
                "line-height: 44px;\n"
                "/* identical to box height, or 157% */\n"
                "\n"
                "text-align: center;\n"
                "\n"
                "/* Neutral/800 */\n"
                "\n"
                "color: rgb(255, 255, 255);\n"
                "}\n"
            )
        else:
            icon1 = QtGui.QIcon()
            icon1.addPixmap(
                # QtGui.QPixmap(os.path.join(os.getcwd(), "resource/play-big@2x.png")),
                QtGui.QPixmap(os.path.join(self.exe_dir, "_internal", "resource" ,"play-big@2x.png")),
                QtGui.QIcon.Normal,
                QtGui.QIcon.Off,
            )
            sender_button.setIcon(icon1)
            self.mainbtn.setIcon(icon1)
            self.mainbtn.setEnabled(False)
            create_task_row.setStyleSheet("background-color: rgb(238, 238, 236);")

            description_text.setStyleSheet("color: rgb(0, 0, 0);\n")
            task_des_text.setStyleSheet(
                "#task_des_text{\n"
                "    color: rgb(0, 0, 0);\n"
                "margin-left:5px;\n"
                "}"
            )
            create_at_text.setStyleSheet("color: rgb(0, 0, 0);")
            update_at_text.setStyleSheet("color: rgb(0, 0, 0);")
            self.clockLabel.setStyleSheet(
                "\n"
                "\n"
                "/* Inside auto layout */\n"
                "#clockLabel{\n"
                "width: 133px;\n"
                "background-color: rgb(46, 52, 54);\n"
                "height: 44px;\n"
                "\n"
                "/* Mobile/Heading H3/Bold */\n"
                "\n"
                "font-family: 'Inter';\n"
                "font-style: normal;\n"
                "font-weight: 400;\n"
                "font-size: 25px;\n"
                "line-height: 44px;\n"
                "/* identical to box height, or 157% */\n"
                "\n"
                "text-align: center;\n"
                "\n"
                "/* Neutral/800 */\n"
                "\n"
                "color: rgb(255, 255, 255);\n"
                "}\n"
            )

        if sender_button.playing:
            for project_widget in self.project_widgets:
                if project_widget and project_widget is not self.project_widgets:
                    project_widget.setEnabled(False)
            for button in self.buttons:
                if button and button is not sender_button:
                    icons5 = QtGui.QIcon()
                    icons5.addPixmap(
                        QtGui.QPixmap(
                            os.path.join(self.exe_dir, "_internal","resource" , "play-big@2x.png")
                            # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                        ),
                        QtGui.QIcon.Normal,
                        QtGui.QIcon.Off,
                    )
                    button.playing = False
                    button.setEnabled(False)
                    button.setIcon(icons5)
        else:
            self.buttons = [button for button in buttons_copy if button]
            for project_widget in self.project_widgets:
                if project_widget and project_widget is not self.project_widgets:
                    project_widget.setEnabled(True)
            for button in self.buttons:
                if button and button is not sender_button:
                    icons5 = QtGui.QIcon()
                    icons5.addPixmap(
                        QtGui.QPixmap(
                            # os.path.join(os.getcwd(), "resource/play-big@2x.png")
                            os.path.join(self.exe_dir, "_internal", "resource" ,"play-big@2x.png")
                        ),
                        QtGui.QIcon.Normal,
                        QtGui.QIcon.Off,
                    )
                    button.setEnabled(True)
                    button.setIcon(icons5)

    def retranslateUi(self, mainwindow):
        _translate = QtCore.QCoreApplication.translate
        mainwindow.setWindowTitle(_translate("mainwindow", "TimeGuruz"))
        self.clockLabel.setText(_translate("mainwindow", "00:00:00"))
        self.project_title_main.setText(_translate("mainwindow", "No Project"))
        self.task_title_left.setText(_translate("mainwindow", "No Task"))

        self.company_name.setText(_translate("mainwindow", " SolGuruz LLP"))
        self.search_project.setPlaceholderText(
            _translate("mainwindow", "Search Projects")
        )
        self.project_time_lbl.setText(_translate("mainwindow", "Project"))
        self.project_duration.setText(_translate("mainwindow", "00:00:00"))
        self.total_time.setText(_translate("mainwindow", "Today"))
        self.today_duration.setText(_translate("mainwindow", "00:00:00"))
        self.project_title_right.setText(_translate("mainwindow", "No Project"))
        self.comboBox.setItemText(0, _translate("mainwindow", "To Do"))
        self.comboBox.setItemText(1, _translate("mainwindow", "In progress"))
        self.comboBox.setItemText(2, _translate("mainwindow", "Completed"))
        self.label_4.setText(_translate("mainwindow", "You have no tasks assigned"))
        self.tasks.setText(_translate("mainwindow", "Tasks"))
        self.listbox.setItemText(0, _translate("mainwindow", "All Task"))
        self.listbox.setItemText(1, _translate("mainwindow", "List"))
        self.checkBox.setText(_translate("mainwindow", "Show Completed"))
        self.search_task.setPlaceholderText(_translate("mainwindow", "Search tasks"))
        self.create_task.setPlaceholderText(_translate("mainwindow", "Create tasks"))
        self.task_title.setText(_translate("mainwindow", "TASK"))
        self.des_title.setText(_translate("mainwindow", "DESCRIPTION"))
        self.create_at_title.setText(_translate("mainwindow", "CREATE AT"))
        self.update_at_title.setText(_translate("mainwindow", "UPDATE AT"))
        self.complete.setText("complete")
        self.no_task_lbl_2.setText("No task selected")

    def start(self, fk_todo_id, task):
        if self.startStopButton_flag == "Stop":
            self.startStopButton_flag = "Start"
            self.timer.stop()
            self.activity_tracker_flag = False
            self.refreshbutton.setEnabled(True)
            self.listbox.setEnabled(True)
            self.checkBox.setEnabled(True)
            self.total_idle_time = 0
            self.idleTime = 0
            self.reset()
            self.start_update_duration = False
            # print(self.project_duration.text())
            self.gettimeduration()
            self.sendallactivitylogs_thread.start()
            self.sendallactivityfailedlogs_thread.start()
            self.backend_thread.terminate()
            self.screenshot_thread.terminate()
            self.sqllite_thread.terminate()
            self.timer_thread.terminate()
            self.image_list = []
        else:
            self.timer.start(1000)
            self.screenshot_thread.start()
            self.sqllite_thread.start()
            self.backend_thread.start()
            self.timer_thread.start()
            self.start_update_duration = True
            t1 = threading.Thread(target=self.update_duration)
            t1.daemon = True
            t1.start()
            self.refreshbutton.setEnabled(False)
            self.listbox.setEnabled(False)
            self.checkBox.setEnabled(False)
            self.task_id = fk_todo_id
            self.task_name = task
            self.task_title_left.setText(self.task_name)
            self.startWatch = True
            self.activity_tracker_flag = True
            self.startStopButton_flag = "Stop"

    def edit_task_data(self):
        if server_check.check_internet_connection():
            try:
                token = db_helper.get_user_token()
                if token:
                    if (
                        not self.edit_task_ui.task_txt.text().strip()
                        or not self.edit_task_ui.textedit.toPlainText().strip()
                    ):
                        self.edit_task_ui.label_4.setVisible(True)
                        self.edit_task_ui.label_4.setText(
                            "Complete all required fields first."
                        )
                    else:
                        if self.startStopButton_flag == "Stop":
                            self.edit_task_ui.label_4.setVisible(True)
                            self.edit_task_ui.label_4.setText(
                                "Please stop progress task..!"
                            )
                        else:
                            if server_check.check_server_status():
                                get_payload = db_helper.get_perticular_task_by_taskid(
                                    self.edit_task_id
                                )
                                edit_payload = {
                                    "temp_id": get_payload[0],
                                    "task": self.edit_task_ui.task_txt.text().strip(),
                                    "description": self.edit_task_ui.textedit.toPlainText().strip(),
                                    "create_task_date": get_payload[5],
                                    "create_task_time": get_payload[6],
                                    "update_task_date": datetime.now().strftime(
                                        "%d-%m-%Y"
                                    ),
                                    "update_task_time": datetime.now().strftime(
                                        "%I:%M %p"
                                    ),
                                    "status": self.edit_task_ui.list.currentText(),
                                }

                                if self.edit_task_ui.list.currentText() == "Completed":
                                    threading.Thread(
                                        target=self.edit_task_completed,
                                        args=(
                                            edit_payload,
                                            get_payload[2],
                                            get_payload[0],
                                            self.edit_task_ui.task_txt.text().strip(),
                                            self.edit_task_ui.textedit.toPlainText().strip(),
                                            self.edit_task_ui.list.currentText(),
                                        ),
                                    ).start()
                                else:
                                    threading.Thread(
                                        target=self.edit_task_uncompleted,
                                        args=(
                                            edit_payload,
                                            get_payload[2],
                                            get_payload[0],
                                        ),
                                    ).start()

                            else:
                                self.edit_task_ui.label_4.setVisible(True)
                                self.edit_task_ui.label_4.setText(
                                    "Server is busy try again letter !"
                                )
                                self.edit_task_ui.label_4.setStyleSheet(
                                    "color: rgb(239, 41, 41);"
                                )
            except Exception as e:
                self.edit_task_ui.label_4.setVisible(True)
                self.edit_task_ui.label_4.setText(
                    "Something Went Wrong,Please contact the Admin!!"
                )
                self.edit_task_ui.label_4.setStyleSheet("color: rgb(239, 41, 41);")
                error_log.store_error_log(str(e))
        else:
            self.edit_task_ui.label_4.setVisible(True)
            self.edit_task_ui.label_4.setText("Internet not available!!")
            self.edit_task_ui.label_4.setStyleSheet("color: rgb(239, 41, 41);")

    def edit_task_completed(
        self, edit_payload, fk_todo_id, task_id, task, description, status
    ):
        try:
            token = db_helper.get_user_token()
            reqs.edit_task(
                db_helper.get_user_token(),
                self.project_id,
                json.dumps(edit_payload),
                db_helper.get_user_id(),
                fk_todo_id,
            )
            reqs.mark_task_complete(token, fk_todo_id)
            task_db.update_create_task_status(task_id, "Completed", 1)
            task_db.update_create_task(
                task,
                description,
                status,
                datetime.now().strftime("%d-%m-%Y"),
                datetime.now().strftime("%I:%M %p"),
                task_id,
            )
            self.edit_task_ui.label_4.setVisible(True)
            self.edit_task_ui.label_4.setText("Task completed successfully")
            self.edit_task_ui.label_4.setStyleSheet("color: rgb(78, 154, 6);")

            for widget in self.task_widgets:
                if (
                    widget.findChild(QtWidgets.QLabel, "create_task_row_id").text()
                    == self.completed_task_id
                ):
                    widget.setStyleSheet("background-color: #EB99F3;")
                    btn_right = widget.findChild(QtWidgets.QPushButton)
                    if btn_right:
                        btn_right.setEnabled(False)
                        self.buttons.remove(btn_right)
                        self.task_widgets.remove(widget)
                        widget.setEnabled(False)
                    break
            if hasattr(self, "bottom_blanck_label_1"):
                self.bottom_blanck_label_1.setVisible(True)
            if not hasattr(self, "bottom_blanck_label_1"):
                self.bottom_blanck_label_1 = QtWidgets.QWidget(self.widget_15)
                sizePolicy = QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
                )
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(
                    self.bottom_blanck_label_1.sizePolicy().hasHeightForWidth()
                )
                self.bottom_blanck_label_1.setSizePolicy(sizePolicy)
                self.bottom_blanck_label_1.setObjectName("bottom_blanck_label_1")
                self.verticalLayout_3.addWidget(self.bottom_blanck_label_1)
        except Exception as e:
            self.edit_task_ui.label_4.setVisible(True)
            self.edit_task_ui.label_4.setText(
                "Something Went Wrong,Please contact the Admin!!"
            )
            self.edit_task_ui.label_4.setStyleSheet("color: rgb(239, 41, 41);")
            error_log.store_error_log(str(e))

    def edit_task_uncompleted(self, edit_payload, fk_todo_id, task_id):
        try:
            reqs.edit_task(
                db_helper.get_user_token(),
                self.project_id,
                json.dumps(edit_payload),
                db_helper.get_user_id(),
                fk_todo_id,
            )

            task_db.update_create_task(
                self.edit_task_ui.task_txt.text().strip(),
                self.edit_task_ui.textedit.toPlainText().strip(),
                self.edit_task_ui.list.currentText(),
                datetime.now().strftime("%d-%m-%Y"),
                datetime.now().strftime("%I:%M %p"),
                task_id,
            )
            self.edit_task_ui.label_4.setVisible(True)
            self.edit_task_ui.label_4.setText("Update successfully please refresh page")
            self.edit_task_ui.label_4.setStyleSheet("color: rgb(78, 154, 6);")
        except Exception as e:
            self.edit_task_ui.label_4.setVisible(True)
            self.edit_task_ui.label_4.setText(
                "Something Went Wrong,Please contact the Admin!!"
            )
            self.edit_task_ui.label_4.setStyleSheet("color: rgb(239, 41, 41);")
            error_log.store_error_log(str(e))

    def create_task_data(self):
        if server_check.check_internet_connection():
            try:
                token = db_helper.get_user_token()
                if token:
                    if (
                        not self.create_task_ui.task_txt.text().strip()
                        or not self.create_task_ui.textedit.toPlainText().strip()
                    ):
                        self.create_task_ui.label_4.setVisible(True)
                        self.create_task_ui.label_4.setText(
                            "Complete all required fields first."
                        )
                    else:
                        if self.project_id != None:
                            id = str(uuid.uuid4())
                            payload = {
                                "temp_id": id,
                                "task": self.create_task_ui.task_txt.text().strip(),
                                "description": self.create_task_ui.textedit.toPlainText().strip(),
                                "create_task_date": datetime.now().strftime("%d-%m-%Y"),
                                "create_task_time": datetime.now().strftime("%I:%M %p"),
                                "update_task_date": datetime.now().strftime("%d-%m-%Y"),
                                "update_task_time": datetime.now().strftime("%I:%M %p"),
                                "status": self.create_task_ui.list.currentText(),
                            }

                            new_task = reqs.create_task(
                                token=db_helper.get_user_token(),
                                project_id=self.project_id,
                                text=json.dumps(payload),
                                user_id=db_helper.get_user_id(),
                            )
                            data = new_task.json()
                            _data = data["data"]
                            _task_detail = json.loads(data["data"]["title"])
                            if _task_detail["status"] == "Completed":
                                reqs.mark_task_complete(token, _data["id"])
                                task_db.store_create_task(
                                    id,
                                    self.project_id,
                                    _data["id"],
                                    _task_detail["task"],
                                    _task_detail["status"],
                                    _task_detail["description"],
                                    _task_detail["create_task_date"],
                                    _task_detail["create_task_time"],
                                    _task_detail["update_task_date"],
                                    _task_detail["update_task_time"],
                                    1,
                                )

                            else:
                                task_db.store_create_task(
                                    id,
                                    self.project_id,
                                    _data["id"],
                                    _task_detail["task"],
                                    _task_detail["status"],
                                    _task_detail["description"],
                                    _task_detail["create_task_date"],
                                    _task_detail["create_task_time"],
                                    _task_detail["update_task_date"],
                                    _task_detail["update_task_time"],
                                    0,
                                )
                            if _task_detail["status"] != "Completed":
                                self.task_payloads.append(payload)
                                self.create_task_widget(id, _data["id"], [payload])
                            self.create_task_dialog.close()

                        else:
                            show_error_message(
                                "Kindly select 'Project' \n once you've added the task \n Thank You !"
                            )
            except Exception as e:
                show_error_message("Something Went Wrong,Please contact the Admin!!")
                error_log.store_error_log(str(e))
        else:
            show_error_message("Internet not available!!")

    def handle_screenshot(self, screenshot):
        self.image_list.append(screenshot)

    def handle_time(self, start_time, end_time):
        self._date_start_time = start_time
        self._date_end_time = end_time

    def gettask_data_finished(self):
        self.gettask_thread.terminate()

    def removetask_data_finished(self):
        pass

    def getuncompletedtask_data_finished(self):
        self.getuncompletedtask_thread.terminate()

    def getcompleted_task_data_finished(self):
        self.getcompleted_thread.terminate()

    def sendallactivitylogs_finished(self):
        self.sendallactivitylogs_thread.terminate()    

    def sendallactivityfailedlogs_finished(self):
        self.sendallactivityfailedlogs_thread.terminate()

    def send_data_to_backend(self):
        if len(db_helper.get_activity_logs_data()) != 0:
            self.process_create_activity_log(db_helper.get_activity_logs_data())

    def process_create_activity_log(self, payloads):
        self.activity_backend_thread = workers_processor.ActivityLogThread(payloads)
        self.activity_backend_thread.finished.connect(self.activity_log_thread_finished)
        self.activity_backend_thread.start()

    def activity_log_thread_finished(self):
        if len(db_helper.get_activity_logs_data()) == 0:
            self.activity_backend_thread.terminate()

    def send_data_to_sqllite(self):
        try:
            create_activity_thread = threading.Thread(
                target=activity_log_db.store_activity_log,
                args=(self.create_payload(), self.image_list),
            )
            create_activity_thread.daemon = True
            create_activity_thread.start()
            self.activities = []
            self.image_list = []
        except Exception as e:
            error_log.store_error_log(str(e))
            pass
    

    

    def create_payload(self):
        self.display_project_details = f"project name: {self.project_name} \n "
        self.display_project_details += f"project id: {self.project_id} \n "
        self.display_task_details = f"task name: {self.task_name} \n"
        self.display_task_details += f"task id: {self.task_id}"
        (
            self.activities,
            self.actual_activity,
            self.actual_time_entry_start_time,
        ) = self.resume_activity(
            self.activities, self.actual_activity, self.actual_time_entry_start_time
        )
        final_ativity_payload = []
        for activity in self.activities:
            final_ativity_payload.append(activity.to_json())

        now = datetime.now()
        dt_date = now.strftime("%m-%d-%Y")
        _final_idle_time = 0
        if self.idle_time_list:
            for single_dle_time_list in self.idle_time_list:
                if single_dle_time_list:
                    _final_idle_time += single_dle_time_list[-1]
                else:
                    pass
        else:
            pass

        _final_idle_time_timestamp = t.strftime("%H:%M:%S", t.gmtime(_final_idle_time))
        if self._date_end_time == "":
            self._date_end_time = now.strftime("%H:%M:%S")
        start_time = datetime.strptime(self._date_start_time, "%H:%M:%S")
        end_time = datetime.strptime(self._date_end_time, "%H:%M:%S")
        duration = end_time - start_time    
        hours, minutes, seconds = map(int, str(duration).split(":"))
        
        payload = {
            "fk_project": self.project_id,
            "fk_todo": self.task_id,
            "date": dt_date,
            "start_time": self._date_start_time,
            "end_time": self._date_end_time,
            "duration": str(f"{hours:02d}:{minutes:02d}:{seconds:02d}"),
            "idle_time": _final_idle_time_timestamp,
            "screen_activity": final_ativity_payload,
        }
        final_ativity_payload = []
        self.idle_time_list = []
        return payload

    def showCounter(self):
        self.time = self.time.addSecs(1)
        self.hour = self.get_hours()
        self.minute = self.get_minutes()
        self.second = self.get_seconds()
        # Check the value of startWatch  variable to start or stop the Stop Watch
        idleTime = 0
        (
            self.activities,
            self.actual_activity,
            self.actual_time_entry_start_time,
        ) = self.resume_activity(
            self.activities, self.actual_activity, self.actual_time_entry_start_time
        )
        idleTime = get_idle_duration(flag=self.activity_tracker_flag)
        if idleTime > 1:
            self.idleTime = idleTime
            if int(self.idleTime) not in self._tmp_idle_time:
                self._tmp_idle_time.append(int(self.idleTime))
        else:
            if self._tmp_idle_time:
                self.idle_time_list.append(self._tmp_idle_time)
            self._tmp_idle_time = []

        self.output_text = self.time.toString("hh:mm:ss")
        # print("output_text",self.output_text)

        if idleTime is not None:
            self.idleTime = idleTime
        self.clockLabel.setText(self.time.toString("hh:mm:ss"))

    def get_hours(self):
        return self.time.hour()

    def get_minutes(self):
        return self.time.minute()

    def get_seconds(self):
        return self.time.second()

    def resume_activity(
        self, activities, actual_activity, actual_time_entry_start_time
    ):
        """Resume the actual activity."""
        current_activity = get_active_window_title()
        # Check if there was a change in the activity
        if current_activity != actual_activity:
            # Look for if the activity exists
            for previus_activity in activities:
                if previus_activity.window_title == actual_activity:
                    break
            else:
                previus_activity = None
            previus_activity_time_entry = TimeEntry(
                start_time=actual_time_entry_start_time,
                end_time=datetime.now(),
            )
            # If not exist the activity, it'll be created
            if not previus_activity:
                previus_activity = Activity(actual_activity)
                activities.append(previus_activity)

            # Add the time entry for the activity
            previus_activity.add_time_entry(previus_activity_time_entry)
            # Set the new actual activity
            actual_activity = current_activity
            actual_time_entry_start_time = datetime.now()

        return activities, actual_activity, actual_time_entry_start_time

    def reset(self):
        self.startWatch = False
        self.count = "00"
        self.clockLabel.setText(f"{self.hour}:{self.minute}:{self.second}")
        self.clockLabel.setText(self.time.toString("hh:mm:ss"))

    def on_complete(self, id):
        token = db_helper.get_user_token()
        if token:
            try:
                print(id)
                if server_check.check_internet_connection():
                    if self.startStopButton_flag == "Stop":
                        show_error_message(
                            "The Task is in progress. \n Please stop it after click on complete..!"
                        )
                    else:
                        if server_check.check_server_status():
                            self.loader = loader2.Loader()
                            self.loader.show()
                            task_data = db_helper.get_perticular_task_by_taskid(id)
                            edit_payload = {
                                "temp_id": task_data[0],
                                "task": task_data[3],
                                "description": task_data[4],
                                "create_task_date": task_data[5],
                                "create_task_time": task_data[6],
                                "update_task_date": datetime.now().strftime("%d-%m-%Y"),
                                "update_task_time": datetime.now().strftime("%I:%M %p"),
                                "status": "Completed",
                            }

                            reqs.edit_task(
                                db_helper.get_user_token(),
                                self.project_id,
                                json.dumps(edit_payload),
                                db_helper.get_user_id(),
                                task_data[2],
                            )
                            reqs.mark_task_complete(token, task_data[2])
                            task_db.update_create_task_status(id, "Completed", 1)

                            threading.Thread(
                                target=self.send_all_task_data_to_server
                            ).start()

                            for widget in self.task_widgets:
                                if (
                                    widget.findChild(
                                        QtWidgets.QLabel, "create_task_row_id"
                                    ).text()
                                    == id
                                ):
                                    widget.setStyleSheet("background-color: #EB99F3;")
                                    btn_right = widget.findChild(QtWidgets.QPushButton)
                                    if btn_right:
                                        btn_right.setEnabled(False)
                                        self.buttons.remove(btn_right)
                                        self.task_widgets.remove(widget)
                                        widget.setEnabled(False)
                                    break

                            if hasattr(self, "blanck_box_right"):
                                self.blanck_box_right.setVisible(False)
                            self.blanck_box_right = QtWidgets.QWidget(
                                self.scrollAreaWidgetContents_2
                            )
                            self.blanck_box_right.setObjectName("blanck_box_right")
                            self.verticalLayout_6.addWidget(self.blanck_box_right)
                            self.complete.setVisible(False)
                            self.menu_btn2.setVisible(False)
                            self.task_title_2.setVisible(False)
                            self.update_at_bottom.setVisible(False)
                            self.task_title_1.setVisible(False)
                            self.widget_16.setVisible(False)
                            self.widget_14.setVisible(True)
                            self.no_task_lbl_2.setVisible(True)
                            self.no_task_lbl_3.setVisible(True)
                        else:
                            show_error_message(
                                "Currently, the server is busy. Don't worry, \n your data will be sent once the server is up..!"
                            )
                            task_db.update_create_task_status(id, "Completed", 0)

                            for widget in self.task_widgets:
                                if (
                                    widget.findChild(
                                        QtWidgets.QLabel, "create_task_row_id"
                                    ).text()
                                    == id
                                ):
                                    widget.setStyleSheet("background-color: #EB99F3;")
                                    btn_right = widget.findChild(QtWidgets.QPushButton)
                                    if btn_right:
                                        btn_right.setEnabled(False)
                                        self.buttons.remove(btn_right)
                                        self.task_widgets.remove(widget)
                                        widget.setEnabled(False)
                                    break

                            if hasattr(self, "blanck_box_right"):
                                self.blanck_box_right.setVisible(False)
                            self.blanck_box_right = QtWidgets.QWidget(
                                self.scrollAreaWidgetContents_2
                            )
                            self.blanck_box_right.setObjectName("blanck_box_right")
                            self.verticalLayout_6.addWidget(self.blanck_box_right)
                            self.complete.setVisible(False)
                            self.menu_btn2.setVisible(False)
                            self.task_title_2.setVisible(False)
                            self.update_at_bottom.setVisible(False)
                            self.task_title_1.setVisible(False)
                            self.widget_16.setVisible(False)
                            self.widget_14.setVisible(True)
                            self.no_task_lbl_2.setVisible(True)
                            self.no_task_lbl_3.setVisible(True)
                            # self.list_task_widget()
                
                else:
                    show_error_message(
                        "Internet connection unavailable.\n Please check."
                    )
            except Exception as e:
                error_log.store_error_log(str(e))
                show_error_message("Something Went Wrong,Please contact the Admin!!")

    def update_duration(self):
        while True:
            t.sleep(125)
            if self.start_update_duration == False:
                break
            else:
                self.gettimeduration()

    def gettimeduration(self):
        try:
            data_to_display = reqs.get_daily_stats(token=db_helper.get_user_token())
            respnse_data_json = data_to_display.json()
            response_data = respnse_data_json["data"]
            time_sum = timedelta()
            _current_project_id = self.project_id

            for i in range(len(response_data)):
                if _current_project_id == response_data[i]["id"]:
                    self.project_duration.setText(
                        f"{response_data[i]['duration']}"
                        if response_data[i]["duration"] is not None
                        else "00:00:00"
                    )
                if response_data[i]["duration"] is not None:
                    duration = response_data[i]["duration"]
                    hours, minutes, seconds = map(int, duration.split(":"))
                    time_sum += timedelta(hours=hours, minutes=minutes, seconds=seconds)
                    hours, minutes, seconds = map(int, str(time_sum).split(":"))
                self.time_left_label_list[i].setText(
                    "00:00"
                    if response_data[i]["duration"] is None
                    else ":".join(response_data[i]["duration"].split(":")[0:2])
                )
            self.today_duration.setText(str(f"{hours:02d}:{minutes:02d}:{seconds:02d}"))
        except Exception as e:
            pass

    def send_all_task_data_to_server(self):
        payload_data = db_helper.get_server_status_failed_task()
        try:
            if len(payload_data) != 0 or payload_data != None:
                token = db_helper.get_user_token()
                for payload in payload_data:
                    if server_check.check_server_status():
                        reqs.mark_task_complete(token, payload[2])
                        task_db.update_create_task_status(payload[0], "Completed", 1)
                    else:
                        continue
            else:
                pass
                
        except Exception as e:
            error_log.store_error_log(str(e))
            show_error_message("Something Went Wrong,Please contact the Admin!!")
            pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = None
    try:
        if server_check.check_internet_connection():
            if server_check.check_server_status():
                if db_helper.get_user_token() != None:
                    main_window = Dashboard()
                else:
                    main_window = Login()
            else:
                show_error_message("Server is busy try again Letter..!")
                sys.exit(0)  
        else:
            show_error_message("No internet connection")
            sys.exit(0) 
    except Exception as e:
        if server_check.check_internet_connection():
            if server_check.check_server_status():
                main_window = Login()
            else:
                show_error_message("Server is busy try again Letter..!")
                sys.exit(0) 
                
        else:
            show_error_message("No internet connection")
            sys.exit(0) 
    main_window.show()
    sys.exit(app.exec_())
