"use strict";

const helperUrl = "http://127.0.0.1:8787/clip";

browser.contextMenus.create({
  id: "clip-to-research",
  title: "Clip selection to Research",
  contexts: ["selection", "page"],
});

async function notify(title, message) {
  try {
    await browser.notifications.create({
      type: "basic",
      title,
      message,
    });
  } catch (_error) {
    console.log(`${title}: ${message}`);
  }
}

async function readSelection(tabId) {
  const [snapshot] = await browser.tabs.executeScript(tabId, {
    code: `(() => ({
      title: document.title,
      url: location.href,
      selection: String(window.getSelection ? window.getSelection() : "").trim()
    }))();`,
  });
  return snapshot;
}

async function clipActive(tab) {
  try {
    const activeTab = tab || (await browser.tabs.query({ active: true, currentWindow: true }))[0];
    if (!activeTab || !activeTab.id) {
      throw new Error("No active tab.");
    }

    const snapshot = await readSelection(activeTab.id);
    if (!snapshot.selection) {
      throw new Error("No text selected.");
    }

    const response = await fetch(helperUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(snapshot),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || data.message || `Helper returned ${response.status}`);
    }

    await notify("Clipped to Research", data.path);
  } catch (error) {
    await notify("Clip failed", error.message);
  }
}

browser.browserAction.onClicked.addListener(clipActive);
browser.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "clip-to-research") {
    clipActive(tab);
  }
});
browser.commands.onCommand.addListener((command) => {
  if (command === "clip-selection") {
    clipActive();
  }
});
