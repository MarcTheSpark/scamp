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

from clockblocks import *


master = Clock("MASTER")
grandchild = None


def c():
    global grandchild
    print("child start")
    grandchild = fork(gc, name="GRANDCHILD")
    wait(8)
    print("child end", master.time())


def gc(clock):
    while True:
        print(clock.beat(), master.beat())
        wait(2)


child = master.fork(c, name="CHILD")


def test():
    global grandchild
    time.sleep(1.5)
    master.rouse_and_hold()
    grandchild.rouse_and_hold()
    grandchild.tempo = 10
    print(master._wait_keeper.being_held, grandchild._wait_keeper.being_held)
    grandchild.release_from_suspension()
    time.sleep(0.001)
    print(master._wait_keeper.being_held, grandchild._wait_keeper.being_held)
    master.release_from_suspension()
    time.sleep(0.001)
    print(master._wait_keeper.being_held, grandchild._wait_keeper.being_held)

# wait(1.5)
# master.rouse_and_hold()
# grandchild.rouse_and_hold()
# grandchild.tempo = 10
# grandchild.release_from_suspension()
# master.release_from_suspension()
threading.Thread(target=test).start()

# master.wait_forever()
master.wait_for_children_to_finish()
