# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 186)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(28, 28, 109, 16))
        self.label.setObjectName("label")
        self.OutputDirectoryEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.OutputDirectoryEdit.setGeometry(QtCore.QRect(164, 90, 303, 20))
        self.OutputDirectoryEdit.setObjectName("OutputDirectoryEdit")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(594, 28, 81, 16))
        self.label_4.setObjectName("label_4")
        self.BrowseForImageRoot = QtWidgets.QPushButton(self.centralwidget)
        self.BrowseForImageRoot.setGeometry(QtCore.QRect(478, 26, 75, 23))
        self.BrowseForImageRoot.setObjectName("BrowseForImageRoot")
        self.ShapeRootInputEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.ShapeRootInputEdit.setGeometry(QtCore.QRect(164, 58, 303, 20))
        self.ShapeRootInputEdit.setObjectName("ShapeRootInputEdit")
        self.BrowseForOutputDir = QtWidgets.QPushButton(self.centralwidget)
        self.BrowseForOutputDir.setGeometry(QtCore.QRect(478, 90, 75, 23))
        self.BrowseForOutputDir.setObjectName("BrowseForOutputDir")
        self.ImageRootInputEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.ImageRootInputEdit.setGeometry(QtCore.QRect(164, 26, 303, 20))
        self.ImageRootInputEdit.setObjectName("ImageRootInputEdit")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(28, 92, 109, 16))
        self.label_3.setObjectName("label_3")
        self.ImageTypeCombo = QtWidgets.QComboBox(self.centralwidget)
        self.ImageTypeCombo.setGeometry(QtCore.QRect(700, 26, 69, 22))
        self.ImageTypeCombo.setObjectName("ImageTypeCombo")
        self.ImageTypeCombo.addItem("")
        self.ImageTypeCombo.addItem("")
        self.ProcessButton = QtWidgets.QPushButton(self.centralwidget)
        self.ProcessButton.setGeometry(QtCore.QRect(698, 90, 75, 23))
        self.ProcessButton.setObjectName("ProcessButton")
        self.BrowseForShapeRoot = QtWidgets.QPushButton(self.centralwidget)
        self.BrowseForShapeRoot.setGeometry(QtCore.QRect(478, 58, 75, 23))
        self.BrowseForShapeRoot.setObjectName("BrowseForShapeRoot")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(28, 60, 109, 16))
        self.label_2.setObjectName("label_2")
        self.ClearButton = QtWidgets.QPushButton(self.centralwidget)
        self.ClearButton.setGeometry(QtCore.QRect(610, 90, 75, 23))
        self.ClearButton.setObjectName("ClearButton")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Image & Shape Renamer"))
        self.label.setText(_translate("MainWindow", "Image Root Directory"))
        self.label_4.setText(_translate("MainWindow", "Image File Type"))
        self.BrowseForImageRoot.setText(_translate("MainWindow", "Browse"))
        self.BrowseForOutputDir.setText(_translate("MainWindow", "Browse"))
        self.label_3.setText(_translate("MainWindow", "Output Directory"))
        self.ImageTypeCombo.setItemText(0, _translate("MainWindow", ".img"))
        self.ImageTypeCombo.setItemText(1, _translate("MainWindow", ".tif"))
        self.ProcessButton.setText(_translate("MainWindow", "Process"))
        self.BrowseForShapeRoot.setText(_translate("MainWindow", "Browse"))
        self.label_2.setText(_translate("MainWindow", "Shape Root Directory"))
        self.ClearButton.setText(_translate("MainWindow", "Clear"))

