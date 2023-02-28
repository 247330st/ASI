"""
Projekt Algorytmy Sztucznej inteligencji
Temat: wykorzystanie metody symulowanego wyżarzania do układania grafiku dla pracowników
Projekt polega na znalezieniu odpowiedniego algorytmu znajdywania lepszych rozwiązań a następnie wzbogazcenie go
o metodę symulowanego wyżarzania. Program nie posiada zabezpieczeń i działa tylko i wyłącznie z odpowiednimi
zestawani danych.
worker_list.txt - baza danych pracowników
data.txt, test.txt - przykładowe dane
penalty.txt - plik tekstowy służący do zapisu aktualnej wartości funkcji celu aby umożliwić śledzenie przebiegu
działania algorytmu
result.txt - plik tekstowy służący do zapisu wyników działania algorytmu wykonanego x razy
"""

import random
import math
import sys
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QTableWidget, QTableWidgetItem, QPushButton,
                               QVBoxLayout, QLabel, QMainWindow, QWidget, QInputDialog, QComboBox)
from PySide6.QtCore import Qt


# Parametry globalne w celu łatwiejszego znajdywania optymalnej wartości
NB_MIN = 100
NB_REPEAT = pow(10, 3)
ANNEALING_FACTOR = 0.95
TEMPERATURE = 10


class Information:
    def __init__(self, data, disposal_list, names_list):
        self.nb_shifts_day = data[0]
        self.nb_workers_shift = data[1]
        self.nb_workers = data[2]
        self.nb_days = data[3]
        self.disposal_list = disposal_list
        self.nb_shifts_to_set = data[0] * data[1] * data[3]
        self.end_diagram = []
        self.min_penalty = 0
        self.names_list = names_list

    def refresh_data(self, end_diagram, min_penalty):
        self.end_diagram = end_diagram
        self.min_penalty = min_penalty


# Interfejs w celu lepszego przedstawienia wyników
class InputWindow(QWidget):
    def __init__(self, diagram):
        super().__init__()
        days = ["Poniedziałek",
                "Wtorek",
                "środa",
                "Czwartek",
                "Piśtek",
                "Sobota",
                "Niedziela"]
        self.worker_availability = []
        self.accepted = False
        self.worker_id = 0
        self.table = QTableWidget()
        self.table.setRowCount(2)
        self.column_amount = len(days)
        self.table.setColumnCount(len(days))
        self.table.setHorizontalHeaderLabels(days)
        self.accept_button = QPushButton("Zatwierdz")
        self.accept_button.clicked.connect(lambda: self.read_data(diagram))
        self.accept_button.clicked.connect(lambda: self.close())

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.accept_button)
        self.setLayout(layout)
        self.fill_table()
        self.disposal_list = diagram.disposal_list

    def fill_table(self):
        prefrences = [
            "Dostępny",
            "Nie bałdzo",
            "Niedostępny"
        ]
        k = 0
        for i in range(self.column_amount):
            for j in range(2):
                combo = QComboBox()
                for k in prefrences:
                    combo.addItem(k)
                self.table.setCellWidget(j, i, combo)

    def read_data(self, diagram):
        k = 0
        for i in range(self.column_amount):
            for j in range(2):
                widget = self.table.cellWidget(j, i)
                if widget.currentText() == "Dostępny":
                    self.worker_availability += '0'
                elif widget.currentText() == "Nie bałdzo":
                    self.worker_availability += '1'
                else:
                    self.worker_availability += '2'
        str_availability = ''.join(map(str, self.worker_availability))
        for i in range(self.column_amount * 2):
            diagram.disposal_list[int(self.worker_id)] = str_availability
        self.worker_availability.clear()
        print(diagram.disposal_list)


