"use strict";

const helperUrl = "http://127.0.0.1:8787/linear";

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

async function activeTabPayload(tab) {
  const activeTab = tab || (await browser.tabs.query({ active: true, currentWindow: true }))[0];
  if (!activeTab) {
    throw new Error("No active tab.");
  }
  return {
    title: activeTab.title || "Untitled",
    url: activeTab.url || "",
  };
}

async function sendToLinear(tab) {
  try {
    const payload = await activeTabPayload(tab);
    const response = await fetch(helperUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (response.status === 501 && data.stub) {
      await notify("Linear stub", "Tab captured locally; token flow is not wired yet.");
      return;
    }
    if (!response.ok || !data.ok) {
      throw new Error(data.error || data.message || `Helper returned ${response.status}`);
    }

    await notify("Sent to Linear", payload.title);
  } catch (error) {
    await notify("Linear send failed", error.message);
  }
}

browser.browserAction.onClicked.addListener(sendToLinear);
browser.commands.onCommand.addListener((command) => {
  if (command === "send-tab-to-linear") {
    sendToLinear();
  }
});
