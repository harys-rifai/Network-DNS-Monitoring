(function () {
  "use strict";

  var NODE_RADIUS = 14;
  var LINK_DISTANCE = 120;
  var CHARGE_STRENGTH = -400;
  var CENTER_STRENGTH = 0.08;
  var FRICTION = 0.85;
  var REPULSE_STRENGTH = 05;

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
    if (window._topologyGraph) {
      window._topologyGraph.update(data);
    }
  }

  /* ------------------------------------------------------------------ *
   *  Minimal force-directed graph (vanilla JS, no external deps)
   * ------------------------------------------------------------------ */
  function ForceGraph(canvasId, opts) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;

    this.width = this.canvas.clientWidth;
    this.height = this.canvas.clientHeight;

    this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.svg.setAttribute("width", this.width);
    this.svg.setAttribute("height", this.height);
    this.svg.setAttribute("style", "position:absolute;top:0;left:0;width:100%;height:100%;");
    this.canvas.appendChild(this.svg);

    this.nodes = [];
    this.links = [];
    this._buildInitial(opts.initial);
    this._animate();
  }

  ForceGraph.prototype._buildInitial = function (data) {
    var self = this;
    var resolverNode = { id: "resolver", label: "Network-DNS-Monitoring", group: "resolver" };

    this.nodes = [resolverNode];
    this.links = [];

    var seenNames = {};
    var clients = data.clients || [];

    clients.forEach(function (c) {
      if (c.name && !seenNames[c.name]) {
        seenNames[c.name] = true;
        self.nodes.push({ id: c.name, label: c.name, group: "client", source: c.source });
        self.links.push({ source: c.name, target: "resolver", type: "query" });
      }
    });

    /* add upstream resolver node */
    var metrics = data.cache_metrics || {};
    if (Object.keys(metrics).length > 0) {
      this.nodes.push({ id: "upstream", label: "Upstream", group: "upstream" });
      this.links.push({ source: "upstream", target: "resolver", type: "upstream" });
    }

    this._position();
  };

  ForceGraph.prototype._position = function () {
    var cx = this.width / 2;
    var cy = this.height / 2;
    var r = Math.min(this.width, this.height) / 2 * 0.45;

    for (var i = 0; i < this.nodes.length; i++) {
      var node = this.nodes[i];
      if (!node.x) node.x = cx + (Math.random() - 0.5) * 100;
      if (!node.y) node.y = cy + (Math.random() - 0.5) * 100;
      if (!node.vx) node.vx = 0;
      if (!node.vy) node.vy = 0;
      if (!node.ax) node.ax = 0;
      if (!node.ay) node.ay = 0;
    }
  };

  ForceGraph.prototype.update = function (data) {
    this._latest = data;
    this._buildInitial(data);
  };

  ForceGraph.prototype._animate = function () {
    var self = this;
    function step() {
      self._tick();
      self._render();
      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  };

  ForceGraph.prototype._tick = function () {
    var i, j, node, link, dx, dy, dist, force, nx, ny;
    var k = 0.1;
    var nodes = this.nodes;
    var links = this.links;

    /* repulsion between nodes */
    for (i = 0; i < nodes.length; i++) {
      nodes[i].vx *= FRICTION;
      nodes[i].vy *= FRICTION;
    }
    for (i = 0; i < nodes.length; i++) {
      for (j = i + 1; j < nodes.length; j++) {
        var a = nodes[i];
        var b = nodes[j];
        dx = b.x - a.x;
        dy = b.y - a.y;
        dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        force = REPULSE_STRENGTH / (dist * dist);
        dx /= dist;
        dy /= dist;
        a.vx -= force * dx;
        a.vy -= force * dy;
        b.vx += force * dx;
        b.vy += force * dy;
      }
    }

    /* spring attraction along links */
    for (i = 0; i < links.length; i++) {
      link = links[i];
      var source = typeof link.source === "object" ? link.source : this._findNodeById(link.source);
      var target = typeof link.target === "object" ? link.target : this._findNodeById(link.target);
      if (!source || !target) continue;
      dx = target.x - source.x;
      dy = target.y - source.y;
      dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      force = k * (dist - LINK_DISTANCE);
      dx /= dist;
      dy /= dist;
      source.vx += force * dx;
      source.vy += force * dy;
      target.vx -= force * dx;
      target.vy -= force * dy;
    }

    /* center gravity */
    var cx = this.width / 2;
    var cy = this.height / 2;
    for (i = 0; i < nodes.length; i++) {
      nodes[i].x += nodes[i].vx;
      nodes[i].y += nodes[i].vy;
      /* bounds */
      if (nodes[i].x < NODE_RADIUS) { nodes[i].x = NODE_RADIUS; nodes[i].vx *= -0.5; }
      if (nodes[i].x > this.width - NODE_RADIUS) { nodes[i].x = this.width - NODE_RADIUS; nodes[i].vx *= -0.5; }
      if (nodes[i].y < NODE_RADIUS) { nodes[i].y = NODE_RADIUS; nodes[i].vy *= -0.5; }
      if (nodes[i].y > this.height - NODE_RADIUS) { nodes[i].y = this.height - NODE_RADIUS; nodes[i].vy *= -0.5; }
    }
  };

  ForceGraph.prototype._findNodeById = function (id) {
    for (var i = 0; i < this.nodes.length; i++) {
      if (this.nodes[i].id === id) return this.nodes[i];
    }
    return null;
  };

  ForceGraph.prototype._render = function () {
    /* clear */
    while (this.svg.firstChild) this.svg.removeChild(this.svg.firstChild);

    /* draw links */
    for (var i = 0; i < this.links.length; i++) {
      var link = this.links[i];
      var source = this._findNodeById(typeof link.source === "string" ? link.source : link.source.id);
      var target = this._findNodeById(typeof link.target === "string" ? link.target : link.target.id);
      if (!source || !target) continue;

      var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", source.x);
      line.setAttribute("y1", source.y);
      line.setAttribute("x2", target.x);
      line.setAttribute("y2", target.y);
      line.setAttribute("stroke", link.type === "upstream" ? "#0a84ff" : "#8e8e93");
      line.setAttribute("stroke-width", link.type === "upstream" ? 2.5 : 1.5);
      line.setAttribute("stroke-dasharray", link.type === "upstream" ? "6,3" : "0");
      this.svg.appendChild(line);
    }

    /* draw nodes */
    for (var j = 0; j < this.nodes.length; j++) {
      var node = this.nodes[j];
      var color = node.group === "resolver" ? "#30b05a" :
                  node.group === "upstream" ? "#0a84ff" : "#ff9f0a";

      var circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", node.x);
      circle.setAttribute("cy", node.y);
      circle.setAttribute("r", node.group === "resolver" ? NODE_RADIUS + 4 : NODE_RADIUS);
      circle.setAttribute("fill", color);
      circle.setAttribute("stroke", "#fff");
      circle.setAttribute("stroke-width", "2");
      circle.style.cursor = "pointer";
      this.svg.appendChild(circle);

      /* label */
      var label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", node.x);
      label.setAttribute("y", node.y + NODE_RADIUS + 16);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", "10");
      label.setAttribute("fill", "var(--muted)");
      label.textContent = node.label;
      this.svg.appendChild(label);
    }
  };

  /* ------------------------------------------------------------------ *
   *  Bootstrap
   * ------------------------------------------------------------------ */
  function init(initialData) {
    var container = document.getElementById("topology-graph");
    if (!container) return;

    var graph = new ForceGraph("topology-graph", { initial: initialData });
    window._topologyGraph = graph;

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
  }

  /* initialise with server-rendered data */
  document.addEventListener("DOMContentLoaded", function () {
    {% if initial_data %}
    init({{ initial_data|tojson }});
    {% endif %}
  });
})();