class ResultWindow(QWidget):
    def __init__(self, diagram):
        super().__init__()
        days = ["Poniedziałek",
                "Wtorek",
                "Środa",
                "Czwartek",
                "Piątek",
                "Sobota",
                "Niedziela"]
        shift = ["I", "I", "I", "II", "II", "II"]
        self.table = QTableWidget()
        #self.table.resize(1000, 250)
        self.table.setRowCount(6)
        self.column_amount = diagram.nb_days
        self.table.setColumnCount(self.column_amount)
        self.table.setHorizontalHeaderLabels(days)
        self.table.setVerticalHeaderLabels(shift)
        for i in range(self.column_amount):
            self.table.setColumnWidth(i, 150)
        self.end_list = []
        self.end_list += diagram.end_diagram
        self.disposal_list = []
        self.disposal_list += diagram.disposal_list
        self.fill_table(diagram)
        self.label = QLabel("Wartosc funkcji celu: {:2d}".format(diagram.min_penalty))
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def fill_table(self, diagram):
        k = 0
        for i in range(self.column_amount):
            for j in range(6):
                item_color = QTableWidgetItem(diagram.names_list[self.end_list[k] - 1])
                item_color.setTextAlignment(Qt.AlignCenter)
                item_color.setBackground(self.get_rgb_from_hex(self.get_color(i, j, self.end_list, self.disposal_list)))
                self.table.setItem(j, i, item_color)
                k += 1

    def get_rgb_from_hex(self, code):
        code_hex = code.replace("#", "")
        rgb = tuple(int(code_hex[i:i + 2], 16) for i in (0, 2, 4))
        return QColor.fromRgb(rgb[0], rgb[1], rgb[2])

    def get_color(self, i, j, end_diagram, disposal_list):
        pos_list = 6 * i + j
        penalty = get_preference(disposal_list, pos_list, end_diagram)
        if penalty == 0:
            return "#00FF00"
        elif penalty == 1:
            return "#F9E56D"
        else:
            return "FF0000"


class MainWindow(QMainWindow):
    def __init__(self, diagram):
        super().__init__()
        self.result_window = None
        self.input_window = None
        layout = QVBoxLayout()
        self.input_id = 0
        self.ok = False
        log_button = QPushButton("Wprowadź dyspozycyjność")
        log_button.clicked.connect(self.get_id)
        log_button.clicked.connect(lambda: self.show_input_window(diagram))
        layout.addWidget(log_button)

        result_button = QPushButton("Wyświetl wyniki")
        result_button.clicked.connect(lambda: self.show_result_window(diagram))
        layout.addWidget(result_button)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)

    def get_id(self):
        text, ok = QInputDialog.getText(self, "Logowanie", "Wprowadź ID")
        self.input_id = text
        self.ok = ok

    def show_input_window(self, diagram):
        self.input_window = InputWindow(diagram)
        if self.ok:
            self.input_window.resize(750, 150)
            self.input_window.setWindowTitle("Wprowadzanie dyspozycyjności")
            self.input_window.show()
            self.input_window.worker_id = self.input_id

    def show_result_window(self, diagram):
        make_better_combination_draw_annealing(diagram, NB_REPEAT)
        # make_better_combination_draw(diagram, NB_REPEAT)
        self.result_window = ResultWindow(diagram)
        self.result_window.setWindowTitle("Grafik")
        self.result_window.resize(1090, 260)
        self.result_window.show()


def run_interface(diagram):
    app = QApplication(sys.argv)
    form = MainWindow(diagram)
    form.setWindowTitle("Menu")
    form.show()
    app.exec()


def load_file():
    """ Wczytywanie z pliku do podanych list"""
    f_data = []
    f_disposal_list = []
    f_names_list = []
    try:
        with open("test.txt", "r") as file:
            lines = list(line for line in (l.strip() for l in file) if line)
            info = []

            for i in range(0, 4):
                f_data.append(int(lines[i]))

            for i in range(0, 4):
                j = i + 4 + int(f_data[2])
                info.append(lines[j])

            diagram_nb_line = 4 + int(f_data[2])
            for nb in range(4, diagram_nb_line):
                new_lines = lines[nb].replace(" ", "")
                f_disposal_list.append(new_lines)

            file.close()
    except IOError:
        print("error 404")

    try:
        with open("worker_list.txt", "r", encoding="utf-8") as file:
            names = list(name for name in (l.strip() for l in file) if name)
            for i in range(int(f_data[2])):
                f_names_list.append(names[i])
    except IOError:
        print("error 404")
    diagram = Information(f_data, f_disposal_list, f_names_list)
    return diagram


def save_results(penalty, configuration, total_attempts, end_attempt):
    file = open("result.txt", "a")
    print("End penalty: ", penalty, file=file, end=", ")
    print("Total attempts: ", total_attempts, file=file, end=", ")
    print("End attempt:{:4d} ".format(end_attempt), file=file, end=" ")
    print("Configuration: ", configuration, file=file)
    file.close()


def get_preference(f_disposal_list, pos_list, f_end_diagram):
    """ Funkcja zwraca informacje o dostepnosci pracownika na podstawie pozycji w grafiku"""

    day_result = int(pos_list/6)
    shift_result = int((pos_list % 6) / 3)
    id_worker = int(f_end_diagram[pos_list]) - 1    # Pozyskanie id pracownika znajdujacego sie na danej pozycji
    pos = int(day_result * 2 + shift_result)
    result = int(f_disposal_list[id_worker][pos])

    return result


