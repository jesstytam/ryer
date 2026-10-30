import csv
import sys
import os
from pathlib import Path

import pymupdf
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QComboBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QRectF, QSettings
from PyQt6.QtGui import QColor, QImage, QPainter, QPalette, QPixmap

from quotes import PageIndex, find_quotes

HIGHLIGHT_COLOUR = QColor(255, 220, 0, 110)
HIGHLIGHT_MARGIN = 80

#functions

def dark_palette():
    role = QPalette.ColorRole
    group = QPalette.ColorGroup
    palette = QPalette()

    palette.setColor(role.Window, QColor(45, 45, 45))
    palette.setColor(role.WindowText, QColor(230, 230, 230))
    palette.setColor(role.Base, QColor(30, 30, 30))
    palette.setColor(role.AlternateBase, QColor(45, 45, 45))
    palette.setColor(role.Text, QColor(230, 230, 230))
    palette.setColor(role.Button, QColor(55, 55, 55))
    palette.setColor(role.ButtonText, QColor(230, 230, 230))
    palette.setColor(role.ToolTipBase, QColor(30, 30, 30))
    palette.setColor(role.ToolTipText, QColor(230, 230, 230))
    palette.setColor(role.PlaceholderText, QColor(140, 140, 140))
    palette.setColor(role.Highlight, QColor(70, 120, 190))
    palette.setColor(role.HighlightedText, QColor(255, 255, 255))

    for disabled_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(group.Disabled, disabled_role, QColor(120, 120, 120))
    return palette

#classes

class PdfViewer(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.document = None
        self.current_pdf_path = None
        self.index_pages = []
        self.quotes = []
        self.page_number = 0
        self.zoom = 1
        self.dark_mode = False

        #pdf path, which can be selected and copied
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        #quote picker
        self.quote_picker = QComboBox()
        self.quote_picker.currentIndexChanged.connect(self.show_quote)

        #page controls
        self.previous_button = QPushButton("Previous")
        self.previous_button.clicked.connect(lambda: self.show_page(self.page_number - 1))
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(lambda: self.show_page(self.page_number + 1))
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls = QHBoxLayout()
        controls.addWidget(self.previous_button)
        controls.addWidget(self.page_label, 1)
        controls.addWidget(self.next_button)

        #page image
        self.page_image = QLabel()
        self.page_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.page_image)
        self.scroll_area.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.path_label)
        layout.addWidget(self.quote_picker)
        layout.addLayout(controls)
        layout.addWidget(self.scroll_area, 1)

    def load(self, pdf_path, data_quote, source=""):
        if pdf_path != self.current_pdf_path:
            self.document = pymupdf.open(pdf_path)
            self.current_pdf_path = pdf_path
            self.index_pages = [PageIndex(page) for page in self.document]
            self.path_label.setText(pdf_path)

        self.quotes =find_quotes(self.index_pages, data_quote, source)

        self.quote_picker.blockSignals(True)
        self.quote_picker.clear()
        for quote in self.quotes:
            page = f"pdf p. {quote.page + 1}" if quote.page >= 0 else "no page"
            self.quote_picker.addItem(f"[{quote.label}] {quote.match}, {page}")
        self.quote_picker.blockSignals(False)

        found = [i for i, quote in enumerate(self.quotes) if quote.page >= 0]
        if found:
            self.quote_picker.setCurrentIndex(found[0])
            self.show_quote(found[0])
        else:
            self.show_page(0)

    def show_quote(self, index):
        if 0 <= index < len(self.quotes) and self.quotes[index].page >= 0:
            self.show_page(self.quotes[index].page, self.quotes[index])

    def show_page(self, page_number, scroll_to=None):
        if self.document is None or not 0 <= page_number < len(self.document):
            return

        self.page_number = page_number
        page = self.document[page_number]
        self.zoom = max(self.scroll_area.viewport().width() - 20, 200) / page.rect.width

        pix = page.get_pixmap(matrix=pymupdf.Matrix(self.zoom, self.zoom), alpha=False)
        if self.dark_mode:
            pix.invert_irect()
        image =QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)

        #highlights from every quote on this page
        painter = QPainter(pixmap)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(HIGHLIGHT_COLOUR)
        for quote in self.quotes:
            if quote.page == page_number:
                for rect in quote.rects:
                    painter.drawRect(self.to_screen(rect))
        painter.end()

        self.page_image.setPixmap(pixmap)
        self.page_label.setText(f"Page {page_number + 1} of {len(self.document)}")
        self.previous_button.setEnabled(page_number > 0)
        self.next_button.setEnabled(page_number < len(self.document) - 1)

        if scroll_to:
            top = self.to_screen(scroll_to.rects[0]).top() if scroll_to.rects else HIGHLIGHT_MARGIN
            self.scroll_area.verticalScrollBar().setValue(int(top) - HIGHLIGHT_MARGIN)

    def to_screen(self, rect):
        return QRectF(
            rect.x0 * self.zoom,
            rect.y0 * self.zoom,
            rect.width * self.zoom,
            rect.height * self.zoom
        )

    def clear(self, message):
        self.document = None
        self.current_pdf_path = None
        self.index_pages = []
        self.quotes = []
        self.quote_picker.clear()
        self.path_label.setText("")
        self.page_label.setText("")
        self.page_image.clear()
        self.page_image.setText(message)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_page(self.page_number)

