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

from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.compat import is_win, is_darwin

if is_win:
    scamp_libs = [lib_info for lib_info in collect_dynamic_libs("scamp")
                  if ".dll" in lib_info[0]]
elif is_darwin:
    scamp_libs = [lib_info for lib_info in collect_dynamic_libs("scamp")
                  if ".dylib" in lib_info[0]]
else:
    scamp_libs = []

binaries = scamp_libs
