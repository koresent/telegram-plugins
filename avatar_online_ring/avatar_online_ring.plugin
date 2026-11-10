# -*- coding: utf-8 -*-
"""
Avatar Online Ring Plugin for exteraGram / AyuGram.
Replaces the standard online status dot indicator with a circular ring
around user avatars in the dialogs list, group chat messages, and member lists.
"""

import time
from typing import Any, Dict, List, Optional

from android.graphics import Color, Paint
from java import jint
from java.lang import System
from org.telegram.messenger import (
    AndroidUtilities,
    ApplicationLoader,
    MessagesController,
    NotificationCenter,
    UserConfig,
)
from org.telegram.tgnet import ConnectionsManager
from org.telegram.ui.ActionBar import Theme

from base_plugin import BasePlugin, MethodHook
from hook_utils import find_class
from ui.settings import Divider, Header, Input, Selector

__id__ = "avatar_online_ring"
__name__ = "Avatar Online Ring"
__description__ = "Replaces the online status dot indicator with a circular ring around user avatars"
__author__ = "@koresent"
__version__ = "1.0.1"
__icon__ = "exteraPlugins/1"
__category__ = ["appearance", "chats"]
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"

# Setting Keys
KEY_COLOR_MODE = "ring_color_mode"
KEY_CUSTOM_HEX = "custom_hex_color"
KEY_THICKNESS = "stroke_thickness"
KEY_GAP = "avatar_gap"

# Excluded system notification bot ID
SERVICE_NOTIF_USER_ID = 777000

COLOR_MODES = [
    "Theme Online Color",
    "Telegram Accent",
    "Vibrant Green (#00C853)",
    "Custom HEX",
]

THICKNESS_OPTIONS = [
    ("1.5 dp (Thin)", 1.5),
    ("2.0 dp (Snug)", 2.0),
    ("2.5 dp (Standard)", 2.5),
    ("3.0 dp (Bold)", 3.0),
    ("4.0 dp (Thick)", 4.0),
]

GAP_OPTIONS = [
    ("0 dp (Snug Fit)", 0.0),
    ("1.0 dp (Tight)", 1.0),
    ("1.5 dp (Normal)", 1.5),
    ("2.0 dp (Spacious)", 2.0),
]


def to_signed32(val: int) -> int:
    n = int(val) & 0xFFFFFFFF
    return (n ^ 0x80000000) - 0x80000000


def to_jint(val: int):
    return jint(to_signed32(val))


