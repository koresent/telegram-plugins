# Chat Web Tabs

Custom web apps and pinned web tabs with persistent sessions for [exteraGram](https://github.com/exteraSquad/exteraGram) and compatible Telegram Android clients.

Embed web services (Vikunja, Notion, Jira, Linear, Grafana, GitHub, custom dashboards) directly into your Telegram groups and forum topics.

---

## Features

- **Topic Integration**: Custom web tabs are placed directly inside Telegram's existing vertical topics sidebar (and top horizontal pills), positioned at the bottom before "+ New Topic".
- **Native Telegram Styling**: Topic typography, theme colors, and selector ripples that match the native UI.
- **Native Emoji Keyboard**: Opens Telegram's full emoji picker (`EmojiView`) with category tabs, search, recent emojis, and installed custom animated emoji packs.
- **Vector Toolbar Controls**: Vector icons (`ic_ab_back`, `msg_retry`, `filled_link`, `ic_ab_close`) tinted to the active theme.
- **Persistent Sessions**: Support for `CookieManager` and `DOM Storage` (`localStorage`/`sessionStorage`) to preserve logins across sessions.
- **Page Resume**: Remembers the last visited URL on dismissal with domain matching to prevent unexpected external redirects, plus a reset button in settings.
- **In-App Browser BottomSheet**:
  - Opens directly inside the chat with swipe-dismiss disabled during page scroll.
  - Toolbar with title, active domain, Back, Refresh, Open in Browser, and Close controls.
  - Progress bar for loading state.
  - Soft keyboard resizing for text input and forms.
- **Configuration**: Empty defaults out-of-the-box, custom group title editing, and dynamic addition or removal of groups and tabs.

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
