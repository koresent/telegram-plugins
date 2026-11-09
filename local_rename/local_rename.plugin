# -*- coding: utf-8 -*-
"""
Local Renamer for exteraGram / AyuGram
Purely visual replacement of display names for bots, groups, channels, and users.
"""

import json
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from android.content import Context, ContextWrapper
from android.view import View
from android.widget import EditText, LinearLayout, TextView
from java import jclass, jint, jlong
from java.lang import String as JString
from org.telegram.messenger import (
    AndroidUtilities,
    ApplicationLoader,
    MessagesController,
    NotificationCenter,
    UserConfig,
)
from org.telegram.ui.ActionBar import Theme

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MenuItemData, MenuItemType, MethodHook
from client_utils import get_last_fragment
from hook_utils import find_class
from ui.alert import AlertDialogBuilder
from ui.bulletin import BulletinHelper
from ui.settings import Divider, Header, Text

__id__ = "local_rename"
__name__ = "Local Renamer"
__description__ = "Purely visual local display name overrides for bots, groups, channels, and users"
__author__ = "@koresent"
__version__ = "1.0.4"
__icon__ = "exteraPlugins/1"
__category__ = ["appearance", "chats"]
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"

CONFIG_KEY = "overrides_v2"
CHANNEL_OFFSET = 1000000000000

# Shared module-level cache so any instance (background or settings UI) shares data
_CONFIG: Dict[str, Dict[str, Dict[str, str]]] = {
    "users": {},
    "chats": {},
    "usernames": {},
}


def debug_log(msg: str):
    try:
        ctx = ApplicationLoader.applicationContext
        if ctx:
            ext = ctx.getExternalFilesDir(None)
            if ext:
                path = ext.getAbsolutePath() + "/rename_debug.log"
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _dialog_to_chat_id(dialog_id: int) -> int:
    if dialog_id <= -CHANNEL_OFFSET:
        return -CHANNEL_OFFSET - dialog_id
    return -dialog_id


def safe_get(ctx: Any, key: str, default: Any = None) -> Any:
    """
    Safely retrieves a value by key from either a Python dict
    or a Java Map (java.util.HashMap / ConcurrentHashMap).
    """
    if ctx is None:
        return default
    if hasattr(ctx, "get"):
        try:
            val = ctx.get(key)
            if val is not None:
                return val
        except Exception:
            pass
    if hasattr(ctx, key):
        try:
            val = getattr(ctx, key)
            if val is not None:
                return val
        except Exception:
            pass
    return default


def java_to_list(container: Any) -> list:
    """
    Safely convert Java collections, ArrayList, ValuesView, arrays,
    or iterables into a standard Python list.
    """
    if container is None:
        return []
    if isinstance(container, (list, tuple)):
        return list(container)
    if hasattr(container, "toArray"):
        try:
            return list(container.toArray())
        except Exception:
            pass
    if hasattr(container, "size") and hasattr(container, "get"):
        try:
            sz = int(container.size())
            return [container.get(i) for i in range(sz)]
        except Exception:
            pass
    if hasattr(container, "iterator"):
        try:
            it = container.iterator()
            items = []
            while it.hasNext():
                items.append(it.next())
            return items
        except Exception:
            pass
    return []


def iterate_cached_objects(container: Any) -> list:
    """
    Safely extracts all objects from MessagesController.users or .chats
    regardless of whether it is a ConcurrentHashMap or LongSparseArray.
    """
    if container is None:
        return []
    if hasattr(container, "values"):
        try:
            return java_to_list(container.values())
        except Exception:
            pass
    if hasattr(container, "size") and hasattr(container, "valueAt"):
        try:
            sz = int(container.size())
            return [container.valueAt(i) for i in range(sz) if container.valueAt(i) is not None]
        except Exception:
            pass
    return java_to_list(container)


