(function () {
  function humanize(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diff = Math.floor((now - then) / 1000);
    if (diff < 60) return `${diff} seconds ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return `${Math.floor(diff / 86400)} days ago`;
  }

  function trimId(id) {
    return id.slice(-5);
  }

  // Format absolute timestamp as hh:mm:ss
  function formatTime(timestamp) {
    const d = new Date(timestamp);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${hh}:${mm}:${ss}`;
  }

  // async function updateRequests() {
  //   try {
  //     const res = await fetch("/api/requests");
  //     if (!res.ok) return;
  //     const data = await res.json();
  //     const ul = document.getElementById("requests-ul");
  //     if (!ul) return;
  //     ul.innerHTML = "";
  //     data.requests
  //       .filter((r) => r.request_type === "external")
  //       .forEach((req) => {
  //         const li = document.createElement("li");
  //         li.textContent = `ID: ${trimId(req.id)}, Floor: ${
  //           req.floor
  //         }, Direction: ${req.direction}, Time: ${formatTime(req.timestamp)}`;
  //         ul.appendChild(li);
  //       });
  //   } catch (err) {
  //     console.error("Failed to fetch requests", err);
  //   }
  // }

  document.addEventListener("DOMContentLoaded", () => {
    // updateRequests();
    // setInterval(updateRequests, 2000);
  });
})();