def get_penalty_amount(f_disposal_list, f_end_diagram):
    """ Funkcja zliczajaca kary z ustalonego grafiku"""

    penalty = 0
    for i in range(0, len(f_end_diagram)):
        # Wyciąganie po kolei kary z danej pozycji w grafiku i sumowanie ich
        preference = get_preference(f_disposal_list, i, f_end_diagram)
        penalty += preference

    # Funkcja zwraca sume kar
    return penalty


def get_rand_combination(diagram):
    nb_shifts = diagram.nb_shifts_to_set
    rand_diagram = []
    shift_combination = []
    j = 0
    while nb_shifts != 0:
        for i in range(0, nb_shifts, 3):
            while len(shift_combination) < 3:
                possible_worker = random.randint(1, 10)
                if possible_worker not in shift_combination:
                    shift_combination.append(possible_worker)
            rand_diagram += shift_combination
            shift_combination.clear()
        if check_if_correct(rand_diagram, nb_shifts, diagram.nb_workers_shift):
            break
        rand_diagram.clear()
        j += 1
    penalty = get_penalty_amount(diagram.disposal_list, rand_diagram)
    print("Number of attempts: {}, penalty: {}".format(j, penalty))
    diagram.refresh_data(rand_diagram, penalty)


def check_if_correct(rand_diagram, nb_shifts, nb_workers_shift):
    correct = True
    i = 0
    # Sprawdzenie czy na jednej zmianie rozni pracownicy
    while i < nb_shifts:
        if rand_diagram[i] == rand_diagram[i + 1]:
            correct = False
        if rand_diagram[i] == rand_diagram[i + 2]:
            correct = False
        if rand_diagram[i + 1] == rand_diagram[i + 2]:
            correct = False
        i += 3
    i = 0
    # Sprawdzenie czy nie ma dwoch zmian pod rzad
    while i < nb_shifts:
        move_next_shift = nb_workers_shift

        for j in range(i, i + nb_workers_shift):
            for k in range(0, nb_workers_shift):
                next_shift = i + move_next_shift + k
                if rand_diagram[i] == rand_diagram[next_shift]:
                    correct = False
                    break
            move_next_shift -= 1
            i += 1
        if not correct:
           break

        i += nb_workers_shift
    # Sprawdzenie czy nie przekracza liczby zmian na tydzien
    for i in range(1, 10):
        if rand_diagram.count(i) > 5:
            correct = False
            break

    return correct


# Dwa algorytmy badane w projeckie wzbogacone o metodę symulowanego wyżarzania
def make_better_combination_draw(diagram, f_nb_repeat):
    nb_while = 0
    nb_while_2 = 0
    last_attempt = 0
    file = open("penalty.txt", "w")
    for i in range(1, f_nb_repeat):
        while diagram.min_penalty != 0:
            nb_while_2 += 1
            rand_diagram = []
            rand_diagram += diagram.end_diagram
            rand_position = random.randint(0, diagram.nb_shifts_to_set - 1)
            rand_worker = random.randint(1, diagram.nb_workers)
            rand_diagram[rand_position] = rand_worker
            if check_if_correct(rand_diagram, diagram.nb_shifts_to_set, diagram.nb_workers_shift):
                temp_penalty = get_penalty_amount(diagram.disposal_list, rand_diagram)
                print(temp_penalty, file=file)
                if temp_penalty < diagram.min_penalty:
                    diagram.refresh_data(rand_diagram, temp_penalty)
                    #print("Penalty: {:2d}, ".format(diagram.min_penalty), "Nb attempts: {:4d},".format(nb_while_2),
                    #      "Total nb attempts: {:4d},".format(nb_while), diagram.end_diagram)
                    nb_while += 1
                    last_attempt = nb_while
                break
            rand_diagram.clear()
            nb_while += 1
    file.close()
    print(nb_while)
    print(diagram.min_penalty)
    save_results(diagram.min_penalty, diagram.end_diagram, nb_while, last_attempt)


