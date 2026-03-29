# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QSplitter,
    QStatusBar, QTextEdit, QVBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1400, 900)
        MainWindow.setStyleSheet(u"QMainWindow {\n"
"    background-color: #f8fafc;\n"
"}")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(u"QSplitter::handle {\n"
"    background-color: #e2e8f0;\n"
"}")
        self.sidebar = QWidget(self.splitter)
        self.sidebar.setObjectName(u"sidebar")
        self.sidebar.setMinimumSize(QSize(280, 0))
        self.sidebar.setMaximumSize(QSize(400, 16777215))
        self.sidebar.setStyleSheet(u"#sidebar {\n"
"    background-color: #ffffff;\n"
"    border-right: 1px solid #e2e8f0;\n"
"}")
        self.sidebarLayout = QVBoxLayout(self.sidebar)
        self.sidebarLayout.setSpacing(0)
        self.sidebarLayout.setObjectName(u"sidebarLayout")
        self.sidebarLayout.setContentsMargins(0, 0, 0, 0)
        self.folderHeader = QWidget(self.sidebar)
        self.folderHeader.setObjectName(u"folderHeader")
        self.folderHeader.setMinimumSize(QSize(0, 48))
        self.folderHeader.setMaximumSize(QSize(16777215, 48))
        self.folderHeader.setStyleSheet(u"#folderHeader {\n"
"    background-color: #f8fafc;\n"
"    border-bottom: 1px solid #e2e8f0;\n"
"}")
        self.folderHeaderLayout = QHBoxLayout(self.folderHeader)
        self.folderHeaderLayout.setObjectName(u"folderHeaderLayout")
        self.folderHeaderLayout.setContentsMargins(16, 0, 12, 0)
        self.folderLabel = QLabel(self.folderHeader)
        self.folderLabel.setObjectName(u"folderLabel")
        self.folderLabel.setStyleSheet(u"font-size: 14px;\n"
"font-weight: 600;\n"
"color: #1e293b;")

        self.folderHeaderLayout.addWidget(self.folderLabel)

        self.folderSpacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.folderHeaderLayout.addItem(self.folderSpacer)

        self.addFolderButton = QPushButton(self.folderHeader)
        self.addFolderButton.setObjectName(u"addFolderButton")
        self.addFolderButton.setMinimumSize(QSize(28, 28))
        self.addFolderButton.setMaximumSize(QSize(28, 28))
        self.addFolderButton.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    border: 1px solid #e2e8f0;\n"
"    border-radius: 6px;\n"
"    color: #64748b;\n"
"    font-size: 16px;\n"
"    font-weight: 500;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #f1f5f9;\n"
"    border-color: #94a3b8;\n"
"    color: #475569;\n"
"}")

        self.folderHeaderLayout.addWidget(self.addFolderButton)

        self.folderDeleteButton = QPushButton(self.folderHeader)
        self.folderDeleteButton.setObjectName(u"folderDeleteButton")
        self.folderDeleteButton.setMinimumSize(QSize(28, 28))
        self.folderDeleteButton.setMaximumSize(QSize(28, 28))
        self.folderDeleteButton.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    border: 1px solid #e2e8f0;\n"
"    border-radius: 6px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #f8fafc;\n"
"    border: 1px solid #cbd5e1;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #e2e8f0;\n"
"    color: #475569;\n"
"}")

        self.folderHeaderLayout.addWidget(self.folderDeleteButton)


        self.sidebarLayout.addWidget(self.folderHeader)

        self.folderTree = QTreeWidget(self.sidebar)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.folderTree.setHeaderItem(__qtreewidgetitem)
        self.folderTree.setObjectName(u"folderTree")
        self.folderTree.setStyleSheet(u"QTreeWidget {\n"
"    background: transparent;\n"
"    border: none;\n"
"    outline: none;\n"
"    padding: 8px;\n"
"}\n"
"QTreeWidget::item {\n"
"    border-radius: 8px;\n"
"    padding: 10px 12px;\n"
"    margin: 2px 0px;\n"
"    color: #475569;\n"
"}\n"
"QTreeWidget::item:hover {\n"
"    background-color: #f1f5f9;\n"
"}\n"
"QTreeWidget::item:selected {\n"
"    background-color: #e0f2fe;\n"
"    color: #0369a1;\n"
"}")
        self.folderTree.setHeaderHidden(True)
        self.folderTree.setIndentation(16)

        self.sidebarLayout.addWidget(self.folderTree)

        self.memoHeader = QWidget(self.sidebar)
        self.memoHeader.setObjectName(u"memoHeader")
        self.memoHeader.setMinimumSize(QSize(0, 48))
        self.memoHeader.setMaximumSize(QSize(16777215, 48))
        self.memoHeader.setStyleSheet(u"#memoHeader {\n"
"    background-color: #f8fafc;\n"
"    border-top: 1px solid #e2e8f0;\n"
"    border-bottom: 1px solid #e2e8f0;\n"
"}")
        self.memoHeaderLayout = QHBoxLayout(self.memoHeader)
        self.memoHeaderLayout.setObjectName(u"memoHeaderLayout")
        self.memoHeaderLayout.setContentsMargins(16, 0, 12, 0)
        self.memoLabel = QLabel(self.memoHeader)
        self.memoLabel.setObjectName(u"memoLabel")
        self.memoLabel.setStyleSheet(u"font-size: 14px;\n"
"font-weight: 600;\n"
"color: #1e293b;")

        self.memoHeaderLayout.addWidget(self.memoLabel)

        self.memoSpacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.memoHeaderLayout.addItem(self.memoSpacer)

        self.addMemoButton = QPushButton(self.memoHeader)
        self.addMemoButton.setObjectName(u"addMemoButton")
        self.addMemoButton.setMinimumSize(QSize(28, 28))
        self.addMemoButton.setMaximumSize(QSize(28, 28))
        self.addMemoButton.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    border: 1px solid #e2e8f0;\n"
