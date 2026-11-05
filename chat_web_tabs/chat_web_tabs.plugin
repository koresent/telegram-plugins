# -*- coding: utf-8 -*-
"""
Chat Web Tabs for exteraGram
Custom web apps and pinned web tabs with persistent sessions for Telegram chats.
"""

import json
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from android.content import Context, Intent
from android.graphics import Color, Typeface
from android.graphics.drawable import GradientDrawable
from android.net import Uri
from android.util import TypedValue
from android.view import Gravity, View, ViewGroup
from android.webkit import (
    CookieManager,
    WebChromeClient,
    WebSettings,
    WebView,
    WebViewClient,
)
from android.widget import (
    FrameLayout,
    HorizontalScrollView,
    ImageView,
    LinearLayout,
    ProgressBar,
    TextView,
)
from java import dynamic_proxy, jclass
from org.telegram.messenger import AndroidUtilities, LocaleController
from org.telegram.ui.ActionBar import (
    ActionBar,
    ActionBarMenu,
    ActionBarMenuItem,
    BottomSheet,
    Theme,
)

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MethodHook
from ui.settings import Custom, Divider, Header, Input, Selector, Switch, Text

__id__ = "chat_web_tabs"
__name__ = "Chat Web Tabs"
__description__ = "Custom web apps and pinned web tabs with persistent sessions for Telegram chats"
__author__ = "@koresent"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__category__ = "general"

TAG_WEB_TABS_CONTAINER = "chat_web_tabs_container"

DEFAULT_CONFIG = [
    {
        "chat_id": "-1002482353775",
        "title": "Личные заметки",
        "tabs": [
            {
                "id": "tab_1",
                "title": "Vikunja",
                "emoji": "📋",
                "url": "https://vikunja.example.com",
                "remember_last_page": True,
                "last_url": "",
            }
        ],
    }
]


def russian() -> bool:
    try:
        return str(LocaleController.getInstance().getCurrentLocale().getLanguage()).startswith("ru")
    except Exception:
        return True


def tr(ru_text: str, en_text: str) -> str:
    return ru_text if russian() else en_text


def dp(value: float) -> int:
    return int(AndroidUtilities.dp(value))


def normalize_chat_id(val: Any) -> str:
    s = str(val).strip()
    if s.startswith("-100"):
        return s[4:]
    if s.startswith("-"):
        return s[1:]
    return s


def matches_chat_id(configured: Any, actual: Any) -> bool:
    c_str = str(configured).strip()
    a_str = str(actual).strip()
    if c_str == a_str:
        return True
    return normalize_chat_id(c_str) == normalize_chat_id(a_str)


from extera_utils.classes import Base, java_subclass, joverload

class OnClickListenerProxy(dynamic_proxy(View.OnClickListener)):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def onClick(self, view):
        try:
            self.callback(view)
        except Exception:
            pass


@java_subclass(WebChromeClient)
class CustomChromeClient(Base):
    @joverload("onProgressChanged", ["android.webkit.WebView", "int"])
    def on_progress_changed(self, view, progress):
        try:
            cb = getattr(self, "on_progress", None)
            if cb:
                cb(int(progress))
        except Exception:
            pass


@java_subclass(WebViewClient)
class CustomWebClient(Base):
    @joverload("onPageFinished", ["android.webkit.WebView", "java.lang.String"])
    def on_page_finished(self, view, url):
        try:
            cb = getattr(self, "on_finish", None)
            if cb:
                cb(view, str(url) if url else "")
        except Exception:
            pass

    @joverload("shouldOverrideUrlLoading", ["android.webkit.WebView", "java.lang.String"])
    def should_override_string(self, view, url):
        return self._handle_url(view, str(url) if url else "")

    @joverload("shouldOverrideUrlLoading", ["android.webkit.WebView", "android.webkit.WebResourceRequest"])
    def should_override_request(self, view, request):
        try:
            url_str = str(request.getUrl()) if request else ""
            return self._handle_url(view, url_str)
        except Exception:
            return False

    def _handle_url(self, view, url_str: str) -> bool:
        if url_str.startswith("http://") or url_str.startswith("https://"):
            return False
        try:
            context = view.getContext()
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url_str))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            return True
        except Exception:
            return False


