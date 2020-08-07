#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  SCAMP (Suite for Computer-Assisted Music in Python)                                           #
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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        scene = QtWidgets.QGraphicsScene(self)
        view = QtWidgets.QGraphicsView(scene)
        # view.setSceneRect(QtCore.QRectF(0, 0, 500, 500))
        scene.setSceneRect(QtCore.QRectF(0, 0, 800, 800))

        self.setCentralWidget(view)

        self.rect_item = QtWidgets.QGraphicsRectItem(QtCore.QRectF(0, 0, 100, 100))
        self.rect_item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        scene.addItem(self.rect_item)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.setFixedSize(QtCore.QSize(800, 800))
    w.show()

    s = Session().run_as_server()
    piano = s.new_part("piano")
    s.start_transcribing()

    speed_response = Envelope.from_levels_and_durations([2, 0.1], [800], [-5])

    def play_notes():
        while True:
            piano.play_note((1-w.rect_item.y()/800) * 40 + 60, 1.0, speed_response.value_at(w.rect_item.x()))

    s.fork(play_notes)

    app.exec_()

    s.stop_transcribing().to_score().show()
