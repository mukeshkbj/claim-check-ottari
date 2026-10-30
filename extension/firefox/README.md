# Claim Check for Firefox

Select a claim on any page (or right-click a link to an article), right-click, and choose
**Check this claim with Claim Check**. Firefox's sidebar opens next to the page and the verdicts stream in:
open-weight agents behind Otari pull out the claims, search for sources, get a second opinion from a
different model family, and give a cited verdict. Each check ends with a link to the full report.
The toolbar button opens or closes the sidebar.

## Install (for testing)
1. Open `about:debugging#/runtime/this-firefox` in Firefox.
2. Click **Load Temporary Add-on...** and pick `manifest.json` in this folder (or `../claim-check-firefox.xpi`).
3. Select some text on any page, right-click, and choose **Check this claim with Claim Check**.

## Privacy
The extension sends only the text you select (or the link you right-click) to the Claim Check app, and only
when you choose the menu item. It can't read pages: its permissions are `contextMenus`, `storage` (to hand the
selection to the sidebar) and access to the Claim Check app's own address.
