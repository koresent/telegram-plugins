# -*- coding: utf-8 -*-
"""
Bot Web Tabs for exteraGram
Custom web app buttons with persistent sessions for Telegram bots.
"""

import json
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from android.content import Context, Intent
from android.graphics import Color, Typeface
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
    ImageView,
    LinearLayout,
    ProgressBar,
    TextView,
)
from java import dynamic_proxy, jclass, jint, jlong
from org.telegram.messenger import (
    AndroidUtilities,
    ApplicationLoader,
    LocaleController,
    UserConfig,
)
from org.telegram.ui.ActionBar import (
    BottomSheet,
    Theme,
)
from extera_utils.classes import Base, java_subclass, joverload

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MethodHook
from ui.settings import Divider, Header, Input, Switch, Text

__id__ = "bot_web_tabs"
__name__ = "Bot Web Tabs"
__description__ = "Custom web app buttons with persistent sessions for Telegram bots"
__author__ = "@koresent"
__version__ = "1.0.1"
__icon__ = "exteraPlugins/1"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"

DEFAULT_CONFIG: List[Dict[str, Any]] = [
    {
        "id": "bot_1",
        "bot_title": "",
        "bot_id": "",
        "button_text": "Open App",
        "url": "",
        "remember_last_page": False,
        "last_url": "",
    }
]


def dp(value: float) -> int:
    return AndroidUtilities.dp(float(value))


def is_ru() -> bool:
    try:
        lang = LocaleController.getInstance().getCurrentLocaleInfo().shortName.lower()
        return lang.startswith("ru")
    except Exception:
        return False


def tr(ru: str, en: str) -> str:
    return ru if is_ru() else en


def normalize_domain(domain: str) -> str:
    domain = (domain or "").strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def domains_match(url1: str, url2: str) -> bool:
    try:
        p1 = urllib.parse.urlparse(url1)
        p2 = urllib.parse.urlparse(url2)
        d1 = normalize_domain(p1.netloc or p1.path)
        d2 = normalize_domain(p2.netloc or p2.path)
        if not d1 or not d2:
            return False
        return d1 == d2 or d1.endswith("." + d2) or d2.endswith("." + d1)
    except Exception:
        return False


def is_url_allowed_for_bot(current_url: str, base_url: str) -> bool:
    if not current_url or not base_url:
        return False
    if current_url in ("about:blank", "data:"):
        return False
    if not (current_url.startswith("http://") or current_url.startswith("https://")):
        return False
    return domains_match(current_url, base_url)


def matches_bot_id(configured: Any, dialog_id: int, current_account: int = 0) -> bool:
    if not configured or not dialog_id:
        return False
    conf_str = str(configured).strip()
    if not conf_str:
        return False
    if conf_str.lstrip("-").isdigit():
        try:
            return int(conf_str) == int(dialog_id)
        except Exception:
            pass
    if conf_str.startswith("@") or conf_str.isalnum():
        uname = conf_str.lstrip("@").lower()
        try:
            MessagesController = jclass("org.telegram.messenger.MessagesController")
            user = MessagesController.getInstance(current_account).getUser(jlong(int(dialog_id)))
            if user and getattr(user, "username", None):
                return str(user.username).lower() == uname
        except Exception:
            pass
    return False


def get_field(obj: Any, field_name: str) -> Any:
    cls = obj.getClass()
    while cls:
        try:
            f = cls.getDeclaredField(field_name)
            f.setAccessible(True)
            return f.get(obj)
        except Exception:
            cls = cls.getSuperclass()
    return None


def set_field(obj: Any, field_name: str, value: Any) -> bool:
    cls = obj.getClass()
    while cls:
        try:
            f = cls.getDeclaredField(field_name)
            f.setAccessible(True)
            f.set(obj, value)
            return True
        except Exception:
            cls = cls.getSuperclass()
    return False


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


class WebTouchListener(dynamic_proxy(View.OnTouchListener)):
    def onTouch(self, v, event):
        try:
            p = v.getParent()
            if p:
                p.requestDisallowInterceptTouchEvent(True)
        except Exception:
            pass
        return False


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
class BotChromeClient(Base):
    @joverload("onProgressChanged", ["android.webkit.WebView", "int"])
    def on_progress_changed(self, view, progress):
        try:
            cb = getattr(self, "on_progress", None)
            if cb:
                cb(int(progress))
        except Exception:
            pass


