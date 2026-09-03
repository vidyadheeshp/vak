# -*- coding: utf-8 -*-
"""गणना — an optional visitor count for the generated pages.

The pages say, in several places, that the playground runs with no server and
that nothing you type leaves the page. Both remain true with a counter on the
page — a page view is not your program — but only if the counter is chosen and
described carefully, so:

  * GoatCounter, which sets no cookies, records no personal data, and does no
    cross-site tracking. It is open source and free for a project like this.
  * Do Not Track is honoured before the script is even fetched, so a reader who
    has asked not to be counted makes no request at all.
  * The footer says the counting is happening. A privacy claim on a page that
    quietly phones home is worse than no claim.

Until SITE is set this emits nothing, and the pages are byte-identical to a
build without it.

To switch it on:

  1. Register a free site at https://www.goatcounter.com (choose a code, e.g.
     `vak` — the dashboard is then at https://vak.goatcounter.com).
  2. Put that code in SITE below, or set the VAK_GOATCOUNTER environment
     variable, and rebuild the pages.
"""
from __future__ import annotations

import os

# The GoatCounter site code — the `vak` in https://vak.goatcounter.com.
#
# Kept here as a literal rather than only in an environment variable. An
# env-var-only setting means any rebuild by anyone who has not exported it
# silently strips the counter back out of the pages, which is exactly what
# happened the first time. The environment variable still overrides, for a
# build that deliberately wants no counter:
#
#     VAK_GOATCOUNTER= python docs/build_landing.py     # emits nothing
SITE = os.environ.get("VAK_GOATCOUNTER", "vak").strip()


def script() -> str:
    """The counter snippet, or an empty string when no site is configured."""
    if not SITE:
        return ""
    return f"""
<!-- गणना — visitor count. No cookies, no personal data, no cross-site
     tracking, and nothing here can see what you type into the playground.
     Do Not Track is checked before the script is requested. -->
<script>
(function () {{
  var dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
  if (dnt === "1" || dnt === "yes") return;      // asked not to be counted
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.js";
  s.setAttribute("data-goatcounter", "https://{SITE}.goatcounter.com/count");
  document.head.appendChild(s);
}})();
</script>"""


def notice(link: bool = True) -> str:
    """One line for a footer, saying that counting happens and on what terms."""
    if not SITE:
        return ""
    where = (f'<a href="https://{SITE}.goatcounter.com">GoatCounter</a>'
             if link else "GoatCounter")
    return (f"<p>Visits are counted with {where} — no cookies, no personal "
            f"data, and Do Not Track is honoured.</p>")
