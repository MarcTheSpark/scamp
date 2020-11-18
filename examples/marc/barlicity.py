#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

from scamp import *
import sys
from sklearn import manifold
import numpy as np
from scamp_extensions.composers.barlicity import harmonicity, _gaussian_discount, get_indispensability_array
from scamp_extensions.pitch.utilities import midi_to_hertz, hertz_to_midi
import random
from PyQt5 import QtCore, QtWidgets, Qt
import math
from fractions import Fraction


##################################################################################################################
#                                       Setting up some of the guiding variables
##################################################################################################################


piano_distillation_timeline = Envelope((0, 1, 0), (120, 120))

SCAN_PERIOD, WIDTH_AVERAGE, WIDTH_VARIATION, WIDTH_VARIATION_PERIOD, WIDTH_START_PHASE = \
    160, 10.0, 5.0, 20, 3*math.pi / 2

PIANO_TEMPO = 140
HARPSICHORD_TEMPO = 840


##################################################################################################################
#                                             Set up the scale pitches
##################################################################################################################


root_frequency = midi_to_hertz(31)
rationalized_bark_intervals = [Fraction(1, 1), Fraction(2, 1), Fraction(3, 1), Fraction(4, 1), Fraction(5, 1),
                               Fraction(6, 1), Fraction(64, 9), Fraction(25, 3), Fraction(28, 3), Fraction(32, 3),
                               Fraction(12, 1), Fraction(64, 5), Fraction(128, 9), Fraction(63, 4), Fraction(50, 3),
                               Fraction(18, 1), Fraction(20, 1), Fraction(64, 3), Fraction(45, 2), Fraction(24, 1)]
piano_scale = [hertz_to_midi(root_frequency * ratio) for ratio in rationalized_bark_intervals]
harpsichord_scale = [x - 24 for x in piano_scale[11:]] + [x - 12 for x in piano_scale[11:]] + piano_scale[11:]

##################################################################################################################
#                                        Do the multidimensional scaling
##################################################################################################################


mds = manifold.MDS(n_components=2, dissimilarity="precomputed", random_state=152)
harmonic_distances = np.array([
    [abs(1/harmonicity((top / bottom).numerator, (top / bottom).denominator)) for bottom in rationalized_bark_intervals]
    for top in rationalized_bark_intervals
])
mds_points = mds.fit(harmonic_distances).embedding_

# scale those mds_points into the range 0-1000 in x and y coordinates for drawing
point_range = min(x[0] for x in mds_points), max(x[0] for x in mds_points), \
              min(x[1] for x in mds_points), max(x[1] for x in mds_points)
scale_factor = 1400 / max(point_range[1] - point_range[0], point_range[3] - point_range[2])
mds_points *= scale_factor
mds_points += 500


##################################################################################################################
#                                                 Main QT Class
##################################################################################################################


class Barlicity(QtWidgets.QMainWindow):
    def __init__(self, points):
        super(Barlicity, self).__init__()

        # set up the scene
        scene = QtWidgets.QGraphicsScene(self)
        view = QtWidgets.QGraphicsView(scene)
        self.setCentralWidget(view)
        self.resize(Qt.QSize(QtWidgets.QDesktopWidget().availableGeometry(self).size().height() * 0.8,
                             QtWidgets.QDesktopWidget().availableGeometry(self).size().height() * 0.8))
        view.setSceneRect(QtCore.QRectF(0, 0, 1000, 1000))

        # create and position the scanner circle
        self.circle = QtWidgets.QGraphicsEllipseItem(QtCore.QRectF(-50, -50, 100, 100))
        self.circle.setOpacity(0.6)
        self.circle.setBrush(Qt.QColor(0, 100, 255))
        # these two variables are set from the scamp threads, and then they are read during the "do_frame" method (which
        # operates in Qt land) and used to actually position the circle. GUI actions can only be on the main QT thread.
        self.circle_center = (500, 500)
        self.circle_width = scale_factor * (WIDTH_AVERAGE + WIDTH_VARIATION * math.sin(WIDTH_START_PHASE))
        # Having defined them, since we're on the Qt thread right now, we position the circle
        self.circle.setPos(*self.circle_center)
        self.circle.setRect(-self.circle_width / 2, -self.circle_width / 2, self.circle_width, self.circle_width)
        scene.addItem(self.circle)

        # the scanner moves around between the different points; this keeps track of where it is
        self.scanner_index = 0

        view.setMouseTracking(True)
        def mme(evt):
            self.start()
        view.mousePressEvent = mme

        # create all of the points
        self.points_graphics = []
        for i, point in enumerate(points):
            self.points_graphics.append(
                scene.addEllipse(Qt.QRectF(point[0] - 5, point[1] - 5, 10, 10), brush=Qt.QColor(0, 0, 0))
            )
            text = scene.addText(str(i))
            text.setPos(point[0] - 25, point[1])

        self.contained_points = []
        # this checks which points are currently in the scanner and puts their indices in self.contained_points
        self.check_contained_points()

        # set up the Qt repaint to happen every 10 milliseconds by calling self.do_frame
        self.repaint_timer = QtCore.QTimer(self)
        self.repaint_timer.timeout.connect(self.do_frame)
        self.repaint_timer.start(10)
        self.repaint()

        # These scamp objects are defined when the window is shown
        self.session = self.piano = self.harpsichord = None

    def showEvent(self, a0):
        # when the window is shown, we set up scamp
        super().showEvent(a0)
        
    def start(self):
        self.session = Session().run_as_server()
        self.harpsichord = self.session.new_part("harpsichord")
        self.piano = self.session.new_part("piano")
        self.session.fork(self.run_scanner, name="SCANNER_CLOCK")
        piano_clock = self.session.fork(self.piano_part, initial_tempo=PIANO_TEMPO, name="PIANO_CLOCK")