@java_subclass(WebViewClient)
class BotWebClient(Base):
    @joverload("onPageFinished", ["android.webkit.WebView", "java.lang.String"])
    def on_page_finished(self, view, url):
        try:
            cb = getattr(self, "on_finish", None)
            if cb:
                cb(view, str(url) if url else "")
        except Exception:
            pass

    @joverload("doUpdateVisitedHistory", ["android.webkit.WebView", "java.lang.String", "boolean"])
    def do_update_visited_history(self, view, url, is_reload):
        try:
            cb = getattr(self, "on_url_change", None)
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


class UpdateBotButtonHook(MethodHook):
    def __init__(self, plugin: "BotWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def before_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            enter_view = param.thisObject
            dialog_id = get_field(enter_view, "dialog_id")
            if not dialog_id:
                return
            self.plugin.apply_bot_menu(enter_view, int(dialog_id))
        except Exception as e:
            self.plugin.log(f"UpdateBotButtonHook error: {e}")


class SetBotInfoHook(MethodHook):
    def __init__(self, plugin: "BotWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            enter_view = param.thisObject
            dialog_id = get_field(enter_view, "dialog_id")
            if not dialog_id:
                return
            if self.plugin.apply_bot_menu(enter_view, int(dialog_id)):
                self.plugin.call_update_bot_button(enter_view, False)
        except Exception as e:
            self.plugin.log(f"SetBotInfoHook error: {e}")


class SetDialogIdHook(MethodHook):
    def __init__(self, plugin: "BotWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            enter_view = param.thisObject
            dialog_id = param.args[0]
            if not dialog_id:
                return
            if self.plugin.apply_bot_menu(enter_view, int(dialog_id)):
                self.plugin.call_update_bot_button(enter_view, False)
        except Exception as e:
            self.plugin.log(f"SetDialogIdHook error: {e}")


class OpenWebViewMenuHook(MethodHook):
    def __init__(self, plugin: "BotWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def before_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            enter_view = param.thisObject
            dialog_id = get_field(enter_view, "dialog_id")
            if not dialog_id:
                return
            bot_cfg = self.plugin.find_bot_config(int(dialog_id))
            if bot_cfg:
                param.setResult(None)
                menu_btn = get_field(enter_view, "botCommandsMenuButton")
                if menu_btn:
                    try:
                        menu_btn.setOpened(False)
                    except Exception:
                        pass
                AndroidUtilities.hideKeyboard(enter_view)
                activity = enter_view.getContext()
                self.plugin.open_bot_web_view(activity, bot_cfg)
        except Exception as e:
            self.plugin.log(f"OpenWebViewMenuHook error: {e}")


class ChatActivityResumeHook(MethodHook):
    def __init__(self, plugin: "BotWebTabsPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            if not self.plugin.is_active:
                return
            chat_activity = param.thisObject
            dialog_id = getattr(chat_activity, "getDialogId", lambda: 0)()
            if not dialog_id:
                return
            bot_cfg = self.plugin.find_bot_config(int(dialog_id))
            if bot_cfg:
                ev = get_field(chat_activity, "chatActivityEnterView")
                if ev:
                    if self.plugin.apply_bot_menu(ev, int(dialog_id)):
                        self.plugin.call_update_bot_button(ev, False)
        except Exception as e:
            self.plugin.log(f"ChatActivityResumeHook error: {e}")


class BotWebTabsPlugin(BasePlugin):
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
        self._bots: List[Dict[str, Any]] = []
        self.m_update_bot_button = None
        self._web_view_enum = None

    def on_plugin_load(self):
        self.is_active = True
        self.load_config()
        self._install_hooks()
        self._refresh_current_chat()
        self.log("BotWebTabs loaded successfully")

    def on_plugin_unload(self):
        self.is_active = False
        self.m_update_bot_button = None
        self._web_view_enum = None
        for unhook in self._hook_objects:
            try:
                self.unhook_method(unhook)
            except Exception:
                pass
        self._hook_objects.clear()
        self.log("BotWebTabs unloaded")

    def _install_hooks(self):
        Class_cls = jclass("java.lang.Class")
        ev_cls = Class_cls.forName("org.telegram.ui.Components.ChatActivityEnterView")

        for m in ev_cls.getDeclaredMethods():
            if m.getName() == "updateBotButton" and len(m.getParameterTypes()) == 1:
                try:
                    m.setAccessible(True)
                    self.m_update_bot_button = m
                    unhook = self.hook_method(m, UpdateBotButtonHook(self))
                    if unhook:
                        self._hook_objects.append(unhook)
                        self.log("Hooked updateBotButton on ChatActivityEnterView")
                except Exception as e:
                    self.log(f"Error hooking updateBotButton: {e}")
                break

        for m in ev_cls.getDeclaredMethods():
            if m.getName() == "setBotInfo" and len(m.getParameterTypes()) == 2:
                try:
                    m.setAccessible(True)
                    unhook = self.hook_method(m, SetBotInfoHook(self))
                    if unhook:
                        self._hook_objects.append(unhook)
                        self.log("Hooked setBotInfo on ChatActivityEnterView")
                except Exception as e:
                    self.log(f"Error hooking setBotInfo: {e}")
                break

        for m in ev_cls.getDeclaredMethods():
            if m.getName() == "setDialogId" and len(m.getParameterTypes()) == 2:
                try:
                    m.setAccessible(True)
                    unhook = self.hook_method(m, SetDialogIdHook(self))
                    if unhook:
                        self._hook_objects.append(unhook)
                        self.log("Hooked setDialogId on ChatActivityEnterView")
                except Exception as e:
                    self.log(f"Error hooking setDialogId: {e}")
                break

        for m in ev_cls.getDeclaredMethods():
            if m.getName() == "openWebViewMenu" and len(m.getParameterTypes()) == 0:
                try:
                    m.setAccessible(True)
                    unhook = self.hook_method(m, OpenWebViewMenuHook(self))
                    if unhook:
                        self._hook_objects.append(unhook)
                        self.log("Hooked openWebViewMenu on ChatActivityEnterView")
                except Exception as e:
                    self.log(f"Error hooking openWebViewMenu: {e}")
                break

        try:
            ca_cls = Class_cls.forName("org.telegram.ui.ChatActivity")
            for m in ca_cls.getDeclaredMethods():
                if m.getName() == "onResume" and len(m.getParameterTypes()) == 0:
                    m.setAccessible(True)
                    unhook = self.hook_method(m, ChatActivityResumeHook(self))
                    if unhook:
                        self._hook_objects.append(unhook)
                        self.log("Hooked onResume on ChatActivity")
                    break
        except Exception as e:
            self.log(f"Error hooking ChatActivity.onResume: {e}")

    def _refresh_current_chat(self):
        def work():
            try:
                LaunchActivity = jclass("org.telegram.ui.LaunchActivity")
                la = LaunchActivity.instance
                if not la or not la.getActionBarLayout():
                    return
                frag = la.getActionBarLayout().getLastFragment()
                if not frag or not frag.getClass().getName().startswith("org.telegram.ui.ChatActivity"):
                    return
                dialog_id = getattr(frag, "getDialogId", lambda: 0)()
                if not dialog_id:
                    return
                bot_cfg = self.find_bot_config(int(dialog_id))
                if bot_cfg:
                    ev = get_field(frag, "chatActivityEnterView")
                    if ev:
                        if self.apply_bot_menu(ev, int(dialog_id)):
                            self.call_update_bot_button(ev, False)
            except Exception as e:
                self.log(f"_refresh_current_chat error: {e}")
        run_on_ui_thread(work)

    def get_web_view_enum(self, enter_view):
        if self._web_view_enum is not None:
            return self._web_view_enum
        cls_ev = enter_view.getClass()
        f_type = None
        while cls_ev and not f_type:
            try:
                f_type = cls_ev.getDeclaredField("botMenuButtonType")
            except Exception:
                cls_ev = cls_ev.getSuperclass()
        if f_type:
            enum_type = f_type.getType()
            self._web_view_enum = enum_type.getField("WEB_VIEW").get(None)
        return self._web_view_enum

    def apply_bot_menu(self, enter_view, dialog_id: int) -> bool:
        bot_cfg = self.find_bot_config(dialog_id)
        if not bot_cfg:
            return False
        try:
            web_view_val = self.get_web_view_enum(enter_view)
            if web_view_val is not None:
                set_field(enter_view, "botMenuButtonType", web_view_val)
            title = bot_cfg.get("button_text") or bot_cfg.get("bot_title") or "App"
            set_field(enter_view, "botMenuWebViewTitle", title)
            set_field(enter_view, "botMenuWebViewUrl", bot_cfg.get("url", ""))
            return True
        except Exception as e:
            self.log(f"apply_bot_menu error: {e}")
            return False

    def call_update_bot_button(self, enter_view, animated: bool = False):
        def run_update():
            try:
                if not self.m_update_bot_button:
                    cls = enter_view.getClass()
                    while cls and not self.m_update_bot_button:
                        for m in cls.getDeclaredMethods():
                            if m.getName() == "updateBotButton" and len(m.getParameterTypes()) == 1:
                                m.setAccessible(True)
                                self.m_update_bot_button = m
                                break
                        cls = cls.getSuperclass()
                if self.m_update_bot_button:
                    self.m_update_bot_button.invoke(enter_view, animated)
            except Exception as e:
                self.log(f"call_update_bot_button error: {e}")
        run_on_ui_thread(run_update)

    def load_config(self):
        try:
            raw = self.get_setting("bots_config", None)
            if raw and isinstance(raw, str):
                self._bots = json.loads(raw)
            elif raw and isinstance(raw, list):
                self._bots = raw
            else:
                self._bots = [dict(b) for b in DEFAULT_CONFIG]
        except Exception as e:
            self.log(f"Error loading bots config: {e}")
            self._bots = [dict(b) for b in DEFAULT_CONFIG]

        for b_idx, bot in enumerate(self._bots):
            if not bot.get("id"):
                bot["id"] = f"bot_{b_idx}_{int(time.time())}"

    def save_config(self, reload_ui: bool = False):
        try:
            self.set_setting("bots_config", json.dumps(self._bots), reload_settings=reload_ui)
        except Exception as e:
            self.log(f"Error saving bots config: {e}")

    def find_bot_config(self, dialog_id: int) -> Optional[Dict[str, Any]]:
        if not dialog_id:
            return None
        for bot in self._bots:
            conf_id = bot.get("bot_id", "")
            if matches_bot_id(conf_id, dialog_id, UserConfig.selectedAccount):
                return bot
        return None

    def is_remember_enabled(self, bot: Dict[str, Any]) -> bool:
        bot_id = str(bot.get("id", "bot_1"))
        direct = self.get_setting(f"remember_{bot_id}", None)
        if direct is not None:
            return bool(direct)
        val = bot.get("remember_last_page", False)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    def get_bot_last_url(self, bot: Dict[str, Any]) -> str:
        bot_id = str(bot.get("id", "bot_1"))
        saved = self.get_setting(f"last_url_{bot_id}", "")
        if saved:
            return str(saved).strip()
        return str(bot.get("last_url", "")).strip()

    def set_bot_last_url(self, bot: Dict[str, Any], url_str: str):
        bot_id = str(bot.get("id", "bot_1"))
        cleaned = str(url_str).strip()
        bot["last_url"] = cleaned
        self.set_setting(f"last_url_{bot_id}", cleaned)
        self.save_config(reload_ui=False)

    def open_bot_web_view(self, context: Context, bot_cfg: Dict[str, Any]):
        activity = get_activity_from_context(context)
        if not activity:
            self.log("Cannot open web view: activity context not found")
            return

        def do_open():
            try:
                base_url = str(bot_cfg.get("url", "")).strip()
                if not base_url:
                    return
                if not (base_url.startswith("http://") or base_url.startswith("https://")):
                    base_url = "https://" + base_url

                remember = self.is_remember_enabled(bot_cfg)
                last_url = self.get_bot_last_url(bot_cfg)

                if remember and last_url and domains_match(last_url, base_url):
                    url_target = last_url
                else:
                    url_target = base_url

                builder = BottomSheet.Builder(activity, True)
                builder.setApplyBottomPadding(False)
                builder.setApplyTopPadding(False)

                root = LinearLayout(activity)
                root.setOrientation(LinearLayout.VERTICAL)
                root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

                header = LinearLayout(activity)
                header.setOrientation(LinearLayout.HORIZONTAL)
                header.setGravity(Gravity.CENTER_VERTICAL)
                header.setPadding(dp(16), dp(8), dp(16), dp(8))
                header.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

                titles_col = LinearLayout(activity)
                titles_col.setOrientation(LinearLayout.VERTICAL)

                bot_title_text = bot_cfg.get("bot_title") or bot_cfg.get("button_text") or "App"
                header_title = TextView(activity)
                header_title.setText(bot_title_text)
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

                progress_bar = ProgressBar(activity, None, 16842872)
                progress_bar.setMax(100)
                progress_bar.setLayoutParams(LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)))
                root.addView(progress_bar)

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
                    cookie_manager = CookieManager.getInstance()
                    cookie_manager.setAcceptCookie(True)
                    cookie_manager.setAcceptThirdPartyCookies(webview, True)
                except Exception:
                    pass

                def on_progress(p: int):
                    try:
                        progress_bar.setProgress(p)
                        progress_bar.setVisibility(View.GONE if p >= 100 else View.VISIBLE)
                    except Exception:
                        pass

                def handle_url_change(view, curr_url: str):
                    try:
                        if not curr_url:
                            return
                        p = urllib.parse.urlparse(curr_url)
                        d = p.netloc or p.path
                        if d:
                            header_sub.setText(d)
                        if self.is_remember_enabled(bot_cfg) and is_url_allowed_for_bot(curr_url, base_url):
                            self.set_bot_last_url(bot_cfg, curr_url)
                    except Exception as e:
                        self.log(f"handle_url_change error: {e}")

                chrome_inst = BotChromeClient.new_instance()
                chrome_inst.on_progress = on_progress
                webview.setWebChromeClient(chrome_inst.java)

                web_inst = BotWebClient.new_instance()
                web_inst.on_finish = handle_url_change
                web_inst.on_url_change = handle_url_change
                webview.setWebViewClient(web_inst.java)

                webview.loadUrl(url_target)
                root.addView(webview)

                builder.setCustomView(root)
                sheet = builder.create()
                try:
                    sheet.setCanDismissWithSwipe(False)
                except Exception:
                    pass
                try:
                    sheet.setAllowNestedScroll(False)
                except Exception:
                    pass
                sheet_ref[0] = sheet

                touch_listener = WebTouchListener()
                root.setOnTouchListener(touch_listener)
                webview.setOnTouchListener(touch_listener)

                def on_dismiss():
                    try:
                        if self.is_remember_enabled(bot_cfg) and web_ref[0]:
                            curr_url = str(web_ref[0].getUrl() or "").strip()
                            if is_url_allowed_for_bot(curr_url, base_url):
                                self.set_bot_last_url(bot_cfg, curr_url)
                        try:
                            CookieManager.getInstance().flush()
                        except Exception:
                            pass
                        if web_ref[0]:
                            web_ref[0].stopLoading()
                            web_ref[0].destroy()
                    except Exception as e:
                        self.log(f"on_dismiss error: {e}")

                sheet.setOnDismissListener(OnDismissListenerProxy(on_dismiss))
                sheet.show()
            except Exception as e:
                self.log(f"Error opening bot web view: {e}")

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

    def create_settings(self) -> List[Any]:
        settings_rows: List[Any] = []

        for b_idx, bot in enumerate(self._bots):
            b_title = bot.get("bot_title", "") or bot.get("bot_id", "") or tr("Новый бот", "New bot")
            settings_rows.append(Header(tr(f"Бот #{b_idx + 1}: {b_title}", f"Bot #{b_idx + 1}: {b_title}")))

            settings_rows.append(
                Input(
                    key=f"b_{b_idx}_title",
                    text=tr("Имя бота", "Bot title"),
                    default=str(bot.get("bot_title", "")),
                    icon="msg_edit",
                    on_change=lambda val, b=b_idx: self.update_bot_field(b, "bot_title", val),
                )
            )

            settings_rows.append(
                Input(
                    key=f"b_{b_idx}_id",
                    text=tr("Bot ID", "Bot ID"),
                    default=str(bot.get("bot_id", "")),
                    subtext=tr("Например: 772433176 или @bot", "E.g.: 772433176 or @bot"),
                    icon="msg_groups",
                    on_change=lambda val, b=b_idx: self.update_bot_field(b, "bot_id", val),
                )
            )

            settings_rows.append(
                Input(
                    key=f"b_{b_idx}_btn",
                    text=tr("Текст кнопки", "Button text"),
                    default=str(bot.get("button_text", "Open App")),
                    subtext=tr("Например: Open App", "E.g.: Open App"),
                    icon="msg_edit",
                    on_change=lambda val, b=b_idx: self.update_bot_field(b, "button_text", val),
                )
            )

            settings_rows.append(
                Input(
                    key=f"b_{b_idx}_url",
                    text=tr("URL", "URL"),
                    default=str(bot.get("url", "")),
                    subtext=tr("Например: https://example.com", "E.g.: https://example.com"),
                    icon="msg_link",
                    on_change=lambda val, b=b_idx: self.update_bot_field(b, "url", val),
                )
            )

            settings_rows.append(
                Switch(
                    key=f"b_{b_idx}_rem",
                    text=tr("Запоминать последнюю страницу", "Remember last open page"),
                    default=self.is_remember_enabled(bot),
                    icon="msg_recent",
                    on_change=lambda val, b=b_idx: self.update_bot_rem(b, val),
                )
            )

            last_saved = self.get_bot_last_url(bot)
            if last_saved:
                settings_rows.append(
                    Text(
                        text=tr("Сбросить сохранённую страницу", "Reset saved page"),
                        subtext=tr(f"Сохранено: {last_saved}", f"Saved: {last_saved}"),
                        icon="msg_retry",
                        on_click=lambda view, b=b_idx: self.reset_last_url(b),
                    )
                )

            if len(self._bots) > 1:
                settings_rows.append(
                    Text(
                        text=tr("Удалить этого бота", "Delete this bot"),
                        red=True,
                        icon="msg_delete",
                        on_click=lambda view, b=b_idx: self.delete_bot(b),
                    )
                )

        settings_rows.append(Divider())
        settings_rows.append(
            Text(
                text=tr("+ Добавить ещё одного бота", "+ Add another bot"),
                accent=True,
                icon="msg_add",
                on_click=lambda view: self.add_bot(),
            )
        )

        return settings_rows

    def update_bot_field(self, b_idx: int, field: str, val: Any):
        if 0 <= b_idx < len(self._bots):
            self._bots[b_idx][field] = str(val).strip()
            self.save_config(reload_ui=False)

    def update_bot_rem(self, b_idx: int, val: bool):
        if 0 <= b_idx < len(self._bots):
            bot = self._bots[b_idx]
            bot["remember_last_page"] = bool(val)
            bot_id = str(bot.get("id", f"bot_{b_idx + 1}"))
            self.set_setting(f"remember_{bot_id}", bool(val))
            if not val:
                bot["last_url"] = ""
                self.set_setting(f"last_url_{bot_id}", "")
            self.save_config(reload_ui=True)

    def reset_last_url(self, b_idx: int):
        if 0 <= b_idx < len(self._bots):
            bot = self._bots[b_idx]
            bot["last_url"] = ""
            bot_id = str(bot.get("id", f"bot_{b_idx + 1}"))
            self.set_setting(f"last_url_{bot_id}", "")
            self.save_config(reload_ui=True)

    def add_bot(self):
        new_idx = len(self._bots) + 1
        self._bots.append({
            "id": f"bot_{new_idx}_{int(time.time())}",
            "bot_title": "",
            "bot_id": "",
            "button_text": "Open App",
            "url": "",
            "remember_last_page": False,
            "last_url": "",
        })
        self.save_config(reload_ui=True)

    def delete_bot(self, b_idx: int):
        if 0 <= b_idx < len(self._bots) and len(self._bots) > 1:
            self._bots.pop(b_idx)
            self.save_config(reload_ui=True)
