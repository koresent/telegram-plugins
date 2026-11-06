# Chat Web Tabs

Custom web apps and pinned web tabs with persistent sessions for [exteraGram](https://github.com/exteraSquad/exteraGram) and compatible Telegram Android clients.

Embed web services (Vikunja, Notion, Jira, Linear, Grafana, GitHub, custom dashboards) directly into your Telegram groups and forum topics.

---

## Features

- **Seamless Topic Integration**: Custom web tabs are placed directly inside Telegram's existing vertical topics sidebar (and top horizontal pills), positioned neatly at the bottom right before "+ New Topic".
- **Native Telegram Styling**: Clean topic typography, theme colors, and selector ripples that look and feel 100% native.
- **Native Emoji Keyboard**: Opens Telegram's full native emoji picker (`EmojiView`) with category tabs, search, recent emojis, and all installed custom animated emoji packs.
- **Vector SVG Toolbar Controls**: Clean vector icons (`ic_ab_back`, `msg_retry`, `filled_link`, `ic_ab_close`) tinted to the active theme, without clunky header badges.
- **Persistent Sessions & Logins**: Full support for `CookieManager` and `DOM Storage` (`localStorage`/`sessionStorage`). Log in once to your self-hosted or cloud service (e.g. Vikunja, Kanban) and stay logged in.
- **Smart & Safe Page Resume**: Remembers the exact SPA board or task visited on dismissal, strictly validates against the base domain to prevent unexpected external redirects, and offers a 1-tap "Reset saved page" button in settings.
- **Clean Configuration**: Empty defaults out-of-the-box (no pre-filled user IDs), custom group title editing, and dynamic addition/removal of groups and tabs.
  - High-performance `BottomSheet` dialog opening directly inside the chat.
  - Toolbar with web app title, active domain, Back, Refresh, Open in Browser, and Close controls.
  - Animated horizontal progress bar.
  - Keyboard-friendly with proper soft input resizing for editing tasks and forms.
- **Dynamic Multi-Group Configuration**: Add unlimited chat groups and unlimited web tabs per group dynamically from the plugin settings page.

---

## Configuration

| Setting | Options / Description |
|---|---|
| **Display format** | *Tab strip under ActionBar*, *Buttons in ActionBar*, *Single button with popup menu* |
| **Show 🌐 globe badge** | Displays a subtle globe overlay to distinguish web tabs from native chat topics. |
| **Chat / Group ID** | Target chat ID (e.g. `-1002482353775` or `2482353775`). Matches both full and normalized formats. |
| **Tab Title** | Display name shown on the tab tile or menu (e.g. `Vikunja`, `Tasks`, `Dashboard`). |
| **Emoji** | Emoji icon displayed on the tile or action button (e.g. `📋`, `📚`, `📊`). |
| **URL Address** | Full URL of the web service (e.g. `https://vikunja.example.com`). |
| **Remember last page** | Toggle to resume on the last navigated URL upon reopening. |

---

## Installation

1. Download [`chat_web_tabs.plugin`](chat_web_tabs.plugin).
2. Open the file in **exteraGram** or send it to your Saved Messages and tap to install.
3. Open **Settings** > **Plugins** and enable **Chat Web Tabs**.
4. Configure your group ID and target web applications.

---

## Compatibility

- **Client**: exteraGram, AyuGram Android, or any client with the Python Plugins Engine.
- **Android**: Android 7.0+ (Nougat) through Android 15+.
