/*
 *  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)
 *  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.
 *
 *  This program is free software: you can redistribute it and/or modify it under the terms of
 *  the GNU General Public License as published by the Free Software Foundation, either version
 *  3 of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 *  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *  See the GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License along with this program.
 *  If not, see <http://www.gnu.org/licenses/>.
 */

// Turns a multi-page score (a ".score-pager" emitted by build_examples_docs.py) into a
// one-page-at-a-time viewer, paged with the prev/next buttons or the left/right arrow keys.
// Arrow keys act on the pager the mouse is over or that holds focus, so several can coexist.
(function () {
    "use strict";

    var hovered = null;  // the pager the mouse is currently over, for arrow-key routing

    function initPager(pager) {
        var pages = Array.prototype.slice.call(pager.querySelectorAll(".score-page"));
        if (pages.length < 2) {
            return;  // a lone page needs no controls
        }
        var status = pager.querySelector(".score-pager-status");
        var prev = pager.querySelector(".score-pager-prev");
        var next = pager.querySelector(".score-pager-next");
        var current = 0;

        function render() {
            pages.forEach(function (img, i) {
                img.style.display = i === current ? "block" : "none";
            });
            status.textContent = (current + 1) + " / " + pages.length;
            prev.disabled = current === 0;
            next.disabled = current === pages.length - 1;
        }

        function go(delta) {
            var target = Math.min(pages.length - 1, Math.max(0, current + delta));
            if (target !== current) {
                current = target;
                render();
            }
        }

        prev.addEventListener("click", function () { go(-1); });
        next.addEventListener("click", function () { go(1); });
        pager.addEventListener("mouseenter", function () { hovered = pager; });
        pager.addEventListener("mouseleave", function () {
            if (hovered === pager) { hovered = null; }
        });
        pager._go = go;
        render();
    }

    document.addEventListener("keydown", function (e) {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") {
            return;
        }
        var t = e.target;
        if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
            return;  // don't steal arrows from a text field
        }
        var active = document.activeElement;
        var pager = active && active.closest ? active.closest(".score-pager") : null;
        if (!pager) {
            pager = hovered;
        }
        if (pager && pager._go) {
            pager._go(e.key === "ArrowLeft" ? -1 : 1);
            e.preventDefault();
        }
    });

    document.addEventListener("DOMContentLoaded", function () {
        Array.prototype.forEach.call(
            document.querySelectorAll(".score-pager"), initPager);
    });
})();
