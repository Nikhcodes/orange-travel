/*!
 * Sabi – de reisadviseur van Orange Travel (chatwidget).
 *
 * Inbouwen op elke website met één regel (FR-20, FR-21):
 *   <script src="https://JOUW-SERVER/widget/sabi.js" defer></script>
 *
 * Optioneel:  data-api="https://andere-server"   (standaard: de server waar dit script vandaan komt)
 *             data-open="true"                    (venster meteen openen)
 *
 * De widget draait in een Shadow DOM, zodat de stijl van de website en de widget elkaar niet raken.
 * Er wordt niets opgeslagen behalve een willekeurig sessie-id in sessionStorage.
 */
(function () {
  "use strict";
  if (window.__orangeSabiLoaded) return;
  window.__orangeSabiLoaded = true;

  var script = document.currentScript || document.querySelector('script[src*="sabi.js"]');
  var API = ((script && script.dataset.api) || new URL(script ? script.src : location.href).origin).replace(/\/$/, "");
  var AUTO_OPEN = script && script.dataset.open === "true";
  var FACTS = [
    "Wist je dat? Rotshaan-mannetjes dansen samen op een open plek in het bos om indruk te maken op de vrouwtjes. 💃",
    "Vrouwtjesrotshanen plakken hun nest van modder tegen rotswanden. Vandaar de naam rotshaan! 🪨",
    "Rotshanen leven in het regenwoud van de Guyana's, ook in Suriname. 🌿",
    "Sabi betekent 'weten' in het Sranantongo. 🧠",
  ];

  function store(key, value) {
    try { if (value === undefined) return sessionStorage.getItem(key); sessionStorage.setItem(key, value); } catch (e) { return null; }
  }
  function esc(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function md(text) { // safe mini-markdown: escape first, then **bold**, *italic*, newlines
    return esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>").replace(/\n/g, "<br>");
  }
  // Mask obvious personal data BEFORE it leaves the browser (FR-19, NFR-07). The server checks again.
  var PII = [
    ["e-mailadres", /[\w.+-]+@[\w-]+\.[\w.-]+/g],
    ["creditcardnummer", /\b(?:\d[ -]?){13,19}\b/g],
    ["telefoonnummer", /(?:\+|00)\d[\d\s-]{6,14}\d|\b0\d{9}\b|\b0?[678]\d{6}\b/g],
  ];
  function mask(text) {
    var found = [];
    PII.forEach(function (p) {
      text = text.replace(p[1], function () { if (found.indexOf(p[0]) < 0) found.push(p[0]); return "[verwijderd]"; });
    });
    return { text: text, found: found };
  }
  function abs(url) { return /^https?:/.test(url) ? url : API + url; }
  function safeUrl(url) { return /^https:\/\/(www\.)?orangesuriname\.com\//.test(url) ? url : "#"; }
  function el(tag, cls, html) { var n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; }

  Promise.all([
    fetch(API + "/widget/sabi.css").then(function (r) { return r.text(); }),
    fetch(API + "/widget/sabi.svg").then(function (r) { return r.text(); }),
  ]).then(function (res) { build(res[0], res[1]); }).catch(function (e) { console.warn("[Sabi] kon niet laden:", e); });

  function build(css, svg) {
    var host = document.createElement("div");
    host.id = "orange-travel-sabi";
    document.body.appendChild(host);
    var root = host.attachShadow({ mode: "open" });
    var sabi = function (cls) { return '<span class="sabi ' + (cls || "") + '" aria-hidden="true">' + svg + "</span>"; };

    root.innerHTML = "<style>" + css + "</style>" +
      '<div class="ot" part="widget">' +
      '  <div class="teaser" hidden><button class="x" aria-label="Sluiten">×</button>Hoi! Zoek je een tour in Suriname? 🧡<small>Ik help je in een paar vragen.</small></div>' +
      '  <button class="launcher" aria-label="Open de reisadviseur Sabi" aria-expanded="false">' + sabi() + "</button>" +
      '  <section class="panel" role="dialog" aria-label="Sabi, reisadviseur van Orange Travel" hidden>' +
      '    <header class="head">' +
      '      <div class="avatar" title="Klik op Sabi!" role="button" tabindex="0" aria-label="Weetje van Sabi">' + sabi() + "</div>" +
      '      <div class="who"><b>Sabi · Orange Travel</b><span>Je reisadviseur · reageert direct</span></div>' +
      '      <button class="icon-btn restart" aria-label="Opnieuw beginnen" title="Opnieuw beginnen">↺</button>' +
      '      <button class="icon-btn close" aria-label="Sluiten" title="Sluiten">✕</button>' +
      "    </header>" +
      '    <div class="log" aria-live="polite"></div>' +
      '    <div class="chips"></div>' +
      '    <form class="compose"><input type="text" maxlength="500" autocomplete="off" aria-label="Typ je bericht" placeholder="Typ je wens of vraag…"><button class="send" type="submit" aria-label="Verstuur">➤</button></form>' +
      '    <div class="foot">🔒 Deel geen persoonsgegevens · Advies, geen boeking</div>' +
      "  </section>" +
      "</div>";

    var $ = function (s) { return root.querySelector(s); };
    var wrap = $(".ot"), launcher = $(".launcher"), panel = $(".panel"), log = $(".log"), chips = $(".chips");
    var input = $(".compose input"), sendBtn = $(".send"), avatar = $(".avatar"), teaser = $(".teaser");
    var sessionId = store("ot-sabi-session");
    var started = false, busy = false, lastRole = null, factIndex = 0;

    function setMood(mood) {
      avatar.className = "avatar mood-" + (mood || "neutral");
      void avatar.offsetWidth; // restart the CSS animation
    }
    function scroll() { log.scrollTop = log.scrollHeight; }
    function row(role, node) {
      var r = el("div", "row " + role + (role === "bot" && lastRole === "bot" ? " cont" : ""));
      if (role === "bot") r.appendChild(el("div", "mini", sabi()));
      r.appendChild(node);
      log.appendChild(r);
      lastRole = role;
      scroll();
      return r;
    }
    function attach(node) { log.appendChild(node); lastRole = "bot-block"; scroll(); }

    function renderCard(card, variant, index) {
      var classes = "card" + (card.badges.some(function (b) { return b.kind === "best"; }) ? " best" : "") + (variant === "over_budget" ? " over" : "");
      var c = el("article", classes);
      c.style.animationDelay = (index * 0.08) + "s";
      var badges = card.badges.map(function (b) { return '<span class="badge ' + esc(b.kind) + '">' + esc(b.label) + "</span>"; }).join("");
      var reasons = card.reasons.map(function (r) { return '<li class="' + esc(r.kind) + '">' + esc(r.text) + "</li>"; }).join("");
      c.innerHTML =
        '<div class="img"><img loading="lazy" alt="" src="' + esc(abs(card.image)) + '"><div class="badges">' + badges + "</div></div>" +
        '<div class="body">' +
        "<h4>" + esc(card.name) + "</h4>" +
        '<div class="meta">' + esc(card.emoji + " " + card.type + " · " + card.duration) + "</div>" +
        '<div class="price"><strong>' + esc(card.price) + "</strong><span>p.p. (vanaf)</span></div>" +
        (card.total ? '<div class="total">' + esc(card.total) + " totaal voor " + esc(card.travelers) + " personen</div>" : "") +
        (card.remaining ? '<span class="left">Je houdt ' + esc(card.remaining) + " p.p. over</span>" : "") +
        '<ul class="reasons">' + reasons + "</ul>" +
        (card.note ? '<div class="note">' + esc(card.note) + "</div>" : "") +
        '<div class="actions"><a class="btn primary" target="_blank" rel="noopener" href="' + esc(safeUrl(card.url)) + '">Bekijk tour ↗</a>' +
        (variant === "advice" ? '<button class="btn why" type="button">Waarom?</button>' : "") + "</div></div>";
      var why = c.querySelector(".why");
      if (why) why.addEventListener("click", function () { send({ payload: "why:" + card.rank, label: "Waarom " + card.name + "?" }); });
      return c;
    }

    function render(messages) {
      messages.forEach(function (m) {
        if (m.type === "text") {
          row("bot", el("div", "bubble " + (m.tone || ""), md(m.text)));
        } else if (m.type === "cards") {
          var box = el("div", "cards");
          m.cards.forEach(function (card, i) { box.appendChild(renderCard(card, m.variant, i)); });
          attach(box);
        } else if (m.type === "compare") {
          var head = "<tr><th></th>" + m.headers.map(function (h) { return "<th>" + esc(h) + "</th>"; }).join("") + "</tr>";
          var body = m.rows.map(function (r) {
            return "<tr><td>" + esc(r.label) + "</td>" + r.values.map(function (v) { return "<td>" + esc(v) + "</td>"; }).join("") + "</tr>";
          }).join("");
          attach(el("div", "table-wrap", "<table>" + head + body + "</table>"));
        } else if (m.type === "list") {
          attach(el("div", "list", m.items.map(function (it) {
            return '<div class="item"><b>' + esc(it.title) + "</b>" + esc(it.text) + (it.example ? "<em>" + esc(it.example) + "</em>" : "") + "</div>";
          }).join("")));
        } else if (m.type === "links") {
          attach(el("div", "links", m.links.map(function (l) {
            return '<a class="link" target="_blank" rel="noopener" href="' + esc(safeUrl(l.url)) + '">' + esc(l.label) + "</a>";
          }).join("")));
        }
      });
    }

    function renderChips(list) {
      chips.innerHTML = "";
      (list || []).forEach(function (q, i) {
        var b = el("button", "chip", esc(q.label));
        b.type = "button";
        b.style.animationDelay = (i * 0.04) + "s";
        b.addEventListener("click", function () { send({ payload: q.payload, label: q.label }); });
        chips.appendChild(b);
      });
    }

    function send(opts) {
      if (busy) return;
      var body = { session_id: sessionId };
      if (opts.event) body.event = opts.event;
      if (opts.payload) body.payload = opts.payload;
      if (opts.text) { var masked = mask(opts.text); opts.text = masked.text; body.message = masked.text; if (masked.found.length) body.redacted = masked.found; }
      if (opts.text || opts.label) row("user", el("div", "bubble", esc(opts.text || opts.label)));
      renderChips([]);
      busy = true; sendBtn.disabled = true; setMood("think");
      var typing = row("bot", el("div", "bubble typing", "<i></i><i></i><i></i>"));
      var started_at = Date.now();
      fetch(API + "/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) {
          var wait = Math.max(0, 550 - (Date.now() - started_at)); // feels more natural than an instant reply
          setTimeout(function () {
            typing.remove(); lastRole = "user";
            sessionId = data.session_id; store("ot-sabi-session", sessionId);
            render(data.messages); renderChips(data.quick_replies); setMood(data.mood);
            done();
          }, wait);
        })
        .catch(function () {
          typing.remove(); lastRole = "user";
          row("bot", el("div", "bubble warning", "Oeps, ik kan de server even niet bereiken. Probeer het zo nog eens."));
          renderChips([{ label: "Opnieuw proberen", payload: "intent:open" }]);
          setMood("sad"); done();
        });
      function done() { busy = false; sendBtn.disabled = false; }
    }

    function open() {
      wrap.classList.add("open"); panel.hidden = false; teaser.hidden = true;
      launcher.setAttribute("aria-expanded", "true");
      var ping = launcher.querySelector(".ping"); if (ping) ping.remove();
      if (!started) { started = true; send({ event: "open" }); }
      setTimeout(function () { input.focus(); }, 250);
    }
    function close() {
      wrap.classList.remove("open"); panel.hidden = true; launcher.setAttribute("aria-expanded", "false"); launcher.focus();
    }

    launcher.addEventListener("click", open);
    $(".close").addEventListener("click", close);
    $(".restart").addEventListener("click", function () { send({ payload: "intent:restart", label: "Opnieuw beginnen" }); });
    root.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) close(); });
    $(".compose").addEventListener("submit", function (e) {
      e.preventDefault();
      var text = input.value.trim();
      if (!text) return;
      input.value = "";
      send({ text: text });
    });
    function fact() {
      var old = root.querySelector(".fact"); if (old) old.remove();
      avatar.classList.add("spin");
      var bubble = el("div", "fact", esc(FACTS[factIndex++ % FACTS.length]));
      panel.appendChild(bubble);
      setTimeout(function () { avatar.classList.remove("spin"); }, 900);
      setTimeout(function () { bubble.remove(); }, 5200);
    }
    avatar.addEventListener("click", fact);
    avatar.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fact(); } });

    // A friendly nudge after a few seconds (once per browser session).
    if (!store("ot-sabi-teased")) {
      setTimeout(function () {
        if (!panel.hidden) return;
        teaser.hidden = false; launcher.appendChild(el("span", "ping")); launcher.classList.add("nudge");
        store("ot-sabi-teased", "1");
      }, 3500);
    }
    teaser.addEventListener("click", function (e) { if (!e.target.classList.contains("x")) open(); });
    teaser.querySelector(".x").addEventListener("click", function (e) { e.stopPropagation(); teaser.hidden = true; });
    setInterval(function () { // little idle nudge every 20 s while closed
      if (!panel.hidden) return;
      launcher.classList.remove("nudge"); void launcher.offsetWidth; launcher.classList.add("nudge");
    }, 20000);

    if (AUTO_OPEN) open();
    window.OrangeSabi = { open: open, close: close };
  }
})();
