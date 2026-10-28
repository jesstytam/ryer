import csv
import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

#classes

class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        #load all parent attibutes from qwidget
        super().__init__(*args, **kwargs)

        #draw window
        self.setWindowTitle("Editor")
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        #csv widget
        self.csv_widget = HorizontalScrollTable()
        self.csv_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.csv_widget.itemSelectionChanged.connect(self.show_selected_pdf)
        self.splitter.addWidget(self.csv_widget)

        #pdf widget
        self.pdf_widget = QWidget()
        self.pdf_layout = QVBoxLayout(self.pdf_widget)
        self.current_pdf_path = None

        self.webView = QWebEngineView()

        settings = self.webView.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PdfViewerEnabled, True
        )

        self.search_after_load = ""
        self.webView.loadFinished.connect(self.search_loaded_pdf)
        self.pdf_layout.addWidget(self.webView)
        self.splitter.addWidget(self.pdf_widget)

        #add menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        #add menu items
        load_action = file_menu.addAction("Load CSV")
        load_action.triggered.connect(self.load_csv)
        # export_action = file_menu.addAction("Export CSV")
        # export_action.triggered.connect(self.?)

        #show window
        self.show()

    def load_csv(self):

        csv_filepath, _ = QFileDialog.getOpenFileName(
            self,
            "File",
            "",
            "CSV files (*.csv)"
        )

        if not csv_filepath:
            return

        with open(csv_filepath, newline="") as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames or []
            rows = list(reader)
            
        self.csv_widget.setColumnCount(len(headers))
        self.csv_widget.setHorizontalHeaderLabels(headers)
        self.csv_widget.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for column_index, header in enumerate(headers):
                value = row.get(header, "")
                item = QTableWidgetItem(value)
                self.csv_widget.setItem(row_index, column_index, item)

    def show_selected_pdf(self):

        row = self.csv_widget.currentRow()
        if row < 0:
            return

        headers = {
            self.csv_widget.horizontalHeaderItem(col).text().strip(): col
            for col in range(self.csv_widget.columnCount())
            if self.csv_widget.horizontalHeaderItem(col) is not None
        }

        # Add the new code here
        pdf_path_col = headers.get("pdf_path")
        location_col = headers.get("data_location")

        if pdf_path_col is None or location_col is None:
            print("CSV needs pdf_path and data_location columns")
            return

        pdf_item = self.csv_widget.item(row, pdf_path_col)
        location_item = self.csv_widget.item(row, location_col)

        if not pdf_item or not location_item:
            return

        pdf_path = os.path.expanduser(pdf_item.text().strip())
        print("Looking for:", repr(pdf_path))

        if not os.path.isfile(pdf_path):
            print("PDF not found:", repr(pdf_path))
            return

        search_text = location_item.text().strip()

        if pdf_path != self.current_pdf_path:
            self.current_pdf_path = pdf_path
            self.search_after_load = search_text
            print("Loading PDF:", pdf_path)
            print("URL:", QUrl.fromLocalFile(pdf_path).toString())
            self.webView.setUrl(QUrl.fromLocalFile(pdf_path))
        elif search_text:
            self.webView.findText(search_text)

    def search_loaded_pdf(self, ok):
        print("PDF page load:", ok)
        if ok and self.search_after_load:
            self.webView.findText(self.search_after_load)

class HorizontalScrollTable(QTableWidget):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            bar = self.horizontalScrollBar()
            bar.setValue(
                bar.value() - event.angleDelta().y()
            )
            event.accept()
            return

        super().wheelEvent(event)

#run

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec())