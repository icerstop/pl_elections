# gui.py
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QWidget,
                               QListWidget, QTextEdit, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDoubleValidator
from models import Committee
from data_loader import load_constituencies
from calculator import ElectionCalculator
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtSvgWidgets import QSvgWidget
from bs4 import BeautifulSoup

class ElectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kalkulator mandatów")
        self.setGeometry(100, 100, 1600, 900)

        # Utwórz centralny widget i główny układ
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Dodaj widget mapy do głównego układu
        self.map_widget = QSvgWidget("okregi.svg")
        self.map_widget.setFixedSize(800, 800)
        self.main_layout.addWidget(self.map_widget)

        # Definicja komitetów
        self.committees = [
            Committee('td', 'Trzecia Droga', 8, [['td', 1]]),
            Committee('nl', 'Lewica', 5, [['nl', 1]]),
            Committee('pis', 'Prawo i Sprawiedliwość', 5, [['pis', 1]]),
            Committee('konf', 'Konfederacja', 5, [['konf', 1]]),
            Committee('ko', 'Koalicja Obywatelska', 5, [['ko', 1]])
        ]

        self.colors = {
            'td': '#FFFF00',  # Trzecia Droga - Żółty
            'nl': '#FF0000',  # Lewica - Czerwony
            'pis': '#000080',  # Prawo i Sprawiedliwość - Granatowy
            'konf': '#8B4513',  # Konfederacja - Brązowy
            'ko': '#FFA500'   # Koalicja Obywatelska - Pomarańczowy
        }

        # Wczytanie okręgów i kalkulator
        self.constituencies = load_constituencies('wybory2023.csv')
        self.calculator = ElectionCalculator(self.committees, self.constituencies)

        # Suwaki i pola tekstowe dla wsparcia
        self.support_sliders = []
        self.support_entries = []
        for committee in self.committees:
            label = QLabel(f"{committee.name} (%):")
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 1000)  # Zakres 0-1000 (0.0%-100.0%, krok 0.1%)
            slider.setValue(0)
            entry = QLineEdit("0.0")
            entry.setFixedWidth(50)
            entry.setValidator(QDoubleValidator(0.0, 100.0, 1))  # 0.0-100.0, 1 miejsce po przecinku

            # Synchronizacja suwaka i pola tekstowego
            slider.valueChanged.connect(lambda val, ent=entry: ent.setText(f"{val / 10:.1f}"))
            entry.editingFinished.connect(lambda ent=entry, sld=slider: self.update_slider_from_entry(ent, sld))
            slider.valueChanged.connect(self.update_mandates)
            entry.editingFinished.connect(self.update_mandates)

            # Układ poziomy
            hbox = QHBoxLayout()
            hbox.addWidget(label)
            hbox.addWidget(slider)
            hbox.addWidget(entry)
            self.main_layout.addLayout(hbox)
            self.support_sliders.append(slider)
            self.support_entries.append(entry)

        # Wyniki ogólne
        self.result_label = QLabel("Mandaty ogólne pojawią się po przesunięciu suwaków")
        self.main_layout.addWidget(self.result_label)

        # Lista okręgów
        self.constituency_list = QListWidget()
        for constituency in self.constituencies:
            self.constituency_list.addItem(f"Okręg {constituency.number} ({constituency.size} mandatów)")
        self.constituency_list.itemSelectionChanged.connect(self.show_constituency_details)
        self.main_layout.addWidget(self.constituency_list)

        # Szczegóły okręgu
        self.details_text = QTextEdit("Wybierz okręg, aby zobaczyć szczegóły")
        self.details_text.setReadOnly(True)
        self.main_layout.addWidget(self.details_text)

        # Miejsce na wykres
        self.canvas = None

        # Timer do debounce
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)  # 300 ms debounce
        self.debounce_timer.timeout.connect(self.calculate_mandates)

    def update_slider_from_entry(self, entry, slider):
        """Aktualizuje suwak na podstawie wartości w polu tekstowym."""
        try:
            value = float(entry.text())
            if 0 <= value <= 100:
                slider.setValue(int(value * 10))  # Skalowanie do 0-1000
            else:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Wpisz wartość od 0.0 do 100.0!")

    def update_mandates(self):
        """Uruchamia timer debounce po zmianie suwaka lub pola tekstowego."""
        self.debounce_timer.start()

    def calculate_mandates(self):
        """Oblicza mandaty na podstawie wartości z pól tekstowych."""
        try:
            support = [float(entry.text()) for entry in self.support_entries]
            total_support = sum(support)
            if total_support > 100:
                QMessageBox.critical(self, "Błąd", f"Suma wsparcia ({total_support:.1f}%) nie może przekraczać 100%.")
                return

            mandates = self.calculator.calculate_mandates(support)

            # Wyświetlanie wyników ogólnych
            result_text = "Mandaty ogólne:\n"
            for i, committee in enumerate(self.committees):
                result_text += f"{committee.name}: {mandates[i]}\n"
            self.result_label.setText(result_text)

            # Domyślne wybranie pierwszego okręgu
            if self.constituency_list.currentRow() == -1:
                self.constituency_list.setCurrentRow(0)
            self.show_constituency_details()

            # Aktualizacja wykresu i mapy
            self.show_donut_chart(mandates)
            self.color_map()

        except ValueError:
            QMessageBox.critical(self, "Błąd", "Wpisz poprawne wartości numeryczne!")

    def show_donut_chart(self, mandates):
        """Rysuje wykres donut z mandatami."""
        if self.canvas:
            self.main_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()

        fig, ax = plt.subplots(figsize=(6, 4))
        labels = [committee.name for committee in self.committees]
        colors = ['#FFFF00', '#FF0000', '#000080', '#8B4513', '#FFA500']
        explode = [0.1 if m > 0 else 0 for m in mandates]

        def absolute_value(val, sizes):
            total = sum(sizes)
            idx = int(val / 100 * total + 0.5)
            return sizes[idx] if idx < len(sizes) else ""

        wedges, texts, autotexts = ax.pie(
            mandates, explode=explode, labels=labels, colors=colors,
            autopct=lambda val: absolute_value(val, mandates), startangle=90,
            wedgeprops=dict(width=0.3, edgecolor='w')
        )
        ax.axis('equal')
        for text in autotexts:
            text.set_color('white')
            text.set_fontsize(10)
            text.set_fontweight('bold')

        self.canvas = FigureCanvas(fig)
        self.main_layout.addWidget(self.canvas)
        plt.close(fig)

    def show_constituency_details(self):
        """Wyświetla szczegóły wybranego okręgu."""
        selected_items = self.constituency_list.selectedItems()
        if not selected_items:
            return

        index = self.constituency_list.row(selected_items[0])
        constituency = self.constituencies[index]
        if not constituency.mandates:
            self.details_text.setText("Przesuń suwaki, aby obliczyć mandaty!")
            return

        details = f"Okręg {constituency.number} ({constituency.size} mandatów):\n"
        for i, committee in enumerate(self.committees):
            details += f"{committee.name}: {constituency.mandates[i]} mandatów\n"
        self.details_text.setText(details)

    def get_winners(self):
        winners = {}
        for constituency in self.constituencies:
            if constituency.mandates:
                # Znajdź komitet z największą liczbą mandatów
                winner_index = constituency.mandates.index(max(constituency.mandates))
                winner_id = self.committees[winner_index].id
                winners[constituency.number] = winner_id
        return winners

    def color_map(self):
        """Koloruje okręgi na mapie na podstawie zwycięzców."""
        # Upewnij się, że używasz właściwego pliku SVG (tutaj 'okregi.svg')
        with open("okregi.svg", 'r', encoding='utf-8') as file:
            svg_content = file.read()

        soup = BeautifulSoup(svg_content, 'xml')
        winners = self.get_winners()

        # Przejdź przez okręgi i ustaw kolor zwycięzcy
        for okreg, winner in winners.items():
            color = self.colors.get(winner, '#FFFFFF')  # Domyślnie biały
            path = soup.find('path', id=f"okreg_{okreg}")
            if path:
                path['style'] = f'fill:{color};stroke:#000000;stroke-width:1px;'

        # Zapisz zmodyfikowany plik SVG i załaduj go
        with open("colored_map.svg", "w", encoding='utf-8') as file:
            file.write(str(soup))
        self.map_widget.load("colored_map.svg")