"    border-radius: 6px;\n"
"    color: #64748b;\n"
"    font-size: 16px;\n"
"    font-weight: 500;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #f1f5f9;\n"
"    border-color: #94a3b8;\n"
"    color: #475569;\n"
"}")

        self.memoHeaderLayout.addWidget(self.addMemoButton)

        self.memoDeleteButton = QPushButton(self.memoHeader)
        self.memoDeleteButton.setObjectName(u"memoDeleteButton")
        self.memoDeleteButton.setMinimumSize(QSize(28, 28))
        self.memoDeleteButton.setMaximumSize(QSize(28, 28))
        self.memoDeleteButton.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    border: 1px solid #e2e8f0;\n"
"    border-radius: 6px;\n"
"    color: #64748b;\n"
"    font-size: 16px;\n"
"    font-weight: 500;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #f1f5f9;\n"
"    border-color: #94a3b8;\n"
"    color: #475569;\n"
"}")

        self.memoHeaderLayout.addWidget(self.memoDeleteButton)


        self.sidebarLayout.addWidget(self.memoHeader)

        self.memoList = QListWidget(self.sidebar)
        self.memoList.setObjectName(u"memoList")
        self.memoList.setStyleSheet(u"QListWidget {\n"
"    background: transparent;\n"
"    border: none;\n"
"    outline: none;\n"
"    padding: 8px;\n"
"}\n"
"QListWidget::item {\n"
"    border-radius: 8px;\n"
"    padding: 10px 12px;\n"
"    margin: 2px 0px;\n"
"    color: #475569;\n"
"}\n"
"QListWidget::item:hover {\n"
"    background-color: #f1f5f9;\n"
"}\n"
"QListWidget::item:selected {\n"
"    background-color: #e0f2fe;\n"
"    color: #0369a1;\n"
"}")

        self.sidebarLayout.addWidget(self.memoList)

        self.splitter.addWidget(self.sidebar)
        self.editorPanel = QWidget(self.splitter)
        self.editorPanel.setObjectName(u"editorPanel")
        self.editorPanel.setStyleSheet(u"#editorPanel {\n"
"    background-color: #f8fafc;\n"
"}")
        self.editorLayout = QVBoxLayout(self.editorPanel)
        self.editorLayout.setObjectName(u"editorLayout")
        self.editorLayout.setContentsMargins(24, 24, 24, 24)
        self.editorCard = QFrame(self.editorPanel)
        self.editorCard.setObjectName(u"editorCard")
        self.editorCard.setStyleSheet(u"QFrame {\n"
"    background-color: #ffffff;\n"
"    border: 1px solid #e2e8f0;\n"
"    border-radius: 16px;\n"
"}")
        self.editorCard.setFrameShape(QFrame.NoFrame)
        self.cardLayout = QVBoxLayout(self.editorCard)
        self.cardLayout.setSpacing(0)
        self.cardLayout.setObjectName(u"cardLayout")
        self.cardLayout.setContentsMargins(0, 0, 0, 0)
        self.editorHeader = QWidget(self.editorCard)
        self.editorHeader.setObjectName(u"editorHeader")
        self.editorHeader.setMinimumSize(QSize(0, 56))
        self.editorHeader.setMaximumSize(QSize(16777215, 56))
        self.editorHeader.setStyleSheet(u"#editorHeader {\n"
"    background-color: transparent;\n"
"    border-bottom: 1px solid #f1f5f9;\n"
"}")
        self.editorHeaderLayout = QHBoxLayout(self.editorHeader)
        self.editorHeaderLayout.setObjectName(u"editorHeaderLayout")
        self.editorHeaderLayout.setContentsMargins(20, 0, 16, 0)
        self.logoLabel = QLabel(self.editorHeader)
        self.logoLabel.setObjectName(u"logoLabel")
        self.logoLabel.setStyleSheet(u"font-size: 22px;")

        self.editorHeaderLayout.addWidget(self.logoLabel)

        self.currentFolderLabel = QLabel(self.editorHeader)
        self.currentFolderLabel.setObjectName(u"currentFolderLabel")
        self.currentFolderLabel.setStyleSheet(u"font-size: 15px;\n"
"font-weight: 600;\n"
"color: #1e293b;")

        self.editorHeaderLayout.addWidget(self.currentFolderLabel)

        self.editorSpacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.editorHeaderLayout.addItem(self.editorSpacer)

        self.settingsButton = QPushButton(self.editorHeader)
        self.settingsButton.setObjectName(u"settingsButton")
        self.settingsButton.setMinimumSize(QSize(32, 32))
        self.settingsButton.setMaximumSize(QSize(32, 32))
        self.settingsButton.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    border: none;\n"
