from PySide6.QtWidgets import (
    QMainWindow, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QWidget,
    QListWidget, QTextEdit, QLineEdit, QMessageBox, QPushButton, QFormLayout,
    QComboBox, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtSvgWidgets import QSvgWidget
from sympy.codegen.ast import continue_

from models import Committee
from data_loader import load_constituencies
from calculator import ElectionCalculator

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from bs4 import BeautifulSoup
import sys

from validators import DotCommaDoubleValidator  # Import walidatora z osobnego pliku

class ElectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kalkulator mandatów")
        self.setGeometry(100, 100, 1600, 900)

        # Główne okno i układ w formie siatki
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QGridLayout(self.central_widget)

        # Definicja komitetów
        self.committees = [
            Committee('td', 'Trzecia Droga', 5, [['td', 1]]),
            Committee('nl', 'Lewica', 5, [['nl', 1]]),
            Committee('pis', 'Prawo i Sprawiedliwość', 5, [['pis', 1]]),
            Committee('konf', 'Konfederacja', 5, [['konf', 1]]),
            Committee('ko', 'Koalicja Obywatelska', 5, [['ko', 1]])
        ]
        self.colors = {
            'td': '#FFFF00',
            'nl': '#FF0000',
            'pis': '#000080',
            'konf': '#8B4513',
            'ko': '#FFA500'
        }

        # Wczytanie okręgów i inicjalizacja kalkulatora
        self.constituencies = load_constituencies('wybory2023.csv')
        self.calculator = ElectionCalculator(self.committees, self.constituencies)

        # --- Sekcja suwaków (kolumna 0, wiersz 0) ---
        self.form_layout = QFormLayout()
        self.support_sliders = []
        self.support_entries = []
        self.threshold_combos = []
        self.last_changed_index = None  # Aby wiedzieć, która partia była ostatnio zmieniana

        self.suwaki_container = QWidget()
        self.suwaki_container.setLayout(self.form_layout)
        self.main_layout.addWidget(self.suwaki_container, 0, 0)

        # Tworzymy wiersze w QFormLayout – dla każdej partii osobny wiersz
        for idx, committee in enumerate(self.committees):
            label = QLabel(f"{committee.name} (%):")

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 1000)  # 0.0% - 100.0% (krok 0.1%)
            slider.setValue(200)      # domyślnie 20%
            slider.setFixedHeight(30)

            color = self.colors[committee.id]

            slider.setStyleSheet(
                f"""
                QSlider::groove:horizontal {{
                    height: 6px;
                    background: {color};
                    margin: 0px;
                    border-radius: 3px;
                }}
                QSlider::handle:horizontal {{
                    background: {color};
                    border: 1px solid #5c5c5c;
                    width: 16px;
                    margin: -5px 0;
                    border-radius: 8px;
                }}
                """
            )

            entry = QLineEdit("20.0")
            entry.setFixedWidth(50)
            validator = DotCommaDoubleValidator(0.0, 100.0, 2)
            entry.setValidator(validator)

            threshold_combo = QComboBox()
            threshold_combo.addItems(["5%", "8%"])

            # Podpięcie sygnałów
            slider.valueChanged.connect(lambda val, i=idx: self.handle_slider_change(i, val))
            entry.editingFinished.connect(lambda i=idx: self.handle_entry_finished(i))
            threshold_combo.currentIndexChanged.connect(lambda index, i=idx: self.handle_threshold_change(i, index))

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.addWidget(slider)
            row_layout.addWidget(entry)
            row_layout.addWidget(threshold_combo)

            self.form_layout.addRow(label, row_widget)

            self.support_sliders.append(slider)
            self.support_entries.append(entry)
            self.threshold_combos.append(threshold_combo)

        self.method_combo = QComboBox()  # [ZM]
        self.method_combo.addItems(["dHondt", "SainteLague"])  # [ZM]
        self.method_combo.currentIndexChanged.connect(lambda: self.update_mandates())  # [ZM]
        self.form_layout.addRow(QLabel("Metoda obliczania mandatów:"), self.method_combo)  # [ZM]

        # --- Sekcja Donut Chart (kolumna 1, wiersz 0) ---
        self.donut_chart_container = QWidget()
        self.donut_chart_layout = QVBoxLayout(self.donut_chart_container)
        self.main_layout.addWidget(self.donut_chart_container, 0, 1)

        # --- Sekcja Bar Chart (kolumna 2, wiersz 0) ---
        self.bar_chart_container = QWidget()
        self.bar_chart_layout = QVBoxLayout(self.bar_chart_container)
        self.main_layout.addWidget(self.bar_chart_container, 0, 2)

        # --- Sekcja MAPA (kolumna 0, wiersz 1) ---
        self.map_widget = QSvgWidget("okregi.svg")
        self.map_widget.setFixedSize(400, 400)
        self.main_layout.addWidget(self.map_widget, 1, 0)

        # --- Sekcja Szczegóły okręgów (kolumna 1, wiersz 1) ---
        # W sekcji Szczegóły okręgów (kolumna 1, wiersz 1)
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.constituency_list = QListWidget()
        for constituency in self.constituencies:
            self.constituency_list.addItem(f"Okręg {constituency.number} ({constituency.size} mandatów)")
        self.constituency_list.itemSelectionChanged.connect(self.show_constituency_details)
        self.details_text = QTextEdit("Wybierz okręg, aby zobaczyć szczegółowy wykres mandatów")
        self.details_text.setReadOnly(True)
        self.details_layout.addWidget(self.constituency_list)
        self.details_layout.addWidget(self.details_text)
        self.main_layout.addWidget(self.details_container, 1, 1)

        self.coalitions_container = QWidget()
        self.coalitions_layout = QVBoxLayout(self.coalitions_container)
        self.coalitions_label = QLabel("Potencjalne koalicje:")
        self.coalitions_text = QTextEdit()
        self.coalitions_text.setReadOnly(True)
        self.coalitions_layout.addWidget(self.coalitions_label)
        self.coalitions_layout.addWidget(self.coalitions_text)
        self.main_layout.addWidget(self.coalitions_container, 1, 2)

        # Timer do opóźnionego przeliczania
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.calculate_mandates)

        self.donut_canvas = None
        self.bar_canvas = None
        self.constituency_canvas = None

        QTimer.singleShot(0, self.calculate_mandates)

    def handle_slider_change(self, index, val):
        self.last_changed_index = index
        self.support_entries[index].blockSignals(True)
        self.support_entries[index].setText(f"{val / 10:.2f}")
        self.support_entries[index].blockSignals(False)
        self.debounce_timer.start()

    def handle_entry_finished(self, index):
        self.last_changed_index = index
        entry = self.support_entries[index]
        slider = self.support_sliders[index]
        try:
            text = entry.text().replace(',', '.')
            value = float(text)
            if 0 <= value <= 100:
                slider.blockSignals(True)
                slider.setValue(int(value * 10))
                slider.blockSignals(False)
            else:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Wpisz wartość od 0.0 do 100.0!")
        self.debounce_timer.start()

    def update_mandates(self):
        self.debounce_timer.start()

    def calculate_mandates(self):
        try:
            support = [float(entry.text().replace(',', '.')) for entry in self.support_entries]
            total_support = sum(support)

            # Jeśli suma przekracza 100%, proporcjonalnie obniżamy wartości pozostałych partii
            if total_support > 100 and self.last_changed_index is not None:
                changed_value = support[self.last_changed_index]
                other_sum = total_support - changed_value
                if other_sum > 0:
                    factor = (100 - changed_value) / other_sum
                    for i in range(len(support)):
                        if i != self.last_changed_index:
                            new_value = support[i] * factor
                            support[i] = new_value
                            self.support_sliders[i].blockSignals(True)
                            self.support_entries[i].blockSignals(True)
                            self.support_sliders[i].setValue(int(new_value * 10))
                            self.support_entries[i].setText(f"{new_value:.2f}")
                            self.support_sliders[i].blockSignals(False)
                            self.support_entries[i].blockSignals(False)
                total_support = sum(support)  # Powinno wynosić 100%

            method = self.method_combo.currentText()  # [ZM]
            mandates = self.calculator.calculate_mandates(support, method=method)  # [ZM]

            if self.constituency_list.currentRow() == -1:
                self.constituency_list.setCurrentRow(0)
            self.show_constituency_details()
            self.show_donut_chart(mandates)
            self.show_bar_chart()
            self.color_map()

            self.update_coalitions_widget(mandates)

        except ValueError:
            QMessageBox.critical(self, "Błąd", "Wpisz poprawne wartości numeryczne!")

    def show_donut_chart(self, mandates):
        if self.donut_canvas is not None:
            self.donut_chart_layout.removeWidget(self.donut_canvas)
            self.donut_canvas.deleteLater()
            self.donut_canvas = None

        fig, ax = plt.subplots(figsize=(5, 4), constrained_layout=True)

        short_name_mapping = {
            "Trzecia Droga": "TD",
            "Lewica": "NL",
            "Konfederacja": "KONF",
            "Koalicja Obywatelska": "KO",
            "Prawo i Sprawiedliwość": "PiS"
        }

        all_labels = [committee.name for committee in self.committees]
        all_colors = ['#FFFF00', '#FF0000', '#000080', '#8B4513', '#FFA500']
        all_explode = [0.1 if m > 0 else 0 for m in mandates]

        indices = [i for i, m in enumerate(mandates) if m > 0]
        labels = [
            f"{short_name_mapping.get(self.committees[i].name, self.committees[i].name)} ({mandates[i]})"
            for i in indices
        ]
        colors = [all_colors[i] for i in indices]
        explode = [all_explode[i] for i in indices]
        data = [mandates[i] for i in indices]

        def absolute_value(val, sizes):
            total = sum(sizes)
            idx = int(val / 100 * total + 0.5)
            return sizes[idx] if idx < len(sizes) else ""

        wedges, texts, autotexts = ax.pie(
            data, explode=explode, labels=labels, colors=colors,
            autopct=lambda val: absolute_value(val, data), startangle=90,
            wedgeprops=dict(width=0.3, edgecolor='w')
        )
        ax.axis('equal')
        for text in autotexts:
            text.set_color('white')
            text.set_fontsize(10)
            text.set_fontweight('bold')

        ax.set_title("Podział mandatów")

        self.donut_canvas = FigureCanvas(fig)
        self.donut_chart_layout.addWidget(self.donut_canvas)
        plt.close(fig)

    def show_bar_chart(self):
        if self.bar_canvas is not None:
            self.bar_chart_layout.removeWidget(self.bar_canvas)
            self.bar_canvas.deleteLater()
            self.bar_canvas = None

        short_name_mapping = {
            "Trzecia Droga": "TD",
            "Lewica": "NL",
            "Konfederacja": "KONF",
            "Koalicja Obywatelska": "KO",
            "Prawo i Sprawiedliwość": "PiS"
        }

        fig, ax = plt.subplots(figsize=(6, 5))
        party_names = [
            short_name_mapping.get(committee.name, committee.name)
            for committee in self.committees
        ]
        support = [float(entry.text().replace(',', '.')) for entry in self.support_entries]
        colors = [self.colors[committee.id] for committee in self.committees]
        data = sorted(zip(support, party_names, colors), key=lambda x: x[0], reverse=True)
        sorted_support, sorted_party_names, sorted_colors = zip(*data)
        bars = ax.bar(sorted_party_names, sorted_support, color=sorted_colors)

        max_support = max(sorted_support) if max(sorted_support) > 0 else 100
        ax.set_ylim(0, max_support * 1.1)

        ax.set_ylabel("Poparcie (%)")
        ax.set_title("Poparcie krajowe partii")
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

        self.bar_canvas = FigureCanvas(fig)
        self.bar_chart_layout.addWidget(self.bar_canvas)
        plt.close(fig)

    def show_constituency_chart(self):
        # Pobieramy zaznaczony okręg
        selected_items = self.constituency_list.selectedItems()
        if not selected_items:
            return
        index = self.constituency_list.row(selected_items[0])
        constituency = self.constituencies[index]
        if not constituency.mandates:
            # Jeśli nie obliczono mandatów, czyścimy wykres
            if hasattr(self, 'constituency_canvas'):
                self.constituency_chart_layout.removeWidget(self.constituency_canvas)
                self.constituency_canvas.deleteLater()
                self.constituency_canvas = None
            self.details_text.setText("Przesuń suwaki, aby obliczyć mandaty!")
            return

        short_name_mapping = {
            "Trzecia Droga": "TD",
            "Lewica": "NL",
            "Konfederacja": "KONF",
            "Koalicja Obywatelska": "KO",
            "Prawo i Sprawiedliwość": "PiS"
        }

        # Filtrujemy partie, które zdobyły co najmniej 1 mandat
        data = []
        national_support = []
        for entry in self.support_entries:
            try:
                val = float(entry.text().replace(',', '.'))
            except ValueError:
                val = 0.0
            national_support.append(val)

        # Przygotowujemy dane – dla każdej partii, która zdobyła co najmniej 1 mandat
        for idx, (committee, mandates) in enumerate(zip(self.committees, constituency.mandates)):
            if mandates > 0:
                short_name = short_name_mapping.get(committee.name, committee.name)
                # Zakładamy, że constituency.support jest listą poparcia lokalnego dla każdej partii
                local_support = constituency.support[idx] if hasattr(constituency, 'support') and len(
                    constituency.support) > idx else 0.0
                nat_support = national_support[idx] if len(national_support) > idx else 0.0
                data.append((short_name, mandates, local_support, nat_support, self.colors[committee.id]))

        if not data:
            self.details_text.setText("Żadna partia nie przekroczyła progu wyborczego w tym okręgu!")
            return

        data_sorted = sorted(data, key=lambda x: (x[1], x[2], x[3]), reverse=True)
        party_names, mandates_values, _, _, colors = zip(*data_sorted)

        # Przygotowujemy wykres słupkowy
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(party_names, mandates_values, color=colors)
        ax.set_ylabel("Liczba mandatów")
        ax.set_ylim(0, max(mandates_values) + 1)
        ax.set_title(f"Okręg {constituency.number} - Mandaty")
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.tick_params(axis='x', labelsize=12)
        fig.tight_layout()

        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom')

        # Jeśli wcześniej był wyświetlany wykres, usuwamy go
        if hasattr(self, 'constituency_canvas') and self.constituency_canvas is not None:
            self.details_layout.removeWidget(self.constituency_canvas)
            self.constituency_canvas.deleteLater()
            self.constituency_canvas = None

        # Tworzymy nowy canvas i dodajemy go do layoutu obszaru szczegółów
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        self.constituency_canvas = FigureCanvas(fig)
        # Jeśli używasz widgetu QTextEdit (self.details_text) do wyświetlania tekstu,
        # możesz chcieć utworzyć nowy kontener (np. QWidget z layoutem) na wykres
        # i dodać go poniżej lub zamiast tekstu.
        # Dla uproszczenia zakładamy, że chcesz zastąpić tekst wykresem:
        self.details_text.hide()  # ukrywamy pole tekstowe
        self.details_layout.addWidget(self.constituency_canvas)
        plt.close(fig)

    def show_constituency_details(self):
        self.show_constituency_chart()

    def show_all_constituency_details(self):
        details = ""
        for constituency in self.constituencies:
            if constituency.mandates:
                details += f"Okręg {constituency.number} ({constituency.size} mandatów):\n"
                for i, committee in enumerate(self.committees):
                    details += f"{committee.name}: {constituency.mandates[i]} mandatów\n"
                details += f"Dokładne wyniki wsparcia lokalnego: {constituency.support}\n\n"
            else:
                details += f"Okręg {constituency.number}: Przesuń suwaki, aby obliczyć mandaty!\n\n"
        self.details_text.setText(details)

    def color_map(self):
        with open("okregi.svg", 'r', encoding='utf-8') as file:
            svg_content = file.read()
        soup = BeautifulSoup(svg_content, 'xml')
        winners = self.get_winners()
        for okreg, winner in winners.items():
            color = self.colors.get(winner, '#FFFFFF')
            path = soup.find('path', id=f"okreg_{okreg}")
            if path:
                path['style'] = f'fill:{color};stroke:#000000;stroke-width:1px;'
        with open("colored_map.svg", "w", encoding='utf-8') as file:
            file.write(str(soup))
        self.map_widget.load("colored_map.svg")

    def get_winners(self):
        winners = {}
        for constituency in self.constituencies:
            if constituency.mandates:
                winner_index = constituency.mandates.index(max(constituency.mandates))
                winner_id = self.committees[winner_index].id
                winners[constituency.number] = winner_id
        return winners

    def update_coalitions_widget(self, mandates):
        from itertools import combinations

        # Przygotowujemy mapowanie pełnych nazw na skróty (tak jak w innych miejscach)
        short_name_mapping = {
            "Trzecia Droga": "TD",
            "Lewica": "NL",
            "Konfederacja": "KONF",
            "Koalicja Obywatelska": "KO",
            "Prawo i Sprawiedliwość": "PiS"
        }

        # Pobieramy krajowe poparcie dla każdej partii (zakładamy, że kolejność jest zgodna)
        national_support = []
        for entry in self.support_entries:
            try:
                val = float(entry.text().replace(',', '.'))
            except ValueError:
                val = 0.0
            national_support.append(val)

        coalitions = []
        n = len(self.committees)
        indices = list(range(n))

        # Przeglądamy wszystkie kombinacje (od 1 do n partii)
        for r in range(1, n + 1):
            for subset in combinations(indices, r):
                subset_ids = [self.committees[i].id for i in subset]
                if 'pis' in subset_ids and 'ko' in subset_ids:
                    continue
                if 'nl' in subset_ids and 'konf' in subset_ids:
                    continue
                if 'nl' in subset_ids and 'pis' in subset_ids:
                    continue
                total = sum(mandates[i] for i in subset)
                if total >= 231:
                    # Dla każdej partii w koalicji zbieramy: skrót nazwy, liczbę mandatów,
                    # lokalne poparcie (jeśli dostępne, zakładamy, że constituency.support nie jest tutaj dostępne)
                    # oraz krajowe poparcie.
                    coalition_data = []
                    for i in subset:
                        abbr = short_name_mapping.get(self.committees[i].name, self.committees[i].name)
                        coalition_data.append((abbr, mandates[i], national_support[i]))
                    # Sortujemy partie w koalicji – najpierw według mandatów, potem krajowego poparcia
                    coalition_data.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    if len(subset) == 1:
                        coalition_str = f"Samodzielna większość: {coalition_data[0][0]} ({coalition_data[0][1]})"
                    else:
                        coalition_str = "Koalicja: " + "+".join(f"{abbr}({mand})" for abbr, mand, _ in coalition_data)
                        coalition_str += f" = {total}"
                    coalitions.append((total, coalition_str))
        # Sortujemy wszystkie koalicje malejąco według sumy mandatów
        coalitions.sort(key=lambda x: x[0], reverse=True)

        # Usuwamy duplikaty – jeżeli te same partie pojawiły się w koalicji (choć przy kombinacjach nie powinno być powtórzeń)
        unique_coalitions = []
        seen = set()
        for total, coalition_str in coalitions:
            if coalition_str not in seen:
                seen.add(coalition_str)
                unique_coalitions.append(coalition_str)

        # Łączymy wynik w jeden tekst (każda kombinacja w nowej linii)
        result_text = "\n".join(unique_coalitions)
        if not result_text:
            result_text = "Brak koalicji dających większość"
        self.coalitions_text.setText(result_text)

    def handle_threshold_change(self, i, index):
        # Pobranie wartości z comboboxa (np. "5%" lub "8%")
        new_threshold_str = self.threshold_combos[i].currentText()
        new_threshold = int(new_threshold_str.replace("%", ""))
        # Zakładamy, że obiekt Committee posiada atrybut threshold
        self.committees[i].threshold = new_threshold
        # Aktualizacja przeliczenia mandatów
        self.update_mandates()

