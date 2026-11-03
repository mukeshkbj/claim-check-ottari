# Claim Check for Firefox

Fact-check what you're reading without leaving the page. Firefox's sidebar shows each claim's verdict,
its top sources and a second opinion from a different open-weight model, all checked through Otari.

- **Right-click selected text** and choose **Check this claim with Claim Check**.
- **Right-click a link** (or anywhere on a page) to check the article it points to.
- **Or type in the sidebar**: paste a claim or a link and press **Check it**.
- After a check, **Draft a calm reply** writes a short, friendly reply with sources you could post under the
  original, and **Full report** opens the shareable report with every source and the agent trace.
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> (or the toolbar button) opens and closes the sidebar.

## Install (for testing)
1. Open `about:debugging#/runtime/this-firefox` in Firefox.
2. Click **Load Temporary Add-on...** and pick `manifest.json` in this folder (or `../claim-check-firefox.xpi`).
3. Select some text on any page, right-click, and choose **Check this claim with Claim Check**.

## Privacy
The extension sends only what you ask it to check (the text you select, the link or page address you
right-click, or what you type in the sidebar) to the Claim Check app, and only when you ask. It can't read
pages: its permissions are `contextMenus`, `storage` (to hand your selection to the sidebar) and access to the
Claim Check app's own address. Firefox shows this as website content and browsing activity being shared.
