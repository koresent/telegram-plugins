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
from android.text import TextUtils
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
    ImageView,
    LinearLayout,
    ProgressBar,
    TextView,
)
from java import dynamic_proxy, jclass, jint
from org.telegram.messenger import AndroidUtilities, LocaleController, MessageObject
from org.telegram.ui.ActionBar import (
    ActionBar,
    ActionBarMenu,
    ActionBarMenuItem,
    BottomSheet,
    Theme,
)
from org.telegram.ui.Components import EmojiView
from extera_utils.classes import Base, java_subclass, joverload

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MethodHook
from ui.settings import Custom, Divider, Header, Input, Selector, Switch, Text

__id__ = "chat_web_tabs"
__name__ = "Chat Web Tabs"
__description__ = "Custom web apps and pinned web tabs with persistent sessions for Telegram chats"
__author__ = "@koresent"
__version__ = "1.0.5"
__icon__ = "exteraPlugins/1"
__category__ = "general"

DEFAULT_CONFIG = [
    {
        "chat_id": "",
        "title": "",
        "tabs": [
            {
                "id": "tab_1",
                "title": "",
                "emoji": "📋",
                "url": "",
                "remember_last_page": False,
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
    if not c_str or not a_str:
        return False
    if c_str == a_str:
        return True
    return normalize_chat_id(c_str) == normalize_chat_id(a_str)


def get_activity_from_context(ctx):
    from android.content import ContextWrapper
    from android.app import Activity
    curr = ctx
    while isinstance(curr, ContextWrapper):
        if isinstance(curr, Activity):
            return curr
        curr = curr.getBaseContext()
    try:
        LaunchActivity = jclass("org.telegram.ui.LaunchActivity")
        if LaunchActivity.instance is not None:
            return LaunchActivity.instance
    except Exception:
        pass
    return None


class OnClickListenerProxy(dynamic_proxy(View.OnClickListener)):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def onClick(self, view):
        try:
            self.callback(view)
        except Exception:
            pass


class OnDismissListenerProxy(dynamic_proxy(jclass("android.content.DialogInterface$OnDismissListener"))):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def onDismiss(self, dialog):
        try:
            if self.callback:
                self.callback()
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


def get_dialog_id(ttv) -> Optional[int]:
    try:
        f = ttv.getClass().getDeclaredField("dialogId")
        f.setAccessible(True)
        return int(f.getLong(ttv))
    except Exception:
        pass
    try:
        f = ttv.getClass().getDeclaredField("fragment")
        f.setAccessible(True)
        frag = f.get(ttv)
        if frag is not None:
            return int(frag.getDialogId())
    except Exception:
        pass
    return None


class VerticalTabsHook(MethodHook):
    def __init__(self, plugin: "ChatWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            ttv = param.thisObject
            items = param.args[0]
            dialog_id = get_dialog_id(ttv)
            if dialog_id is None:
                return

            group_config = self.plugin.find_group_config(dialog_id)
            if not group_config or not group_config.get("tabs"):
                return

            context = ttv.getContext()
            UItem = jclass("org.telegram.ui.Components.UItem")

            # Place web tabs at the bottom, right before the "+ New Topic" button (id == -2)
            insert_idx = items.size()
            for i in range(items.size()):
                it = items.get(i)
                if getattr(it, "id", 0) == -2:
                    insert_idx = i
                    break

            tabs = group_config.get("tabs", [])
            for tab in reversed(tabs):
                tile = self.plugin.create_sidebar_tile_view(context, tab)
                uitem = UItem.asCustom(tile)
                items.add(insert_idx, uitem)
        except Exception as e:
            self.plugin.log(f"VerticalTabsHook error: {e}")


class HorizontalTabsHook(MethodHook):
    def __init__(self, plugin: "ChatWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            ttv = param.thisObject
            items = param.args[0]
            dialog_id = get_dialog_id(ttv)
            if dialog_id is None:
                return

            group_config = self.plugin.find_group_config(dialog_id)
            if not group_config or not group_config.get("tabs"):
                return

            context = ttv.getContext()
            UItem = jclass("org.telegram.ui.Components.UItem")

            # Place horizontal web pills before "+ New Topic" button
            insert_idx = items.size()
            for i in range(items.size()):
                it = items.get(i)
                if getattr(it, "id", 0) == -2:
                    insert_idx = i
                    break

            tabs = group_config.get("tabs", [])
            for tab in reversed(tabs):
                tile = self.plugin.create_horizontal_tab_view(context, tab)
                uitem = UItem.asCustom(tile)
                items.add(insert_idx, uitem)
        except Exception as e:
            self.plugin.log(f"HorizontalTabsHook error: {e}")


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
        ttv_cls = Class_cls.forName("org.telegram.ui.Components.TopicsTabsView")
        arr_cls = Class_cls.forName("java.util.ArrayList")
        adp_cls = Class_cls.forName("org.telegram.ui.Components.UniversalAdapter")

        # 1. Hook fillVerticalTabs(ArrayList, UniversalAdapter) for the left side panel
        try:
            m_vertical = ttv_cls.getDeclaredMethod("fillVerticalTabs", arr_cls, adp_cls)
            m_vertical.setAccessible(True)
            unhook = self.hook_method(m_vertical, VerticalTabsHook(self))
            if unhook:
                self._hook_objects.append(unhook)
                self.log("Hooked fillVerticalTabs on TopicsTabsView")
        except Exception as e:
            self.log(f"Error hooking fillVerticalTabs: {e}")

        # 2. Hook fillHorizontalTabs(ArrayList, UniversalAdapter) for top horizontal mode
        try:
            m_horizontal = ttv_cls.getDeclaredMethod("fillHorizontalTabs", arr_cls, adp_cls)
            m_horizontal.setAccessible(True)
            unhook = self.hook_method(m_horizontal, HorizontalTabsHook(self))
            if unhook:
                self._hook_objects.append(unhook)
                self.log("Hooked fillHorizontalTabs on TopicsTabsView")
        except Exception as e:
            self.log(f"Error hooking fillHorizontalTabs: {e}")

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

        self._show_globe_badge = bool(self.get_setting("show_globe_badge", True))

    def save_config(self, reload_ui: bool = False):
        try:
            self.set_setting("groups_config", json.dumps(self._groups), reload_settings=reload_ui)
        except Exception as e:
            self.log(f"Error saving groups config: {e}")

    def find_group_config(self, dialog_id: int) -> Optional[Dict[str, Any]]:
        for group in self._groups:
            configured_id = group.get("chat_id", "")
            if matches_chat_id(configured_id, dialog_id):
                return group
        return None

    # =========================================================================
    # Sidebar Tile View (Inserted into left Topics panel)
    # =========================================================================

    def create_sidebar_tile_view(self, context: Context, tab: Dict[str, Any]) -> View:
        tile = LinearLayout(context)
        tile.setOrientation(LinearLayout.VERTICAL)
        tile.setGravity(Gravity.CENTER_HORIZONTAL)
        tile.setPadding(dp(2), dp(6), dp(2), dp(4))

        # Size matching vertical topic tiles in left sidebar
        tile.setLayoutParams(ViewGroup.LayoutParams(dp(56), dp(62)))

        # Icon container (matching native topic tab icon in vertical topics bar)
        icon_box = FrameLayout(context)
        icon_box_lp = LinearLayout.LayoutParams(dp(32), dp(32))
        icon_box_lp.gravity = Gravity.CENTER_HORIZONTAL
        icon_box.setLayoutParams(icon_box_lp)

        # Centered Emoji (clean, no artificial box background, matching topic items)
        emoji_view = TextView(context)
        emoji_view.setText(tab.get("emoji", "📋") or "📋")
        emoji_view.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 24)
        emoji_view.setGravity(Gravity.CENTER)
        icon_box.addView(emoji_view, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
            Gravity.CENTER
        ))

        # Vector Globe badge (SVG / Vector Drawable from Telegram tinted to theme)
        if self._show_globe_badge:
            globe_iv = ImageView(context)
            r_drawable = jclass("org.telegram.messenger.R$drawable")
            globe_iv.setImageResource(r_drawable.msg_language)
            globe_iv.setColorFilter(Theme.getColor(Theme.key_windowBackgroundWhiteGrayIcon))
            badge_lp = FrameLayout.LayoutParams(dp(11), dp(11), Gravity.TOP | Gravity.RIGHT)
            icon_box.addView(globe_iv, badge_lp)

        tile.addView(icon_box)

        # Label underneath (matching "Бэкап" and "Заметки" styling in Topics bar)
        title_view = TextView(context)
        title_view.setText(tab.get("title", "Tab") or "Tab")
        title_view.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 10.5)
        title_view.setTypeface(Typeface.DEFAULT)
        title_view.setTextColor(Theme.getColor(Theme.key_chats_nameMessage_threeLines))
        title_view.setSingleLine(True)
        title_view.setEllipsize(TextUtils.TruncateAt.END)
        title_view.setGravity(Gravity.CENTER_HORIZONTAL)
        title_lp = LinearLayout.LayoutParams(dp(54), ViewGroup.LayoutParams.WRAP_CONTENT)
        title_lp.topMargin = dp(2)
        title_lp.gravity = Gravity.CENTER_HORIZONTAL
        tile.addView(title_view, title_lp)

        # Native selector ripple
        try:
            selector = Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 2)
            tile.setBackground(selector)
        except Exception:
            pass

        tile.setClickable(True)
        tile.setFocusable(True)
        tile.setOnClickListener(OnClickListenerProxy(lambda v: self.open_web_tab(v, tab)))

        return tile

    # =========================================================================
    # Horizontal Tab View (Pill for top topics bar)
    # =========================================================================

    def create_horizontal_tab_view(self, context: Context, tab: Dict[str, Any]) -> View:
        pill = LinearLayout(context)
        pill.setOrientation(LinearLayout.HORIZONTAL)
        pill.setGravity(Gravity.CENTER_VERTICAL)
        pill.setPadding(dp(10), dp(4), dp(10), dp(4))

        bg = GradientDrawable()
        bg.setShape(GradientDrawable.RECTANGLE)
        bg.setCornerRadius(dp(15))
        bg.setColor(Theme.getColor(Theme.key_chat_inBubble))
        pill.setBackground(bg)

        emoji_tv = TextView(context)
        emoji_tv.setText(tab.get("emoji", "📋") or "📋")
        emoji_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
        pill.addView(emoji_tv)

        if self._show_globe_badge:
            globe = ImageView(context)
            r_drawable = jclass("org.telegram.messenger.R$drawable")
            globe.setImageResource(r_drawable.msg_language)
            globe.setColorFilter(Theme.getColor(Theme.key_windowBackgroundWhiteBlueHeader))
            glp = LinearLayout.LayoutParams(dp(12), dp(12))
            glp.leftMargin = dp(3)
            pill.addView(globe, glp)

        title_tv = TextView(context)
        title_tv.setText(tab.get("title", "Tab") or "Tab")
        title_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
        title_tv.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
        title_tv.setSingleLine(True)
        tlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        tlp.leftMargin = dp(5)
        pill.addView(title_tv, tlp)

        pill.setClickable(True)
        pill.setFocusable(True)
        pill.setOnClickListener(OnClickListenerProxy(lambda v: self.open_web_tab(v, tab)))
        return pill

    # =========================================================================
    # Fullscreen WebView BottomSheet
    # =========================================================================

    def open_web_tab(self, context_or_view, tab: Dict[str, Any]):
        def do_open():
            try:
                activity = get_activity_from_context(context_or_view)
                if activity is None:
                    LaunchActivity = jclass("org.telegram.ui.LaunchActivity")
                    activity = LaunchActivity.instance
                if activity is None:
                    self.log("Cannot locate Activity to show BottomSheet")
                    return

                base_url = tab.get("url", "").strip()
                if not base_url:
                    return

                base_parsed = urllib.parse.urlparse(base_url)
                base_domain = (base_parsed.netloc or "").lower()

                url_target = base_url
                if tab.get("remember_last_page", False):
                    saved_url = str(tab.get("last_url", "")).strip()
                    if saved_url.startswith("http://") or saved_url.startswith("https://"):
                        saved_domain = (urllib.parse.urlparse(saved_url).netloc or "").lower()
                        if saved_domain == base_domain:
                            url_target = saved_url

                builder = BottomSheet.Builder(activity, True)  # needFocus = True for soft keyboard
                builder.setApplyBottomPadding(False)
                builder.setApplyTopPadding(False)

                root = LinearLayout(activity)
                root.setOrientation(LinearLayout.VERTICAL)
                root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

                # 1. Header Toolbar (height 52dp)
                header = LinearLayout(activity)
                header.setOrientation(LinearLayout.HORIZONTAL)
                header.setGravity(Gravity.CENTER_VERTICAL)
                header.setPadding(dp(16), dp(8), dp(16), dp(8))
                header.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

                # Emoji Icon in header
                header_emoji = TextView(activity)
                header_emoji.setText(tab.get("emoji", "📋") or "📋")
                header_emoji.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 22)
                header.addView(header_emoji)

                # Title & Subtitle (domain)
                titles_col = LinearLayout(activity)
                titles_col.setOrientation(LinearLayout.VERTICAL)
                titles_col.setPadding(dp(12), 0, dp(12), 0)

                header_title = TextView(activity)
                header_title.setText(tab.get("title", "Web Tab"))
                header_title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                header_title.setTypeface(Typeface.DEFAULT_BOLD)
                header_title.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
                header_title.setSingleLine(True)
                titles_col.addView(header_title)

                parsed = urllib.parse.urlparse(url_target)
                domain_str = parsed.netloc or parsed.path
                header_sub = TextView(activity)
                header_sub.setText(domain_str)
                header_sub.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 11)
                header_sub.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText))
                header_sub.setSingleLine(True)
                titles_col.addView(header_sub)

                header.addView(titles_col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))

                # Native SVG Vector Buttons: Back, Refresh, Open in Browser, Close
                sheet_ref = [None]
                icon_color = Theme.getColor(Theme.key_windowBackgroundWhiteBlackText)
                r_drawable = jclass("org.telegram.messenger.R$drawable")

                def icon_btn(drawable_id: int, on_tap, pad: int = 6):
                    b = ImageView(activity)
                    b.setImageResource(drawable_id)
                    b.setColorFilter(icon_color)
                    b.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
                    b.setPadding(dp(pad), dp(pad), dp(pad), dp(pad))
                    b_lp = LinearLayout.LayoutParams(dp(36), dp(36))
                    b_lp.gravity = Gravity.CENTER_VERTICAL
                    b_lp.leftMargin = dp(2)
                    b.setLayoutParams(b_lp)
                    try:
                        b.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 1))
                    except Exception:
                        pass
                    b.setClickable(True)
                    b.setFocusable(True)
                    b.setOnClickListener(OnClickListenerProxy(lambda v: on_tap()))
                    return b

                web_ref = [None]
                btn_back = icon_btn(r_drawable.ic_ab_back, lambda: web_ref[0].goBack() if web_ref[0] and web_ref[0].canGoBack() else None, pad=5)
                btn_reload = icon_btn(r_drawable.msg_retry, lambda: web_ref[0].reload() if web_ref[0] else None, pad=5)
                btn_external = icon_btn(r_drawable.filled_link, lambda: self._open_external_browser(activity, web_ref[0].getUrl() if web_ref[0] else url_target), pad=4)
                btn_close = icon_btn(r_drawable.ic_ab_close, lambda: sheet_ref[0].dismiss() if sheet_ref[0] else None, pad=2)

                header.addView(btn_back)
                header.addView(btn_reload)
                header.addView(btn_external)
                header.addView(btn_close)

                root.addView(header, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)))

                # 2. Loading ProgressBar
                progress_bar = ProgressBar(activity, None, 16842872)
                progress_bar.setMax(100)
                progress_bar.setLayoutParams(LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)))
                root.addView(progress_bar)

                # 3. WebView
                webview = WebView(activity)
                web_ref[0] = webview
                webview.setLayoutParams(LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    int(AndroidUtilities.displaySize.y * 0.85)
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
                            p = urllib.parse.urlparse(finished_url)
                            header_sub.setText(p.netloc or p.path)
                            if tab.get("remember_last_page", False):
                                f_str = str(finished_url).strip()
                                if f_str.startswith("http://") or f_str.startswith("https://"):
                                    f_domain = (urllib.parse.urlparse(f_str).netloc or "").lower()
                                    if f_domain == base_domain:
                                        tab["last_url"] = f_str
                                        self.save_config(reload_ui=False)
                    except Exception:
                        pass

                chrome_inst = CustomChromeClient.new_instance()
                chrome_inst.on_progress = on_progress
                webview.setWebChromeClient(chrome_inst.java)

                web_inst = CustomWebClient.new_instance()
                web_inst.on_finish = on_page_finish
                webview.setWebViewClient(web_inst.java)

                webview.loadUrl(url_target)
                root.addView(webview)

                builder.setCustomView(root)
                sheet = builder.create()
                sheet_ref[0] = sheet

                def on_dismiss():
                    try:
                        if tab.get("remember_last_page", False) and web_ref[0]:
                            curr_url = str(web_ref[0].getUrl() or "").strip()
                            if curr_url.startswith("http://") or curr_url.startswith("https://"):
                                curr_domain = (urllib.parse.urlparse(curr_url).netloc or "").lower()
                                if curr_domain == base_domain:
                                    tab["last_url"] = curr_url
                                    self.save_config(reload_ui=False)
                        if web_ref[0]:
                            web_ref[0].stopLoading()
                            web_ref[0].destroy()
                    except Exception:
                        pass

                sheet.setOnDismissListener(OnDismissListenerProxy(on_dismiss))
                sheet.show()
            except Exception as e:
                self.log(f"Error opening web tab: {e}")

        run_on_ui_thread(do_open)

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
    # Emoji Picker Dialog Integration
    # =========================================================================

    def open_emoji_picker(self, view, g_idx: int, t_idx: int):
        try:
            LaunchActivity = jclass("org.telegram.ui.LaunchActivity")
            la = LaunchActivity.instance
            activity = la or get_activity_from_context(view)
            frag = None
            try:
                if la and la.getActionBarLayout():
                    frag = la.getActionBarLayout().getLastFragment()
            except Exception:
                pass

            EmojiView = jclass("org.telegram.ui.Components.EmojiView")
            EmojiViewDelegate = jclass("org.telegram.ui.Components.EmojiView$EmojiViewDelegate")

            sheet_ref = [None]

            class PickerDelegate(dynamic_proxy(EmojiViewDelegate)):
                def __init__(self, plugin, g, t):
                    super().__init__()
                    self.plugin = plugin
                    self.g = g
                    self.t = t

                def onEmojiSelected(self, emoji_str):
                    try:
                        self.plugin.update_tab(self.g, self.t, "emoji", str(emoji_str))
                        self.plugin.save_config(reload_ui=True)
                    except Exception as e:
                        self.plugin.log(f"Error picking emoji: {e}")
                    finally:
                        if sheet_ref[0]:
                            sheet_ref[0].dismiss()

                def onCustomEmojiSelected(self, doc_id, doc, s, z):
                    try:
                        emoji_str = "📋"
                        if s:
                            emoji_str = str(s)
                        elif doc is not None:
                            emoticon = MessageObject.findAnimatedEmojiEmoticon(doc)
                            if emoticon:
                                emoji_str = str(emoticon)
                        elif doc_id is not None:
                            emoji_str = str(doc_id)
                        self.plugin.update_tab(self.g, self.t, "emoji", emoji_str)
                        self.plugin.save_config(reload_ui=True)
                    except Exception as e:
                        self.plugin.log(f"Error picking custom emoji: {e}")
                    finally:
                        if sheet_ref[0]:
                            sheet_ref[0].dismiss()

            ev = EmojiView(frag, True, False, False, activity, False, None, None, False, None, False)
            ev.setDelegate(PickerDelegate(self, g_idx, t_idx))

            builder = BottomSheet.Builder(activity)
            lp = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                int(AndroidUtilities.displaySize.y * 0.58)
            )
            ev.setLayoutParams(lp)
            builder.setCustomView(ev)
            sheet = builder.create()
            sheet_ref[0] = sheet
            sheet.show()
        except Exception as e:
            self.log(f"Error opening emoji picker: {e}")

    # =========================================================================
    # Settings Screen
    # =========================================================================

    def create_settings(self) -> List[Any]:
        settings_rows: List[Any] = []

        settings_rows.append(Header(tr("Отображение", "Display")))
        settings_rows.append(
            Switch(
                key="show_globe_badge",
                text=tr("Значок глобуса на иконках", "Globe badge on icons"),
                subtext=tr("Векторный индикатор, отличающий веб-вкладки от обычных тем", "Vector icon indicator distinguishing web tabs from regular topics"),
                default=self._show_globe_badge,
                icon="msg_language",
                on_change=lambda val: self._on_globe_badge_change(val),
            )
        )

        for g_idx, group in enumerate(self._groups):
            g_title = group.get("title", "") or group.get("chat_id", "") or tr("Новая группа", "New group")
            settings_rows.append(Header(tr(f"Группа #{g_idx + 1}: {g_title}", f"Group #{g_idx + 1}: {g_title}")))

            settings_rows.append(
                Input(
                    key=f"g_{g_idx}_title",
                    text=tr("Название группы / чата", "Chat / Group title"),
                    default=str(group.get("title", "")),
                    subtext=tr("Отображается в заголовке настроек", "Displayed in settings section header"),
                    icon="msg_edit",
                    on_change=lambda val, g=g_idx: self.update_group_title(g, val),
                )
            )

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

                # Tap to open Telegram's Native Emoji Picker Dialog
                settings_rows.append(
                    Text(
                        text=tr(f"Выбрать эмодзи в пикере: {tab.get('emoji', '📋')}", f"Pick emoji from picker: {tab.get('emoji', '📋')}"),
                        subtext=tr("Нажмите, чтобы открыть пикер эмодзи Telegram", "Tap to open native Telegram emoji picker"),
                        icon="msg_smile",
                        accent=True,
                        on_click=lambda view, g=g_idx, t=t_idx: self.open_emoji_picker(view, g, t),
                    )
                )

                # Or manual input
                settings_rows.append(
                    Input(
                        key=f"t_{g_idx}_{t_idx}_emoji",
                        text=tr("Или введите символ вручную", "Or enter symbol manually"),
                        default=str(tab.get("emoji", "📋")),
                        icon="msg_edit",
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
                        default=bool(tab.get("remember_last_page", False)),
                        icon="msg_history",
                        on_change=lambda val, g=g_idx, t=t_idx: self.update_tab(g, t, "remember_last_page", val),
                    )
                )

                if tab.get("last_url"):
                    settings_rows.append(
                        Text(
                            text=tr("Сбросить сохранённую страницу", "Reset saved page"),
                            subtext=tr(f"Сохранено: {tab.get('last_url')}", f"Saved: {tab.get('last_url')}"),
                            icon="msg_retry",
                            on_click=lambda view, g=g_idx, t=t_idx: self.reset_last_url(g, t),
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

    def _on_globe_badge_change(self, val: bool):
        self._show_globe_badge = bool(val)
        self.set_setting("show_globe_badge", self._show_globe_badge)

    def update_group_title(self, g_idx: int, val: str):
        if 0 <= g_idx < len(self._groups):
            self._groups[g_idx]["title"] = str(val).strip()
            self.save_config(reload_ui=False)

    def update_group_id(self, g_idx: int, val: str):
        if 0 <= g_idx < len(self._groups):
            self._groups[g_idx]["chat_id"] = str(val).strip()
            self.save_config(reload_ui=False)

    def reset_last_url(self, g_idx: int, t_idx: int):
        self.update_tab(g_idx, t_idx, "last_url", "")
        self.save_config(reload_ui=True)

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
                "title": "",
                "emoji": "📋",
                "url": "",
                "remember_last_page": False,
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
            "title": "",
            "tabs": [
                {
                    "id": "tab_1",
                    "title": "",
                    "emoji": "📋",
                    "url": "",
                    "remember_last_page": False,
                    "last_url": "",
                }
            ],
        })
        self.save_config(reload_ui=True)

    def delete_group(self, g_idx: int):
        if 0 <= g_idx < len(self._groups) and len(self._groups) > 1:
            self._groups.pop(g_idx)
            self.save_config(reload_ui=True)