def make_better_combination_draw_annealing(diagram, f_nb_repeat):
    nb_while = 0
    nb_while_2 = 0
    last_attempt = 0
    temperature = TEMPERATURE
    file = open("penalty.txt", "w")
    while temperature > 0.05:
        for i in range(1, f_nb_repeat):
            while diagram.min_penalty != 0:
                nb_while_2 += 1
                rand_diagram = []
                rand_diagram += diagram.end_diagram
                rand_position = random.randint(0, diagram.nb_shifts_to_set - 1)
                rand_worker = random.randint(1, diagram.nb_workers)
                rand_diagram[rand_position] = rand_worker
                if check_if_correct(rand_diagram, diagram.nb_shifts_to_set, diagram.nb_workers_shift):
                    temp_penalty = get_penalty_amount(diagram.disposal_list, rand_diagram)
                    if temp_penalty < diagram.min_penalty:
                        diagram.refresh_data(rand_diagram, temp_penalty)
                        nb_while += 1
                        last_attempt = nb_while
                        if nb_while % 5 == 0:
                            print(temp_penalty, file=file)
                    else:
                        delta = temp_penalty - diagram.min_penalty
                        probability = math.exp((-delta) / temperature)
                        rand_probability = random.randint(0, 1000) / 1000
                        if probability > rand_probability:
                            diagram.refresh_data(rand_diagram, temp_penalty)
                            if nb_while % 5 == 0:
                                print(temp_penalty, file=file)
                    break
                rand_diagram.clear()
                nb_while += 1
        temperature *= ANNEALING_FACTOR
    file.close()
    print(nb_while)
    print(diagram.min_penalty)
    print(diagram.end_diagram, get_penalty_amount(diagram.disposal_list, diagram.end_diagram))
    save_results(diagram.min_penalty, diagram.end_diagram, nb_while, last_attempt)


def make_better_combination_swap(diagram):
    acceptable_combinations = []  # wszystkie zaakceptowane
    rand_diagram = []  # ta ktora bedzie mieszana
    start_combination = []  # poczatkowa wylosowana randowmowo
    start_combination += diagram.end_diagram
    rand_diagram += diagram.end_diagram
    for k in range(NB_REPEAT):
        for i in range(len(rand_diagram) - 1):
            for j in range(i + 1, len(rand_diagram)):
                rand_diagram[i], rand_diagram[j] = rand_diagram[j], rand_diagram[i]
                if check_if_correct(rand_diagram, diagram.nb_shifts_to_set, diagram.nb_workers_shift):
                    x = []
                    x += rand_diagram
                    acceptable_combinations.append(x)
                    penalty = get_penalty_amount(diagram.disposal_list, rand_diagram)
                    if penalty < diagram.min_penalty:
                        diagram.refresh_data(rand_diagram, penalty)
                rand_diagram.clear()
                rand_diagram += start_combination
        pos = random.randint(0, len(acceptable_combinations) - 1)
        start_combination.clear()
        rand_diagram.clear()
        start_combination += acceptable_combinations[pos]
        rand_diagram += start_combination
        acceptable_combinations.clear()
        print(k)
    print(diagram.end_diagram, diagram.min_penalty)


def make_better_combination_swap_annealing(diagram):
    rand_diagram = []
    start_combination = []
    temperature = TEMPERATURE
    file = open("penalty.txt", "w")
    i = 0
    while temperature > 0.01:
        for j in range(20000):
            correct = False
            start_combination += diagram.end_diagram

            while not correct:
                i += 1
                rand_diagram.clear()
                rand_diagram += start_combination
                first = random.randint(0, len(rand_diagram) - 1)
                second = random.randint(0, len(rand_diagram) - 1)
                rand_diagram[first], rand_diagram[second] = rand_diagram[second], rand_diagram[first]
                if check_if_correct(rand_diagram, diagram.nb_shifts_to_set, diagram.nb_workers_shift):
                    penalty = get_penalty_amount(diagram.disposal_list, rand_diagram)
                    correct = True
                    delta = penalty - diagram.min_penalty
                    if delta < 0:
                        diagram.refresh_data(rand_diagram, penalty)
                    elif delta >= 0:
                        probability = math.exp((-delta)/temperature)
                        rand_probability = random.randint(0, 1000) / 1000
                        #print(probability, rand_probability)
                        if probability > rand_probability:
                            diagram.refresh_data(rand_diagram, penalty)
                            #if i % 100 == 0:
                                # print(penalty, file=file)
            start_combination.clear()
        temperature *= ANNEALING_FACTOR
    print(temperature)
    print(diagram.end_diagram, diagram.min_penalty)

    file.close()


def main():

    diagram = load_file()
    get_rand_combination(diagram)
    # make_better_combination_draw(diagram, NB_REPEAT)
    # make_better_combination_swap(diagram)
    # make_better_combination_swap_annealing(diagram)
    # make_better_combination_draw_annealing(diagram, NB_REPEAT)

    run_interface(diagram)


main()

