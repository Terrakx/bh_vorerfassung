import sys
import os
import shutil
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QFrame, QDialog, QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QGridLayout, QDateEdit, QMessageBox, QStyledItemDelegate, QLineEdit, QDialogButtonBox
from PyQt5.QtGui import QRegExpValidator, QFontDatabase, QIcon, QColor, QFont
from PyQt5.QtCore import Qt, QRegExp, QLocale, QObject, QEvent, QTextStream, QFile
from PyQt5.QtCore import QSignalBlocker
from sort_json import sortiere_und_speichere_json

# -*- coding: utf-8 -*-

os.makedirs('data', exist_ok=True)
os.makedirs('Belege', exist_ok=True)

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
            reg_ex = QRegExp("^-?\d*(\,\d+)?$")  # Achten Sie darauf, dass der Dezimaltrenner Ihrem Bedarf entspricht (\. für Punkt oder \, für Komma)
        validator = QRegExpValidator(reg_ex, editor)
        editor.setValidator(validator)
        return editor

class Hauptfenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadUserPreferences()
        self.oldPos = None
        self.isAddingRow = False
        self.buchungstabelle.cellChanged.connect(self.handleCellChange)
        self.ladenAusJson() 
        self.validateRowsAndSetIcons()
        self.buchungstabelle.selectionModel().selectionChanged.connect(self.onSelectionChanged)
        self.loadKontoplan()
        self.month_dropdown.currentIndexChanged.connect(self.datenLadenSpeichern)
        self.year_dropdown.currentIndexChanged.connect(self.datenLadenSpeichern)
        self.buchungstabelle.itemChanged.connect(self.speichernAlsJson)
        self.buchungstabelle.cellChanged.connect(self.updateKontobezeichnung)
        self.buchungstabelle.itemChanged.connect(self.handleItemChanged)
        self.keyEventFilter = KeyEventFilter(self)
        self.buchungstabelle.installEventFilter(self.keyEventFilter)
        # Set the alignment for the columns you want to right-align
        right_aligned_columns = [5, 6, 7, 8, 9]  # Replace with the actual column indices
        for column in right_aligned_columns:
            for row in range(self.buchungstabelle.rowCount()):
                item = self.buchungstabelle.item(row, column)
                if item:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)
        # Einstiegsdaten Section
        einstiegsdaten_layout = QVBoxLayout()
        einstiegsdaten_headline = QLabel("Einstiegsdaten")
        einstiegsdaten_headline.setObjectName("EinstiegsdatenLabel")  # Objekt-Identifer setzen
        einstiegsdaten_layout.addWidget(einstiegsdaten_headline)
        self.setAcceptDrops(True)
        # Settings Icon
        self.settingsButton = QPushButton(QIcon("img/settings.png"), "", self)  # Pfad zum Zahnrad-Icon anpassen
        self.settingsButton.clicked.connect(self.openSettingsDialog)
        self.settingsButton.setToolTip("Einstellungen")
        self.settingsButton.setStyleSheet("""
            QPushButton { background-color: #808080; } /* Grey */
            QPushButton:hover { background-color: #A9A9A9; } /* Light Grey on hover */
        """)
        self.settingsButton.resize(self.settingsButton.sizeHint())
        # Positionieren des Buttons im Hauptfenster
        self.settingsButton.move(1600, 10)  # Position anpassen
        # Beenden Icon
        self.quitButton = QPushButton(QIcon("img/beenden.png"), "", self)  # Pfad zum Beenden-Icon anpassen
        self.quitButton.clicked.connect(self.closeApplication)
        self.quitButton.setToolTip("Beenden")
        self.quitButton.setStyleSheet("""
            QPushButton { background-color: #FF0000; } /* Red */
            QPushButton:hover { background-color: #FFCCCC; } /* Light Red on hover*/
        """)
        self.quitButton.resize(self.quitButton.sizeHint())
        # Positionieren des Beenden Buttons im Hauptfenster, direkt neben dem Settings Button
        quitButtonXPosition = self.settingsButton.x() + self.settingsButton.width() + 10  # 10 Pixel Abstand zwischen den Buttons
        self.quitButton.move(quitButtonXPosition, 10)
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
        self.buchungsart_dropdown.currentIndexChanged.connect(self.datenLadenSpeichern)
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
        vorerfassung_headline.setObjectName("VorerfassungLabel")  # Objekt-Identifer setzen
        self.buchungstabelle = QTableWidget()
        self.buchungstabelle.setColumnCount(12)
        self.buchungstabelle.setHorizontalHeaderLabels(["Tag", "Belegnummer", "Buchungstext", "Kontonummer", "Konto","Eingang", "Ausgang", "StC", "Prozent", "Umsatzsteuer", "Dokument", ""])
        self.buchungstabelle.horizontalHeader().setStretchLastSection(True)
        self.buchungstabelle.setColumnWidth(0, 60)
        self.buchungstabelle.setColumnWidth(1, 120)
        self.buchungstabelle.setColumnWidth(2, 300)
        self.buchungstabelle.setColumnWidth(3, 140)
        self.buchungstabelle.setColumnWidth(4, 210)
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
        self.buchungstabelle.setColumnWidth(10, 250)
        self.buchungstabelle.setColumnWidth(11, 40)
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
        # Button-Layout für "Export" Button
        button_layout = QVBoxLayout()
        layout.addLayout(button_layout)
        self.exportButton = QPushButton("Export")
        #self.exportButton.clicked.connect(self.exportData)  # Hier sollten Sie die entsprechende Exportfunktion anstelle von self.closeApplication einfügen
        self.exportButton.setObjectName("exportButton")
        button_layout.addWidget(self.exportButton)
        #Stylesheet Import
        #stylesheet = self.loadStylesheet("style.css")
        #self.setStyleSheet(stylesheet)

    def loadStylesheet(self, filename):
        try:
            with open(filename, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Fehler beim Laden des Stylesheets: {e}")
            return ""

    def loadUserPreferences(self):
        try:
            with open('user_settings.json', 'r') as config_file:
                config = json.load(config_file)

                # Lade das Stylesheet, falls vorhanden
                stylesheetName = config.get("stylesheet")
                if stylesheetName:
                    self.applyStylesheetByName(stylesheetName)

                # Lade die Fensterposition, falls vorhanden
                windowPosition = config.get("windowPosition")
                if windowPosition:
                    self.move(windowPosition['x'], windowPosition['y'])

        except FileNotFoundError:
            print("Keine Benutzereinstellungen gefunden. Standard-Stylesheet und -position werden verwendet.")
        except json.JSONDecodeError:
            print("Fehler beim Lesen der Benutzereinstellungen. Standard-Stylesheet und -position werden verwendet.")


    def applyStylesheetByName(self, stylesheetName):
        stylesheetNameToPathMapping = {
            "Hell": "styles/light.css",
            "Dunkel": "styles/dark.css",
            "Klassisch": "styles/classic.css"
        }
        stylesheetPath = stylesheetNameToPathMapping.get(stylesheetName)
        if stylesheetPath:
            absoluteStylesheetPath = os.path.join(os.path.dirname(__file__), stylesheetPath)
            try:
                with open(absoluteStylesheetPath, "r") as f:
                    newStylesheet = f.read()
                    self.setStyleSheet(newStylesheet)
            except Exception as e:
                print(f"Fehler beim Laden des Stylesheets: {e}")

    def loadKontoplan(self):
        try:
            with open('kontoplan.json', 'r', encoding='utf-8') as file:
                self.kontoplan_data = json.load(file)
            self.updateKontobezeichnungForAllRows()  # Diese Methode muss implementiert werden
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden des Kontoplans", f"Ein Fehler ist aufgetreten: {e}")
            self.kontoplan_data = {"Kontoplan": []}  # Set an empty Kontoplan as a fallback

    def updateKontobezeichnungForAllRows(self):
        for row in range(self.buchungstabelle.rowCount()):
            kontonummer_item = self.buchungstabelle.item(row, 3)  # Kontonummer
            if kontonummer_item:
                self.updateKontobezeichnung(row, 3)  # Aktualisiere jede Zeile basierend auf der Kontonummer

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

    def adjustTextAlignment(self):
        rowCount = self.buchungstabelle.rowCount()
        for row in range(rowCount):
            for column in range(5, 10):  # Angenommen, dies sind die Spalten von "Eingang" bis "Umsatzsteuer"
                item = self.buchungstabelle.item(row, column)
                if item is not None:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)


    def handleItemChanged(self, item):
        # This method will be called whenever an item in the table is changed
        # Check if the item is in one of the relevant columns (Eingang, Ausgang, Prozent)
        if item.column() in [5, 6, 8]:
            self.updateUmsatzsteuer(item)

    def handleCellChange(self, row, column):
        # Verhindere, dass die Funktion ausgeführt wird, wenn die Tabelle gerade befüllt wird
        if self.isAddingRow or self.buchungstabelle.currentRow() == -1:
            return

        # Prüfe, ob die Änderung in der Spalte "Eingang" oder "Ausgang" erfolgt ist
        if column in [5, 6]:  # Angenommen, Eingang ist Spalte 5 und Ausgang ist Spalte 6
            item = self.buchungstabelle.item(row, column)
            if item is not None:
                try:
                    # Konvertiere den Textwert der Zelle in eine Fließkommazahl
                    value = float(item.text().replace('.', '').replace(',', '.'))
                    
                    # Formatiere die Zahl im europäischen Format
                    formatted_value = "{:,.2f}".format(value).replace(',', ' ').replace('.', ',').replace(' ', '.')
                    
                    # Aktualisiere die Zelle mit dem formatierten Wert
                    item.setText(formatted_value)   
                except ValueError:
                    # Optional: Fehlerbehandlung oder Zurücksetzen des Feldes
                    pass

        # Rechtsausrichtung für "StC", "Prozent", und "Umsatzsteuer" ohne Formatierung
        if column in [7, 8, 9]:  # Angenommen, diese Spalten sind StC, Prozent, und Umsatzsteuer
            item = self.buchungstabelle.item(row, column)
            if item is not None:
                # Richte den Text in der Zelle rechtsbündig aus
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

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

        # Hier könnten weitere Aktionen eingefügt werden, z.B. die automatische Berechnung der Umsatzsteuer
        # basierend auf den aktualisierten Werten in "Eingang" oder "Ausgang".

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
        self.validateRowsAndSetIcons()

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
        self.loadUserPreferences()
        self.show()

    def datenLadenSpeichern(self):
        # Clear the table before loading new data
        self.buchungstabelle.setRowCount(0)

        # Load the data for the selected month/year if the file exists
        self.ladenAusJson()
        monatIndex = self.month_dropdown.currentIndex() + 1
        jahr = self.year_dropdown.currentText()
        dateipfad = f'data/data_{monatIndex:02d}-{jahr}.json'
        self.adjustTextAlignment()
        # If the file doesn't exist, create a new one
        if not os.path.exists(dateipfad):
            self.speichernAlsJson()
        self.validateRowsAndSetIcons()

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
        buchungsart = self.buchungsart_dropdown.currentText()

        dateipfad = f'data/{jahr}_{monatIndex:02d}.json'

        self.buchungstabelle.setRowCount(0)

        if os.path.exists(dateipfad):
            with open(dateipfad, 'r') as file:
                gesamteDaten = json.load(file)
                daten = gesamteDaten.get(buchungsart, [])

            for row_data in daten:
                row = self.buchungstabelle.rowCount()
                self.buchungstabelle.insertRow(row)
                for column, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    self.buchungstabelle.setItem(row, column, item)
        else:
            print("Keine Daten für diesen Monat/Jahr und Buchungsart gefunden.")

           
    def speichernAlsJson(self):
        monatIndex = self.month_dropdown.currentIndex() + 1
        jahr = self.year_dropdown.currentText()
        buchungsart = self.buchungsart_dropdown.currentText()
        datenZuSpeichern = self.getCurrentTableData()

        dateipfad = f'data/{jahr}_{monatIndex:02d}.json'

        # Laden der existierenden Daten aus der Datei, falls vorhanden
        if os.path.exists(dateipfad):
            with open(dateipfad, 'r') as file:
                gesamteDaten = json.load(file)
        else:
            gesamteDaten = {}

        # Aktualisieren der Daten für die gewählte Buchungsart
        gesamteDaten[buchungsart] = datenZuSpeichern

        try:
            with open(dateipfad, 'w') as file:
                json.dump(gesamteDaten, file, indent=4)
        except Exception as e:
            print(f"Ein Fehler ist aufgetreten beim Speichern der Daten: {e}")


    def convertToFloat(self, value):
        try:
            # Entfernen der Tausendertrennzeichen und Ersetzen von Kommas durch Punkte
            clean_value = value.replace('.', '').replace(',', '.')
            return float(clean_value)
        except ValueError:
            return 0.0

    def formatNumberForDisplay(self, number):
        # Zuerst wird die Zahl in einen String mit zwei Dezimalstellen umgewandelt.
        number_str = "{:.2f}".format(number)
        
        # Ersetze den Punkt durch ein Komma für das Dezimaltrennzeichen.
        number_str = number_str.replace('.', ',')
        
        # Füge Tausendertrennzeichen hinzu.
        parts = number_str.split(',')
        before_decimal = parts[0]
        after_decimal = parts[1] if len(parts) > 1 else '00'
        
        # Umkehren, Trennzeichen hinzufügen, und wieder umkehren
        before_decimal_with_dots = ".".join([before_decimal[max(i - 3, 0):i] for i in range(len(before_decimal), 0, -3)][::-1])
        
        # Zusammenfügen der Teile zu einem finalen String
        return before_decimal_with_dots + ',' + after_decimal

    def updateUmsatzsteuer(self, changed_item):
        row = changed_item.row()
        eingang_text = self.buchungstabelle.item(row, 5).text().strip() if self.buchungstabelle.item(row, 5) else '0'
        ausgang_text = self.buchungstabelle.item(row, 6).text().strip() if self.buchungstabelle.item(row, 6) else '0'
        prozent_text = self.buchungstabelle.item(row, 8).text().strip() if self.buchungstabelle.item(row, 8) else '0'

        eingang = self.convertToFloat(eingang_text)
        ausgang = self.convertToFloat(ausgang_text)
        prozent = self.convertToFloat(prozent_text)

        # Berechne die Umsatzsteuer basierend auf Eingang, Ausgang und dem Steuerprozentsatz
        if prozent != 0:
            # Umsatzsteuer = (Eingang + Ausgang) * Prozent / 100
            umsatzsteuer = ((eingang + ausgang) * prozent) / 100
            formatted_umsatzsteuer = self.formatNumberForDisplay(umsatzsteuer)

            # Finde das Umsatzsteuer-Item in der Tabelle und setze den formatierten Wert
            umsatzsteuer_item = self.buchungstabelle.item(row, 9)
            if umsatzsteuer_item is None:
                umsatzsteuer_item = QTableWidgetItem(formatted_umsatzsteuer)
                self.buchungstabelle.setItem(row, 9, umsatzsteuer_item)
            else:
                umsatzsteuer_item.setText(formatted_umsatzsteuer)
        else:
            # Wenn der Prozentwert 0 ist, setze die Umsatzsteuer auf ''
            umsatzsteuer_item = self.buchungstabelle.item(row, 9)
            if umsatzsteuer_item:
                umsatzsteuer_item.setText('')

    def validateRowsAndSetIcons(self):
        print("Validiere Zeilen und setze Icons...")
        rowCount = self.buchungstabelle.rowCount()
        for row in range(rowCount):
            isValid = self.isRowValid(row)
            self.setCheckIcon(row, isValid)

    def setCheckIcon(self, row, isValid):
        # Definieren Sie hier die Pfade zu den Icons
        checkIconPath = "img/check.png"  # Pfad zum "gültig" Icon, angepasst an Ihren Ordnerstruktur
        removeIconPath = "img/remove.png"  # Pfad zum "ungültig" Icon
        
        # Wählen Sie das entsprechende Icon basierend auf der Gültigkeit
        iconPath = checkIconPath if isValid else removeIconPath
        
        print(f"Setze Icon für Zeile {row}: {iconPath}")
        item = self.buchungstabelle.item(row, 11)  # Angenommen, die Check-Spalte ist Spalte 11
        if item is None:
            item = QTableWidgetItem()
            self.buchungstabelle.setItem(row, 11, item)
        
        # Überprüfen Sie, ob der Pfad absolut ist, und passen Sie ihn ggf. an
        if not os.path.isabs(iconPath):
            iconPath = os.path.join(os.path.dirname(__file__), iconPath)
        
        icon = QIcon(iconPath)
        item.setIcon(icon)
        if icon.isNull():
            print(f"Fehler: Icon {iconPath} konnte nicht geladen werden.")
        else:
            print(f"Icon {iconPath} erfolgreich geladen.")


    def isRowValid(self, row):
        print(f"Überprüfe Zeile {row} auf Gültigkeit...")
        requiredColumns = [0, 1, 2, 3]  # Tag, Belegnummer, Buchungstext, Kontonummer
        for col in requiredColumns:
            item = self.buchungstabelle.item(row, col)
            if not item or not item.text().strip():
                print(f"Zeile {row}, Spalte {col} ist ungültig.")
                return False
        
        # Prüfe, ob entweder Eingang oder Ausgang befüllt ist
        eingangItem = self.buchungstabelle.item(row, 5)
        ausgangItem = self.buchungstabelle.item(row, 6)
        if (eingangItem and eingangItem.text().strip()) or (ausgangItem and ausgangItem.text().strip()):
            print(f"Zeile {row} ist gültig.")
            return True
        else:
            print(f"Zeile {row} hat weder gültigen Eingang noch Ausgang.")
            return False

    def onSelectionChanged(self, selected, deselected):
            # Hier können Sie die Logik implementieren, die ausgelöst wird, wenn die Auswahl geändert wird.
            # Zum Beispiel die Validierung der Daten in der verlassenen Zeile und das Setzen der Icons.
            
            # Sie können deselected.indexes() verwenden, um die Indizes der Zellen zu erhalten, die nicht mehr ausgewählt sind.
            # Beachten Sie, dass deselected eine QItemSelection ist, die eine oder mehrere Bereiche (QItemSelectionRange) enthalten kann.
            # Jeder Bereich enthält die Indizes der Zellen, die zuvor ausgewählt waren, aber jetzt nicht mehr ausgewählt sind.
            
            if deselected.indexes():
                # Extrahieren der Zeilennummern der zuvor ausgewählten Zellen
                rows = set(index.row() for index in deselected.indexes())
                for row in rows:
                    # Führen Sie hier Ihre Validierungs- und Icon-Setzungslogik für jede verlassene Zeile aus.
                    self.validateRowsAndSetIcons()

    def openKontoplanDialog(self, row, column):
        # Holen Sie den ausgewählten Kontenplan aus der Dropdown-Liste
        selectedKontoplanName = self.kontoplan_dropdown.currentText()
        dialog = KontoplanDialog(selectedKontoplanName, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selectedKontonummer:
            # Aktualisieren Sie die Kontonummer in der Tabelle, basierend auf der Auswahl
            item = self.buchungstabelle.item(row, column)
            if item:
                item.setText(dialog.selectedKontonummer)

    def openSettingsDialog(self):
            dialog = SettingsWindow(self)
            dialog.exec_()

    def closeEvent(self, event):
        self.saveWindowPosition()
        self.speichernAlsJson()
        event.accept()  # Schließt das Fenster

    def saveWindowPosition(self):
        config = {}
        try:
            # Versuche, bestehende Einstellungen zu laden, falls vorhanden
            with open('user_settings.json', 'r') as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            print("Konfigurationsdatei nicht gefunden. Eine neue wird erstellt.")
        except json.JSONDecodeError:
            print("Fehler beim Lesen der Konfigurationsdatei. Die Datei wird überschrieben.")

        # Aktualisiere die Konfiguration mit der aktuellen Fensterposition
        config['windowPosition'] = {'x': self.x(), 'y': self.y()}
        with open('user_settings.json', 'w') as config_file:
            json.dump(config, config_file, indent=4)

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Darstellung")
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor("#202128"))
        self.setPalette(p)
        layout = QVBoxLayout()

        # Label, um zu erklären, wofür das Dropdown-Menü verwendet wird
        label = QLabel("Wählen Sie ein Design aus:")
        layout.addWidget(label)

        self.stylesheetComboBox = QComboBox()
        # Angenommen, Sie haben eine Liste von Stylesheet-Namen
        stylesheetNames = ["Hell", "Dunkel", "Klassisch"]
        self.stylesheetComboBox.addItems(stylesheetNames)

        applyButton = QPushButton("Anwenden")
        applyButton.clicked.connect(self.applyStylesheet)

        layout.addWidget(self.stylesheetComboBox)
        layout.addWidget(applyButton)
        self.setLayout(layout)

    def applyStylesheet(self):
            selectedStylesheetName = self.stylesheetComboBox.currentText()
            stylesheetNameToPathMapping = {
                "Hell": "styles/light.css",
                "Dunkel": "styles/dark.css",
                "Klassisch": "styles/classic.css"
            }
            stylesheetPath = stylesheetNameToPathMapping.get(selectedStylesheetName)
            if stylesheetPath:
                absoluteStylesheetPath = os.path.join(os.path.dirname(__file__), stylesheetPath)
                try:
                    with open(absoluteStylesheetPath, "r") as f:
                        newStylesheet = f.read()
                        self.parent().setStyleSheet(newStylesheet)
                        # Speichern der Auswahl
                        self.saveUserPreference(selectedStylesheetName)
                except Exception as e:
                    print(f"Fehler beim Laden des Stylesheets: {e}")
            else:
                print(f"Stylesheet {selectedStylesheetName} nicht gefunden.")

    def saveUserPreference(self, stylesheetName):
        config = {"stylesheet": stylesheetName}
        with open('user_settings.json', 'w') as config_file:
            json.dump(config, config_file, indent=4)

