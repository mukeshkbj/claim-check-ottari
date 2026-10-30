// Claim Check for Firefox: right-click a claim or a link and the check runs in the sidebar, next to the page.
const MAX = 4000;

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({ id: "cc-selection", title: "Check this claim with Claim Check", contexts: ["selection"] });
  browser.contextMenus.create({ id: "cc-link", title: "Check this link with Claim Check", contexts: ["link"] });
});

browser.contextMenus.onClicked.addListener((info) => {
  // sidebarAction.open() must be the first thing called in the click handler (it needs the user gesture)
  browser.sidebarAction.open();
  const text = info.menuItemId === "cc-link" ? info.linkUrl : (info.selectionText || "").trim();
  if (text) browser.storage.local.set({ pending: { text: text.slice(0, MAX), ts: Date.now() } });
});

browser.action.onClicked.addListener(() => browser.sidebarAction.toggle());
