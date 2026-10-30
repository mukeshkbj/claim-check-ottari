// Claim Check for Firefox: send the selected text (or a link) to the Claim Check web app.
const APP = "https://claim-check-tr4f.onrender.com/";
const MAX = 4000;

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({ id: "cc-selection", title: "Check this claim with Claim Check", contexts: ["selection"] });
  browser.contextMenus.create({ id: "cc-link", title: "Check this link with Claim Check", contexts: ["link"] });
});

function openCheck(text) {
  const url = text ? `${APP}?q=${encodeURIComponent(text.trim().slice(0, MAX))}` : APP;
  browser.tabs.create({ url });
}

browser.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId === "cc-selection") openCheck(info.selectionText);
  if (info.menuItemId === "cc-link") openCheck(`Check the claims made at this link: ${info.linkUrl}`);
});

browser.action.onClicked.addListener(() => openCheck(""));
