# Claim Check for Firefox

Select any text on a page, right-click, and choose **Check this claim with Claim Check**. A new tab opens the
Claim Check app with your selection and starts the check: open-weight agents behind Otari pull out the claims,
search for sources and give a cited verdict. You can also right-click a link, or click the toolbar button.

## Install (for testing)
1. Open `about:debugging#/runtime/this-firefox` in Firefox.
2. Click **Load Temporary Add-on...** and pick `manifest.json` in this folder (or `claim-check-firefox.xpi`).
3. Select some text on any page, right-click, and choose **Check this claim with Claim Check**.

The extension sends only the text you select (or the link you right-click) to the Claim Check app, and only when
you choose the menu item. It has no access to pages otherwise: its only permission is `contextMenus`.
