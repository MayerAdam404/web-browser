import sys
import os
import json
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLineEdit, QToolBar,
                             QAction, QDialog, QVBoxLayout, QComboBox, QLabel,
                             QPushButton, QTabWidget, QMenu, QToolButton, QInputDialog,
                             QStyleFactory)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from urllib.parse import quote_plus
from PyQt5.QtGui import QColor, QPalette, QIcon

# Keresőmotor URL-ek
SEARCH_ENGINES = {
    "Google": "https://www.google.com/search?q={}",
    "Brave": "https://search.brave.com/search?q={}",
    "Ecosia": "https://www.ecosia.org/search?q={}",
    "Wikipedia": "https://hu.wikipedia.org/wiki/Special:Search?search={}",
    "YouTube": "https://www.youtube.com/results?search_query={}"
}

# Nyelvi beállítások
LANGUAGES = {
    "hu": {
        "title": "MediaCat Web Browser",
        "back": "Vissza",
        "forward": "Előre",
        "home": "Kezdőlap",
        "refresh": "Frissítés",
        "settings": "Beállítások",
        "new_tab": "Új lap",
        "url_bar": "Adjon meg URL-t vagy keresési kifejezést",
        "settings_title": "Beállítások",
        "theme": "Téma:",
        "search_engine": "Keresőmotor:",
        "language": "Nyelv:",
        "save": "Mentés",
        "bookmarks_menu": "Könyvjelzők",
        "add_bookmark": "Könyvjelző hozzáadása",
        "add_bookmark_title": "Könyvjelző hozzáadása",
        "shortcut_success": "Parancsikon sikeresen létrehozva asztalon!"
    },
    "en": {
        "title": "MediaCat Web Browser",
        "back": "Back",
        "forward": "Forward",
        "home": "Home",
        "refresh": "Refresh",
        "settings": "Settings",
        "new_tab": "New Tab",
        "url_bar": "Enter URL or search query",
        "settings_title": "Settings",
        "theme": "Theme:",
        "search_engine": "Search Engine:",
        "language": "Language:",
        "save": "Save",
        "bookmarks_menu": "Bookmarks",
        "add_bookmark": "Add Bookmark",
        "add_bookmark_title": "Add Bookmark",
        "shortcut_success": "Shortcut successfully created on desktop!"
    }
}

