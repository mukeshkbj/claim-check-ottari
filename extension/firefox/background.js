// Claim Check for Firefox: right-click a claim, a link or a page, and the check runs in the sidebar next to it.
const MAX = 4000;

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({ id: "cc-selection", title: "Check this claim with Claim Check", contexts: ["selection"] });
  browser.contextMenus.create({ id: "cc-link", title: "Check this link with Claim Check", contexts: ["link"] });
  browser.contextMenus.create({ id: "cc-page", title: "Check this page with Claim Check", contexts: ["page"] });
});

browser.contextMenus.onClicked.addListener((info) => {
  // sidebarAction.open() must be the first thing called in the click handler (it needs the user gesture)
  browser.sidebarAction.open();
  const isWeb = (u) => /^https?:\/\//i.test(u || "");
  let pending;
  if (info.menuItemId === "cc-selection") {
    const text = (info.selectionText || "").trim();
    if (text) pending = { text: text.slice(0, MAX) };
  } else {
    const url = info.menuItemId === "cc-link" ? info.linkUrl : info.pageUrl;
    pending = isWeb(url) ? { text: url } : { error: "Claim Check can only read ordinary web pages (http or https)." };
  }
  if (pending) browser.storage.local.set({ pending: { ...pending, ts: Date.now() } });
});

browser.action.onClicked.addListener(() => browser.sidebarAction.toggle());