def get_activity():
    try:
        frag = get_last_fragment()
        if frag and hasattr(frag, "getParentActivity") and frag.getParentActivity():
            return frag.getParentActivity()
    except Exception:
        pass
    try:
        LaunchActivity = jclass("org.telegram.ui.LaunchActivity")
        if LaunchActivity.instance is not None:
            return LaunchActivity.instance
    except Exception:
        pass
    return None


class CacheHook(MethodHook):
    def __init__(self, plugin: "LocalRenamePlugin", kind: str, is_batch: bool):
        super().__init__()
        self.plugin = plugin
        self.kind = kind
        self.is_batch = is_batch

    def before_hooked_method(self, param):
        if not self.plugin.is_active:
            return
        try:
            arg = param.args[0]
            if arg is None:
                return
            if self.is_batch:
                for obj in java_to_list(arg):
                    self.plugin.apply_override(self.kind, obj)
            else:
                self.plugin.apply_override(self.kind, arg)
        except Exception as e:
            debug_log(f"CacheHook {self.kind} error: {e}")


class UserNameHook(MethodHook):
    def __init__(self, plugin: "LocalRenamePlugin"):
        super().__init__()
        self.plugin = plugin

    def before_hooked_method(self, param):
        if not self.plugin.is_active:
            return
        try:
            args = param.args
            if not args or len(args) == 0:
                return
            user = args[0]
            if user is not None:
                ov = self.plugin.get_user_override(user)
                if ov and ov.get("name"):
                    param.setResult(JString(str(ov["name"])))
        except Exception as e:
            debug_log(f"UserNameHook error: {e}")


