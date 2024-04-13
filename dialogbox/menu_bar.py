from PyQt5 import QtCore, QtGui, QtWidgets
import os,sys

class Menubar(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)    
    def setupUi(self, menu):
        menu.setObjectName("menu")
        menu.resize(237, 360)
        self.exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(
                # os.path.join(os.getcwd(), "resource/sgLogo.ico")
                os.path.join(self.exe_dir, "_internal","resource" , "sgLogo.ico")
                ))
        menu.setWindowIcon(icon)
        self.verticalLayout = QtWidgets.QVBoxLayout(menu)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(menu)
        self.widget.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.widget.setObjectName("widget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.line = QtWidgets.QFrame(self.widget)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_2.addWidget(self.line)
        self.label_2 = QtWidgets.QLabel(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setMinimumSize(QtCore.QSize(0, 20))
        self.label_2.setCursor(QtGui.QCursor(QtCore.Qt.ForbiddenCursor))
        self.label_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_2.setStyleSheet("width: 133px;\n"
"height: 44px;\n"
"\n"
"/* Mobile/Heading H3/Bold */\n"
"\n"
"font-family: \'Inter\';\n"
"font-style: normal;\n"
"font-weight: 600;\n"
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
"")
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.label = QtWidgets.QLabel(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setCursor(QtGui.QCursor(QtCore.Qt.ForbiddenCursor))
        self.label.setStyleSheet("width: 133px;\n"
"height: 44px;\n"
"\n"
"/* Mobile/Heading H3/Bold */\n"
"\n"
"font-family: \'Inter\';\n"
"font-style: normal;\n"
"font-weight: 600;\n"
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
"")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.sign_out_btn = QtWidgets.QPushButton(self.widget)
        self.sign_out_btn.setMinimumSize(QtCore.QSize(0, 30))
        self.sign_out_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.sign_out_btn.setStyleSheet("#sign_out_btn{\n"
"border-radius:10px;}\n"
"\n"
"QPushButton:hover {\n"
"   \n"
"    background-color: rgb(211, 215, 207);\n"
"        }")
        self.sign_out_btn.setObjectName("sign_out_btn")
        self.verticalLayout_2.addWidget(self.sign_out_btn)
        self.line_2 = QtWidgets.QFrame(self.widget)
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.verticalLayout_2.addWidget(self.line_2)
        self.open_dash = QtWidgets.QPushButton(self.widget)
        self.open_dash.setMinimumSize(QtCore.QSize(0, 30))
        self.open_dash.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.open_dash.setStyleSheet("#open_dash{border-radius:10px;}\n"
"\n"
"QPushButton:hover {\n"
"   \n"
"    background-color: rgb(211, 215, 207);\n"
"        }")
        self.open_dash.setObjectName("open_dash")
        self.verticalLayout_2.addWidget(self.open_dash)
        self.add_edit_time = QtWidgets.QPushButton(self.widget)
        self.add_edit_time.setMinimumSize(QtCore.QSize(0, 30))
        self.add_edit_time.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.add_edit_time.setStyleSheet("#add_edit_time{\n"
"border-radius:10px;}\n"
"\n"
"QPushButton:hover {\n"
"   \n"
"    background-color: rgb(211, 215, 207);\n"
"        }")
        self.add_edit_time.setObjectName("add_edit_time")
        self.verticalLayout_2.addWidget(self.add_edit_time)
        self.quit = QtWidgets.QPushButton(self.widget)
        self.quit.setMinimumSize(QtCore.QSize(0, 30))
        self.quit.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.quit.setStyleSheet("#quit{border-radius:10px;}\n"
"\n"
"QPushButton:hover {\n"
"   \n"
"    background-color: rgb(211, 215, 207);\n"
"        }")
        self.quit.setObjectName("quit")
        self.verticalLayout_2.addWidget(self.quit)
        self.line = QtWidgets.QFrame(self.widget)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_2.addWidget(self.line)
        self.verticalLayout.addWidget(self.widget)
        self.retranslateUi(menu)
        QtCore.QMetaObject.connectSlotsByName(menu)

    def retranslateUi(self, menu):
        _translate = QtCore.QCoreApplication.translate
        menu.setWindowTitle(_translate("menu", "Menu WIndow"))
        self.sign_out_btn.setText(_translate("menu", "Signout"))
        self.open_dash.setText(_translate("menu", "Open Dashboard"))
        self.add_edit_time.setText(_translate("menu", "Add Edit Timer"))
        self.quit.setText(_translate("menu", "Quit TimeGuruz"))


# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     menu = QtWidgets.QDialog()
#     ui = Menubar()
#     ui.setupUi(menu)
#     menu.show()
#     sys.exit(app.exec_())