class IconManager:
    @staticmethod
    def get_icon(icon_name):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LANGUAGES[parent.language]["settings_title"])
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.setFixedSize(300, 200)

        # Téma választó
        self.theme_label = QLabel(LANGUAGES[parent.language]["theme"])
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Fekete", "Fehér"])
        self.theme_combo.setCurrentText("Fekete" if parent.current_theme == "dark" else "Fehér")
        
        # Keresőmotor választó
        self.engine_label = QLabel(LANGUAGES[parent.language]["search_engine"])
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(SEARCH_ENGINES.keys())
        self.engine_combo.setCurrentText(parent.current_engine)

        # Nyelv választó
        self.language_label = QLabel(LANGUAGES[parent.language]["language"])
        self.language_combo = QComboBox()
        self.language_combo.addItems(["hu", "en"])
        self.language_combo.setCurrentText(parent.language)

        # Mentés gomb
        self.save_button = QPushButton(LANGUAGES[parent.language]["save"])
        self.save_button.clicked.connect(self.save_settings)

        self.layout.addWidget(self.theme_label)
        self.layout.addWidget(self.theme_combo)
        self.layout.addWidget(self.engine_label)
        self.layout.addWidget(self.engine_combo)
        self.layout.addWidget(self.language_label)
        self.layout.addWidget(self.language_combo)
        self.layout.addWidget(self.save_button)

    def save_settings(self):
        selected_theme = self.theme_combo.currentText()
        self.parent.set_theme("dark" if selected_theme == "Fekete" else "light")
        self.parent.current_engine = self.engine_combo.currentText()
        self.parent.language = self.language_combo.currentText()
        self.parent.update_ui_language()
        self.accept()

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.language = "hu"
        self.current_theme = "dark"
        self.current_engine = "Google"
        self.bookmarks_file = "bookmarks.json"
        self.bookmarks = self.load_bookmarks()
        
        # Sütik mentése: Beállítjuk az alapértelmezett profilt, hogy engedélyezze az állandó sütiket.
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

        self.setWindowTitle(LANGUAGES[self.language]["title"])

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.navigation_bar = QToolBar("Navigáció")
        self.addToolBar(self.navigation_bar)
        
        # Navigációs gombok
        self.back_button = QAction(IconManager.get_icon("back.png"), LANGUAGES[self.language]["back"], self)
        self.back_button.triggered.connect(lambda: self.tabs.currentWidget().back())
        self.navigation_bar.addAction(self.back_button)

        self.forward_button = QAction(IconManager.get_icon("forward.png"), LANGUAGES[self.language]["forward"], self)
        self.forward_button.triggered.connect(lambda: self.tabs.currentWidget().forward())
        self.navigation_bar.addAction(self.forward_button)

        self.home_button = QAction(IconManager.get_icon("home.png"), LANGUAGES[self.language]["home"], self)
        self.home_button.triggered.connect(self.go_home)
        self.navigation_bar.addAction(self.home_button)
        
        self.refresh_button = QAction(IconManager.get_icon("refresh.png"), LANGUAGES[self.language]["refresh"], self)
        self.refresh_button.triggered.connect(lambda: self.tabs.currentWidget().reload())
        self.navigation_bar.addAction(self.refresh_button)

        # Címsor
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setPlaceholderText(LANGUAGES[self.language]["url_bar"])
        self.navigation_bar.addWidget(self.url_bar)

        # "Kedvencek" gomb
        self.add_bookmark_button = QAction(IconManager.get_icon("bookmark.png"), "★", self)
        self.add_bookmark_button.triggered.connect(self.add_bookmark_dialog)
        self.navigation_bar.addAction(self.add_bookmark_button)
        
        self.new_tab_button = QAction(IconManager.get_icon("new_tab.png"), LANGUAGES[self.language]["new_tab"], self)
        self.new_tab_button.triggered.connect(self.add_new_tab)
        self.navigation_bar.addAction(self.new_tab_button)

        self.settings_button = QAction(IconManager.get_icon("settings.png"), LANGUAGES[self.language]["settings"], self)
        self.settings_button.triggered.connect(self.show_settings)
        self.navigation_bar.addAction(self.settings_button)

        # Könyvjelzők sáv
        self.bookmarks_toolbar = QToolBar("Könyvjelzők sáv")
        self.addToolBar(Qt.BottomToolBarArea, self.bookmarks_toolbar)
        self.bookmarks_menu_button = QToolButton()
        self.bookmarks_menu_button.setText(LANGUAGES[self.language]["bookmarks_menu"])
        self.bookmarks_toolbar.addWidget(self.bookmarks_menu_button)
        self.bookmarks_menu = QMenu(self)
        self.bookmarks_menu_button.setMenu(self.bookmarks_menu)
        self.bookmarks_menu_button.setPopupMode(QToolButton.InstantPopup)
        
        self.tabs.currentChanged.connect(self.current_tab_changed)

        self.add_new_tab(QUrl("https://www.google.com"), 'Kezdőlap')
        self.set_theme(self.current_theme)
        self.update_bookmarks_menu()

        self.showMaximized()

    def load_bookmarks(self):
        if os.path.exists(self.bookmarks_file):
            try:
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError):
                return {}
        return {}

    def save_bookmarks(self):
        with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
            json.dump(self.bookmarks, f, indent=4)

    def update_bookmarks_menu(self):
        self.bookmarks_menu.clear()
        
        for name, url in self.bookmarks.items():
            action = self.bookmarks_menu.addAction(name)
            action.triggered.connect(lambda checked, url=url, name=name: self.add_new_tab(QUrl(url), name))
    
    def add_bookmark_dialog(self):
        current_url = self.tabs.currentWidget().url().toString()
        current_title = self.tabs.currentWidget().page().title()
        
        name, ok = QInputDialog.getText(self, LANGUAGES[self.language]["add_bookmark_title"], "Név:", QLineEdit.Normal, current_title)
        if ok and name:
            self.bookmarks[name] = current_url
            self.save_bookmarks()
            self.update_bookmarks_menu()

    def add_new_tab(self, qurl=None, label="új lap"):
        browser = QWebEngineView()
        
        # Javított sor: A QWebEnginePage-t direktben hozzuk létre, és a profilt adjuk át neki
        browser.setPage(QWebEnginePage(self.profile, self))

        if qurl is None or isinstance(qurl, bool):
            browser.setUrl(QUrl("https://www.google.com"))
        else:
            browser.setUrl(qurl)
        
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_url_bar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))
        
        self.update_tab_style()

    def close_tab(self, index):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(index)

    def go_home(self):
        self.tabs.currentWidget().setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url:
            return
            
        if not url.startswith(("http://", "https://")):
            if "." in url:
                url = "https://" + url
                self.tabs.currentWidget().setUrl(QUrl(url))
            else:
                search_query = quote_plus(url)
                selected_engine_url = SEARCH_ENGINES[self.current_engine].format(search_query)
                self.tabs.currentWidget().setUrl(QUrl(selected_engine_url))
        else:
            self.tabs.currentWidget().setUrl(QUrl(url))

    def update_url_bar(self, qurl, browser=None):
        if browser != self.tabs.currentWidget():
            return
        self.url_bar.setText(qurl.toString())

    def current_tab_changed(self, index):
        if self.tabs.currentWidget():
            qurl = self.tabs.currentWidget().url()
            self.update_url_bar(qurl)

    def set_theme(self, theme):
        self.current_theme = theme
        palette = QPalette()
        if theme == "dark":
            self.setStyleSheet(self.get_dark_stylesheet())
        else:
            self.setStyleSheet(self.get_light_stylesheet())
        
        self.setPalette(palette)
        
    def get_dark_stylesheet(self):
        return """
            QMainWindow {
                background-color: #2e2e2e;
            }
            QToolBar {
                background-color: #1e1e1e;
                spacing: 10px;
                padding: 5px;
            }
            QTabWidget::pane { /* A tabok pane-je */
                border: 1px solid #505050;
                background-color: #2e2e2e;
            }
            QTabBar::tab {
                background: #353535;
                color: #e0e0e0;
                padding: 8px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border: 1px solid #505050;
                margin-top: 2px;
                margin-left: 2px;
            }
            QTabBar::tab:selected {
                background: #4a4a4a;
                border-bottom-color: #4a4a4a;
            }
            QTabBar::tab:hover {
                background: #505050;
            }
            QLineEdit {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 15px;
                padding: 5px 15px;
            }
            QAction {
                color: #e0e0e0;
                padding: 5px;
            }
            QAction:hover {
                background-color: #4a4a4a;
                border-radius: 5px;
            }
            QMenu {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #505050;
            }
            QMenu::item:selected {
                background-color: #505050;
            }
            QToolButton {
                border: none;
                padding: 5px 10px;
                color: #e0e0e0;
            }
            QToolButton:hover {
                background-color: #4a4a4a;
                border-radius: 5px;
            }
        """

    def get_light_stylesheet(self):
        return """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QToolBar {
                background-color: #e0e0e0;
                spacing: 10px;
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: #f0f0f0;
            }
            QTabBar::tab {
                background: #d0d0d0;
                color: #1e1e1e;
                padding: 8px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border: 1px solid #c0c0c0;
                margin-top: 2px;
                margin-left: 2px;
            }
            QTabBar::tab:selected {
                background: #f0f0f0;
                border-bottom-color: #f0f0f0;
            }
            QTabBar::tab:hover {
                background: #c0c0c0;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #cccccc;
                border-radius: 15px;
                padding: 5px 15px;
            }
            QAction {
                color: #1e1e1e;
                padding: 5px;
            }
            QAction:hover {
                background-color: #c0c0c0;
                border-radius: 5px;
            }
            QMenu {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #cccccc;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QToolButton {
                border: none;
                padding: 5px 10px;
                color: #1e1e1e;
            }
            QToolButton:hover {
                background-color: #d0d0d0;
                border-radius: 5px;
            }
        """
    def update_tab_style(self):
        # A stíluslap most már globálisan van beállítva, így ez a metódus már nem szükséges
        pass

    def show_settings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec_()
        
    def update_ui_language(self):
        texts = LANGUAGES[self.language]
        self.setWindowTitle(texts["title"])
        self.back_button.setText(texts["back"])
        self.forward_button.setText(texts["forward"])
        self.home_button.setText(texts["home"])
        self.refresh_button.setText(texts["refresh"])
        self.add_bookmark_button.setText(texts["add_bookmark"])
        self.settings_button.setText(texts["settings"])
        self.new_tab_button.setText(texts["new_tab"])
        self.url_bar.setPlaceholderText(texts["url_bar"])
        self.bookmarks_menu_button.setText(texts["bookmarks_menu"])
        self.update_bookmarks_menu()

    def create_shortcut(self):
        try:
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            desktop_path = shell.SpecialFolders('Desktop')
            shortcut_path = os.path.join(desktop_path, "MediaCat Web Browser.lnk")
            
            shortcut = shell.CreateShortcut(shortcut_path)
            shortcut.TargetPath = os.path.abspath(__file__)
            shortcut.IconLocation = os.path.abspath(__file__)
            shortcut.Save()
            print(LANGUAGES[self.language]["shortcut_success"])
        except ImportError:
            print("Figyelem: A 'pywin32' modul nincs telepítve. Az asztali parancsikon nem hozható létre.")
            print("Telepítsd a 'pip install pywin32' paranccsal.")
        except Exception as e:
            print(f"Hiba történt a parancsikon létrehozása közben: {e}")

if __name__ == '__main__':
    if sys.platform.startswith('win'):
        try:
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            desktop_path = shell.SpecialFolders('Desktop')
            shortcut_path = os.path.join(desktop_path, "MediaCat Web Browser.lnk")
            
            if not os.path.exists(shortcut_path):
                shortcut = shell.CreateShortcut(shortcut_path)
                shortcut.TargetPath = os.path.abspath(__file__)
                shortcut.IconLocation = os.path.abspath(__file__)
                shortcut.Save()
                print(LANGUAGES["hu"]["shortcut_success"])
        except ImportError:
            pass

    app = QApplication(sys.argv)
    window = Browser()
    sys.exit(app.exec_())