// WalterFetch Zen profile preferences.
// Zen keys verified in this repo against prefs/zen/*.yaml and src/zen modules
// for the Firefox 151 / Zen 1.20.1b base.

user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Horizontal tabs on top (Chrome/Comet-style), not Zen's vertical sidebar.
user_pref("zen.tabs.vertical", false);
user_pref("zen.view.use-single-toolbar", false);

// Zen compact mode: OFF by default. Enabling it at startup with hide-tabbar
// hides the sidebar + nav and looks like a chrome-less full-screen window.
// Leave compact to the user to toggle (Ctrl+Cmd+C); do not force it on.
user_pref("zen.view.compact.enable-at-startup", false);
user_pref("zen.view.compact.hide-tabbar", false);
user_pref("zen.view.compact.hide-toolbar", false);

// Zen split view.
user_pref("zen.splitView.enable-tab-drop", true);
user_pref("zen.splitView.enable-tab-click-split", true);
user_pref("zen.splitView.enable-drag-over-split", true);

// Containers are core to the six-client workspace model.
user_pref("privacy.userContext.enabled", true);
user_pref("privacy.userContext.ui.enabled", true);

// First-run and update noise.
user_pref("zen.welcome-screen.seen", true);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");

// Blank new tab + home (Mike's pick: minimal, no distraction page). Session/
// workspace restore is left untouched.
user_pref("browser.newtabpage.enabled", false);
user_pref("browser.startup.homepage", "about:blank");

// Dense, dark, ops-oriented defaults.
user_pref("browser.uidensity", 0);
user_pref("browser.tabs.hoverPreview.enabled", false);
user_pref("browser.download.autohideButton", false);
user_pref("ui.systemUsesDarkTheme", 1);

// Keep the bookmark bar visible.
user_pref("browser.toolbars.bookmarks.visibility", "always");
