const input = document.getElementById("query-input");
const askBtn = document.getElementById("ask-btn");
const statusText = document.getElementById("status-text");
const resultSection = document.getElementById("result-section");
const resultContent = document.getElementById("result-content");

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    input.value = chip.dataset.example;
    input.focus();
  });
});

askBtn.addEventListener("click", submitQuery);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitQuery();
});

async function submitQuery() {
  const query = input.value.trim();
  if (!query) {
    statusText.textContent = "Please describe your situation first.";
    return;
  }

  askBtn.disabled = true;
  statusText.textContent = "Searching relevant sections…";
  resultSection.hidden = true;

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    resultContent.innerHTML = renderAnswer(data.answer);
    resultSection.hidden = false;
    statusText.textContent = "";
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    statusText.textContent = "Error: " + err.message;
  } finally {
    askBtn.disabled = false;
  }
}

/**
 * Very small markdown-ish renderer for the specific patterns our
 * backend produces: ## headers, **bold**, numbered lists, bullet lists.
 */
function renderAnswer(text) {
  const lines = text.split("\n");
  let html = "";
  let inOl = false;
  let inUl = false;

  const closeLists = () => {
    if (inOl) { html += "</ol>"; inOl = false; }
    if (inUl) { html += "</ul>"; inUl = false; }
  };

  for (let raw of lines) {
    const line = raw.trim();

    if (line.startsWith("## ")) {
      closeLists();
      html += `<h3>${inlineFormat(line.slice(3))}</h3>`;
    } else if (/^\d+\.\s/.test(line)) {
      if (!inOl) { closeLists(); html += "<ol>"; inOl = true; }
      html += `<li>${inlineFormat(line.replace(/^\d+\.\s/, ""))}</li>`;
    } else if (line.startsWith("- ")) {
      if (!inUl) { closeLists(); html += "<ul>"; inUl = true; }
      html += `<li>${inlineFormat(line.slice(2))}</li>`;
    } else if (line.startsWith("_") && line.endsWith("_") && line.length > 1) {
      closeLists();
      html += `<p class="disclaimer">${inlineFormat(line.slice(1, -1))}</p>`;
    } else if (line === "") {
      closeLists();
    } else {
      closeLists();
      html += `<p>${inlineFormat(line)}</p>`;
    }
  }
  closeLists();
  return html || '<p class="no-match">No answer generated.</p>';
}

function inlineFormat(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, '<span class="law-cite">$1</span>');
}
