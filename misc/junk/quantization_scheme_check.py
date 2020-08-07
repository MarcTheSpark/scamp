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

# This allows the user to simply give a time signature as a quantization_scheme.
if not isinstance(quantization_scheme, QuantizationScheme):
    if not isinstance(quantization_scheme, (TimeSignature, str, tuple)):
        raise ValueError("Uninterpretable quantization_scheme")
    elif isinstance(quantization_scheme, TimeSignature):
        time_signature = quantization_scheme
    else:
        try:
            if isinstance(quantization_scheme, str):
                time_signature = TimeSignature.from_string(quantization_scheme)
            else:
                time_signature = TimeSignature(*quantization_scheme)
        except Exception:
            raise ValueError("Uninterpretable quantization_scheme")
    quantization_scheme = QuantizationScheme.from_time_signature(time_signature)