class LocalRenamePlugin(BasePlugin):
    def log(self, text: str):
        debug_log(str(text))
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
        self._unhooks: List[Any] = []
        self._users: Dict[str, Dict[str, str]] = _CONFIG["users"]
        self._chats: Dict[str, Dict[str, str]] = _CONFIG["chats"]
        self._usernames: Dict[str, Dict[str, str]] = _CONFIG["usernames"]
        # In-memory original values: (kind, str(id)) -> {"field": original_value}
        self._originals: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # Ensure config is loaded on any newly instantiated instance (including settings activity)
        self.load_config()

    def on_plugin_load(self):
        self.is_active = True
        self.log("on_plugin_load started")
        self.load_config()
        self._install_hooks()
        self._install_menu()
        self.apply_all()
        self.log("LocalRenamePlugin successfully loaded")

    def on_plugin_unload(self):
        self.is_active = False
        for u in self._unhooks:
            try:
                self.unhook_method(u)
            except Exception:
                pass
        self._unhooks.clear()
        self.restore_all()
        self.refresh_ui()
        self.log("LocalRenamePlugin successfully unloaded")

    # ---------- Storage ----------

    def load_config(self):
        try:
            raw = self.get_setting(CONFIG_KEY, "{}")
            if isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {}
            elif isinstance(raw, dict):
                data = raw
            else:
                data = {}

            # Also check fallback if empty
            if not data:
                raw_old = self.get_setting("overrides_config", None)
                if raw_old:
                    if isinstance(raw_old, str):
                        try:
                            old_data = json.loads(raw_old)
                        except Exception:
                            old_data = []
                    elif isinstance(raw_old, list):
                        old_data = raw_old
                    else:
                        old_data = []
                    if isinstance(old_data, list):
                        for item in old_data:
                            tgt = str(item.get("target", "")).strip()
                            nm = str(item.get("name", "")).strip()
                            if nm and tgt:
                                if tgt.startswith("@"):
                                    _CONFIG["usernames"][tgt.lstrip("@").lower()] = {
                                        "kind": "user",
                                        "name": nm,
                                        "was": item.get("orig_name", ""),
                                    }
                                elif tgt.lstrip("-").isdigit():
                                    did = int(tgt)
                                    if did > 0:
                                        _CONFIG["users"][str(did)] = {
                                            "name": nm,
                                            "target": tgt,
                                            "was": item.get("orig_name", ""),
                                        }
                                    else:
                                        cid = _dialog_to_chat_id(did)
                                        _CONFIG["chats"][str(cid)] = {
                                            "name": nm,
                                            "target": tgt,
                                            "was": item.get("orig_name", ""),
                                        }
            else:
                _CONFIG["users"] = {str(k): dict(v) for k, v in data.get("users", {}).items() if isinstance(v, dict)}
                _CONFIG["chats"] = {str(k): dict(v) for k, v in data.get("chats", {}).items() if isinstance(v, dict)}
                _CONFIG["usernames"] = {str(k).lower().lstrip("@"): dict(v) for k, v in data.get("usernames", {}).items() if isinstance(v, dict)}

            self._users = _CONFIG["users"]
            self._chats = _CONFIG["chats"]
            self._usernames = _CONFIG["usernames"]
            self.log(f"Config loaded: {len(self._users)} users, {len(self._chats)} chats, {len(self._usernames)} usernames")
        except Exception as e:
            self.log(f"load_config error: {e}\n{traceback.format_exc()}")

    def save_config(self, reload_ui: bool = True):
        try:
            data = {
                "users": self._users,
                "chats": self._chats,
                "usernames": self._usernames,
            }
            json_str = json.dumps(data, ensure_ascii=False)
            self.set_setting(CONFIG_KEY, json_str, reload_settings=reload_ui)
            self.log(f"Config saved ({len(self._users)} users, {len(self._chats)} chats)")
        except Exception as e:
            self.log(f"save_config error: {e}")

    # ---------- Hooks ----------

    def _install_hooks(self):
        try:
            mc_cls = find_class("org.telegram.messenger.MessagesController")
            if mc_cls is None:
                self.log("MessagesController class not found")
                return

            # Hook putUser, putUsers, putChat, putChats
            table = (
                ("putUser", "user", False),
                ("putUsers", "user", True),
                ("putChat", "chat", False),
                ("putChats", "chat", True),
            )
            methods = []
            if hasattr(mc_cls, "getClass"):
                try:
                    methods = list(mc_cls.getClass().getDeclaredMethods())
                except Exception:
                    pass
            if not methods and hasattr(mc_cls, "getDeclaredMethods"):
                try:
                    methods = list(mc_cls.getDeclaredMethods())
                except Exception:
                    pass

            for m in methods:
                m_name = m.getName()
                for name, kind, is_batch in table:
                    if m_name == name:
                        m.setAccessible(True)
                        h = self.hook_method(m, CacheHook(self, kind, is_batch))
                        if h:
                            self._unhooks.append(h)

            # Hook UserObject.getUserName
            uo_cls = find_class("org.telegram.messenger.UserObject")
            if uo_cls is not None:
                uo_methods = []
                if hasattr(uo_cls, "getClass"):
                    try:
                        uo_methods = list(uo_cls.getClass().getDeclaredMethods())
                    except Exception:
                        pass
                if not uo_methods and hasattr(uo_cls, "getDeclaredMethods"):
                    try:
                        uo_methods = list(uo_cls.getDeclaredMethods())
                    except Exception:
                        pass

                for m in uo_methods:
                    if m.getName() == "getUserName" and len(m.getParameterTypes()) >= 1:
                        m.setAccessible(True)
                        h = self.hook_method(m, UserNameHook(self))
                        if h:
                            self._unhooks.append(h)

            self.log(f"Installed {len(self._unhooks)} hooks")
        except Exception as e:
            self.log(f"_install_hooks error: {e}\n{traceback.format_exc()}")

    # ---------- Override Application ----------

    def get_user_override(self, user: Any) -> Optional[Dict[str, str]]:
        if not user or not self.is_active:
            return None
        uid = str(getattr(user, "id", ""))
        if uid and uid in self._users:
            return self._users[uid]

        # Match by main username
        uname = str(getattr(user, "username", "") or "").lower().lstrip("@")
        if uname and uname in self._usernames:
            ov = self._usernames[uname]
            if uid:
                self._users[uid] = {"name": ov["name"], "target": f"@{uname}", "was": ov.get("was", "")}
            return ov

        # Match by collectible / additional usernames
        other_unames = getattr(user, "usernames", None)
        if other_unames:
            for u in java_to_list(other_unames):
                alt = str(getattr(u, "username", "") or "").lower().lstrip("@")
                if alt and alt in self._usernames:
                    ov = self._usernames[alt]
                    if uid:
                        self._users[uid] = {"name": ov["name"], "target": f"@{alt}", "was": ov.get("was", "")}
                    return ov

        return None

    def get_chat_override(self, chat: Any) -> Optional[Dict[str, str]]:
        if not chat or not self.is_active:
            return None
        cid = str(getattr(chat, "id", ""))
        if cid and cid in self._chats:
            return self._chats[cid]

        # Match by main username
        uname = str(getattr(chat, "username", "") or "").lower().lstrip("@")
        if uname and uname in self._usernames:
            ov = self._usernames[uname]
            if cid:
                self._chats[cid] = {"name": ov["name"], "target": f"@{uname}", "was": ov.get("was", "")}
            return ov

        # Match by additional usernames
        other_unames = getattr(chat, "usernames", None)
        if other_unames:
            for u in java_to_list(other_unames):
                alt = str(getattr(u, "username", "") or "").lower().lstrip("@")
                if alt and alt in self._usernames:
                    ov = self._usernames[alt]
                    if cid:
                        self._chats[cid] = {"name": ov["name"], "target": f"@{alt}", "was": ov.get("was", "")}
                    return ov

        return None

    def apply_override(self, kind: str, obj: Any):
        if not obj or not self.is_active:
            return
        try:
            if kind == "user":
                ov = self.get_user_override(obj)
                if not ov:
                    return
                new_name = ov.get("name")
                if not new_name:
                    return
                uid = str(getattr(obj, "id", ""))
                curr_first = getattr(obj, "first_name", None)
                curr_last = getattr(obj, "last_name", None)
                if (kind, uid) not in self._originals:
                    self._originals[(kind, uid)] = {
                        "first_name": curr_first,
                        "last_name": curr_last,
                    }
                setattr(obj, "first_name", JString(new_name))
                setattr(obj, "last_name", JString(""))
            elif kind == "chat":
                ov = self.get_chat_override(obj)
                if not ov:
                    return
                new_title = ov.get("name")
                if not new_title:
                    return
                cid = str(getattr(obj, "id", ""))
                curr_title = getattr(obj, "title", None)
                if (kind, cid) not in self._originals:
                    self._originals[(kind, cid)] = {
                        "title": curr_title,
                    }
                setattr(obj, "title", JString(new_title))
        except Exception as e:
            self.log(f"apply_override {kind} error: {e}")

    def restore_object(self, kind: str, obj_id: str, account: int):
        saved = self._originals.pop((kind, obj_id), None)
        obj = self.get_cached_object(kind, obj_id, account)
        if obj is not None and saved:
            for field, val in saved.items():
                try:
                    setattr(obj, field, val if val is not None else JString(""))
                except Exception as e:
                    self.log(f"restore error: {e}")
        else:
            self._reload_from_server(kind, obj_id, account)

    def _reload_from_server(self, kind: str, obj_id: str, account: int):
        try:
            mc = MessagesController.getInstance(account)
            frag = get_last_fragment()
            guid = frag.getClassGuid() if frag is not None and hasattr(frag, "getClassGuid") else 0
            if kind == "user":
                user = mc.getUser(jlong(int(obj_id)))
                if user is not None:
                    mc.loadFullUser(user, guid, True)
            else:
                mc.loadFullChat(jlong(int(obj_id)), guid, True)
        except Exception as e:
            self.log(f"server reload error: {e}")

    def apply_all(self):
        if not self.is_active:
            return
        for account in range(UserConfig.MAX_ACCOUNT_COUNT):
            try:
                mc = MessagesController.getInstance(account)
                if not mc:
                    continue
                # Traverse cached users
                if mc.users:
                    for u in iterate_cached_objects(mc.users):
                        self.apply_override("user", u)

                # Traverse cached chats
                if mc.chats:
                    for c in iterate_cached_objects(mc.chats):
                        self.apply_override("chat", c)
            except Exception as e:
                self.log(f"apply_all error on acc {account}: {e}")
        self.refresh_ui()

    def restore_all(self):
        for account in range(UserConfig.MAX_ACCOUNT_COUNT):
            for (kind, obj_id) in list(self._originals.keys()):
                self.restore_object(kind, obj_id, account)
        self._originals.clear()

    def get_cached_object(self, kind: str, obj_id: str, account: int) -> Optional[Any]:
        try:
            mc = MessagesController.getInstance(account)
            if not mc:
                return None
            num_id = int(obj_id)
            if kind == "user":
                return mc.getUser(jlong(num_id))
            return mc.getChat(jlong(num_id))
        except Exception:
            return None

    def refresh_ui(self, account: int = 0):
        def run():
            try:
                nc = NotificationCenter.getInstance(account)
                if nc:
                    mask = (
                        getattr(MessagesController, "UPDATE_MASK_NAME", 1)
                        | getattr(MessagesController, "UPDATE_MASK_CHAT_NAME", 16)
                        | getattr(MessagesController, "UPDATE_MASK_CHAT", 8192)
                    )
                    nc.postNotificationName(NotificationCenter.updateInterfaces, jint(mask))
                    nc.postNotificationName(NotificationCenter.dialogsNeedReload)
                    nc.postNotificationName(NotificationCenter.dialogsUnreadCounterChanged)
                    nc.postNotificationName(NotificationCenter.mainUserInfoChanged)
            except Exception as e:
                self.log(f"refresh_ui notification error: {e}")

            try:
                frag = get_last_fragment()
                if frag is not None:
                    getter = getattr(frag, "getChatListView", None)
                    if getter:
                        lv = getter()
                        if lv:
                            lv.invalidate()
                            if lv.getAdapter():
                                lv.getAdapter().notifyDataSetChanged()
                    if hasattr(frag, "updateSubtitle"):
                        frag.updateSubtitle()
                    ab = getattr(frag, "actionBar", None)
                    if ab:
                        ab.invalidate()
            except Exception as e:
                self.log(f"refresh_ui fragment error: {e}")

        run_on_ui_thread(run)

    # ---------- Menu & Editor ----------

    def _install_menu(self):
        for type_name in ("PROFILE_ACTION_MENU", "CHAT_ACTION_MENU"):
            menu_type = getattr(MenuItemType, type_name, None)
            if menu_type is not None:
                try:
                    self.add_menu_item(
                        MenuItemData(
                            menu_type=menu_type,
                            text="Rename locally",
                            icon="msg_edit",
                            on_click=self._on_menu_click,
                        )
                    )
                except Exception as e:
                    self.log(f"Menu item registration failed for {type_name}: {e}")

    def _resolve_target(self, context: Any) -> Optional[Tuple[str, str, int]]:
        account = safe_get(context, "account")
        if not isinstance(account, int):
            try:
                account = UserConfig.selectedAccount
            except Exception:
                account = 0

        user = safe_get(context, "user")
        chat = safe_get(context, "chat")
        if user and getattr(user, "id", None):
            return "user", str(user.id), account
        if chat and getattr(chat, "id", None):
            return "chat", str(chat.id), account

        user_id = safe_get(context, "user_id") or safe_get(context, "userId")
        chat_id = safe_get(context, "chat_id") or safe_get(context, "chatId")
        dialog_id = safe_get(context, "dialog_id") or safe_get(context, "dialogId")

        if user_id:
            return "user", str(abs(int(user_id))), account
        if chat_id:
            return "chat", str(abs(int(chat_id))), account

        if not dialog_id:
            try:
                frag = get_last_fragment()
                if frag:
                    if hasattr(frag, "currentUser") and frag.currentUser:
                        return "user", str(frag.currentUser.id), account
                    if hasattr(frag, "currentChat") and frag.currentChat:
                        return "chat", str(frag.currentChat.id), account
                    if hasattr(frag, "getDialogId"):
                        dialog_id = frag.getDialogId()
                    elif hasattr(frag, "dialog_id"):
                        dialog_id = frag.dialog_id
            except Exception:
                dialog_id = None

        if dialog_id:
            d_val = int(dialog_id)
            if d_val > 0:
                return "user", str(d_val), account
            return "chat", str(_dialog_to_chat_id(d_val)), account

        return None

    def _on_menu_click(self, context: Any):
        try:
            self.log(f"Menu clicked with context: {context}")
            target = self._resolve_target(context)
            if target is None:
                BulletinHelper.show_error("Could not determine peer")
                return
            kind, obj_id, account = target
            self.show_editor(kind, obj_id, account)
        except Exception as e:
            self.log(f"_on_menu_click error: {e}\n{traceback.format_exc()}")
            BulletinHelper.show_error("Failed to open editor")

    def show_editor(self, kind: str, obj_id: str, account: int):
        def build():
            try:
                activity = get_activity()
                if activity is None:
                    self.log("show_editor: Activity not found")
                    BulletinHelper.show_error("Could not find window")
                    return

                store = self._users if kind == "user" else self._chats
                existing_ov = store.get(obj_id, {})
                cached = self.get_cached_object(kind, obj_id, account)

                # Get original name
                saved = self._originals.get((kind, obj_id), {})
                if kind == "user":
                    f_name = saved.get("first_name", getattr(cached, "first_name", None)) if cached else ""
                    l_name = saved.get("last_name", getattr(cached, "last_name", None)) if cached else ""
                    was = f"{f_name or ''} {l_name or ''}".strip()
                else:
                    was = saved.get("title", getattr(cached, "title", None)) if cached else ""
                was = was or existing_ov.get("was") or "Unknown"

                uname = str(getattr(cached, "username", "") or "")
                current_target = f"@{uname}" if uname else obj_id

                layout = LinearLayout(activity)
                layout.setOrientation(LinearLayout.VERTICAL)
                pad_h = AndroidUtilities.dp(24)
                pad_v = AndroidUtilities.dp(16)
                layout.setPadding(pad_h, pad_v, pad_h, pad_v)

                info = TextView(activity)
                type_name = "Bot / User" if kind == "user" else "Channel / Group"
                info.setText(f"{type_name}: {was}\nID: {obj_id}")
                info.setTextSize(14.0)
                info.setTextColor(Theme.getColor(Theme.key_dialogTextGray2))
                info.setPadding(0, 0, 0, AndroidUtilities.dp(12))
                layout.addView(info)

                edit = EditText(activity)
                edit.setHint("New display name")
                edit.setSingleLine(True)
                edit.setTextSize(16.0)
                edit.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                edit.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))

                prefill = existing_ov.get("name") or was
                if prefill and prefill != "Unknown":
                    edit.setText(str(prefill))
                    edit.setSelection(edit.length())
                layout.addView(edit)

                def on_save(dialog, which):
                    new_val = str(edit.getText().toString()).strip()
                    if new_val:
                        self.set_override(kind, obj_id, current_target, new_val, was, account)
                        BulletinHelper.show_success(f"Name changed to \"{new_val}\"")
                    else:
                        self.remove_override(kind, obj_id, account)
                        BulletinHelper.show_info("Original name restored")
                    dialog.dismiss()

                def on_reset(dialog, which):
                    self.remove_override(kind, obj_id, account)
                    BulletinHelper.show_info("Original name restored")
                    dialog.dismiss()

                builder = AlertDialogBuilder(activity)
                builder.set_title("Rename locally")
                builder.set_view(layout)
                builder.set_positive_button("Save", on_save)
                if obj_id in store:
                    builder.set_neutral_button("Reset", on_reset)
                    builder.make_button_red(AlertDialogBuilder.BUTTON_NEUTRAL)
                builder.set_negative_button("Cancel", lambda d, w: d.dismiss())
                builder.show()

                edit.requestFocus()
                AndroidUtilities.showKeyboard(edit)
            except Exception as e:
                self.log(f"show_editor build error: {e}\n{traceback.format_exc()}")
                BulletinHelper.show_error("Could not show dialog")

        run_on_ui_thread(build)

    def set_override(self, kind: str, obj_id: str, target: str, name: str, was: str, account: int):
        store = self._users if kind == "user" else self._chats
        store[obj_id] = {
            "name": name,
            "target": target,
            "was": was,
        }
        if target.startswith("@"):
            clean_u = target.lstrip("@").lower()
            self._usernames[clean_u] = {"kind": kind, "name": name, "was": was}

        self.save_config(reload_ui=True)
        obj = self.get_cached_object(kind, obj_id, account)
        if obj is not None:
            self.apply_override(kind, obj)
        self.apply_all()
        self.refresh_ui(account)

    def remove_override(self, kind: str, obj_id: str, account: int):
        store = self._users if kind == "user" else self._chats
        ov = store.pop(obj_id, None)
        if ov and ov.get("target", "").startswith("@"):
            clean_u = ov["target"].lstrip("@").lower()
            self._usernames.pop(clean_u, None)

        self.restore_object(kind, obj_id, account)
        self.save_config(reload_ui=True)
        self.apply_all()
        self.refresh_ui(account)

    # ---------- Settings UI ----------

    def create_settings(self) -> List[Any]:
        # Always reload freshest config when settings page is built
        self.load_config()
        self.log(f"create_settings: {len(self._users)} users, {len(self._chats)} chats")

        rows: List[Any] = []
        rows.append(Header("Local Renamer"))
        rows.append(
            Divider(
                text="Purely visual local replacement of bot, group, channel, and user names in client.\n\n"
                     "You can rename any peer directly from the (⋮) menu in chat or profile, "
                     "or configure overrides manually below."
            )
        )

        total_count = len(self._users) + len(self._chats)
        if total_count == 0:
            rows.append(
                Divider(text="No active overrides yet. Tap '+ Add override manually' below or open any chat/profile menu.")
            )
        else:
            if self._users:
                rows.append(Header(f"Bots & Users ({len(self._users)})"))
                for uid, item in list(self._users.items()):
                    rows.append(self._make_setting_row("user", uid, item))

            if self._chats:
                rows.append(Header(f"Groups & Channels ({len(self._chats)})"))
                for cid, item in list(self._chats.items()):
                    rows.append(self._make_setting_row("chat", cid, item))

        rows.append(Divider())
        rows.append(
            Text(
                text="+ Add override manually",
                accent=True,
                icon="msg_add",
                on_click=lambda v: self._show_manual_dialog(),
            )
        )

        if total_count > 0:
            rows.append(Divider())
            rows.append(
                Text(
                    text="Reset all overrides",
                    red=True,
                    icon="msg_retry",
                    on_click=lambda v: self._confirm_reset_all(),
                )
            )

        return rows

    def _make_setting_row(self, kind: str, obj_id: str, item: Dict[str, str]):
        name = item.get("name", "Unnamed")
        target = item.get("target", obj_id)
        was = item.get("was")
        sub = f"Target: {target}"
        if was and was != "Unknown":
            sub += f" | Original: {was}"

        return Text(
            text=name,
            subtext=sub,
            icon="msg_edit",
            on_click=lambda v, k=kind, i=obj_id: self.show_editor(k, i, UserConfig.selectedAccount),
        )

    def _show_manual_dialog(self):
        def build():
            try:
                activity = get_activity()
                if not activity:
                    return

                layout = LinearLayout(activity)
                layout.setOrientation(LinearLayout.VERTICAL)
                pad_h = AndroidUtilities.dp(24)
                pad_v = AndroidUtilities.dp(16)
                layout.setPadding(pad_h, pad_v, pad_h, pad_v)

                desc = TextView(activity)
                desc.setText("Enter target ID (e.g. 1029384756 or -1002938475610) or @username:")
                desc.setTextSize(14.0)
                desc.setTextColor(Theme.getColor(Theme.key_dialogTextGray2))
                desc.setPadding(0, 0, 0, AndroidUtilities.dp(8))
                layout.addView(desc)

                target_edit = EditText(activity)
                target_edit.setHint("Target (@username or ID)")
                target_edit.setSingleLine(True)
                target_edit.setTextSize(16.0)
                target_edit.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                target_edit.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))
                layout.addView(target_edit)

                name_edit = EditText(activity)
                name_edit.setHint("New display name")
                name_edit.setSingleLine(True)
                name_edit.setTextSize(16.0)
                name_edit.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                name_edit.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))
                layout.addView(name_edit)

                def on_save(dialog, which):
                    raw_target = str(target_edit.getText().toString()).strip()
                    new_name = str(name_edit.getText().toString()).strip()
                    if raw_target and new_name:
                        self._apply_manual_entry(raw_target, new_name)
                    dialog.dismiss()

                builder = AlertDialogBuilder(activity)
                builder.set_title("Add override manually")
                builder.set_view(layout)
                builder.set_positive_button("Add", on_save)
                builder.set_negative_button("Cancel", lambda d, w: d.dismiss())
                builder.show()

                target_edit.requestFocus()
                AndroidUtilities.showKeyboard(target_edit)
            except Exception as e:
                self.log(f"_show_manual_dialog error: {e}")

        run_on_ui_thread(build)

    def _apply_manual_entry(self, target: str, name: str):
        account = UserConfig.selectedAccount
        mc = MessagesController.getInstance(account)

        clean_tgt = target.strip()
        if clean_tgt.startswith("@"):
            clean_uname = clean_tgt.lstrip("@").lower()
            # Try to resolve via MessagesController cache
            cached_obj = mc.getUserOrChat(clean_uname) if hasattr(mc, "getUserOrChat") else None
            if cached_obj:
                cls_name = str(cached_obj.getClass().getName())
                if "User" in cls_name:
                    self.set_override("user", str(cached_obj.id), clean_tgt, name, getattr(cached_obj, "first_name", ""), account)
                else:
                    self.set_override("chat", str(cached_obj.id), clean_tgt, name, getattr(cached_obj, "title", ""), account)
                BulletinHelper.show_success(f"Added override for {clean_tgt}")
                return
            else:
                # Store as username override
                self._usernames[clean_uname] = {"kind": "user", "name": name, "was": ""}
                self.save_config(reload_ui=True)
                self.apply_all()
                BulletinHelper.show_success(f"Added override for @{clean_uname}")
                return

        # Numeric target
        try:
            num = int(clean_tgt)
            if num > 0:
                self.set_override("user", str(num), clean_tgt, name, "", account)
            else:
                chat_id = _dialog_to_chat_id(num)
                self.set_override("chat", str(chat_id), clean_tgt, name, "", account)
            BulletinHelper.show_success("Override added")
        except Exception:
            BulletinHelper.show_error("Invalid ID or username")

    def _confirm_reset_all(self):
        def build():
            try:
                activity = get_activity()
                if not activity:
                    return
                builder = AlertDialogBuilder(activity)
                builder.set_title("Reset all overrides?")
                builder.set_message("All local name overrides will be removed and original names restored.")
                builder.set_positive_button("Reset", lambda d, w: self._reset_all_data())
                builder.set_negative_button("Cancel", lambda d, w: d.dismiss())
                builder.show()
            except Exception as e:
                self.log(f"_confirm_reset_all error: {e}")

        run_on_ui_thread(build)

    def _reset_all_data(self):
        self.restore_all()
        self._users.clear()
        self._chats.clear()
        self._usernames.clear()
        self.save_config(reload_ui=True)
        self.refresh_ui()
        BulletinHelper.show_success("All overrides reset")
