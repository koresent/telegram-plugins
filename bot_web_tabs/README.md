# Bot Web Tabs

Custom web app buttons with persistent sessions for [exteraGram](https://github.com/exteraSquad/exteraGram) and compatible Telegram Android clients.

Add a native WebApp button to any Telegram bot by its ID or username, even if the bot developer did not configure one via BotFather.

---

## Features

- **Native Bot Menu Button**: Injects Telegram's native input bar menu button (`BotCommandsMenuView`) with the official animated webview icon and custom button text (e.g. "Open App").
- **Bot Targeting**: Configure bots by numeric Bot ID (e.g. `772433176`) or username (e.g. `@newreleasesiobot`).
- **Persistent Sessions**: Support for `CookieManager` and `DOM Storage` (`localStorage`/`sessionStorage`) to preserve logins across restarts.
- **Page Resume**: Remembers the last visited page on that domain upon reopening, with domain validation to avoid external redirects and a reset button in settings.
- **In-App Browser Bottom Sheet**:
  - Opens directly inside the chat with swipe-dismiss disabled during page scroll.
  - Header toolbar with bot name, active domain subtitle, and action buttons: **Back**, **Reload**, **Open in External Browser**, and **Close**.
  - Integrated loading progress bar.
  - Soft keyboard support for text inputs and forms.
- **Multi-Bot Configuration**: Add and configure multiple bots directly from the plugin settings.

---

## Configuration

| Setting | Description |
|---|---|
| **Bot title** | Display name shown in the settings and web view header (e.g. `NewReleases`). |
| **Bot ID** | Numeric user ID (e.g. `772433176`) or bot username (e.g. `@newreleasesiobot`). |
| **Button text** | Label displayed on the native Telegram menu button in chat (e.g. `Open App`). |
| **URL** | Full web address to open (e.g. `https://newreleases.io`). |
| **Remember last open page** | Toggle to automatically resume on the last visited page on that domain upon reopening. |

---

## Example Bots

- **NewReleases**: `@newreleasesiobot` (ID: `772433176`) → `https://newreleases.io`
- Reference bot with native button: `@recall_personal_bot` (ID: `8651310725`)

---

## Installation

1. Download [`bot_web_tabs.plugin`](bot_web_tabs.plugin).
2. Open the file in **exteraGram** or send it to your Saved Messages and tap to install.
3. Open **Settings** > **Plugins** and enable **Bot Web Tabs**.
4. Configure your bot ID and target URL in plugin settings.

---

## Compatibility

- **Client**: exteraGram 12.5.1+ or any client with the Python Plugins Engine (SDK >= 1.4.4.3).
- **Android**: Android 7.0+ (Nougat) through Android 15+.