class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        #load all parent attibutes from qwidget
        super().__init__(*args, **kwargs)

        #draw window
        self.setWindowTitle("Editor")
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)
        self.csv_filepath = None

        #csv widget
        self.csv_widget = HorizontalScrollTable()
        self.csv_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.csv_widget.currentCellChanged.connect(self.show_selected_pdf)
        self.splitter.addWidget(self.csv_widget)

        #pdf widget
        self.pdf_widget = PdfViewer()
        self.splitter.addWidget(self.pdf_widget)

        #add menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        #add menu items
        load_action = file_menu.addAction("Load CSV")
        load_action.triggered.connect(self.load_csv)
        # export_action = file_menu.addAction("Export CSV")
        # export_action.triggered.connect(self.?)

        #dark mode, which starts from the last choice or else the system theme
        self.settings = QSettings("ryer", "ryer")
        system_dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        dark_mode = self.settings.value("dark_mode", system_dark, type=bool)

        view_menu = menu_bar.addMenu("&View")
        dark_action = view_menu.addAction("Dark mode")
        dark_action.setCheckable(True)
        dark_action.setChecked(dark_mode)
        dark_action.toggled.connect(self.toggle_dark_mode)
        self.set_dark_mode(dark_mode)

        #show window
        self.show()

    def toggle_dark_mode(self, dark_mode):
        self.settings.setValue("dark_mode", dark_mode)
        self.set_dark_mode(dark_mode)

    def set_dark_mode(self, dark_mode):
        app = QApplication.instance()
        app.setPalette(dark_palette() if dark_mode else app.style().standardPalette())
        self.pdf_widget.dark_mode = dark_mode
        self.pdf_widget.show_page(self.pdf_widget.page_number)

    def load_csv(self):

        csv_filepath, _ = QFileDialog.getOpenFileName(
            self,
            "File",
            "",
            "CSV files (*.csv)"
        )

        if not csv_filepath:
            return

        self.open_csv(csv_filepath)

    def open_csv(self, csv_filepath):

        self.csv_filepath = csv_filepath

        with open(csv_filepath, newline="", encoding="utf-8-sig") as file:
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

    def resolve_pdf_path(self, pdf_path):
        #relative paths may start from any folder above the csv, e.g. the project root
        path = Path(pdf_path).expanduser()
        if path.is_absolute():
            return path if path.is_file() else None

        csv_folder = Path(self.csv_filepath).resolve().parent
        for folder in [csv_folder, *csv_folder.parents]:
            if (folder / path).is_file():
                return folder / path
        return None

    def show_selected_pdf(self, row):

        if row < 0:
            return

        headers = {
            self.csv_widget.horizontalHeaderItem(col).text().strip(): col
            for col in range(self.csv_widget.columnCount())
            if self.csv_widget.horizontalHeaderItem(col) is not None
        }

        pdf_path_col = headers.get("pdf_path")
        quote_col = headers.get("data_quote")

        if pdf_path_col is None or quote_col is None:
            self.pdf_widget.clear("CSV needs pdf_path and data_quote columns")
            return

        pdf_item = self.csv_widget.item(row, pdf_path_col)
        quote_item = self.csv_widget.item(row, quote_col)

        pdf_text = pdf_item.text().strip() if pdf_item else ""
        if not pdf_text or pdf_text == "NA":
            self.pdf_widget.clear("This row has no pdf_path")
            return

        pdf_path = self.resolve_pdf_path(pdf_text)
        if pdf_path is None:
            self.pdf_widget.clear(f"PDF not found: {pdf_text}")
            return

        source_col = headers.get("source")
        source_item = self.csv_widget.item(row, source_col) if source_col is not None else None

        self.pdf_widget.load(
            str(pdf_path),
            quote_item.text() if quote_item else "",
            source_item.text() if source_item else ""
        )

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
    app.setStyle("Fusion")
    window = Window()
    sys.exit(app.exec())
