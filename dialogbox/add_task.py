from PyQt5 import QtCore, QtGui, QtWidgets
import os,sys

class Addtask(QtWidgets.QDialog):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(542, 371)
        self.exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(
                                    # os.path.join(os.getcwd(), "resource/sgLogo.ico")
                                      os.path.join(self.exe_dir, "_internal", "resource" ,"sgLogo.ico")  
                                     ))
        Dialog.setWindowIcon(icon)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(Dialog)
        self.widget.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.widget.setObjectName("widget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.widget_2 = QtWidgets.QWidget(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setStyleSheet("margin-left:5px;")
        self.label.setObjectName("label")
        self.label.setMinimumSize(QtCore.QSize(100, 0))
        self.label.setMaximumSize(QtCore.QSize(100, 16777215))
        self.horizontalLayout.addWidget(self.label)
        self.task_txt = QtWidgets.QLineEdit(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.task_txt.sizePolicy().hasHeightForWidth())
        self.task_txt.setSizePolicy(sizePolicy)
        self.task_txt.setMinimumSize(QtCore.QSize(0, 0))
        self.task_txt.setObjectName("task_txt")
        self.task_txt.setStyleSheet("""
                QLineEdit {
                border: 1px solid #7f7f7f;
                border-radius: 5px;
                padding: 5px;
                min-width: 10em;
                background-color: white;
                color: black;
            }
            QLineEdit:focus {
                border-color: #4d90fe;
            }""")
        self.horizontalLayout.addWidget(self.task_txt)
        self.verticalLayout_2.addWidget(self.widget_2)
        self.widget_3 = QtWidgets.QWidget(self.widget)
        self.widget_3.setObjectName("widget_3")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_3)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.widget_5 = QtWidgets.QWidget(self.widget_3)
        self.widget_5.setMinimumSize(QtCore.QSize(100, 0))
        self.widget_5.setMaximumSize(QtCore.QSize(100, 16777215))
        self.widget_5.setObjectName("widget_5")
        self.label_2 = QtWidgets.QLabel(self.widget_5)
        self.label_2.setGeometry(QtCore.QRect(10, 10, 82, 18))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.widget_5)
        self.textedit = QtWidgets.QTextEdit(self.widget_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textedit.sizePolicy().hasHeightForWidth())
        self.textedit.setSizePolicy(sizePolicy)
        self.textedit.setObjectName("textedit")
        self.textedit.setStyleSheet("""
                                    QTextEdit {
                border: 1px solid #7f7f7f;
                border-radius: 5px;
                padding: 5px;
                min-width: 10em;
                background-color: white;
                color: black;
            }
            QTextEdit:focus {
                border-color: #4d90fe;
            }""")
        self.horizontalLayout_2.addWidget(self.textedit)
        self.verticalLayout_2.addWidget(self.widget_3)
        self.widget_4 = QtWidgets.QWidget(self.widget)
        self.widget_4.setMinimumSize(QtCore.QSize(0, 50))
        self.widget_4.setMaximumSize(QtCore.QSize(16777215, 50))
        self.widget_4.setObjectName("widget_4")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_4)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_3 = QtWidgets.QLabel(self.widget_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("margin-left:10px;")
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_3.addWidget(self.label_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setMinimumSize(QtCore.QSize(100, 0))
        self.label_3.setMaximumSize(QtCore.QSize(100, 16777215))
        self.list = QtWidgets.QComboBox(self.widget_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.list.sizePolicy().hasHeightForWidth())
        self.list.setSizePolicy(sizePolicy)
        self.list.setMinimumSize(QtCore.QSize(0, 0))
        self.list.setObjectName("list")
        self.list.addItem("")
        self.list.addItem("")
        self.list.addItem("")
        self.list.setStyleSheet("""
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
            """% {"image_path":
                   os.path.join(self.exe_dir, "_internal", "resource" ,"down_arrow2.png")    
                                # os.path.join(os.getcwd(), "resource/down_arrow2.png")    
                  })
        
        self.horizontalLayout_3.addWidget(self.list)
        self.verticalLayout_2.addWidget(self.widget_4)
        self.label_4 = QtWidgets.QLabel(self.widget)
        font = QtGui.QFont()
        font.setFamily("Courier 10 Pitch")
        font.setPointSize(13)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet("color: rgb(239, 41, 41);")
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.label_4.setVisible(False)
        self.verticalLayout_2.addWidget(self.label_4)
        self.verticalLayout.addWidget(self.widget)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        self.buttonBox.rejected.connect(Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        # Dialog.setWindowTitle(_translate("Dialog", "Add task to project<project_name>"))
        self.label.setText(_translate("Dialog", "Task"))
        self.label_2.setText(_translate("Dialog", "Description"))
        self.label_3.setText(_translate("Dialog", "List"))
        self.list.setItemText(0, _translate("Dialog", "To Do"))
        self.list.setItemText(1, _translate("Dialog", "In progress"))
        self.list.setItemText(2, _translate("Dialog", "Completed"))
        # self.label_4.setText(_translate("Dialog", "Add Text filed "))


# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     Dialog = QtWidgets.QDialog()
#     ui = Addtask()
#     ui.setupUi(Dialog)
#     Dialog.show()
#     sys.exit(app.exec_())
