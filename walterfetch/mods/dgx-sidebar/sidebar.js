"use strict";

const helperUrl = "http://127.0.0.1:8787/dgx/summarize";
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const button = document.getElementById("summarize");

function setStatus(message) {
  statusEl.textContent = message;
}

async function activeTabSnapshot() {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    throw new Error("No active tab.");
  }

  const [snapshot] = await browser.tabs.executeScript(tab.id, {
    code: `(() => ({
      title: document.title,
      url: location.href,
      text: (document.body ? document.body.innerText : document.documentElement.innerText || "").slice(0, 60000)
    }))();`,
  });

  return {
    title: snapshot?.title || tab.title || "Untitled",
    url: snapshot?.url || tab.url || "",
    text: snapshot?.text || "",
  };
}

async function summarize() {
  button.disabled = true;
  summaryEl.textContent = "";
  setStatus("Reading active tab...");

  try {
    const snapshot = await activeTabSnapshot();
    if (!snapshot.text.trim()) {
      throw new Error("Active tab has no readable text.");
    }

    setStatus("Sending page text to local DGX helper...");
    const response = await fetch(helperUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(snapshot),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || data.message || `Helper returned ${response.status}`);
    }

    summaryEl.textContent = data.summary;
    setStatus(`Summary from ${data.model}.`);
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

button.addEventListener("click", summarize);