"    border-radius: 8px;\n"
"    font-size: 14px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #f1f5f9;\n"
"}")

        self.editorHeaderLayout.addWidget(self.settingsButton)

        self.syncButton = QPushButton(self.editorHeader)
        self.syncButton.setObjectName(u"syncButton")
        self.syncButton.setMinimumSize(QSize(32, 32))
        self.syncButton.setMaximumSize(QSize(32, 32))
        self.syncButton.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    border: none;\n"
"    border-radius: 8px;\n"
"    font-size: 14px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #f1f5f9;\n"
"}")

        self.editorHeaderLayout.addWidget(self.syncButton)

        self.syncStatusLabel = QLabel(self.editorHeader)
        self.syncStatusLabel.setObjectName(u"syncStatusLabel")
        self.syncStatusLabel.setStyleSheet(u"font-size: 13px;\n"
"font-weight: 500;\n"
"color: #22c55e;")

        self.editorHeaderLayout.addWidget(self.syncStatusLabel)


        self.cardLayout.addWidget(self.editorHeader)

        self.editor = QTextEdit(self.editorCard)
        self.editor.setObjectName(u"editor")
        self.editor.setStyleSheet(u"QTextEdit {\n"
"    background-color: #ffffff;\n"
"    border: none;\n"
"    padding: 16px 20px;\n"
"    font-family: \"Malgun Gothic\", \"Segoe UI\", sans-serif;\n"
"    font-size: 14px;\n"
"    line-height: 1.6;\n"
"    color: #334155;\n"
"    selection-background-color: #bae6fd;\n"
"}")

        self.cardLayout.addWidget(self.editor)


        self.editorLayout.addWidget(self.editorCard)

        self.splitter.addWidget(self.editorPanel)

        self.verticalLayout.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"\ub204\ub2c8\uba54\ubaa8", None))
        self.folderLabel.setText(QCoreApplication.translate("MainWindow", u"\ud3f4\ub354", None))
        self.addFolderButton.setText(QCoreApplication.translate("MainWindow", u"+", None))
        self.folderDeleteButton.setText(QCoreApplication.translate("MainWindow", u"🗑", None))
        self.memoLabel.setText(QCoreApplication.translate("MainWindow", u"\uba54\ubaa8", None))
        self.addMemoButton.setText(QCoreApplication.translate("MainWindow", u"+", None))
        self.memoDeleteButton.setText(QCoreApplication.translate("MainWindow", u"🗑", None))
        self.logoLabel.setText(QCoreApplication.translate("MainWindow", u"\U0001f4dd", None))
        self.currentFolderLabel.setText(QCoreApplication.translate("MainWindow", u"\ud3f4\ub354: \uba54\ubaa8", None))
        self.settingsButton.setText(QCoreApplication.translate("MainWindow", u"\u2699\ufe0f", None))
        self.syncButton.setText(QCoreApplication.translate("MainWindow", u"\U0001f504", None))
        self.syncStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\ub3d9\uae30\ud654 \uc0c1\ud0dc", None))
        self.editor.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\uc5ec\uae30\uc5d0 \uba54\ubaa8\ub97c \uc791\uc131\ud558\uc138\uc694...\n"
"\n"
"\ud301: Ctrl+V\ub85c \ud074\ub9bd\ubcf4\ub4dc \uc774\ubbf8\uc9c0\ub97c \ubc14\ub85c \ubd99\uc5ec\ub123\uc744 \uc218 \uc788\uc2b5\ub2c8\ub2e4.", None))
    # retranslateUi
