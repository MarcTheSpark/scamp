"""
Module containing the demand-driven tick driver that samples parameter animations for playback.

Rather than each animated parameter scheduling its own stream of updates (at its own rate and phase),
a single recurring tick per clock family walks a registry of active animations and samples each one
live at that clock's current beat. Because it's one driver, concurrent animations coincide on the same
scheduler wakes instead of each contending for the scheduler thread separately. It is reference-counted,
so it costs nothing while nothing is animating.
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

from __future__ import annotations
import logging
from threading import Lock
from weakref import WeakKeyDictionary
from clockblocks import Clock, Moment, DeadClockError, ClockKilledError
from .settings import playback_settings


# each master clock gets one _AnimationTickDriver; weak ref for garbage collection
_drivers: WeakKeyDictionary[Clock, _AnimationTickDriver] = WeakKeyDictionary()
# _drivers is process-global: separate clock families run on their own scheduler threads, so this
# guards against concurrent mutation of the _drivers dictionary
_drivers_lock = Lock()


def get_animation_driver(clock: Clock) -> _AnimationTickDriver:
    """Return (creating if needed) the tick driver for the clock family that `clock` belongs to."""
    master = clock.master
    with _drivers_lock:
        driver = _drivers.get(master)
        if driver is None:
            driver = _drivers[master] = _AnimationTickDriver(master)
        return driver


class _AnimationTickDriver:

    """
    Samples every active parameter animation in one clock family on a single recurring tick.

    The registered segments are ``_ParameterChangeSegment``s (from instruments.py); the tick reads each
    one's ``clock``, ``_anim_start_beat`` (where its envelope's beat-zero sits on that clock), ``value_at``,
    ``do_change_parameter`` and ``running``. They're held without importing that class, purely to keep this
    module free of a dependency on instruments.py.
    """

    def __init__(self, master: Clock):
        self.master = master
        self._active_segments = set()
        self._tick_scheduled = False
        # guards _active_segments and _tick_scheduled together: register() must add a segment and, if no
        # tick is pending, schedule one, as a single step. In-family calls are already serialized, so this
        # only matters when a note is started/ended from outside the clock system (e.g. run_as_server).
        self._lock = Lock()

    def register(self, segment) -> None:
        """
        Registers a new segment to be animated, and starts the tick anew if it's not currently going
        (i.e. if there is no tick scheduled).
        """
        with self._lock:
            self._active_segments.add(segment)
            if not self._tick_scheduled:
                self._schedule_tick()

    def deregister(self, segment) -> None:
        """
        Deregisters the given segment. No need to cancel the next tick; if there are other segments
        it needs to keep animating them, and if not, it will cancel itself.
        """
        with self._lock:
            self._active_segments.discard(segment)

    def _schedule_tick(self) -> None:
        """
        Schedule the next tick, one interval ahead of the current master time. Note that when called
        from tick in a rescheduling cycle, there is no gap because the scheduler is frozen while
        executing tick. Called under self._lock.
        """
        next_tick_time = self.master.time + playback_settings.animation_tick_interval
        try:
            self.master.schedule_action(self._tick, Moment.at_time(next_tick_time))
            self._tick_scheduled = True
        except (DeadClockError, ClockKilledError):
            # The family is tearing down; there's nothing left to animate.
            self._tick_scheduled = False

    def _tick(self) -> None:
        """
        The actual meat of animating segments: Grab the list of active segments, and set the associated
        parameters reading from the envelope at the number of beats past since animation start.
        """
        # snapshot the active segments under the lock, then sample outside it: do_change_parameter calls
        # into playback, which we must not hold the lock across
        with self._lock:
            segments = list(self._active_segments)
        for segment in segments:
            try:
                if segment.running:
                    segment.do_change_parameter(
                        segment.value_at(segment.clock.beat - segment._anim_start_beat))
            except Exception:
                logging.exception("Error sampling parameter animation.")
        with self._lock:
            # _tick_scheduled was left True above so a concurrent register() won't start a second chain.
            # If there are segments still active, schedule the next tick; otherwise set to False since
            # we're done animating (for now)
            if self._active_segments:
                self._schedule_tick()
            else:
                self._tick_scheduled = False
