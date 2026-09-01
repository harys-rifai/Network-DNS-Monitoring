(function () {
  "use strict";

  function fmtPct(h, m) {
    h = h || 0;
    m = m || 0;
    var total = h + m;
    if (total === 0) return "0.0";
    return ((h / total) * 100).toFixed(1);
  }

  function updateView(data) {
    if (data.type === "ping") return;
    var cc = document.getElementById("client-count");
    var hr = document.getElementById("hit-rate");
    if (cc) cc.textContent = data.client_count || 0;
    if (hr) {
      var s = data.cache_stats || {};
      hr.textContent = fmtPct(s.hit, s.miss) + "%";
    }
  }

  var src = new EventSource("{% url 'topology_stream' %}");
  src.onmessage = function (event) {
    try {
      var data = JSON.parse(event.data);
      updateView(data);
    } catch (e) {
      /* ignore non-JSON events */
    }
  };
  src.onerror = function () {
    /* daemon may be down; SSE auto-reconnects */
  };
})();
