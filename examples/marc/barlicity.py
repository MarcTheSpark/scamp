from scamp import *
import sys
from sklearn import manifold
import numpy as np
from scamp_extensions.barlicity import harmonicity, gaussian_discount, get_indispensability_array
from scamp_extensions.utils import hertz_to_midi

from random import random

from PyQt5 import QtCore, QtWidgets, Qt

scan_period, width_average, width_variation, width_variation_period, width_start_phase = \
    160, 10.0, 5.0, 20, 3*math.pi / 2
scanner_index = 0

piano_distillation_timeline = Envelope.from_levels_and_durations((0, 1, 0), (120, 120))

piano_ratios = ((1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (64, 9), (25, 3), (28, 3), (32, 3), (12, 1), (64, 5),
                (128, 9), (63, 4), (50, 3), (18, 1), (20, 1), (64, 3), (45, 2))
fractions = [Fraction(*ratio) for ratio in piano_ratios]
distances = [[abs(1/harmonicity((top / bottom).numerator, (top / bottom).denominator)) for bottom in fractions]
             for top in fractions]

mds = manifold.MDS(n_components=2, dissimilarity="precomputed", random_state=152)
similarities = np.array(distances)
piano_pos = mds.fit(similarities).embedding_
point_range = min(x[0] for x in piano_pos), max(x[0] for x in piano_pos), \
              min(x[1] for x in piano_pos), max(x[1] for x in piano_pos)
scaled_points = [((x - point_range[0]) / (point_range[1] - point_range[0]) * 1000,
                  (y - point_range[2]) / (point_range[3] - point_range[2]) * 1000)
                 for x, y in piano_pos]
scale_factor = 1000 / (point_range[1] - point_range[0])
scanner_width = width_average * scale_factor


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, points):
        super(MainWindow, self).__init__()
        scene = QtWidgets.QGraphicsScene(self)
        view = QtWidgets.QGraphicsView(scene)
        self.setCentralWidget(view)
        self.resize(Qt.QSize(QtWidgets.QDesktopWidget().availableGeometry(self).size().height() * 0.8,
                             QtWidgets.QDesktopWidget().availableGeometry(self).size().height() * 0.8))
        view.setSceneRect(QtCore.QRectF(0, 0, 1000, 1000))
        view.centerOn(500, 500)

        self.circle = QtWidgets.QGraphicsEllipseItem(QtCore.QRectF(-50, -50, 100, 100))
        self.circle.setPos(0, 0)
        self.circle.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.circle.setOpacity(0.6)
        self.circle.setBrush(Qt.QColor(0, 100, 255))

        self.circle_center = (0, 0)
        self.circle_width = 100
        scene.addItem(self.circle)

        self.repaint_timer = QtCore.QTimer(self)
        self.repaint_timer.timeout.connect(self.do_frame)
        self.repaint_timer.start(10)
        self.repaint()

        self.points = []
        self.contained_points = []

        for i, point in enumerate(points):
            self.points.append(
                scene.addEllipse(Qt.QRectF(point[0] - 5, point[1] - 5, 10, 10), brush=Qt.QColor(0, 0, 0))
            )
            text = scene.addText(str(i))
            text.setPos(point[0] - 25, point[1])

    def do_frame(self):
        self.circle.setPos(*self.circle_center)
        self.circle.setRect(-self.circle_width/2, -self.circle_width/2, self.circle_width, self.circle_width)
        contained_points = []
        for i, point in enumerate(self.points):
            if self.circle.collidesWithItem(point):
                contained_points.append(i)
        self.contained_points = contained_points
        super().repaint()


app = QtWidgets.QApplication(sys.argv)
w = MainWindow(scaled_points)

w.show()

s = Session().run_as_server()
piano = s.new_part("piano")
s.start_transcribing()

speed_response = Envelope.from_levels_and_durations([2, 0.1], [800], [-5])


