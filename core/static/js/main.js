// Network-DNS-Monitoring clone — client behaviour.
// Highlights the active dock item on load (in addition to server-side marking).
document.addEventListener("DOMContentLoaded", function () {
  var here = location.pathname.split("/").filter(Boolean)[0] || "";
  var item = document.querySelector('.dock-item[href="/' + here + '/"]');
  if (item) item.classList.add("active-js");
});