#         self.session.fork(self.harpsichord_part, initial_tempo=HARPSICHORD_TEMPO, name="PIANO_CLOCK")
        self.session.start_transcribing(clock=piano_clock)

    def closeEvent(self, a0):
        # when the window is closed, we stop transcribing and create a score
        super().closeEvent(a0)
        self.session.stop_transcribing().to_score(
            time_signature="3/4", title="Barlicity (raw)", composer="Marc Evanstein").show_xml()

    def piano_part(self, clock: Clock):
        piano_indispensabilities = get_indispensability_array(((3, 2), 3, 2), normalize=True)
        last_piano_note_pool = None
        self.piano.send_midi_cc(64, 1.0)
        while True:
            which_beat = int(round((clock.beat() * 2) % len(piano_indispensabilities)))
            this_indispensability = piano_indispensabilities[which_beat]
            note_pool = [piano_scale[i] for i in self.contained_points]

            if last_piano_note_pool != note_pool:
                self.piano.send_midi_cc(64, 0.0)
                self.piano.send_midi_cc(64, 1.0)

            last_piano_note_pool = note_pool

            syncopation_prob = 1 - ((self.circle_width / scale_factor - WIDTH_AVERAGE) / (2 * WIDTH_VARIATION) + 0.5)
            piano_distillation_factor = piano_distillation_timeline.value_at(clock.time())

            # spensability is either indispensability or dispensability, depending on whether it's syncopated
            spensability = this_indispensability if random.random() < syncopation_prob else 1 - this_indispensability

            if len(note_pool) > 0 and spensability >= piano_distillation_factor:
                # distillation allows only the most "spensible" beats to play, and to play with bigger chords
                # at distillation_factor 0, the number of notes should be 1,
                # at distillation_factor 1 and spensibility 1, it should by all the notes
                num_notes = int(1 + round(piano_distillation_factor * spensability * (len(note_pool) - 1)))
                first_note_index = int(0.999 * spensability * (len(note_pool) - num_notes + 1))

                volume = 0.4 + 0.5 * this_indispensability
                self.piano.play_chord(note_pool[first_note_index: first_note_index + num_notes], volume, 0.5)
            else:
                wait(0.5)

    def harpsichord_part(self, clock: Clock):
        harpsichord_indispensabilities = get_indispensability_array((2, 3, (3, 2)), normalize=True)

        running = False
        scale_index = None
        direction = None
        octave_transposition = 0

        while True:
            runniness = 0.02 + 0.98 * piano_distillation_timeline.value_at(clock.time())
            which_beat = int(round((clock.beat()) % len(harpsichord_indispensabilities)))
            this_indispensability = harpsichord_indispensabilities[which_beat]

            if not running:
                # if not running, a high runniness and a high indispensibility will tend to start a run
                if random.random() < runniness * this_indispensability:
                    running = True
                    octave_transposition = Barlicity.get_an_octave_transposition(clock.time())
                    # play the first note "on the beat"
                    scale_index = random.randrange(len(harpsichord_scale) // 3) + len(harpsichord_scale) // 3
                    direction = random.choice([-1, 1])
                    self.harpsichord.play_note(harpsichord_scale[scale_index] + octave_transposition, 0.9, 1.0)
                else:
                    wait(1)
            else:
                # play the last note "on the beat"
                scale_index += direction
                self.harpsichord.play_note(harpsichord_scale[scale_index] + octave_transposition, 0.9, 1.0)

                if random.random() * 1.5 < this_indispensability or \
                        scale_index == 0 or scale_index == len(harpsichord_scale) - 1:
                    # change run direction if on an important beat or at the top or bottom
                    direction *= -1

                # if running, a low runniness and a high indispensibility will tend to stop a run
                if random.random() < (1 - runniness) * this_indispensability:
                    running = False

    @staticmethod
    def get_an_octave_transposition(time_passed):
        most_octaves_transposed = min(int((time_passed / 140.0) * 2), 2)

        transposition = random.choice([-1, 1]) * random.choice(
            [max(most_octaves_transposed - 1, 0), most_octaves_transposed])
        return transposition * 12

    def set_scanner_position(self, dt):
        self.circle_width = scale_factor * (
                WIDTH_AVERAGE + WIDTH_VARIATION *
                math.sin(2 * math.pi * self.session.time() / WIDTH_VARIATION_PERIOD + WIDTH_START_PHASE)
        )

        total_multiplier = 0
        new_location = np.array([0.0, 0.0])
        for i, point in enumerate(mds_points):
            index_distance = min((i - self.scanner_index) % len(mds_points),
                                 (self.scanner_index - i) % len(mds_points))
            index_discount = _gaussian_discount(index_distance, 0, 0.45)
            total_multiplier += index_discount
            new_location[0] += point[0] * index_discount
            new_location[1] += point[1] * index_discount

        new_location /= total_multiplier
        scanner_location = new_location
        self.circle_center = scanner_location
        self.scanner_index = (self.scanner_index + dt * len(mds_points) / SCAN_PERIOD) % len(mds_points)

    def run_scanner(self):
        while True:
            wait(0.05)
            self.set_scanner_position(0.05)

    def do_frame(self):
        self.circle.setPos(*self.circle_center)
        self.circle.setRect(-self.circle_width/2, -self.circle_width/2, self.circle_width, self.circle_width)
        self.check_contained_points()
        super().repaint()

    def check_contained_points(self):
        contained_points = []
        for i, point in enumerate(self.points_graphics):
            if self.circle.collidesWithItem(point):
                contained_points.append(i)
        self.contained_points = contained_points


app = QtWidgets.QApplication(sys.argv)

w = Barlicity(mds_points)
w.show()

app.exec_()