def set_scanner_position(dt):
    global scanner_index, scanner_width
    scanner_width = (width_average + width_variation *
                     math.sin(2 * math.pi * s.time() / width_variation_period + width_start_phase)) * scale_factor
    w.circle_width = scanner_width

    total_multiplier = 0
    new_location = np.array([0.0, 0.0])
    for i, point in enumerate(scaled_points):
        index_distance = min((i - scanner_index) % len(scaled_points), (scanner_index - i) % len(scaled_points))
        index_discount = gaussian_discount(index_distance, 0, 0.45)
        total_multiplier += index_discount
        new_location[0] += point[0] * index_discount
        new_location[1] += point[1] * index_discount

    new_location /= total_multiplier
    scanner_location = new_location
    w.circle_center = scanner_location
    scanner_index = (scanner_index + dt * len(scaled_points) / scan_period) % len(scaled_points)


def run_scanner():
    while True:
        wait(0.05)
        set_scanner_position(0.05)



rationalized_bark = [50.148940804313106, 100.29788160862621, 150.44682241293933, 200.59576321725243, 250.74470402156552,
                     300.89364482587865, 356.6146901640043, 417.90784003594257, 468.05678084025567, 534.9220352460064,
                     601.7872896517573, 641.9064422952079, 713.2293803280086, 789.8458176679314, 835.8156800718851,
                     902.6809344776359, 1002.9788160862621, 1069.8440704920129, 1128.3511680970448, 1203.574579304]
piano_scale = [hertz_to_midi(x) for x in rationalized_bark]
piano_scale = [x - (piano_scale[0] - int(piano_scale[0])) for x in piano_scale]

last_piano_note_pool = None

piano_indispensabilities = get_indispensability_array(((3, 2), 3, 2), normalize=True)
harpsichord_indispensabilities = get_indispensability_array((2, 3, (3, 2)), normalize=True)
piano_tempo = 280
harpsichord_tempo = 840


def piano_process(clock: Clock):
    global last_piano_note_pool
    while True:
        piano.send_midi_cc(64, 1.0)
        which_beat = int(round(clock.beat() % len(piano_indispensabilities)))
        this_indispensability = piano_indispensabilities[which_beat]
        note_pool = [piano_scale[i] for i in w.contained_points]

        if last_piano_note_pool != note_pool:
            piano.send_midi_cc(64, 0.0)
            piano.send_midi_cc(64, 1.0)

        last_piano_note_pool = note_pool

        syncopation_prob = 1 - ((scanner_width/scale_factor - width_average) / (2 * width_variation) + 0.5)
        piano_distillation_factor = piano_distillation_timeline.value_at(clock.time())

        # spensability is either indispensability or dispensability, depending on whether it's syncopated
        spensability = this_indispensability if random() < syncopation_prob else 1 - this_indispensability

        if len(note_pool) > 0 and spensability >= piano_distillation_factor:
            # distillation allows only the most "spensible" beats to play, and to play with bigger chords
            # at distillation_factor 0, the number of notes should be 1,
            # at distillation_factor 1 and spensibility 1, it should by all the notes
            num_notes = int(1 + round(piano_distillation_factor * spensability * (len(note_pool) - 1)))
            first_note_index = int(0.999 * spensability * (len(note_pool) - num_notes + 1))

            volume = 0.4 + 0.5 * this_indispensability
            # if last_volume is not None:
            #     volume = last_volume * volume_li_factor + volume * (1 - volume_li_factor)
            # last_volume = volume
            piano.play_chord(note_pool[first_note_index: first_note_index + num_notes], volume, 1.0)
            # for pitch_to_play in note_pool[first_note_index: first_note_index + num_notes]:
            #     piano.start_note(pitch_to_play, volume)
            #     piano_no_sustain.play_note(pitch_to_play, volume, piano_beat_length)
        else:
            wait(1)


s.fork(run_scanner)
s.fork(piano_process, initial_tempo=280)

app.exec_()

# s.stop_transcribing().to_score().show()
