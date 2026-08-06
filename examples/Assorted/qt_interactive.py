"""
SCAMP Example: Qt Interactive

A draggable PyQt rectangle drives live playback in a server session. Moving the rectangle
fires a callback that sets the tempo of the clock running the note loop; its vertical position
still sets the pitch.

Tags: gui integration, run_as_server, live interaction, callback
"""

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

from PyQt5 import QtCore, QtWidgets


class DraggableRect(QtWidgets.QGraphicsRectItem):
    """Movable rectangle that calls `on_move(x, y)` each time it is dragged."""

    def __init__(self, rect, on_move=None):
        super().__init__(rect)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.on_move = on_move

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.on_move is not None:
            self.on_move(value.x(), value.y())
        return super().itemChange(change, value)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        scene = QtWidgets.QGraphicsScene(self)
        view = QtWidgets.QGraphicsView(scene)
        scene.setSceneRect(QtCore.QRectF(0, 0, 800, 800))

        self.setCentralWidget(view)

        self.rect_item = DraggableRect(QtCore.QRectF(0, 0, 100, 100))
        scene.addItem(self.rect_item)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.setFixedSize(QtCore.QSize(800, 800))
    w.show()

    # map the rectangle's x position (0–800) to a tempo in BPM
    tempo_response = Envelope([30, 600], [800], [3])

    # leaving the `with` block kills the session (and the forked note loop), so closing
    # the window shuts everything down gracefully rather than leaking the scheduler thread
    with Session().run_as_server() as s:
        piano = s.new_part("piano")
        s.start_transcribing()

        def play_notes():
            while True:
                piano.play_note((1 - w.rect_item.y() / 800) * 40 + 60, 1.0, 1.0)

        play_clock = s.fork(play_notes)

        # whenever the rectangle moves, retune the note loop's tempo from its x position
        w.rect_item.on_move = lambda x, y: setattr(play_clock, "tempo", tempo_response.value_at(x))

        app.exec_()  # blocks until the window is closed

        performance = s.stop_transcribing()

    performance.to_score().show()