class AvatarOnlineRingPlugin(BasePlugin):
    """Plugin implementation for drawing circular online indicator rings."""

    def __init__(self):
        super().__init__()
        self._unhooks: List[Any] = []
        self._online_cells: Dict[int, bool] = {}
        self._paint: Optional[Paint] = None

        # Reflection field caches
        self._f_dc_avatar = None
        self._f_dc_user = None
        self._f_dc_account = None

        self._f_cmc_last_online = None
        self._f_cmc_progress = None
        self._f_cmc_user_id = None

        # Cached settings
        self._cfg_color_mode = 0
        self._cfg_custom_hex = "#00C853"
        self._cfg_thickness_dp = 2.0
        self._cfg_gap_dp = 0.0

    def on_plugin_load(self):
        self._load_settings()
        self._init_paint()
        self._install_hooks()
        self.refresh_ui()

    def on_plugin_unload(self):
        for u in self._unhooks:
            try:
                self.unhook_method(u)
            except Exception:
                pass
        self._unhooks.clear()
        self._online_cells.clear()
        self.refresh_ui()

    # ---------- Configuration ----------

    def _load_settings(self):
        try:
            self._cfg_color_mode = int(self.get_setting(KEY_COLOR_MODE, 0))
            self._cfg_custom_hex = str(self.get_setting(KEY_CUSTOM_HEX, "#00C853")).strip()

            thickness_idx = int(self.get_setting(KEY_THICKNESS, 1))
            if 0 <= thickness_idx < len(THICKNESS_OPTIONS):
                self._cfg_thickness_dp = THICKNESS_OPTIONS[thickness_idx][1]
            else:
                self._cfg_thickness_dp = 2.0

            gap_idx = int(self.get_setting(KEY_GAP, 0))
            if 0 <= gap_idx < len(GAP_OPTIONS):
                self._cfg_gap_dp = GAP_OPTIONS[gap_idx][1]
            else:
                self._cfg_gap_dp = 0.0
        except Exception:
            pass

    def _init_paint(self):
        if self._paint is None:
            self._paint = Paint(Paint.ANTI_ALIAS_FLAG)
            self._paint.setStyle(Paint.Style.STROKE)

    def _get_ring_color(self) -> int:
        mode = self._cfg_color_mode
        if mode == 0:
            # Theme Online Color (e.g. key_chats_onlineCircle)
            try:
                return Theme.getColor(Theme.key_chats_onlineCircle)
            except Exception:
                return 0xFF00C853
        elif mode == 1:
            # Telegram Accent Color
            try:
                return Theme.getColor(Theme.key_featuredStickers_addButton)
            except Exception:
                try:
                    return Theme.getColor(Theme.key_windowBackgroundWhiteBlueText)
                except Exception:
                    return 0xFF2AABEE
        elif mode == 2:
            # Vibrant Green
            return 0xFF00C853
        elif mode == 3:
            # Custom HEX
            try:
                hex_str = self._cfg_custom_hex
                if not hex_str.startswith("#"):
                    hex_str = "#" + hex_str
                return int(Color.parseColor(hex_str))
            except Exception:
                return 0xFF00C853
        return 0xFF00C853

    def get_paint(self) -> Paint:
        if self._paint is None:
            self._init_paint()
        color = self._get_ring_color()
        stroke_px = float(AndroidUtilities.dp(self._cfg_thickness_dp))
        self._paint.setColor(to_jint(color))
        self._paint.setStrokeWidth(stroke_px)
        return self._paint

    # ---------- Status Detection ----------

    def is_tl_user_online(self, user, account: int = 0) -> bool:
        """Determines if a TLRPC$User object represents an online user."""
        if not user:
            return False
        try:
            uid = getattr(user, "id", None)
            if uid is None or uid == SERVICE_NOTIF_USER_ID:
                return False
            if getattr(user, "self", False) or getattr(user, "bot", False):
                return False

            status = getattr(user, "status", None)
            if not status:
                return False

            expires = int(getattr(status, "expires", 0))
            if expires <= 0:
                mc = MessagesController.getInstance(account)
                if mc and hasattr(mc, "onlinePrivacy"):
                    if mc.onlinePrivacy.containsKey(uid) or mc.onlinePrivacy.containsKey(int(uid)):
                        return True
                return False

            cm = ConnectionsManager.getInstance(account)
            cur_time = cm.getCurrentTime() if cm else int(time.time())
            return expires > cur_time
        except Exception:
            return False

    def is_dialog_cell_online(self, cell) -> bool:
        """Online check for DialogCell."""
        try:
            if self._f_dc_user is None:
                self._f_dc_user = cell.getClass().getDeclaredField("user")
                self._f_dc_user.setAccessible(True)
            user = self._f_dc_user.get(cell)

            if self._f_dc_account is None:
                self._f_dc_account = cell.getClass().getDeclaredField("currentAccount")
                self._f_dc_account.setAccessible(True)
            acc = int(self._f_dc_account.getInt(cell))

            return self.is_tl_user_online(user, acc)
        except Exception:
            return False

    # ---------- Geometry & Drawing ----------

    def draw_ring_on_image(self, canvas, img):
        """Draws a smooth circular ring around the given ImageReceiver."""
        if img is None or canvas is None:
            return
        try:
            w = float(img.getImageWidth())
            h = float(img.getImageHeight())
            if w <= 0 or h <= 0:
                return

            x = float(img.getImageX())
            y = float(img.getImageY())
            cx = x + w / 2.0
            cy = y + h / 2.0

            gap_px = float(AndroidUtilities.dp(self._cfg_gap_dp))
            stroke_px = float(AndroidUtilities.dp(self._cfg_thickness_dp))

            if gap_px <= 0.0:
                radius = (w / 2.0)
            else:
                radius = (w / 2.0) + gap_px + (stroke_px / 2.0)

            paint = self.get_paint()
            canvas.drawCircle(float(cx), float(cy), float(radius), paint)
        except Exception:
            pass

    def draw_ring_on_view(self, canvas, view):
        """Draws a smooth circular ring inside the given avatar View (BackupImageView)."""
        if view is None or canvas is None:
            return
        try:
            w = float(view.getWidth())
            h = float(view.getHeight())
            if w <= 0 or h <= 0:
                return

            cx = w / 2.0
            cy = h / 2.0

            gap_px = float(AndroidUtilities.dp(self._cfg_gap_dp))
            stroke_px = float(AndroidUtilities.dp(self._cfg_thickness_dp))

            if gap_px <= 0.0:
                # Snug fit within the view boundaries
                radius = (w / 2.0) - (stroke_px / 2.0)
            else:
                radius = (w / 2.0) + gap_px + (stroke_px / 2.0)

            paint = self.get_paint()
            canvas.drawCircle(float(cx), float(cy), float(radius), paint)
        except Exception:
            pass

    # ---------- Hook Installation ----------

    def _install_hooks(self):
        plugin_self = self

        # 1. DialogCell Hooks (Main Chat List)
        class DialogCellIsOnlineHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    cell = param.thisObject
                    h = System.identityHashCode(cell)

                    # Check dialog ID exclusion for 777000
                    dialog_id = getattr(cell, "currentDialogId", 0)
                    if dialog_id == SERVICE_NOTIF_USER_ID:
                        plugin_self._online_cells[h] = False
                        param.setResult(False)
                        return

                    is_online = bool(param.getResult())
                    plugin_self._online_cells[h] = is_online
                    # Always suppress the default green dot badge
                    param.setResult(False)
                except Exception:
                    pass

        class DialogCellOverlayHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    cell = param.thisObject
                    dialog_id = getattr(cell, "currentDialogId", 0)
                    if dialog_id == SERVICE_NOTIF_USER_ID:
                        return

                    canvas = param.args[0]
                    h = System.identityHashCode(cell)

                    is_online = plugin_self._online_cells.get(h)
                    if is_online is None:
                        is_online = plugin_self.is_dialog_cell_online(cell)

                    if not is_online:
                        return

                    if plugin_self._f_dc_avatar is None:
                        plugin_self._f_dc_avatar = cell.getClass().getDeclaredField("avatarImage")
                        plugin_self._f_dc_avatar.setAccessible(True)
                    img = plugin_self._f_dc_avatar.get(cell)
                    plugin_self.draw_ring_on_image(canvas, img)
                except Exception:
                    pass

        try:
            dc_cls = find_class("org.telegram.ui.Cells.DialogCell")
            if dc_cls:
                j_cls = dc_cls.getClass()
                for m in j_cls.getDeclaredMethods():
                    if m.getName() == "isOnline" and len(m.getParameterTypes()) == 0:
                        m.setAccessible(True)
                        h = self.hook_method(m, DialogCellIsOnlineHook())
                        if h:
                            self._unhooks.append(h)
                    elif m.getName() == "drawAvatarOverlays" and len(m.getParameterTypes()) == 1:
                        m.setAccessible(True)
                        h = self.hook_method(m, DialogCellOverlayHook())
                        if h:
                            self._unhooks.append(h)
        except Exception:
            pass

        # 2. ChatMessageCell Hooks (Inside Group Chats)
        class CMCStatusHook(MethodHook):
            def __init__(self):
                super().__init__()
                self.saved_online: Dict[int, bool] = {}

            def before_hooked_method(self, param):
                try:
                    cell = param.thisObject
                    cls = cell.getClass()
                    if plugin_self._f_cmc_last_online is None:
                        plugin_self._f_cmc_last_online = cls.getDeclaredField("avatarOnlineLastOnline")
                        plugin_self._f_cmc_last_online.setAccessible(True)
                    if plugin_self._f_cmc_progress is None:
                        plugin_self._f_cmc_progress = cls.getDeclaredField("avatarOnlineProgress")
                        plugin_self._f_cmc_progress.setAccessible(True)
                    if plugin_self._f_cmc_user_id is None:
                        try:
                            plugin_self._f_cmc_user_id = cls.getDeclaredField("avatarOnlineUserId")
                            plugin_self._f_cmc_user_id.setAccessible(True)
                        except Exception:
                            pass

                    # Check 777000 exclusion
                    if plugin_self._f_cmc_user_id is not None:
                        try:
                            uid = plugin_self._f_cmc_user_id.getLong(cell)
                            if uid == SERVICE_NOTIF_USER_ID:
                                return
                        except Exception:
                            pass

                    last_on = bool(plugin_self._f_cmc_last_online.getBoolean(cell))
                    prog = float(plugin_self._f_cmc_progress.getFloat(cell))
                    is_online = last_on or (prog > 0.1)

                    cell_h = System.identityHashCode(cell)
                    self.saved_online[cell_h] = is_online

                    if is_online:
                        # Suppress the default green dot badge
                        plugin_self._f_cmc_last_online.setBoolean(cell, False)
                        plugin_self._f_cmc_progress.setFloat(cell, 0.0)
                except Exception:
                    pass

            def after_hooked_method(self, param):
                try:
                    cell = param.thisObject
                    canvas = param.args[0]
                    img = param.args[1]
                    cell_h = System.identityHashCode(cell)
                    is_online = self.saved_online.pop(cell_h, False)

                    # Restore state so Telegram animation tracking is preserved
                    if is_online:
                        try:
                            plugin_self._f_cmc_last_online.setBoolean(cell, True)
                            plugin_self._f_cmc_progress.setFloat(cell, 1.0)
                        except Exception:
                            pass
                        plugin_self.draw_ring_on_image(canvas, img)
                except Exception:
                    pass

        try:
            cmc_cls = find_class("org.telegram.ui.Cells.ChatMessageCell")
            if cmc_cls:
                j_cls = cmc_cls.getClass()
                for m in j_cls.getDeclaredMethods():
                    if m.getName() == "drawAvatarWithOnlineStatus":
                        m.setAccessible(True)
                        h = self.hook_method(m, CMCStatusHook())
                        if h:
                            self._unhooks.append(h)
                        break
        except Exception:
            pass

        # 3. BackupImageView Hooks (Group Members List & User Cells)
        class BIVDrawHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    view = param.thisObject
                    parent = view.getParent()
                    if parent is None:
                        return

                    user = None
                    p_name = parent.getClass().getSimpleName()

                    if p_name in ("ManageChatUserCell", "UserCell", "UserCell2", "GroupCreateUserCell"):
                        if hasattr(parent, "getCurrentObject"):
                            user = parent.getCurrentObject()
                    elif p_name == "ChatAvatarContainer":
                        frag = getattr(parent, "parentFragment", None)
                        if frag and hasattr(frag, "getCurrentUser"):
                            user = frag.getCurrentUser()

                    if user is None:
                        return

                    if not plugin_self.is_tl_user_online(user):
                        return

                    canvas = param.args[0]
                    plugin_self.draw_ring_on_view(canvas, view)
                except Exception:
                    pass

        try:
            biv_cls = find_class("org.telegram.ui.Components.BackupImageView")
            if biv_cls:
                j_cls = biv_cls.getClass()
                for m in j_cls.getDeclaredMethods():
                    if m.getName() == "onDraw" and len(m.getParameterTypes()) == 1:
                        m.setAccessible(True)
                        h = self.hook_method(m, BIVDrawHook())
                        if h:
                            self._unhooks.append(h)
                        break
        except Exception:
            pass

    # ---------- UI Refresh ----------

    def refresh_ui(self):
        """Notifies Telegram to redraw dialogs and chat list cells."""
        try:
            acc = UserConfig.selectedAccount
            nc = NotificationCenter.getInstance(acc)
            if nc:
                mask = (
                    getattr(MessagesController, "UPDATE_MASK_NAME", 1)
                    | getattr(MessagesController, "UPDATE_MASK_CHAT_NAME", 16)
                    | getattr(MessagesController, "UPDATE_MASK_STATUS", 4)
                )
                nc.postNotificationName(NotificationCenter.updateInterfaces, to_jint(mask))
                nc.postNotificationName(NotificationCenter.dialogsNeedReload)
        except Exception:
            pass

    # ---------- Settings Interface ----------

    def create_settings(self) -> List[Any]:
        self._load_settings()

        def on_change():
            self._load_settings()
            self._init_paint()
            self.refresh_ui()

        rows: List[Any] = []
        rows.append(Header("Avatar Online Ring"))
        rows.append(
            Divider(
                text="Replaces the standard online status dot indicator with a clean circular "
                     "ring around user avatars in the chat list, group messages, and chat member lists."
            )
        )

        rows.append(Header("Ring Styling"))
        rows.append(
            Selector(
                key=KEY_COLOR_MODE,
                text="Ring Color",
                items=COLOR_MODES,
                default=int(self.get_setting(KEY_COLOR_MODE, 0)),
                icon="msg_colors",
                on_change=lambda _: on_change(),
            )
        )
        rows.append(
            Input(
                key=KEY_CUSTOM_HEX,
                text="Custom Color HEX",
                subtext="Active when 'Custom HEX' color mode is selected (e.g. #00C853)",
                default=str(self.get_setting(KEY_CUSTOM_HEX, "#00C853")),
                icon="msg_edit",
                on_change=lambda _: on_change(),
            )
        )
        rows.append(
            Selector(
                key=KEY_THICKNESS,
                text="Ring Thickness",
                items=[label for label, _ in THICKNESS_OPTIONS],
                default=int(self.get_setting(KEY_THICKNESS, 1)),
                icon="msg_settings",
                on_change=lambda _: on_change(),
            )
        )
        rows.append(
            Selector(
                key=KEY_GAP,
                text="Avatar Gap",
                items=[label for label, _ in GAP_OPTIONS],
                default=int(self.get_setting(KEY_GAP, 0)),
                icon="msg_folders",
                on_change=lambda _: on_change(),
            )
        )

        rows.append(
            Divider(
                text="Changes are applied immediately to all visible and upcoming chats."
            )
        )

        return rows