class KontoplanDialog(QDialog):
    def __init__(self, kontoplanName="Standard", parent=None):
        super().__init__(parent)
        self.kontoplanName = kontoplanName
        self.setWindowTitle("Kontoplan")
        self.resize(900, 700)  # Fenstergröße anpassen
        self.setStyleSheet(open("styles/styles_kontoplan.css").read())
        self.layout = QVBoxLayout(self)
        # QLabel für den geladenen Kontoplan-Namen
        self.loadedKontoplanLabel = QLabel(f"Geladener Kontoplan: {kontoplanName}")
        self.layout.addWidget(self.loadedKontoplanLabel)
        # Tabelle für Kontoplan
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Kontonummer", "Bezeichnung", "Steuercode", "Prozent"])
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 400)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # Ganze Zeilen auswählen
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Bearbeitung deaktivieren
        self.table.doubleClicked.connect(self.acceptOnDoubleClick)  # Doppelklick-Ereignis
        self.layout.addWidget(self.table)

        # Button für Neues Konto hinzufügen
        self.newKontoButton = QPushButton("Neues Konto hinzufügen")
        self.newKontoButton.clicked.connect(self.addNewKonto)
        self.layout.addWidget(self.newKontoButton)

        # Button-Leiste hinzufügen
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Abbrechen")
        self.cancelButton.clicked.connect(self.reject)
        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)
        self.layout.addLayout(self.buttonLayout)

        self.selectedKontonummer = None
        self.loadKontoplan(kontoplanName)

    def loadKontoplan(self, kontoplanName):
        self.table.setRowCount(0)  # Löscht alle vorhandenen Zeilen in der Tabelle
        try:
            with open('kontoplan.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                kontenGefunden = False  # Flag, um zu überprüfen, ob Konten gefunden wurden
                letzteUeberschrift = None  # Letzte eingefügte Überschrift speichern
                for kontoplan in data["Kontoplan"]:
                    if kontoplan["KontenplanName"] == kontoplanName:
                        kontenGefunden = True
                        for konto in kontoplan["Konten"]:
                            kontonummer = konto["Kontonummer"]
                            # Bestimme die Überschrift basierend auf der Kontonummer
                            ueberschrift = self.bestimmeUeberschrift(kontonummer)
                            if ueberschrift != letzteUeberschrift:
                                # Füge die Überschrift als neue Zeile ein
                                self.insertHeaderRow(ueberschrift, self.table.rowCount())
                                letzteUeberschrift = ueberschrift
                            # Füge die Kontenzeile ein
                            row_position = self.table.rowCount()
                            self.table.insertRow(row_position)
                            self.table.setItem(row_position, 0, QTableWidgetItem(konto["Kontonummer"]))
                            self.table.setItem(row_position, 1, QTableWidgetItem(konto["Bezeichnung"]))
                            self.table.setItem(row_position, 2, QTableWidgetItem(konto.get("StC", "")))
                            prozent = konto.get("Prozent")
                            prozent_str = "" if prozent == 0.0 else str(prozent)
                            self.table.setItem(row_position, 3, QTableWidgetItem(prozent_str))

                        break
                if not kontenGefunden:
                    print(f"Keine Konten für den Kontenplan '{kontoplanName}' gefunden.")
        except FileNotFoundError:
            print("Kontoplan-Datei nicht gefunden.")
        except json.JSONDecodeError:
            print("Fehler beim Lesen der Kontoplan-Datei.")

    def bestimmeUeberschrift(self, kontonummer):
        laenge = len(kontonummer)
        if laenge == 5:  # Für 5-stellige Kontonummern
            ersteZiffer = kontonummer[0]
            if ersteZiffer == '1':
                return "Inventurkonten"
            elif ersteZiffer == '2':
                return "Forderungen und Geldmittel"
            elif ersteZiffer == '3':
                return "Verbindlichkeiten"
            elif ersteZiffer == '4':
                return "Erlöskonten"
            elif ersteZiffer == '5':
                return "Materialaufwand"
            elif ersteZiffer == '6':
                return "Personalaufwand"
            elif ersteZiffer == '7':
                return "Sonstiger Aufwand"
            elif ersteZiffer == '8':
                return "Finanzergebnis"
            elif ersteZiffer == '9':
                return "Kapitalkonten"
        elif laenge == 4:  # Für 4-stellige Kontonummern
            return "Anlagevermögen"
        # Standardüberschrift für alle anderen Fälle
        return "Andere Konten"

    def insertHeaderRow(self, ueberschrift, position):
            # Füge eine neue Zeile für die Überschrift ein
            self.table.insertRow(position)
            # Erstelle ein QTableWidgetItem für die Überschrift
            headerItem = QTableWidgetItem(ueberschrift)
            # Setze die Eigenschaften des Überschriften-Items
            headerItem.setBackground(QColor("#5a56ff"))  # Hintergrundfarbe der Überschrift
            headerItem.setForeground(Qt.white)  # Textfarbe
            headerItem.setTextAlignment(Qt.AlignCenter)  # Zentrierte Ausrichtung des Textes
            headerItem.setFlags(Qt.ItemIsEnabled)  # Überschrift nicht anklickbar machen
            headerItem.setFlags(headerItem.flags() & ~Qt.ItemIsSelectable)  # Disable selection
            # Füge das Überschriften-Item in die Tabelle ein
            self.table.setItem(position, 0, headerItem)
            # Spanne das Überschriften-Item über alle Spalten der Tabelle
            self.table.setSpan(position, 0, 1, self.table.columnCount())

    def acceptOnDoubleClick(self, item):
        # Check if the double-clicked item is a header item
        if item.row() < 0:
            return
        # If it's not a header item, proceed with the default double-click action
        self.accept()

    def addNewKonto(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Neues Konto hinzufügen")

        layout = QVBoxLayout(dialog)

        kontonummerLineEdit = QLineEdit()
        kontonummerLineEdit.setPlaceholderText("Kontonummer")
        layout.addWidget(kontonummerLineEdit)

        bezeichnungLineEdit = QLineEdit()
        bezeichnungLineEdit.setPlaceholderText("Bezeichnung")
        layout.addWidget(bezeichnungLineEdit)

        steuercodeLineEdit = QLineEdit()
        steuercodeLineEdit.setPlaceholderText("Steuercode")
        layout.addWidget(steuercodeLineEdit)

        prozentLineEdit = QLineEdit()
        prozentLineEdit.setPlaceholderText("Prozent")
        layout.addWidget(prozentLineEdit)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        layout.addWidget(buttonBox)

        if dialog.exec_() == QDialog.Accepted:
            kontonummer = kontonummerLineEdit.text()
            bezeichnung = bezeichnungLineEdit.text()
            steuercode = steuercodeLineEdit.text()
            prozent = prozentLineEdit.text()

            # Add the new Konto to the table
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(kontonummer))
            self.table.setItem(row_position, 1, QTableWidgetItem(bezeichnung))
            self.table.setItem(row_position, 2, QTableWidgetItem(steuercode))
            self.table.setItem(row_position, 3, QTableWidgetItem(prozent))
            # Save the new Konto to the JSON file
            try:
                with open('kontoplan.json', 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except FileNotFoundError:
                data = {"Kontoplan": []}

            kontoplanName = "Standard"  # Modify this if needed
            for kontoplan in data["Kontoplan"]:
                if kontoplan["KontenplanName"] == kontoplanName:
                    kontoplan["Konten"].append({
                        "Kontonummer": kontonummer,
                        "Bezeichnung": bezeichnung,
                        "StC": steuercode,
                        "Prozent": float(prozent) if prozent else 0.0
                    })
                    break
            else:
                data["Kontoplan"].append({
                    "KontenplanName": kontoplanName,
                    "Konten": [{
                        "Kontonummer": kontonummer,
                        "Bezeichnung": bezeichnung,
                        "StC": steuercode,
                        "Prozent": float(prozent) if prozent else 0.0
                    }]
                })

            with open('kontoplan.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            sortiere_und_speichere_json('kontoplan.json')
            self.loadKontoplan(self.kontoplanName)
            self.parent().loadKontoplan()  # Neu laden des Kontoplans im Hauptfenster
            


    def accept(self):
        selectedItems = self.table.selectedItems()
        if selectedItems:
            self.selectedKontonummer = selectedItems[0].text()  # Nehmen Sie an, dass die erste Spalte die Kontonummer enthält
        super().accept()


class KeyEventFilter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_F4:
            # Finden Sie heraus, ob die aktuelle Zelle die Kontonummer-Zelle ist
            if isinstance(watched, QTableWidget):
                currentRow = watched.currentRow()
                currentColumn = watched.currentColumn()
                if currentColumn == 3:  # Angenommen, Spalte 3 ist die Kontonummerspalte
                    # Korrigieren Sie dies, um sowohl die Zeile als auch die Spalte zu übergeben
                    self.parent().openKontoplanDialog(currentRow, currentColumn)  # Fügen Sie hier die Spaltennummer hinzu
            return True
        return super().eventFilter(watched, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))
    # Verzeichnis in dem sich Schriftarten befinden
    font_directory = "./fonts"
    for file in os.listdir(font_directory):
        if file.endswith(".ttf"):
            font_path = os.path.join(font_directory, file)
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                print("Geladene Schriftartenfamilien:", font_families)
            else:
                print(f"Fehler beim Laden der Schriftart: {font_path}")
    fenster = Hauptfenster()
    fenster.start()
    sys.exit(app.exec_())
