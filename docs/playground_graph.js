/* कारकालेखः — the kāraka graph, drawn live in the playground.
 *
 * The engine (the self-hosted toolchain, compiled to WebAssembly) builds the
 * graph with `--आलेखः`; this file only draws it. Three views, one per question
 * a learner asks:
 *
 *   क्रियाः    what roles does each action declare?
 *   वाक्यानि   how does each call fill those roles — by name, by position,
 *              left unstated, or not at all?
 *   सम्बन्धः   which actions depend on which, and what is passed where?
 *
 * Inlined into docs/playground.html by docs/build_playground.py, which also
 * supplies KARAKA_TABLE from vaak/tokens.py so the legend cannot drift from
 * the language.
 */
var KarakaGraph = (function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";
  var ORDER = __KARAKA_ORDER__;          // the six roles, in Pāṇini's order
  var TABLE = __KARAKA_TABLE__;          // role -> "vibhakti — meaning"
  var SLUG = {
    "कर्ता": "karta", "कर्म": "karma", "करणम्": "karana",
    "सम्प्रदानम्": "sampradana", "अपादानम्": "apadana", "अधिकरणम्": "adhikarana"
  };
  var HOW = {
    "नाम्ना": "नाम्ना · by name",
    "स्थानेन": "स्थानेन · by position",
    "अनुक्तम्": "अनुक्तम् · unstated, default used",
    "न्यूनम्": "न्यूनम् · missing"
  };
  var uid = 0;

  /* ------------------------------------------------------------ helpers */
  function svg(tag, attrs, parent) {
    var node = document.createElementNS(SVGNS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  function html(tag, cls, parent, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    if (parent) parent.appendChild(node);
    return node;
  }
  function label(parent, x, y, str, cls, anchor) {
    var t = svg("text", { x: x, y: y, "class": cls || "", "text-anchor": anchor || "middle" }, parent);
    t.textContent = str;
    return t;
  }
  /* Devanagari vowel signs and viramas take no width of their own; counting
     them made every box too wide. */
  function visibleLength(str) {
    var n = 0;
    Array.from(String(str)).forEach(function (c) {
      if (!/[ऀ-ःऺ-ॏ॑-ॗॢॣ]/.test(c)) n += 1;
    });
    return n;
  }
  function clip(str, max) {
    str = String(str);
    return visibleLength(str) > max ? Array.from(str).slice(0, max).join("") + "…" : str;
  }
  function boxWidth(lines, min) {
    var widest = 0;
    lines.forEach(function (s) { widest = Math.max(widest, visibleLength(s)); });
    return Math.max(min, widest * 8.4 + 26);
  }
  function roleClass(role) { return "k-" + (SLUG[role] || "none"); }
  function arrowMarker(root) {
    var id = "kg-arrow-" + (++uid);
    var defs = svg("defs", {}, root);
    var m = svg("marker", { id: id, viewBox: "0 0 10 10", refX: "9", refY: "5",
                            markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" }, defs);
    svg("path", { d: "M0,0 L10,5 L0,10 z", "class": "kg-arrowhead" }, m);
    return "url(#" + id + ")";
  }
  function figure(parent, title, sub, line, onLine) {
    var card = html("figure", "kg-card", parent);
    var head = html("figcaption", "kg-head", card);
    html("span", "kg-title", head, title);
    if (sub) html("span", "kg-sub", head, sub);
    if (line) {
      var b = html("button", "kg-line", head, "पङ्क्तिः " + line);
      b.type = "button";
      b.title = "Show line " + line + " in the editor";
      b.addEventListener("click", function () { if (onLine) onLine(line); });
    }
    return card;
  }

  /* ------------------------------------------------------------- legend */
  function legend(parent) {
    var bar = html("div", "kg-legend", parent);
    ORDER.forEach(function (role) {
      var chip = html("span", "kg-chip " + roleClass(role), bar);
      html("b", "", chip, role);
      html("span", "", chip, (TABLE[role] || "").split(" — ")[0]);
      chip.title = TABLE[role] || role;
    });
    var ways = html("div", "kg-ways", parent);
    [["नाम्ना", "solid"], ["स्थानेन", "dotted"], ["अनुक्तम्", "ghost"], ["न्यूनम्", "missing"]]
      .forEach(function (w) {
        var s = html("span", "kg-way kg-way-" + w[1], ways);
        html("i", "", s);
        html("span", "", s, HOW[w[0]]);
      });
  }

  /* ------------------------------------------------ क्रिया — one action */
  function drawAction(parent, act, onLine) {
    var params = act["प्राचलाः"] || [];
    var faults = act["दोषाः"] || [];
    var card = figure(parent, act["नाम"], "→ " + act["प्रतिफलम्"], act["पङ्क्तिः"], onLine);
    var counts = {};
    params.forEach(function (p) { if (p["कारकम्"]) counts[p["कारकम्"]] = (counts[p["कारकम्"]] || 0) + 1; });

    var W = 600, H = params.length ? 300 : 110, cx = W / 2, cy = params.length ? H / 2 : 55;
    var root = svg("svg", { viewBox: "0 0 " + W + " " + H, "class": "kg-svg", role: "img",
      "aria-label": "Action " + act["नाम"] + " with " + params.length + " parameters" }, card);
    var edges = svg("g", {}, root), nodes = svg("g", {}, root);

    var n = params.length;
    params.forEach(function (p, i) {
      var angle = (-90 + (360 / n) * i) * Math.PI / 180;
      var x = cx + Math.cos(angle) * 205, y = cy + Math.sin(angle) * 105;
      var role = p["कारकम्"];
      var clash = role && (role === "कर्ता" || role === "कर्म") && counts[role] > 1;
      svg("line", { x1: cx, y1: cy, x2: x, y2: y,
        "class": "kg-edge " + roleClass(role) + (p["मूलम्"] ? " kg-default" : "") + (clash ? " kg-bad" : "") }, edges);
      var line1 = role || "— कारकम् नास्ति";
      var line2 = clip(p["नाम"], 12) + " : " + p["प्रकारः"];
      var w = boxWidth([line1, line2 + (p["मूलम्"] ? "  = मूलम्" : "")], 118), h = 48;
      var g = svg("g", { "class": "kg-node " + roleClass(role) + (clash ? " kg-bad" : "") }, nodes);
      svg("rect", { x: x - w / 2, y: y - h / 2, width: w, height: h, rx: 6,
        "class": "kg-slot" + (p["मूलम्"] ? " kg-default" : "") }, g);
      label(g, x, y - 5, line1, "kg-role");
      label(g, x, y + 14, line2 + (p["मूलम्"] ? "  = मूलम्" : ""), "kg-name");
      svg("title", {}, g).textContent = (role ? role + " — " + (TABLE[role] || "") : "no kāraka declared") +
        (p["मूलम्"] ? " · has a default, so a call may leave it unstated" : "");
    });

    var head = clip(act["नाम"], 16), pw = boxWidth([head], 110);
    var pill = svg("g", { "class": "kg-action" }, nodes);
    svg("rect", { x: cx - pw / 2, y: cy - 22, width: pw, height: 44, rx: 22 }, pill);
    label(pill, cx, cy + 6, head, "kg-verb");
    svg("title", {}, pill).textContent = "क्रिया — the action; its parameters are the roles around it";
    if (!n) label(root, cx, cy + 44, "प्राचलाः न सन्ति · no parameters", "kg-note");

    faults.forEach(function (f) { html("p", "kg-fault", card, "⚠ " + f + " — Pāṇini allows one कर्ता and one कर्म per action"); });
  }

  /* --------------------------------------------- वाक्यम् — one call */
  function drawSentence(parent, call, onLine) {
    var binds = call["बन्धाः"] || [];
    var faults = call["दोषाः"] || [];
    var where = call["अन्तः"] ? "within " + call["अन्तः"] : "at the top level";
    var card = figure(parent, call["कार्यम्"] + "(…)", where, call["पङ्क्तिः"], onLine);
    var rowH = 54, top = 30, n = Math.max(binds.length, 1);
    var W = 640, H = top + n * rowH + 20;
    var root = svg("svg", { viewBox: "0 0 " + W + " " + H, "class": "kg-svg", role: "img",
      "aria-label": "Call to " + call["कार्यम्"] + " on line " + call["पङ्क्तिः"] }, card);
    var arrow = arrowMarker(root);
    label(root, 105, 18, "सहभागिनः · participants", "kg-colhead");
    label(root, 330, 18, "कारकाणि · roles", "kg-colhead");
    label(root, 545, 18, "क्रिया · action", "kg-colhead");

    var edges = svg("g", {}, root), nodes = svg("g", {}, root);
    var vx = 105, sx = 330, ax = 545, ay = top + (n * rowH) / 2;

    binds.forEach(function (b, i) {
      var y = top + i * rowH + rowH / 2;
      var role = b["कारकम्"], how = b["रीतिः"];
      var slotText = role || b["प्राचलः"];
      var sw = boxWidth([slotText, b["प्राचलः"]], 128);
      var slot = svg("g", { "class": "kg-node " + roleClass(role) + (how === "न्यूनम्" ? " kg-bad" : "") }, nodes);
      svg("rect", { x: sx - sw / 2, y: y - 21, width: sw, height: 42, rx: 6,
        "class": "kg-slot" + (how === "अनुक्तम्" ? " kg-default" : "") + (how === "न्यूनम्" ? " kg-missing" : "") }, slot);
      label(slot, sx, y - 3, role || "—", "kg-role");
      label(slot, sx, y + 13, clip(b["प्राचलः"], 14), "kg-name");
      svg("title", {}, slot).textContent = (role ? role + " — " + (TABLE[role] || "") : "an unmarked parameter") +
        " · " + HOW[how];

      svg("path", { d: "M" + (sx + sw / 2) + "," + y + " C" + (sx + sw / 2 + 50) + "," + y + " " +
        (ax - 90) + "," + ay + " " + (ax - 62) + "," + ay, "class": "kg-edge kg-thin " + roleClass(role) }, edges);

      if (how === "नाम्ना" || how === "स्थानेन") {
        var text = clip(b["मूल्यम्"], 16), vw = boxWidth([text], 96);
        var val = svg("g", { "class": "kg-value" }, nodes);
        svg("rect", { x: vx - vw / 2, y: y - 17, width: vw, height: 34, rx: 17 }, val);
        label(val, vx, y + 5, text, "kg-name");
        svg("line", { x1: vx + vw / 2, y1: y, x2: sx - sw / 2 - 4, y2: y, "marker-end": arrow,
          "class": "kg-edge kg-bind " + roleClass(role) + (how === "स्थानेन" ? " kg-positional" : "") }, edges);
        label(edges, (vx + vw / 2 + sx - sw / 2) / 2, y - 7, how, "kg-how");
      } else if (how === "अनुक्तम्") {
        label(nodes, vx, y + 5, "(मूलम् · default)", "kg-ghost");
      } else {
        var miss = svg("g", { "class": "kg-value kg-bad" }, nodes);
        svg("rect", { x: vx - 30, y: y - 17, width: 60, height: 34, rx: 17, "class": "kg-missing" }, miss);
        label(miss, vx, y + 6, "?", "kg-name");
        svg("line", { x1: vx + 30, y1: y, x2: sx - sw / 2 - 4, y2: y, "marker-end": arrow,
          "class": "kg-edge kg-bind kg-bad kg-positional" }, edges);
        label(edges, (vx + 30 + sx - sw / 2) / 2, y - 7, "न्यूनम्", "kg-how kg-bad");
      }
    });

    var head = clip(call["कार्यम्"], 14), pw = boxWidth([head], 104);
    var pill = svg("g", { "class": "kg-action" }, nodes);
    svg("rect", { x: ax - pw / 2, y: ay - 22, width: pw, height: 44, rx: 22 }, pill);
    label(pill, ax, ay + 6, head, "kg-verb");
    if (!binds.length) label(root, 330, top + 30, "प्राचलाः न सन्ति · takes nothing", "kg-note");

    faults.forEach(function (f) { html("p", "kg-fault", card, "⚠ " + f); });
  }

  /* ------------------------------------------- सम्बन्धः — connectivity */
  function drawConnectivity(parent, g, onLine) {
    var acts = g["कार्याणि"] || [], calls = g["आह्वानानि"] || [];
    var card = figure(parent, "सम्बन्धः", "who calls whom, and which actions are passed as roles");
    var MAIN = "मुख्यम्";
    var names = [MAIN];
    acts.forEach(function (a) { if (names.indexOf(a["नाम"]) < 0) names.push(a["नाम"]); });

    var callEdges = {}, roleEdges = [];
    calls.forEach(function (c) {
      var from = c["अन्तः"] || MAIN, key = from + "→" + c["कार्यम्"];
      callEdges[key] = callEdges[key] || { from: from, to: c["कार्यम्"], count: 0, line: c["पङ्क्तिः"] };
      callEdges[key].count += 1;
      (c["बन्धाः"] || []).forEach(function (b) {
        if (b["मूल्यम्"] && names.indexOf(b["मूल्यम्"]) > 0) {
          roleEdges.push({ from: b["मूल्यम्"], to: c["कार्यम्"], role: b["कारकम्"], line: c["पङ्क्तिः"] });
        }
      });
    });

    // layers: breadth-first from the top level over calls; the unreached last
    var depth = {}; depth[MAIN] = 0;
    var queue = [MAIN];
    while (queue.length) {
      var at = queue.shift();
      Object.keys(callEdges).forEach(function (k) {
        var e = callEdges[k];
        if (e.from === at && depth[e.to] === undefined) { depth[e.to] = depth[at] + 1; queue.push(e.to); }
      });
    }
    var maxDepth = 0;
    Object.keys(depth).forEach(function (k) { maxDepth = Math.max(maxDepth, depth[k]); });
    var unreached = names.filter(function (nm) { return depth[nm] === undefined; });
    unreached.forEach(function (nm) { depth[nm] = maxDepth + 1; });
    var columns = [];
    names.forEach(function (nm) { (columns[depth[nm]] = columns[depth[nm]] || []).push(nm); });

    var colW = 190, rowH = 70, left = 90;
    var rows = 1;
    columns.forEach(function (c) { rows = Math.max(rows, (c || []).length); });
    var W = Math.max(600, left + (columns.length - 1) * colW + 110), H = 70 + rows * rowH;
    var root = svg("svg", { viewBox: "0 0 " + W + " " + H, "class": "kg-svg", role: "img",
      "aria-label": "Call graph of " + acts.length + " actions" }, card);
    var arrow = arrowMarker(root);
    var pos = {};
    columns.forEach(function (col, d) {
      (col || []).forEach(function (nm, i) {
        pos[nm] = { x: left + d * colW, y: 50 + i * rowH + rowH / 2 };
      });
      var headText = d === 0 ? "आरम्भः · start" : (unreached.length && d === maxDepth + 1 ? "न साक्षात् आहूतम् · never called by name" : "स्तरः " + d);
      label(root, left + d * colW, 22, headText, "kg-colhead");
    });

    var edges = svg("g", {}, root), nodes = svg("g", {}, root);
    function curve(a, b, bend) {
      if (a === b) {
        return "M" + (a.x - 18) + "," + (a.y - 20) + " C" + (a.x - 48) + "," + (a.y - 70) + " " +
          (a.x + 48) + "," + (a.y - 70) + " " + (a.x + 18) + "," + (a.y - 21);
      }
      var x1 = a.x + 56, x2 = b.x - 60;
      if (b.x <= a.x) {                        // backwards or sideways: go round underneath
        var low = Math.max(a.y, b.y) + 46 + bend;
        return "M" + a.x + "," + (a.y + 20) + " C" + a.x + "," + low + " " + b.x + "," + low + " " + b.x + "," + (b.y + 22);
      }
      return "M" + x1 + "," + (a.y + bend) + " C" + (x1 + 60) + "," + (a.y + bend) + " " +
        (x2 - 60) + "," + (b.y + bend) + " " + x2 + "," + (b.y + bend);
    }
    Object.keys(callEdges).forEach(function (k) {
      var e = callEdges[k], a = pos[e.from], b = pos[e.to];
      if (!a || !b) return;
      svg("path", { d: curve(a, b, 0), "class": "kg-edge kg-call", "marker-end": arrow }, edges);
      if (e.count > 1) label(edges, (a.x + b.x) / 2, (a.y + b.y) / 2 - 6, "×" + e.count, "kg-how");
    });
    roleEdges.forEach(function (e, i) {
      var a = pos[e.from], b = pos[e.to];
      if (!a || !b) return;
      svg("path", { d: curve(a, b, 10 + i * 4), "class": "kg-edge kg-passed " + roleClass(e.role), "marker-end": arrow }, edges);
      label(edges, (a.x + b.x) / 2, (a.y + b.y) / 2 + 20 + i * 4, (e.role || "—") + " रूपेण", "kg-how " + roleClass(e.role));
    });
    names.forEach(function (nm) {
      var p = pos[nm], w = boxWidth([clip(nm, 14)], 104);
      var gnode = svg("g", { "class": nm === MAIN ? "kg-main" : "kg-action" }, nodes);
      svg("rect", { x: p.x - w / 2, y: p.y - 20, width: w, height: 40, rx: 20 }, gnode);
      label(gnode, p.x, p.y + 6, nm === MAIN ? "मुख्यम्" : clip(nm, 14), "kg-verb");
    });
    html("p", "kg-note-html", card,
      "Solid arrows are calls. Coloured dashed arrows are actions handed to another as one of its roles — a function passed as करणम् is literally its instrument.");
  }

  /* -------------------------------------------------------------- render */
  function render(pane, g, opts) {
    opts = opts || {};
    pane.classList.remove("kg-stale");
    var body = pane.querySelector(".kg-body") || html("div", "kg-body", pane);
    var banner = pane.querySelector(".kg-banner");
    if (banner) banner.remove();
    body.textContent = "";

    var acts = g["कार्याणि"] || [], calls = g["आह्वानानि"] || [];
    var faults = 0;
    acts.forEach(function (a) { faults += (a["दोषाः"] || []).length; });
    calls.forEach(function (c) { faults += (c["दोषाः"] || []).length; });

    var summary = html("p", "kg-summary", body);
    summary.textContent = acts.length + " क्रियाः · " + calls.length + " वाक्यानि · " +
      (faults ? faults + " दोषाः" : "निर्दोषम्");
    if (faults) summary.classList.add("kg-bad");
    legend(body);

    if (!acts.length) {
      html("p", "kg-empty", body,
        "कार्यम् घोषयतु — declare a कार्यम् whose parameters name their kāraka, and its graph appears here as you type. The कारकाणि sample is a good start.");
      return;
    }
    html("h3", "kg-section", body, "क्रियाः · actions and their roles");
    acts.forEach(function (a) { drawAction(body, a, opts.onLine); });
    html("h3", "kg-section", body, "वाक्यानि · how each call fills the roles");
    if (!calls.length) html("p", "kg-empty", body, "No calls to these actions yet — call one and its sentence is drawn here.");
    calls.forEach(function (c) { drawSentence(body, c, opts.onLine); });
    html("h3", "kg-section", body, "सम्बन्धः · dependency and connectivity");
    drawConnectivity(body, g, opts.onLine);
  }

  function fail(pane, message) {
    pane.classList.add("kg-stale");
    var banner = pane.querySelector(".kg-banner");
    if (!banner) {
      banner = document.createElement("p");
      banner.className = "kg-banner";
      pane.insertBefore(banner, pane.firstChild);
    }
    banner.textContent = "⚠ " + (message || "the program does not parse") +
      " — the last graph that could be drawn is shown below.";
  }

  /* ------------------------------------------------ wiring to the engine */
  function attach(o) {
    var timer = null, generation = 0, visible = false;

    function selectLine(n) {
      var text = o.src.value, start = 0;
      for (var i = 1; i < n; i++) {
        var next = text.indexOf("\n", start);
        if (next < 0) break;
        start = next + 1;
      }
      var end = text.indexOf("\n", start);
      if (end < 0) end = text.length;
      o.src.focus();
      o.src.setSelectionRange(start, end);
      var lh = parseFloat(getComputedStyle(o.src).lineHeight) || 22;
      o.src.scrollTop = Math.max(0, (n - 3) * lh);
    }

    function draw() {
      if (!visible) return;
      var mine = ++generation, text = o.src.value, lines = [];
      o.status.textContent = "रचयति… · drawing";
      VakModule({
        noInitialRun: true,
        stdin: function () { return null; },
        print: function (t) { lines.push(t); },
        printErr: function (t) { lines.push(t); }
      }).then(function (mod) {
        if (mine !== generation) return;
        mod.FS.writeFile("/program.vak", text);
        try { mod.callMain(["--आलेखः", "/program.vak"]); }
        catch (e) { lines.push(String(e && e.message ? e.message : e)); }
        var joined = lines.join("\n"), graph = null;
        try { graph = JSON.parse(joined); } catch (e) { graph = null; }
        if (graph && graph["कार्याणि"]) {
          render(o.pane, graph, { onLine: selectLine });
          o.status.textContent = "● जीवम् · live";
        } else {
          fail(o.pane, joined.split("\n")[0]);
          o.status.textContent = "○ पुरातनम् · stale";
        }
      }).catch(function (e) {
        fail(o.pane, "the engine failed to start: " + e);
      });
    }

    function schedule(delay) {
      clearTimeout(timer);
      timer = setTimeout(draw, delay);
    }

    function show(which) {
      visible = which === "graph";
      o.outBox.hidden = visible;
      o.pane.hidden = !visible;
      o.tabOut.setAttribute("aria-selected", String(!visible));
      o.tabGraph.setAttribute("aria-selected", String(visible));
      o.clear.hidden = visible;
      try { localStorage.setItem("vak-playground-tab", which); } catch (e) {}
      if (visible) schedule(0);
    }

    o.tabOut.addEventListener("click", function () { show("out"); });
    o.tabGraph.addEventListener("click", function () { show("graph"); });
    o.src.addEventListener("input", function () { schedule(380); });
    o.picker.addEventListener("change", function () { schedule(0); });
    // running a program shows its output, whichever tab was open
    o.run.addEventListener("click", function () { show("out"); }, true);
    o.check.addEventListener("click", function () { show("out"); }, true);

    var wanted = /(^|[#&])graph\b/.test(location.hash) ? "graph" : null;
    if (!wanted) { try { wanted = localStorage.getItem("vak-playground-tab"); } catch (e) {} }
    show(wanted === "graph" ? "graph" : "out");
  }

  return { render: render, fail: fail, attach: attach };
})();