class ChatViewCreateHook(MethodHook):
    def __init__(self, plugin: "ChatWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            fragment = param.thisObject
            root_view = param.getResult()
            if root_view is None:
                return

            dialog_id = self.plugin.get_fragment_dialog_id(fragment)
            if dialog_id is None:
                return

            group_config = self.plugin.find_group_config(dialog_id)
            if group_config and group_config.get("tabs"):
                self.plugin.attach_tabs_ui(fragment, root_view, group_config)
        except Exception as e:
            self.plugin.log(f"ChatViewCreateHook error: {e}")


class ChatWebTabsPlugin(BasePlugin):
    def log(self, text: str):
        try:
            self.logger.info(str(text))
        except Exception:
            try:
                super().log(str(text))
            except Exception:
                pass

    def __init__(self):
        super().__init__()
        self.is_active = False
        self._hook_objects = []
        self._groups: List[Dict[str, Any]] = []
        self._global_display_mode: int = 0  # 0: Tab strip under ActionBar, 1: Buttons in ActionBar, 2: Popup in ActionBar
        self._show_globe_badge: bool = True

    def on_plugin_load(self):
        self.is_active = True
        self.load_config()
        self._install_hooks()
        self.log("ChatWebTabs loaded successfully")

    def on_plugin_unload(self):
        self.is_active = False
        for unhook in self._hook_objects:
            try:
                self.unhook_method(unhook)
            except Exception:
                pass
        self._hook_objects.clear()
        self.log("ChatWebTabs unloaded")

    def _install_hooks(self):
        Class_cls = jclass("java.lang.Class")
        Context_cls = Class_cls.forName("android.content.Context")
        hook = ChatViewCreateHook(self)

        for class_name in ("org.telegram.ui.ChatActivity", "org.telegram.ui.TopicsFragment"):
            try:
                target_cls = Class_cls.forName(class_name)
                create_view_method = target_cls.getDeclaredMethod("createView", Context_cls)
                create_view_method.setAccessible(True)
                unhook = self.hook_method(create_view_method, hook)
                if unhook:
                    self._hook_objects.append(unhook)
                    self.log(f"Hooked createView on {class_name}")
            except Exception as e:
                self.log(f"Error hooking createView on {class_name}: {e}")

    def load_config(self):
        try:
            raw = self.get_setting("groups_config", None)
            if raw and isinstance(raw, str):
                self._groups = json.loads(raw)
            elif raw and isinstance(raw, list):
                self._groups = raw
            else:
                self._groups = [dict(g) for g in DEFAULT_CONFIG]
        except Exception as e:
            self.log(f"Error loading groups config: {e}")
            self._groups = [dict(g) for g in DEFAULT_CONFIG]

        self._global_display_mode = int(self.get_setting("global_display_mode", 0))
        self._show_globe_badge = bool(self.get_setting("show_globe_badge", True))

    def save_config(self, reload_ui: bool = False):
        try:
            self.set_setting("groups_config", json.dumps(self._groups), reload_settings=reload_ui)
        except Exception as e:
            self.log(f"Error saving groups config: {e}")

    def get_fragment_dialog_id(self, fragment) -> Optional[int]:
        try:
            if hasattr(fragment, "getDialogId"):
                return int(fragment.getDialogId())
        except Exception:
            pass
        try:
            if hasattr(fragment, "chatId"):
                cid = int(fragment.chatId)
                return -cid if cid > 0 else cid
        except Exception:
            pass
        try:
            if hasattr(fragment, "dialogId"):
                return int(fragment.dialogId)
        except Exception:
            pass
        return None

    def find_group_config(self, dialog_id: int) -> Optional[Dict[str, Any]]:
        for group in self._groups:
            configured_id = group.get("chat_id", "")
            if matches_chat_id(configured_id, dialog_id):
                return group
        return None

    # =========================================================================
    # UI In-Chat Attachment
    # =========================================================================

    def attach_tabs_ui(self, fragment, root_view: View, group_config: Dict[str, Any]):
        tabs = group_config.get("tabs", [])
        if not tabs:
            return

        run_on_ui_thread(lambda: self._do_attach_tabs(fragment, root_view, tabs))

    def _do_attach_tabs(self, fragment, root_view: View, tabs: List[Dict[str, Any]]):
        try:
            context = root_view.getContext()
            action_bar = getattr(fragment, "actionBar", None)
            display_mode = self._global_display_mode

            if display_mode == 0:
                # Mode 0: Clean Tab Strip under ActionBar (matching forum topics aesthetic)
                self._attach_strip_under_action_bar(fragment, root_view, context, tabs)
            elif display_mode == 1:
                # Mode 1: Individual buttons in ActionBar
                if action_bar:
                    self._attach_buttons_to_action_bar(action_bar, context, tabs)
            elif display_mode == 2:
                # Mode 2: Single popup button in ActionBar
                if action_bar:
                    self._attach_popup_to_action_bar(action_bar, context, tabs)
        except Exception as e:
            self.log(f"Error attaching tabs UI: {e}")

    def _attach_strip_under_action_bar(self, fragment, root_view: View, context: Context, tabs: List[Dict[str, Any]]):
        try:
            # Check if container already exists
            existing = root_view.findViewWithTag(TAG_WEB_TABS_CONTAINER)
            if existing is not None:
                if isinstance(existing.getParent(), ViewGroup):
                    existing.getParent().removeView(existing)

            # Strip ScrollView
            scroll = HorizontalScrollView(context)
            scroll.setTag(TAG_WEB_TABS_CONTAINER)
            scroll.setHorizontalScrollBarEnabled(False)
            scroll.setOverScrollMode(View.OVER_SCROLL_NEVER)

            # Background & border
            bg_color = Theme.getColor(Theme.key_windowBackgroundWhite)
            scroll.setBackgroundColor(bg_color)

            # Container
            container = LinearLayout(context)
            container.setOrientation(LinearLayout.HORIZONTAL)
            container.setGravity(Gravity.CENTER_VERTICAL)
            container.setPadding(dp(12), dp(6), dp(12), dp(6))

            for tab in tabs:
                tile = self._create_topic_tile_view(context, tab)
                container.addView(tile)

            scroll.addView(container)

            # Insert into root_view (SizeNotifierFrameLayout / FrameLayout)
            if isinstance(root_view, ViewGroup):
                lp = FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    dp(66),
                    Gravity.TOP | Gravity.LEFT
                )
                lp.topMargin = dp(56)  # Standard ActionBar height
                root_view.addView(scroll, lp)
        except Exception as e:
            self.log(f"Error creating tab strip: {e}")

    def _create_topic_tile_view(self, context: Context, tab: Dict[str, Any]) -> View:
        tile = LinearLayout(context)
        tile.setOrientation(LinearLayout.VERTICAL)
        tile.setGravity(Gravity.CENTER_HORIZONTAL)
        tile.setPadding(dp(6), dp(2), dp(6), dp(2))

        # Icon card container (rounded box like Telegram topics)
        card_size = dp(38)
        card = FrameLayout(context)
        card_lp = LinearLayout.LayoutParams(card_size, card_size)
        card_lp.gravity = Gravity.CENTER_HORIZONTAL
        card.setLayoutParams(card_lp)

        # Rounded background
        card_bg = GradientDrawable()
        card_bg.setShape(GradientDrawable.RECTANGLE)
        card_bg.setCornerRadius(dp(10))
        # Subtle theme surface color
        card_bg_color = Theme.getColor(Theme.key_chat_inBubble)
        card_bg.setColor(card_bg_color)
        card.setBackground(card_bg)

        # Emoji TextView
        emoji_view = TextView(context)
        emoji_view.setText(tab.get("emoji", "📋") or "📋")
        emoji_view.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 20)
        emoji_view.setGravity(Gravity.CENTER)
        card.addView(emoji_view, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
            Gravity.CENTER
        ))

        # Mini globe badge 🌐 in top-right corner
        if self._show_globe_badge:
            globe_badge = TextView(context)
            globe_badge.setText("🌐")
            globe_badge.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 9)
            globe_badge.setGravity(Gravity.CENTER)
            badge_lp = FrameLayout.LayoutParams(dp(14), dp(14), Gravity.TOP | Gravity.RIGHT)
            card.addView(globe_badge, badge_lp)

        tile.addView(card)

        # Title TextView below the icon
        title_view = TextView(context)
        title_view.setText(tab.get("title", "Tab") or "Tab")
        title_view.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 11)
        title_view.setTypeface(Typeface.DEFAULT_BOLD)
        title_view.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
        title_view.setSingleLine(True)
        title_view.setGravity(Gravity.CENTER_HORIZONTAL)
        title_lp = LinearLayout.LayoutParams(dp(64), ViewGroup.LayoutParams.WRAP_CONTENT)
        title_lp.topMargin = dp(3)
        tile.addView(title_view, title_lp)

        # Ripple on click
        try:
            selector = Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 2)
            tile.setBackground(selector)
        except Exception:
            pass

        tile.setClickable(True)
        tile.setFocusable(True)
        tile.setOnClickListener(OnClickListenerProxy(lambda v: self.open_web_tab(context, tab)))

        return tile

    def _attach_buttons_to_action_bar(self, action_bar: ActionBar, context: Context, tabs: List[Dict[str, Any]]):
        try:
            menu = action_bar.createMenu()
            for tab in tabs:
                item_btn = FrameLayout(context)
                item_btn.setPadding(dp(8), 0, dp(8), 0)

                emoji_txt = TextView(context)
                emoji_txt.setText(tab.get("emoji", "📋") or "📋")
                emoji_txt.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 19)
                emoji_txt.setGravity(Gravity.CENTER)
                item_btn.addView(emoji_txt, FrameLayout.LayoutParams(dp(28), dp(28), Gravity.CENTER))

                if self._show_globe_badge:
                    globe = TextView(context)
                    globe.setText("🌐")
                    globe.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 8)
                    item_btn.addView(globe, FrameLayout.LayoutParams(dp(12), dp(12), Gravity.TOP | Gravity.RIGHT))

                item_btn.setClickable(True)
                item_btn.setOnClickListener(OnClickListenerProxy(lambda v, t=tab: self.open_web_tab(context, t)))
                menu.addView(item_btn, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.MATCH_PARENT))
        except Exception as e:
            self.log(f"Error attaching buttons to action bar: {e}")

    def _attach_popup_to_action_bar(self, action_bar: ActionBar, context: Context, tabs: List[Dict[str, Any]]):
        try:
            menu = action_bar.createMenu()
            btn = FrameLayout(context)
            btn.setPadding(dp(10), 0, dp(10), 0)

            globe_icon = TextView(context)
            globe_icon.setText("🌐")
            globe_icon.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 20)
            globe_icon.setGravity(Gravity.CENTER)
            btn.addView(globe_icon, FrameLayout.LayoutParams(dp(30), dp(30), Gravity.CENTER))

            # On click, show BottomSheet / popup of available tabs
            btn.setClickable(True)
            btn.setOnClickListener(OnClickListenerProxy(lambda v: self.show_tabs_selection_sheet(context, tabs)))
            menu.addView(btn, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.MATCH_PARENT))
        except Exception as e:
            self.log(f"Error attaching popup to action bar: {e}")

    def show_tabs_selection_sheet(self, context: Context, tabs: List[Dict[str, Any]]):
        try:
            builder = BottomSheet.Builder(context)
            builder.setTitle(tr("Веб-вкладки", "Web Tabs"))

            root = LinearLayout(context)
            root.setOrientation(LinearLayout.VERTICAL)
            root.setPadding(dp(16), dp(8), dp(16), dp(16))

            for tab in tabs:
                row = LinearLayout(context)
                row.setOrientation(LinearLayout.HORIZONTAL)
                row.setGravity(Gravity.CENTER_VERTICAL)
                row.setPadding(dp(8), dp(10), dp(8), dp(10))

                emoji_v = TextView(context)
                emoji_v.setText(f"{tab.get('emoji', '📋')} 🌐")
                emoji_v.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 20)
                row.addView(emoji_v)

                title_v = TextView(context)
                title_v.setText(tab.get("title", "Tab"))
                title_v.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
                title_v.setTypeface(Typeface.DEFAULT_BOLD)
                title_v.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
                title_v.setPadding(dp(12), 0, 0, 0)
                row.addView(title_v)

                row.setClickable(True)
                row.setOnClickListener(OnClickListenerProxy(lambda v, t=tab: [sheet.dismiss(), self.open_web_tab(context, t)]))
                root.addView(row)

            builder.setCustomView(root)
            sheet = builder.create()
            sheet.show()
        except Exception as e:
            self.log(f"Error showing tabs selection sheet: {e}")

    # =========================================================================
    # Fullscreen WebView BottomSheet
    # =========================================================================

    def open_web_tab(self, context: Context, tab: Dict[str, Any]):
        try:
            url_target = tab.get("url", "").strip()
            if not url_target:
                return

            if tab.get("remember_last_page") and tab.get("last_url"):
                url_target = tab.get("last_url")

            builder = BottomSheet.Builder(context, True)  # needFocus = True for keyboard input
            builder.setApplyBottomPadding(False)
            builder.setApplyTopPadding(False)

            root = LinearLayout(context)
            root.setOrientation(LinearLayout.VERTICAL)
            root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

            # 1. Header Toolbar
            header = LinearLayout(context)
            header.setOrientation(LinearLayout.HORIZONTAL)
            header.setGravity(Gravity.CENTER_VERTICAL)
            header.setPadding(dp(16), dp(8), dp(16), dp(8))
            header.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

            # Emoji + Globe
            header_emoji = TextView(context)
            header_emoji.setText(f"{tab.get('emoji', '📋')} 🌐")
            header_emoji.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 20)
            header.addView(header_emoji)

            # Titles layout (Title + domain)
            titles_col = LinearLayout(context)
            titles_col.setOrientation(LinearLayout.VERTICAL)
            titles_col.setPadding(dp(10), 0, dp(10), 0)

            header_title = TextView(context)
            header_title.setText(tab.get("title", "Web Tab"))
            header_title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
            header_title.setTypeface(Typeface.DEFAULT_BOLD)
            header_title.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
            header_title.setSingleLine(True)
            titles_col.addView(header_title)

            parsed = urllib.parse.urlparse(url_target)
            domain_str = parsed.netloc or parsed.path
            header_sub = TextView(context)
            header_sub.setText(domain_str)
            header_sub.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 11)
            header_sub.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText))
            header_sub.setSingleLine(True)
            titles_col.addView(header_sub)

            header.addView(titles_col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))

            # Buttons: Back, Refresh, Open in Browser, Close
            def btn(text_label: str, on_tap):
                b = TextView(context)
                b.setText(text_label)
                b.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
                b.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
                b.setPadding(dp(8), dp(4), dp(8), dp(4))
                b.setGravity(Gravity.CENTER)
                b.setClickable(True)
                b.setOnClickListener(OnClickListenerProxy(lambda v: on_tap()))
                return b

            # WebView placeholder handle
            web_ref = [None]

            btn_back = btn("◀", lambda: web_ref[0].goBack() if web_ref[0] and web_ref[0].canGoBack() else None)
            btn_reload = btn("🔄", lambda: web_ref[0].reload() if web_ref[0] else None)
            btn_external = btn("↗", lambda: self._open_external_browser(context, web_ref[0].getUrl() if web_ref[0] else url_target))
            btn_close = btn("✕", lambda: sheet.dismiss())

            header.addView(btn_back)
            header.addView(btn_reload)
            header.addView(btn_external)
            header.addView(btn_close)

            root.addView(header, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(54)))

            # 2. Loading ProgressBar
            progress_bar = ProgressBar(context, None, 16842872)  # progressBarStyleHorizontal
            progress_bar.setMax(100)
            progress_bar.setLayoutParams(LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)))
            root.addView(progress_bar)

            # 3. WebView
            webview = WebView(context)
            web_ref[0] = webview
            webview.setLayoutParams(LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                int(AndroidUtilities.displaySize.y * 0.85)  # 85% of screen height
            ))

            settings = webview.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setDatabaseEnabled(True)
            settings.setCacheMode(WebSettings.LOAD_DEFAULT)
            settings.setUseWideViewPort(True)
            settings.setLoadWithOverviewMode(True)
            settings.setSupportZoom(True)
            settings.setBuiltInZoomControls(True)
            settings.setDisplayZoomControls(False)

            # Accept cookies & third-party cookies for seamless logins
            try:
                cm = CookieManager.getInstance()
                cm.setAcceptCookie(True)
                cm.setAcceptThirdPartyCookies(webview, True)
            except Exception:
                pass

            def on_progress(p: int):
                progress_bar.setProgress(p)
                if p >= 100:
                    progress_bar.setVisibility(View.GONE)
                else:
                    progress_bar.setVisibility(View.VISIBLE)

            def on_page_finish(view, finished_url: str):
                try:
                    if finished_url:
                        # Update domain in header
                        p = urllib.parse.urlparse(finished_url)
                        header_sub.setText(p.netloc or p.path)

                        # Remember last page if configured
                        if tab.get("remember_last_page"):
                            tab["last_url"] = finished_url
                            self.save_config(reload_ui=False)
                except Exception:
                    pass

            chrome_inst = CustomChromeClient.new_instance()
            chrome_inst.on_progress = on_progress
            webview.setWebChromeClient(chrome_inst.java)

            web_inst = CustomWebClient.new_instance()
            web_inst.on_finish = on_page_finish
            webview.setWebViewClient(web_inst.java)

            # Load the target URL
            webview.loadUrl(url_target)
            root.addView(webview)

            builder.setCustomView(root)
            sheet = builder.create()

            # Clean up WebView on dismiss to prevent memory leaks
            def on_dismiss():
                try:
                    webview.stopLoading()
                    webview.destroy()
                except Exception:
                    pass

            sheet.setOnDismissListener(dynamic_proxy(jclass("android.content.DialogInterface$OnDismissListener"))(
                bare(lambda d: on_dismiss())
            ))
            sheet.show()
        except Exception as e:
            self.log(f"Error opening web tab: {e}")

    def _open_external_browser(self, context: Context, url_str: str):
        try:
            if not url_str:
                return
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url_str))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        except Exception as e:
            self.log(f"Error opening external browser: {e}")

    # =========================================================================
    # Settings Screen (Dynamic configuration)
    # =========================================================================

    def create_settings(self) -> List[Any]:
        settings_rows: List[Any] = []

        # 1. Global Display Mode
        settings_rows.append(Header(tr("Отображение в чатах", "Chat Display Mode")))
        settings_rows.append(
            Selector(
                key="global_display_mode",
                text=tr("Режим отображения", "Display format"),
                default=self._global_display_mode,
                items=[
                    tr("Полоса вкладок под шапкой (как топики)", "Tab strip under ActionBar (like topics)"),
                    tr("Кнопки в шапке (ActionBar)", "Buttons in ActionBar"),
                    tr("Единая кнопка с выпадающим меню", "Single button with popup menu"),
                ],
                icon="msg_theme",
                on_change=lambda val: self._on_display_mode_change(val),
            )
        )
        settings_rows.append(
            Switch(
                key="show_globe_badge",
                text=tr("Значок 🌐 на иконках", "Show 🌐 globe badge on icons"),
                subtext=tr("Отличает веб-вкладки от обычных тем чата", "Distinguishes web tabs from regular forum topics"),
                default=self._show_globe_badge,
                icon="msg_channel",
                on_change=lambda val: self._on_globe_badge_change(val),
            )
        )

        # 2. Configured Groups & Tabs
        for g_idx, group in enumerate(self._groups):
            g_title = group.get("title", "") or group.get("chat_id", "")
            settings_rows.append(Header(tr(f"Группа #{g_idx + 1}: {g_title}", f"Group #{g_idx + 1}: {g_title}")))

            settings_rows.append(
                Input(
                    key=f"g_{g_idx}_id",
                    text=tr("ID группы / чата", "Chat / Group ID"),
                    default=str(group.get("chat_id", "")),
                    subtext=tr("Например: -1002482353775", "E.g.: -1002482353775"),
                    icon="msg_groups",
                    on_change=lambda val, g=g_idx: self.update_group_id(g, val),
                )
            )

            tabs = group.get("tabs", [])
            for t_idx, tab in enumerate(tabs):
                tab_name = tab.get("title", "") or tr("Без названия", "Untitled")
                settings_rows.append(Divider(tr(f"Вкладка #{t_idx + 1}: {tab_name}", f"Tab #{t_idx + 1}: {tab_name}")))

                settings_rows.append(
                    Input(
                        key=f"t_{g_idx}_{t_idx}_title",
                        text=tr("Название вкладки", "Tab title"),
                        default=str(tab.get("title", "")),
                        icon="msg_edit",
                        on_change=lambda val, g=g_idx, t=t_idx: self.update_tab(g, t, "title", val),
                    )
                )

                settings_rows.append(
                    Input(
                        key=f"t_{g_idx}_{t_idx}_emoji",
                        text=tr("Эмодзи", "Emoji"),
                        default=str(tab.get("emoji", "📋")),
                        subtext=tr("Символ эмодзи для иконки (например: 📋, 📚, 📊)", "Emoji character for icon (e.g.: 📋, 📚, 📊)"),
                        icon="msg_smile",
                        on_change=lambda val, g=g_idx, t=t_idx: self.update_tab(g, t, "emoji", val),
                    )
                )

                settings_rows.append(
                    Input(
                        key=f"t_{g_idx}_{t_idx}_url",
                        text=tr("URL адрес сайта", "Website URL address"),
                        default=str(tab.get("url", "")),
                        subtext=tr("Полная ссылка (https://...)", "Full URL (https://...)"),
                        icon="msg_link",
                        on_change=lambda val, g=g_idx, t=t_idx: self.update_tab(g, t, "url", val),
                    )
                )

                settings_rows.append(
                    Switch(
                        key=f"t_{g_idx}_{t_idx}_rem",
                        text=tr("Запоминать последнюю страницу", "Remember last open page"),
                        subtext=tr("При повторном открытии загружает страницу, на которой вы остановились", "Resume where you left off instead of reloading base URL"),
                        default=bool(tab.get("remember_last_page", True)),
                        icon="msg_history",
                        on_change=lambda val, g=g_idx, t=t_idx: self.update_tab(g, t, "remember_last_page", val),
                    )
                )

                if len(tabs) > 1:
                    settings_rows.append(
                        Text(
                            text=tr("Удалить эту вкладку", "Delete this tab"),
                            red=True,
                            icon="msg_delete",
                            on_click=lambda view, g=g_idx, t=t_idx: self.delete_tab(g, t),
                        )
                    )

            settings_rows.append(
                Text(
                    text=tr("+ Добавить сайт в эту группу", "+ Add website to this group"),
                    accent=True,
                    icon="msg_add",
                    on_click=lambda view, g=g_idx: self.add_tab(g),
                )
            )

            if len(self._groups) > 1:
                settings_rows.append(
                    Text(
                        text=tr("Удалить эту группу", "Delete this group"),
                        red=True,
                        icon="msg_delete",
                        on_click=lambda view, g=g_idx: self.delete_group(g),
                    )
                )

        settings_rows.append(Divider())
        settings_rows.append(
            Text(
                text=tr("+ Добавить ещё одну группу", "+ Add another group"),
                accent=True,
                icon="msg_add",
                on_click=lambda view: self.add_group(),
            )
        )

        return settings_rows

    def _on_display_mode_change(self, val: int):
        self._global_display_mode = int(val)
        self.set_setting("global_display_mode", self._global_display_mode)

    def _on_globe_badge_change(self, val: bool):
        self._show_globe_badge = bool(val)
        self.set_setting("show_globe_badge", self._show_globe_badge)

    def update_group_id(self, g_idx: int, val: str):
        if 0 <= g_idx < len(self._groups):
            self._groups[g_idx]["chat_id"] = str(val).strip()
            self.save_config(reload_ui=False)

    def update_tab(self, g_idx: int, t_idx: int, field: str, val: Any):
        if 0 <= g_idx < len(self._groups):
            tabs = self._groups[g_idx].get("tabs", [])
            if 0 <= t_idx < len(tabs):
                tabs[t_idx][field] = val
                self.save_config(reload_ui=False)

    def add_tab(self, g_idx: int):
        if 0 <= g_idx < len(self._groups):
            tabs = self._groups[g_idx].setdefault("tabs", [])
            new_idx = len(tabs) + 1
            tabs.append({
                "id": f"tab_{new_idx}",
                "title": f"Web App {new_idx}",
                "emoji": "🌐",
                "url": "https://",
                "remember_last_page": True,
                "last_url": "",
            })
            self.save_config(reload_ui=True)

    def delete_tab(self, g_idx: int, t_idx: int):
        if 0 <= g_idx < len(self._groups):
            tabs = self._groups[g_idx].get("tabs", [])
            if 0 <= t_idx < len(tabs) and len(tabs) > 1:
                tabs.pop(t_idx)
                self.save_config(reload_ui=True)

    def add_group(self):
        new_idx = len(self._groups) + 1
        self._groups.append({
            "chat_id": "",
            "title": f"Group {new_idx}",
            "tabs": [
                {
                    "id": "tab_1",
                    "title": "Main Web App",
                    "emoji": "📋",
                    "url": "https://",
                    "remember_last_page": True,
                    "last_url": "",
                }
            ],
        })
        self.save_config(reload_ui=True)

    def delete_group(self, g_idx: int):
        if 0 <= g_idx < len(self._groups) and len(self._groups) > 1:
            self._groups.pop(g_idx)
            self.save_config(reload_ui=True)


def bare(func, scope=None):
    import types
    return types.FunctionType(
        func.__code__,
        scope or {},
        func.__name__,
        func.__defaults__,
        func.__closure__,
    )
