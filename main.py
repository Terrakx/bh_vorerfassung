import sys
import os
import shutil
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QGridLayout, QDateEdit, QMessageBox, QStyledItemDelegate, QLineEdit
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtCore import QSignalBlocker

os.makedirs('data', exist_ok=True)

class ExtendedNumericDelegate(QStyledItemDelegate):
    def __init__(self, column, parent=None):
        super().__init__(parent)
        self.column = column

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # Unterscheidung der Validierung basierend auf der Spalte
        if self.column == 'Tag':  # Nur eine Zahl mit maximal 2 Stellen für das Belegdatum
            reg_ex = QRegExp("^[0-9]{1,2}$")
        elif self.column in ['Kontonummer', 'Prozent', 'StC']:  # Ganzzahlen für Kontonummer, Prozent und StC
            reg_ex = QRegExp("^[0-9]*$")
        elif self.column in ['Eingang', 'Ausgang']:  # Kommazahlen für Eingang und Ausgang
            reg_ex = QRegExp("^-?\d*(\.\d+)?$")  # Achten Sie darauf, dass der Dezimaltrenner Ihrem Bedarf entspricht (\. für Punkt oder \, für Komma)
        validator = QRegExpValidator(reg_ex, editor)
        editor.setValidator(validator)
        return editor

class Hauptfenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.oldPos = None
        self.isAddingRow = False
        self.buchungstabelle.cellChanged.connect(self.handleCellChange)
        self.ladenAusJson() 
        self.loadKontoplan()
        self.month_dropdown.currentIndexChanged.connect(self.datenLadenSpeichern)
        self.year_dropdown.currentIndexChanged.connect(self.datenLadenSpeichern)
        self.buchungstabelle.itemChanged.connect(self.speichernAlsJson)
        self.buchungstabelle.cellChanged.connect(self.handleCellChange)
        self.buchungstabelle.cellChanged.connect(self.updateKontobezeichnung)

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)

        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)
        # Einstiegsdaten Section
        einstiegsdaten_layout = QVBoxLayout()
        einstiegsdaten_headline = QLabel("Einstiegsdaten")
        einstiegsdaten_layout.addWidget(einstiegsdaten_headline)
        self.setAcceptDrops(True)
        # Layout für Buchungsmonat
        buchungsmonat_layout = QGridLayout()
        buchungsmonat_label = QLabel("Buchungsmonat:")
        self.month_dropdown = QComboBox()
        self.month_dropdown.addItems(["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"])
        self.month_dropdown.setFixedWidth(150)
        buchungsmonat_layout.addWidget(buchungsmonat_label, 0, 0, 2, 1)  # Label erstreckt sich über 2 Reihen
        buchungsmonat_layout.addWidget(self.month_dropdown, 0, 2, 2, 8)  # Dropdown-Feld erstreckt sich über 8 Spalten

        einstiegsdaten_layout.addLayout(buchungsmonat_layout)

        # Layout für Buchungsjahr
        buchungsjahr_layout = QGridLayout()
        buchungsjahr_label = QLabel("Buchungsjahr:")
        self.year_dropdown = QComboBox()
        self.year_dropdown.addItems(["2022", "2023", "2024", "2025"])
        self.year_dropdown.setFixedWidth(150)
        buchungsjahr_layout.addWidget(buchungsjahr_label, 0, 0, 2, 1)  # Label erstreckt sich über 2 Reihen
        buchungsjahr_layout.addWidget(self.year_dropdown, 0, 2, 2, 8)  # Dropdown-Feld erstreckt sich über 8 Spalten

        einstiegsdaten_layout.addLayout(buchungsjahr_layout)


        # Layout für Buchungseinstellung
        buchungseinstellung_layout = QGridLayout()
        buchungseinstellung_label = QLabel("Buchungseinstellung:")
        self.buchungsart_dropdown = QComboBox()
        self.buchungsart_dropdown.addItems(["Bankbuch", "Kassabuch"])
        self.buchungsart_dropdown.setFixedWidth(150)  # Legen Sie die gewünschte Breite fest, z.B. 150 Pixel
        buchungseinstellung_layout.addWidget(buchungseinstellung_label, 0, 0, 2, 1)  # Label erstreckt sich über 2 Reihen
        buchungseinstellung_layout.addWidget(self.buchungsart_dropdown, 0, 2, 2, 8)  # Dropdown-Feld erstreckt sich über 8 Spalten

        einstiegsdaten_layout.addLayout(buchungseinstellung_layout)

        # Layout for Kontoplan dropdown
        kontoplan_label = QLabel("Kontoplan:")
        self.kontoplan_dropdown = QComboBox()
        self.kontoplan_dropdown.addItems(["Standard", "Land- und Forstwirtschaft", "Vermietung"])
        self.kontoplan_dropdown.setFixedWidth(150)
        buchungseinstellung_layout.addWidget(kontoplan_label, 2, 0, 2, 1)  # Label extends over 2 rows
        buchungseinstellung_layout.addWidget(self.kontoplan_dropdown, 2, 2, 2, 8)  # Dropdown field extends over 8 columns

        einstiegsdaten_layout.addLayout(buchungseinstellung_layout)

        # Vorerfassung Section
        vorerfassung_layout = QVBoxLayout()
        vorerfassung_headline = QLabel("Vorerfassung")
        self.buchungstabelle = QTableWidget()
        self.buchungstabelle.setColumnCount(11)
        self.buchungstabelle.setHorizontalHeaderLabels(["Tag", "Belegnummer", "Buchungstext", "Kontonummer", "Konto","Eingang", "Ausgang", "StC", "Prozent", "Umsatzsteuer", "Dokument"])
        self.buchungstabelle.horizontalHeader().setStretchLastSection(True)
        self.buchungstabelle.setColumnWidth(0, 110)
        self.buchungstabelle.setColumnWidth(1, 110)
        self.buchungstabelle.setColumnWidth(2, 300)
        self.buchungstabelle.setColumnWidth(3, 110)
        self.buchungstabelle.setColumnWidth(4, 190)
        self.buchungstabelle.setColumnWidth(5, 120)
        self.buchungstabelle.setColumnWidth(6, 120)
        self.buchungstabelle.setColumnWidth(7, 65)

        self.belegdatumDelegate = ExtendedNumericDelegate('Tag')
        self.buchungstabelle.setItemDelegateForColumn(0, self.belegdatumDelegate)

        self.kontonummerDelegate = ExtendedNumericDelegate('Kontonummer')
        self.buchungstabelle.setItemDelegateForColumn(3, self.kontonummerDelegate)

        self.eingangDelegate = ExtendedNumericDelegate('Eingang')
        self.buchungstabelle.setItemDelegateForColumn(5, self.eingangDelegate)

        self.ausgangDelegate = ExtendedNumericDelegate('Ausgang')
        self.buchungstabelle.setItemDelegateForColumn(6, self.ausgangDelegate) 

        self.stcDelegate = ExtendedNumericDelegate('StC')
        self.buchungstabelle.setItemDelegateForColumn(7, self.stcDelegate)

        self.prozentDelegate = ExtendedNumericDelegate('Prozent')
        self.buchungstabelle.setItemDelegateForColumn(8, self.prozentDelegate)

        self.buchungstabelle.setColumnWidth(8, 80)
        self.buchungstabelle.setColumnWidth(9, 120)
        self.buchungstabelle.setColumnWidth(10, 150)
        self.buchungstabelle.setAcceptDrops(True)
        self.buchungstabelle.setDragDropOverwriteMode(False)
        self.buchungstabelle.setDragDropMode(QTableWidget.DropOnly)
        self.buchungstabelle.setSelectionBehavior(QTableWidget.SelectRows)
        self.buchungstabelle.setDropIndicatorShown(True)
        self.buchungstabelle.cellChanged.connect(self.handleCellChange)
        vorerfassung_layout.addWidget(vorerfassung_headline)
        vorerfassung_layout.addWidget(self.buchungstabelle)

        self.addRowButton = QPushButton("Zeile manuell hinzufügen")
        self.addRowButton.clicked.connect(self.addTableRow)
        vorerfassung_layout.addWidget(self.addRowButton)

        layout.addLayout(einstiegsdaten_layout)
        layout.addLayout(vorerfassung_layout)

        # Button-Layout für "Beenden" Button
        button_layout = QVBoxLayout()
        layout.addLayout(button_layout)

        self.beendenButton = QPushButton("Beenden")
        self.beendenButton.clicked.connect(self.closeApplication)
        self.beendenButton.setStyleSheet("QPushButton { background-color: red; color: white; font-weight: bold; }")
        button_layout.addWidget(self.beendenButton)

        stylesheet = self.loadStylesheet("style.css")
        self.setStyleSheet(stylesheet)

    def loadStylesheet(self, filename):
        try:
            with open(filename, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Fehler beim Laden des Stylesheets: {e}")
            return ""

    def loadKontoplan(self):
        try:
            with open('kontoplan.json', 'r') as file:
                self.kontoplan_data = json.load(file)
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden des Kontoplans", f"Ein Fehler ist aufgetreten: {e}")
            self.kontoplan_data = {"Kontoplan": []}  # Set an empty Kontoplan as a fallback

    # Add this slot function to your Hauptfenster class
    def updateKontobezeichnung(self, row, column):
        if column == 3:  # Check if the change occurred in the "Kontonummer" column
            kontonummer_item = self.buchungstabelle.item(row, column)
            if kontonummer_item:
                kontonummer = kontonummer_item.text()
                selected_kontoplan = self.kontoplan_dropdown.currentText()
                
                # Find the corresponding "Kontobezeichnung" in the selected Kontoplan
                kontobezeichnung = ""
                for kontoplan in self.kontoplan_data["Kontoplan"]:
                    if kontoplan["KontenplanName"] == selected_kontoplan:
                        for konten in kontoplan["Konten"]:
                            if konten["Kontonummer"] == kontonummer:
                                kontobezeichnung = konten["Bezeichnung"]
                                break
                
                # Update the "Konto" field
                konto_item = self.buchungstabelle.item(row, 4)
                if konto_item:
                    # Block signals temporarily to prevent infinite recursion
                    with QSignalBlocker(self.buchungstabelle):
                        konto_item.setText(kontobezeichnung)
   

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.pdf'):
                    print("Drag Enter Event akzeptiert für: ", url.toLocalFile())
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            print("Drop Event für Datei: ", file_path)
            if file_path.lower().endswith('.pdf'):
                self.handlePdfDrop(file_path)
                event.acceptProposedAction()
                return
        event.ignore()

    def handleCellChange(self, row, column):
        # Verhindere, dass die Funktion ausgeführt wird, wenn die Tabelle gerade befüllt wird
        if self.isAddingRow or self.buchungstabelle.currentRow() == -1:
            return

        # Überprüfe, ob die Änderung in der Spalte "Eingang" erfolgt ist
        if column == 5:  # Angenommen, "Eingang" ist jetzt Spalte 5
            currentEingangItem = self.buchungstabelle.item(row, 5)
            if currentEingangItem and currentEingangItem.text().strip():
                # Lösche den Wert in "Ausgang", falls vorhanden
                ausgangItem = self.buchungstabelle.item(row, 6)
                if ausgangItem:
                    ausgangItem.setText('')

        # Überprüfe, ob die Änderung in der Spalte "Ausgang" erfolgt ist
        elif column == 6:  # Angenommen, "Ausgang" ist jetzt Spalte 6
            currentAusgangItem = self.buchungstabelle.item(row, 6)
            if currentAusgangItem and currentAusgangItem.text().strip():
                # Lösche den Wert in "Eingang", falls vorhanden
                eingangItem = self.buchungstabelle.item(row, 5)
                if eingangItem:
                    eingangItem.setText('')


    def handlePdfDrop(self, file_path):
        # Extrahieren des ausgewählten Jahres und Monats
        selectedYear = self.year_dropdown.currentText()
        selectedMonthName = self.month_dropdown.currentText()

        # Umwandlung des Monatsnamens in eine Zahl (01 für Jänner, 02 für Februar, usw.)
        monthNames = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        selectedMonth = monthNames.index(selectedMonthName) + 1
        selectedMonthStr = f"{selectedMonth:02d}"  # Führende Null für einstellige Monate

        # Konstruktion des Speicherpfads mit Jahr und Monat
        save_path = os.path.join("Belege", selectedYear, selectedMonthStr)

        try:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            # Kopieren der PDF-Datei in den Zielordner
            shutil.copy(file_path, save_path)

            # Bestimmung der Zielzeile
            selectedItems = self.buchungstabelle.selectedItems()
            if selectedItems:
                row = selectedItems[0].row()
            else:
                QMessageBox.warning(self, "Keine Zeile ausgewählt", "Bitte wählen Sie eine Zeile aus, bevor Sie eine PDF-Datei ablegen.")
                return

            # Eintrag in der Tabelle erstellen
            self.buchungstabelle.setItem(row, 10, QTableWidgetItem(os.path.join(save_path, os.path.basename(file_path))))
            QMessageBox.information(self, "PDF Hinzugefügt", f"PDF '{os.path.basename(file_path)}' wurde erfolgreich in Zeile {row + 1} hinzugefügt.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Hinzufügen der PDF", f"Ein Fehler ist aufgetreten: {e}")

    def addTableRow(self):
        rowCount = self.buchungstabelle.rowCount()
        self.buchungstabelle.insertRow(rowCount)
        for column in range(self.buchungstabelle.columnCount()):
            item = QTableWidgetItem()
            if column == 9:  # Angenommen, die Umsatzsteuer ist in Spalte 8
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Sperrt die Zelle für die Bearbeitung
            self.buchungstabelle.setItem(rowCount, column, item)


    def closeApplication(self):
        self.close()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def start(self):
        self.setWindowTitle("Vorerfassung Buchungen")
        self.setGeometry(100, 100, 1680, 900)
        self.show()

    def datenLadenSpeichern(self):
        # Clear the table before loading new data
        self.buchungstabelle.setRowCount(0)

        # Load the data for the selected month/year if the file exists
        self.ladenAusJson()
        monatIndex = self.month_dropdown.currentIndex() + 1
        jahr = self.year_dropdown.currentText()
        dateipfad = f'data/data_{monatIndex:02d}-{jahr}.json'

        # If the file doesn't exist, create a new one
        if not os.path.exists(dateipfad):
            self.speichernAlsJson()

    def isDataChanged(self):
        # Compare the current data with the data loaded from the JSON file
        monatIndex = self.month_dropdown.currentIndex() + 1
        jahr = self.year_dropdown.currentText()
        dateipfad = f'data/data_{monatIndex:02d}-{jahr}.json'

        if os.path.exists(dateipfad):
            try:
                with open(dateipfad, 'r') as file:
                    loaded_data = json.load(file)
                    current_data = self.getCurrentTableData()
                    return loaded_data != current_data
            except json.JSONDecodeError:
                print("Fehler beim Lesen der JSON-Datei. Die Datei ist möglicherweise beschädigt.")
        return False

    def getCurrentTableData(self):
        data = []
        for row in range(self.buchungstabelle.rowCount()):
            row_data = []
            for column in range(self.buchungstabelle.columnCount()):
                item = self.buchungstabelle.item(row, column)
                if item is not None:
                    row_data.append(item.text())
                else:
                    row_data.append("")
            data.append(row_data)
        return data


    def ladenAusJson(self):
        monatIndex = self.month_dropdown.currentIndex() + 1
        jahr = self.year_dropdown.currentText()
        dateipfad = f'data/data_{monatIndex:02d}-{jahr}.json'
        
        # Leere die Tabelle vor dem Laden neuer Daten
        self.buchungstabelle.setRowCount(0)

        if os.path.exists(dateipfad):
            try:
                with open(dateipfad, 'r') as file:
                    daten = json.load(file)
                    for row_data in daten:
                        row = self.buchungstabelle.rowCount()
                        self.buchungstabelle.insertRow(row)
                        for column, value in enumerate(row_data):
                            item = QTableWidgetItem(str(value))  # Konvertiere value zu String, falls nötig
                            self.buchungstabelle.setItem(row, column, item)
            except json.JSONDecodeError:
                print("Fehler beim Lesen der JSON-Datei. Die Datei ist möglicherweise beschädigt.")
        else:
            # Keine Daten für diesen Monat/Jahr gefunden, die Tabelle bleibt leer
            print("Keine Daten für diesen Monat/Jahr gefunden.")
            
    def speichernAlsJson(self):
        monatIndex = self.month_dropdown.currentIndex() + 1
        #monat = self.month_dropdown.currentText()
        jahr = self.year_dropdown.currentText()
        datenZuSpeichern = []
        for row in range(self.buchungstabelle.rowCount()):
            row_data = []
            for column in range(self.buchungstabelle.columnCount()):
                item = self.buchungstabelle.item(row, column)
                if item is not None:
                    row_data.append(item.text())
                else:
                    row_data.append("")
            datenZuSpeichern.append(row_data)

        dateipfad = f'data/data_{monatIndex:02d}-{jahr}.json'
        try:
            with open(dateipfad, 'w') as file:
                json.dump(datenZuSpeichern, file, indent=4)
        except Exception as e:
            print(f"Ein Fehler ist aufgetreten beim Speichern der Daten: {e}")

    def closeEvent(self, event):
        self.speichernAlsJson()
        event.accept()  # Schließt das Fenster

if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenster = Hauptfenster()
    fenster.start()
    sys.exit(app.exec_())
