# -*- coding: utf-8 -*-
"""
Notes Vault Plugin for exteraGram / AyuGram
Markdown notes editor connected directly to your Git repository from Telegram.
"""

import base64
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from android.content import Context, Intent
from android.graphics import Color, Typeface
from android.graphics.drawable import GradientDrawable
from android.text import Editable, Spannable, TextWatcher
from android.text.style import (
    BackgroundColorSpan,
    ForegroundColorSpan,
    RelativeSizeSpan,
    StrikethroughSpan,
    StyleSpan,
    TypefaceSpan,
    UnderlineSpan,
)
from android.util import TypedValue
from android.view import Gravity, View, ViewGroup
from android.widget import (
    EditText,
    FrameLayout,
    HorizontalScrollView,
    ImageView,
    LinearLayout,
    ProgressBar,
    ScrollView,
    TextView,
)
from java import dynamic_proxy, jclass
from java.lang import Class as JClass
from org.telegram.messenger import (
    AndroidUtilities,
    ApplicationLoader,
    LocaleController,
)
from org.telegram.ui.ActionBar import BottomSheet, Theme

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MethodHook
from client_utils import get_last_fragment, run_on_queue
from hook_utils import find_class, get_private_field
from ui.alert import AlertDialogBuilder
from ui.bulletin import BulletinHelper
from ui.settings import Divider, Header, Input, Selector, Switch

__id__ = "notes_vault"
__name__ = "Notes Vault"
__description__ = "Markdown notes editor connected directly to your GitHub repository from the chat input bar"
__author__ = "@koresent"
__version__ = "1.1.0"
__icon__ = "exteraPlugins/1"
__category__ = ["chats", "productivity"]
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"

DEFAULT_REPO = "koresent/notes"
DEFAULT_BRANCH = "main"
DEFAULT_VAULT_PATH = "vault"
DEFAULT_BOT_NAME = "Notes Bot"
DEFAULT_BOT_EMAIL = "notes-bot@users.noreply.github.com"


def debug_log(msg: str):
    try:
        ctx = ApplicationLoader.applicationContext
        if ctx:
            ext = ctx.getExternalFilesDir(None)
            if ext:
                path = ext.getAbsolutePath() + "/notes_vault_debug.log"
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def dp(val: float) -> int:
    return int(AndroidUtilities.dp(val))


def to_int32(val: int) -> int:
    val = int(val) & 0xFFFFFFFF
    if val >= 0x80000000:
        val -= 0x100000000
    return int(val)


def russian() -> bool:
    try:
        return str(LocaleController.getInstance().getCurrentLocale().getLanguage()).startswith("ru")
    except Exception:
        return True


def tr(ru_text: str, en_text: str) -> str:
    return ru_text if russian() else en_text


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


class WebTouchListener(dynamic_proxy(View.OnTouchListener)):
    def onTouch(self, v, event):
        try:
            p = v.getParent()
            if p:
                p.requestDisallowInterceptTouchEvent(True)
        except Exception:
            pass
        return False


class OnClickListenerProxy(dynamic_proxy(View.OnClickListener)):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def onClick(self, view):
        try:
            self.callback(view)
        except Exception:
            pass


class GitHubNotesClient:
    def __init__(
        self,
        token: str,
        repo: str = DEFAULT_REPO,
        branch: str = DEFAULT_BRANCH,
        vault_path: str = DEFAULT_VAULT_PATH,
    ):
        self.token = str(token or "").strip()
        self.repo = str(repo or DEFAULT_REPO).strip().strip("/")
        self.branch = str(branch or DEFAULT_BRANCH).strip()
        self.vault_path = str(vault_path or DEFAULT_VAULT_PATH).strip().strip("/")

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ExteraGram-NotesVault/1.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def list_notes(self) -> List[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{self.repo}/contents/{self.vault_path}?ref={self.branch}"
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=12) as resp:
            items = json.loads(resp.read().decode("utf-8"))
            notes = []
            for item in items:
                if item.get("type") == "file":
                    name = item.get("name", "")
                    if name.endswith(".md") or name.endswith(".txt"):
                        notes.append({
                            "name": name,
                            "path": item.get("path", f"{self.vault_path}/{name}"),
                            "sha": item.get("sha", ""),
                            "size": item.get("size", 0),
                        })
            return sorted(notes, key=lambda x: x["name"])

    def get_note_content(self, path: str) -> Tuple[str, str]:
        url = f"https://api.github.com/repos/{self.repo}/contents/{path}?ref={self.branch}"
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("content", "")
            encoding = data.get("encoding", "")
            sha = data.get("sha", "")
            if encoding == "base64":
                raw_bytes = base64.b64decode(raw)
                text = raw_bytes.decode("utf-8", errors="replace")
            else:
                text = raw
            return text, sha

    def push_note(
        self,
        filename: str,
        content: str,
        sha: Optional[str] = None,
        committer_name: str = DEFAULT_BOT_NAME,
        committer_email: str = DEFAULT_BOT_EMAIL,
    ) -> str:
        clean_name = filename.strip()
        if not clean_name.endswith(".md") and not clean_name.endswith(".txt"):
            clean_name += ".md"
        path = f"{self.vault_path}/{clean_name}"
        url = f"https://api.github.com/repos/{self.repo}/contents/{path}"

        timestamp = time.strftime("%Y-%m-%d %H:%M")
        commit_msg = f"sync: auto-commit {timestamp}"

        b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        payload = {
            "message": commit_msg,
            "content": b64_content,
            "branch": self.branch,
            "committer": {
                "name": committer_name or DEFAULT_BOT_NAME,
                "email": committer_email or DEFAULT_BOT_EMAIL,
            },
        }
        if sha:
            payload["sha"] = sha

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="PUT")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("content", {}).get("sha", "")


class MarkdownHighlighter:
    SPAN_FLAGS = Spannable.SPAN_EXCLUSIVE_EXCLUSIVE

    @classmethod
    def apply_syntax_highlighting(cls, editable: Editable):
        if editable is None or editable.length() == 0:
            return

        text_str = str(editable.toString())
        len_str = len(text_str)

        existing_spans = editable.getSpans(0, len_str, JClass.forName("java.lang.Object"))
        for s in existing_spans:
            s_name = s.getClass().getName()
            if any(k in s_name for k in ("ForegroundColorSpan", "RelativeSizeSpan", "StyleSpan", "StrikethroughSpan", "BackgroundColorSpan")):
                editable.removeSpan(s)

        header_color = Theme.getColor(Theme.key_windowBackgroundWhiteBlueHeader)
        accent_color = Theme.getColor(Theme.key_featuredStickers_addButton)
        gray_color = Theme.getColor(Theme.key_windowBackgroundWhiteGrayText)
        code_bg_color = Theme.getColor(Theme.key_chat_messagePanelBackground)
        is_dark = Theme.isCurrentThemeDark() if hasattr(Theme, "isCurrentThemeDark") else True
        if code_bg_color == 0:
            code_bg_color = to_int32(0x22FFFFFF) if is_dark else 0x15000000

        lines = text_str.split("\n")
        idx = 0
        in_code_block = False
        code_block_start = 0

        for line in lines:
            line_len = len(line)
            line_end = idx + line_len

            if line.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = idx
                else:
                    in_code_block = False
                    editable.setSpan(TypefaceSpan("monospace"), code_block_start, line_end, cls.SPAN_FLAGS)
                    editable.setSpan(BackgroundColorSpan(code_bg_color), code_block_start, line_end, cls.SPAN_FLAGS)
                    editable.setSpan(ForegroundColorSpan(gray_color), code_block_start, line_end, cls.SPAN_FLAGS)
                idx = line_end + 1
                continue

            if in_code_block:
                idx = line_end + 1
                continue

            stripped = line.lstrip()
            indent = line_len - len(stripped)

            if stripped.startswith("### "):
                editable.setSpan(StyleSpan(Typeface.BOLD), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(RelativeSizeSpan(1.12), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(header_color), idx, line_end, cls.SPAN_FLAGS)
            elif stripped.startswith("## "):
                editable.setSpan(StyleSpan(Typeface.BOLD), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(RelativeSizeSpan(1.22), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(header_color), idx, line_end, cls.SPAN_FLAGS)
            elif stripped.startswith("# "):
                editable.setSpan(StyleSpan(Typeface.BOLD), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(RelativeSizeSpan(1.36), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(header_color), idx, line_end, cls.SPAN_FLAGS)
            elif stripped.startswith("> "):
                editable.setSpan(StyleSpan(Typeface.ITALIC), idx, line_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(gray_color), idx, line_end, cls.SPAN_FLAGS)
            elif stripped.startswith("- [ ] "):
                box_end = idx + indent + 5
                editable.setSpan(StyleSpan(Typeface.BOLD), idx + indent, box_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(accent_color), idx + indent, box_end, cls.SPAN_FLAGS)
            elif stripped.startswith("- [x] ") or stripped.startswith("- [X] "):
                box_end = idx + indent + 5
                editable.setSpan(StyleSpan(Typeface.BOLD), idx + indent, box_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(gray_color), idx + indent, box_end, cls.SPAN_FLAGS)
                if line_end > box_end + 1:
                    editable.setSpan(StrikethroughSpan(), box_end + 1, line_end, cls.SPAN_FLAGS)
                    editable.setSpan(ForegroundColorSpan(gray_color), box_end + 1, line_end, cls.SPAN_FLAGS)

            for m in re.finditer(r"`([^`\n]+)`", line):
                m_start = idx + m.start()
                m_end = idx + m.end()
                editable.setSpan(TypefaceSpan("monospace"), m_start, m_end, cls.SPAN_FLAGS)
                editable.setSpan(BackgroundColorSpan(code_bg_color), m_start, m_end, cls.SPAN_FLAGS)
                editable.setSpan(ForegroundColorSpan(accent_color), m_start, m_end, cls.SPAN_FLAGS)

            for m in re.finditer(r"\*\*([^*]+)\*\*", line):
                editable.setSpan(StyleSpan(Typeface.BOLD), idx + m.start(), idx + m.end(), cls.SPAN_FLAGS)

            for m in re.finditer(r"(?<!\*)\*([^*]+)\*(?!\*)", line):
                editable.setSpan(StyleSpan(Typeface.ITALIC), idx + m.start(), idx + m.end(), cls.SPAN_FLAGS)

            idx = line_end + 1


class ChatCreateHook(MethodHook):
    def __init__(self, plugin: "NotesVaultPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        fragment = param.thisObject
        run_on_ui_thread(lambda: self.plugin.attach_button(fragment))


class ChatResumeHook(MethodHook):
    def __init__(self, plugin: "NotesVaultPlugin"):
        super().__init__()
        self.plugin = plugin

    def after_hooked_method(self, param):
        fragment = param.thisObject
        run_on_ui_thread(lambda: self.plugin.attach_button(fragment))


class NotesVaultPlugin(BasePlugin):
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
        self._cached_notes: List[Dict[str, Any]] = []
        self._note_drafts: Dict[str, str] = {}
        self._orig_edit_padding: Optional[Tuple[int, int, int, int]] = None

    def on_plugin_load(self):
        self.is_active = True
        self._install_hooks()
        try:
            frag = get_last_fragment()
            self.log(f"on_plugin_load: frag={frag}")
            if frag and "ChatActivity" in frag.getClass().getName():
                run_on_ui_thread(lambda: self.attach_button(frag))
        except Exception as e:
            self.log(f"on_plugin_load attach error: {e}")
        self.log("NotesVaultPlugin loaded successfully")

    def on_plugin_unload(self):
        self.is_active = False
        for u in self._unhooks:
            try:
                self.unhook_method(u)
            except Exception:
                pass
        self._unhooks.clear()
        self.detach_button()
        try:
            import sys
            sys.modules.pop("notes_vault", None)
        except Exception:
            pass
        self.log("NotesVaultPlugin unloaded")

    def _install_hooks(self):
        try:
            ChatActivity_cls = find_class("org.telegram.ui.ChatActivity")
            Context_cls = find_class("android.content.Context")
            if not ChatActivity_cls or not Context_cls:
                return

            j_cls = ChatActivity_cls.getClass()
            for m in j_cls.getDeclaredMethods():
                m_name = m.getName()
                if m_name == "createView" and len(m.getParameterTypes()) == 1:
                    m.setAccessible(True)
                    h = self.hook_method(m, ChatCreateHook(self))
                    if h:
                        self._unhooks.append(h)
                elif m_name == "onResume" and len(m.getParameterTypes()) == 0:
                    m.setAccessible(True)
                    h = self.hook_method(m, ChatResumeHook(self))
                    if h:
                        self._unhooks.append(h)
        except Exception as e:
            self.log(f"_install_hooks error: {e}")

    def detach_button(self):
        try:
            frag = get_last_fragment()
            if not frag:
                return
            ev = getattr(frag, "chatActivityEnterView", None) or (
                frag.getChatActivityEnterView() if hasattr(frag, "getChatActivityEnterView") else None
            )
            if ev:
                btn = ev.findViewWithTag("notes_vault_btn")
                if btn and btn.getParent():
                    btn.getParent().removeView(btn)

                if self._orig_edit_padding:
                    msg_edit = get_private_field(ev, "messageEditText")
                    if msg_edit:
                        p = self._orig_edit_padding
                        msg_edit.setPadding(p[0], p[1], p[2], p[3])
                    self._orig_edit_padding = None

            action_bar = getattr(frag, "actionBar", None)
            if action_bar:
                menu = getattr(action_bar, "menu", None)
                if menu:
                    item = getattr(menu, "getItem", lambda id: None)(99882)
                    if item:
                        item.setVisibility(View.GONE)
        except Exception:
            pass

    def attach_button(self, fragment: Any):
        if not fragment or not self.is_active:
            return
        try:
            ev = getattr(fragment, "chatActivityEnterView", None) or (
                fragment.getChatActivityEnterView() if hasattr(fragment, "getChatActivityEnterView") else None
            )
            if not ev:
                return

            pos = int(self.get_setting("btn_position", 1))

            old_btn = ev.findViewWithTag("notes_vault_btn")
            if old_btn and old_btn.getParent() and isinstance(old_btn.getParent(), ViewGroup):
                old_btn.getParent().removeView(old_btn)

            msg_edit = get_private_field(ev, "messageEditText")
            if msg_edit:
                if self._orig_edit_padding is None:
                    self._orig_edit_padding = (
                        msg_edit.getPaddingLeft(),
                        msg_edit.getPaddingTop(),
                        msg_edit.getPaddingRight(),
                        msg_edit.getPaddingBottom(),
                    )
                p = self._orig_edit_padding
                msg_edit.setPadding(p[0], p[1], p[2], p[3])

            action_bar = getattr(fragment, "actionBar", None)
            r_drawable = jclass("org.telegram.messenger.R$drawable")

            if pos == 2:
                if action_bar:
                    menu = action_bar.createMenu()
                    if menu:
                        item = getattr(menu, "getItem", lambda id: None)(99882)
                        if item is None:
                            item = menu.addItem(99882, r_drawable.msg_edit)
                            if item:
                                item.setOnClickListener(OnClickListenerProxy(lambda v: self.on_button_clicked(fragment)))
                        else:
                            item.setVisibility(View.VISIBLE)
                return
            else:
                if action_bar:
                    menu = getattr(action_bar, "menu", None)
                    if menu:
                        item = getattr(menu, "getItem", lambda id: None)(99882)
                        if item:
                            item.setVisibility(View.GONE)

            btn = FrameLayout(ev.getContext())
            btn.setTag("notes_vault_btn")
            try:
                btn.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 1))
            except Exception:
                pass

            iv = ImageView(ev.getContext())
            iv.setImageResource(r_drawable.msg_edit)
            accent_col = Theme.getColor(Theme.key_windowBackgroundWhiteBlueHeader)
            if accent_col == 0:
                accent_col = Theme.getColor(Theme.key_featuredStickers_addButton)
            if accent_col == 0:
                accent_col = to_int32(0xFF2AABEE)
            iv.setColorFilter(accent_col)
            iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)

            pad = dp(7)
            btn.setPadding(pad, pad, pad, pad)
            btn.addView(iv, FrameLayout.LayoutParams(dp(22), dp(22), Gravity.CENTER))
            btn.setClickable(True)
            btn.setFocusable(True)
            btn.setOnClickListener(OnClickListenerProxy(lambda v: self.on_button_clicked(fragment)))

            if pos == 0:
                emoji_btn = get_private_field(ev, "emojiButton")
                if emoji_btn and emoji_btn.getParent() and isinstance(emoji_btn.getParent(), ViewGroup):
                    parent = emoji_btn.getParent()
                    if isinstance(parent, LinearLayout):
                        idx = parent.indexOfChild(emoji_btn)
                        lp = LinearLayout.LayoutParams(dp(36), dp(36))
                        lp.gravity = Gravity.BOTTOM
                        lp.leftMargin = dp(2)
                        lp.rightMargin = dp(2)
                        lp.bottomMargin = dp(6)
                        parent.addView(btn, idx + 1, lp)
                    else:
                        lp = FrameLayout.LayoutParams(dp(36), dp(36))
                        lp.gravity = Gravity.LEFT | Gravity.BOTTOM
                        lp.leftMargin = dp(52)
                        lp.bottomMargin = dp(6)
                        parent.addView(btn, lp)
                else:
                    lp = LinearLayout.LayoutParams(dp(36), dp(36))
                    lp.gravity = Gravity.BOTTOM
                    ev.addView(btn, 0, lp)

                btn.bringToFront()
                try:
                    btn.setElevation(dp(6))
                except Exception:
                    pass

                if msg_edit and self._orig_edit_padding:
                    p = self._orig_edit_padding
                    msg_edit.setPadding(p[0] + dp(46), p[1], p[2], p[3])
            elif pos == 1:
                attach_layout = get_private_field(ev, "attachLayout")
                if attach_layout and attach_layout.getParent() and isinstance(attach_layout.getParent(), ViewGroup):
                    parent = attach_layout.getParent()
                    if isinstance(parent, LinearLayout):
                        idx = parent.indexOfChild(attach_layout)
                        lp = LinearLayout.LayoutParams(dp(36), dp(36))
                        lp.gravity = Gravity.BOTTOM
                        lp.bottomMargin = dp(6)
                        parent.addView(btn, idx, lp)
                    else:
                        lp = FrameLayout.LayoutParams(dp(36), dp(36))
                        lp.gravity = Gravity.RIGHT | Gravity.BOTTOM
                        lp.rightMargin = dp(48)
                        lp.bottomMargin = dp(6)
                        parent.addView(btn, lp)
                else:
                    lp = LinearLayout.LayoutParams(dp(36), dp(36))
                    lp.gravity = Gravity.BOTTOM
                    ev.addView(btn, lp)

                btn.bringToFront()
                try:
                    btn.setElevation(dp(6))
                except Exception:
                    pass

                if msg_edit and self._orig_edit_padding:
                    p = self._orig_edit_padding
                    msg_edit.setPadding(p[0], p[1], p[2] + dp(46), p[3])
        except Exception as e:
            self.log(f"attach_button error: {e}")

    def _get_client(self) -> GitHubNotesClient:
        token = str(self.get_setting("github_token", "")).strip()
        repo = str(self.get_setting("github_repo", DEFAULT_REPO)).strip() or DEFAULT_REPO
        branch = str(self.get_setting("github_branch", DEFAULT_BRANCH)).strip() or DEFAULT_BRANCH
        vault_path = str(self.get_setting("vault_path", DEFAULT_VAULT_PATH)).strip() or DEFAULT_VAULT_PATH
        return GitHubNotesClient(token=token, repo=repo, branch=branch, vault_path=vault_path)

    def on_button_clicked(self, fragment: Any):
        token = str(self.get_setting("github_token", "")).strip()
        repo = str(self.get_setting("github_repo", DEFAULT_REPO)).strip() or DEFAULT_REPO
        self.log(f"on_button_clicked: token_len={len(token)}, repo={repo}")
        if not token:
            self._prompt_token_dialog()
            return
        self._load_and_open_editor(fragment)

    def _prompt_token_dialog(self):
        self.log("_prompt_token_dialog opened")
        def build():
            activity = get_activity()
            if not activity:
                return

            layout = LinearLayout(activity)
            layout.setOrientation(LinearLayout.VERTICAL)
            layout.setPadding(dp(24), dp(16), dp(24), dp(16))

            desc = TextView(activity)
            desc.setText(tr(
                "Для синхронизации с Git требуется токен GitHub (Personal Access Token).\n\n"
                "Создайте токен с областью 'repo' на github.com/settings/tokens и укажите его здесь:",
                "GitHub Personal Access Token is required to access your notes repository.\n\n"
                "Please enter a token with 'repo' scope (from github.com/settings/tokens):"
            ))
            desc.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
            desc.setTextColor(Theme.getColor(Theme.key_dialogTextGray2))
            layout.addView(desc)

            token_edit = EditText(activity)
            token_edit.setHint("ghp_... or gho_...")
            token_edit.setSingleLine(True)
            token_edit.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
            token_edit.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
            token_edit.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))
            layout.addView(token_edit)

            def on_save(dialog, which):
                new_tok = str(token_edit.getText().toString()).strip()
                if new_tok:
                    self.set_setting("github_token", new_tok, reload_settings=True)
                    BulletinHelper.show_success(tr("Токен сохранен!", "GitHub Token saved!"))
                    self.on_button_clicked(get_last_fragment())
                dialog.dismiss()

            builder = AlertDialogBuilder(activity)
            builder.set_title(tr("Требуется токен GitHub", "GitHub Token Required"))
            builder.set_view(layout)
            builder.set_positive_button(tr("Сохранить", "Save"), on_save)
            builder.set_negative_button(tr("Отмена", "Cancel"), lambda d, w: d.dismiss())
            builder.show()

            token_edit.requestFocus()
            AndroidUtilities.showKeyboard(token_edit)

        run_on_ui_thread(build)

    def _load_and_open_editor(self, fragment: Any):
        client = self._get_client()
        self.log(f"_load_and_open_editor: repo={client.repo}, vault={client.vault_path}, branch={client.branch}")
        BulletinHelper.show_info(tr("Подключение к GitHub...", "Connecting to GitHub..."))

        def worker():
            self.log("worker: started, calling client.list_notes()")
            try:
                notes = client.list_notes()
                self.log(f"worker: list_notes returned {len(notes)} notes")
                if not notes:
                    notes = [{"name": "home.md", "path": f"{client.vault_path}/home.md", "sha": "", "size": 0}]

                self._cached_notes = notes
                first_note = notes[0]
                content = self._note_drafts.get(first_note["name"], "")
                sha = first_note.get("sha", "")
                if not content and sha:
                    try:
                        self.log(f"worker: fetching content for {first_note['name']}")
                        content, sha = client.get_note_content(first_note["path"])
                        self.log(f"worker: content fetched, len={len(content)}")
                    except Exception as e:
                        self.log(f"Failed to fetch content for {first_note['name']}: {e}")

                first_note["sha"] = sha

                def open_ui():
                    self.log(f"open_ui: starting _show_fullscreen_editor with note={first_note['name']}")
                    try:
                        self._show_fullscreen_editor(notes, 0, content, sha, fragment)
                        self.log("open_ui: _show_fullscreen_editor completed successfully")
                    except Exception as e:
                        import traceback
                        tb = traceback.format_exc()
                        self.log(f"_show_fullscreen_editor error: {e}\n{tb}")
                        BulletinHelper.show_error(f"UI Error: {e}")

                run_on_ui_thread(open_ui)
            except urllib.error.HTTPError as he:
                msg = f"GitHub API Error {he.code}"
                if he.code == 401:
                    msg = tr("Неверный токен GitHub (401)", "Invalid GitHub Token (401 Unauthorized)")
                elif he.code == 404:
                    msg = tr(f"Репозиторий {client.repo}/{client.vault_path} не найден (404)", f"Repo {client.repo}/{client.vault_path} not found (404)")
                self.log(f"worker HTTPError: {he.code} -> {msg}")
                run_on_ui_thread(lambda: BulletinHelper.show_error(msg))
            except Exception as e:
                import traceback
                self.log(f"worker exception: {e}\n{traceback.format_exc()}")
                run_on_ui_thread(lambda: BulletinHelper.show_error(f"Error: {e}"))

        self.log("Queueing worker on background queue...")
        run_on_queue(lambda: worker())

    def _show_fullscreen_editor(
        self,
        notes: List[Dict[str, Any]],
        current_idx: int,
        initial_content: str,
        current_sha: str,
        fragment: Any,
    ):
        activity = get_activity()
        if not activity:
            return

        client = self._get_client()
        r_drawable = jclass("org.telegram.messenger.R$drawable")
        preview_drawable = getattr(r_drawable, "msg_saved", r_drawable.ic_ab_back)
        edit_drawable = getattr(r_drawable, "msg_edit", preview_drawable)
        folder_drawable = getattr(r_drawable, "msg_folders", preview_drawable)

        state = {
            "notes": list(notes),
            "idx": current_idx,
            "sha": current_sha,
            "modified": False,
            "preview_mode": False,
            "sheet": None,
            "edit_ref": [None],
            "status_ref": [None],
            "progress_ref": [None],
            "title_ref": [None],
            "preview_box_ref": [None],
            "editor_scroll_ref": [None],
            "preview_scroll_ref": [None],
            "tabs_container_ref": [None],
        }

        builder = BottomSheet.Builder(activity, True)
        builder.setApplyBottomPadding(False)
        builder.setApplyTopPadding(False)

        root = LinearLayout(activity)
        root.setOrientation(LinearLayout.VERTICAL)
        root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))
        root.setLayoutParams(ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            int(AndroidUtilities.displaySize.y * 0.92)
        ))

        # 1. Header Toolbar (52dp)
        header = LinearLayout(activity)
        header.setOrientation(LinearLayout.HORIZONTAL)
        header.setGravity(Gravity.CENTER_VERTICAL)
        header.setPadding(dp(12), dp(6), dp(12), dp(6))
        header.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

        icon_color = Theme.getColor(Theme.key_windowBackgroundWhiteBlackText)

        def make_icon_btn(drawable_id: int, on_tap, pad_dp: int = 6):
            btn = ImageView(activity)
            btn.setImageResource(drawable_id)
            btn.setColorFilter(icon_color)
            btn.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
            btn.setPadding(dp(pad_dp), dp(pad_dp), dp(pad_dp), dp(pad_dp))
            try:
                btn.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 1))
            except Exception:
                pass
            lp = LinearLayout.LayoutParams(dp(40), dp(40))
            lp.gravity = Gravity.CENTER_VERTICAL
            btn.setLayoutParams(lp)
            btn.setClickable(True)
            btn.setFocusable(True)
            btn.setOnClickListener(OnClickListenerProxy(lambda v: on_tap()))
            return btn

        btn_close = make_icon_btn(r_drawable.ic_ab_back, lambda: on_close_clicked())
        header.addView(btn_close)

        title_col = LinearLayout(activity)
        title_col.setOrientation(LinearLayout.VERTICAL)
        title_col.setPadding(dp(10), 0, dp(10), 0)
        try:
            title_col.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 2))
        except Exception:
            pass
        title_col.setClickable(True)
        title_col.setFocusable(True)
        title_col.setOnClickListener(OnClickListenerProxy(lambda v: open_notes_list_sheet()))

        title_row = LinearLayout(activity)
        title_row.setOrientation(LinearLayout.HORIZONTAL)
        title_row.setGravity(Gravity.CENTER_VERTICAL)

        curr_note = state["notes"][state["idx"]]
        title_tv = TextView(activity)
        title_tv.setText(curr_note["name"])
        title_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
        title_tv.setTypeface(Typeface.DEFAULT_BOLD)
        title_tv.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
        title_tv.setSingleLine(True)
        state["title_ref"][0] = title_tv
        title_row.addView(title_tv)

        chevron = TextView(activity)
        chevron.setText(" ▾")
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
        chevron.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText))
        title_row.addView(chevron)
        title_col.addView(title_row)

        sub_tv = TextView(activity)
        sub_tv.setText(f"{client.repo}/{client.vault_path}")
        sub_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 11)
        sub_tv.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText))
        sub_tv.setSingleLine(True)
        title_col.addView(sub_tv)

        header.addView(title_col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))

        btn_preview_ref = [None]

        def toggle_mode():
            state["preview_mode"] = not state["preview_mode"]
            update_mode_views()

        btn_preview = make_icon_btn(preview_drawable, toggle_mode, pad_dp=6)
        btn_preview_ref[0] = btn_preview
        header.addView(btn_preview)

        push_btn = TextView(activity)
        push_btn.setText(tr("Пуш", "Push"))
        push_btn.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
        push_btn.setTypeface(Typeface.DEFAULT_BOLD)
        push_btn.setTextColor(to_int32(0xFFFFFFFF))
        push_btn.setGravity(Gravity.CENTER)
        push_bg = GradientDrawable()
        push_bg.setCornerRadius(dp(16))
        accent_col = Theme.getColor(Theme.key_featuredStickers_addButton)
        if accent_col == 0:
            accent_col = to_int32(0xFF2AABEE)
        push_bg.setColor(accent_col)
        push_btn.setBackground(push_bg)
        push_btn.setPadding(dp(14), dp(6), dp(14), dp(6))
        push_lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(34))
        push_lp.gravity = Gravity.CENTER_VERTICAL
        push_lp.leftMargin = dp(6)
        push_btn.setLayoutParams(push_lp)
        push_btn.setClickable(True)
        push_btn.setFocusable(True)
        push_btn.setOnClickListener(OnClickListenerProxy(lambda v: push_current_note()))
        header.addView(push_btn)

        root.addView(header, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)))

        progress_bar = ProgressBar(activity, None, 16842872)
        progress_bar.setMax(100)
        progress_bar.setIndeterminate(True)
        progress_bar.setVisibility(View.GONE)
        progress_bar.setLayoutParams(LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(2)))
        state["progress_ref"][0] = progress_bar
        root.addView(progress_bar)

        # 2. Horizontal Note Tabs Strip
        scroll_tabs = HorizontalScrollView(activity)
        scroll_tabs.setHorizontalScrollBarEnabled(False)
        scroll_tabs.setPadding(dp(12), dp(4), dp(12), dp(6))
        tab_container = LinearLayout(activity)
        tab_container.setOrientation(LinearLayout.HORIZONTAL)
        tab_container.setGravity(Gravity.CENTER_VERTICAL)
        scroll_tabs.addView(tab_container)
        state["tabs_container_ref"][0] = tab_container
        root.addView(scroll_tabs, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        # 3. Content Frame (Editor / Preview)
        content_frame = FrameLayout(activity)
        content_frame_lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1.0)
        content_frame.setLayoutParams(content_frame_lp)

        # 3a. Edit View
        editor_scroll = ScrollView(activity)
        editor_scroll.setFillViewport(True)
        touch_listener = WebTouchListener()
        editor_scroll.setOnTouchListener(touch_listener)

        edit = EditText(activity)
        edit.setText(initial_content)
        edit.setHint(tr("Заметки в формате Markdown...", "Write markdown notes here..."))
        edit.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
        edit.setTypeface(Typeface.MONOSPACE)
        edit.setGravity(Gravity.TOP | Gravity.START)
        edit.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
        edit.setHintTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText))
        edit.setBackgroundColor(0)
        edit.setPadding(dp(16), dp(10), dp(16), dp(16))
        state["edit_ref"][0] = edit

        editor_scroll.addView(edit, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        content_frame.addView(editor_scroll, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        state["editor_scroll_ref"][0] = editor_scroll

        # 3b. Rendered Preview View
        preview_scroll = ScrollView(activity)
        preview_scroll.setFillViewport(True)
        preview_scroll.setOnTouchListener(touch_listener)
        preview_scroll.setVisibility(View.GONE)

        preview_box = LinearLayout(activity)
        preview_box.setOrientation(LinearLayout.VERTICAL)
        preview_box.setPadding(dp(16), dp(10), dp(16), dp(24))
        preview_scroll.addView(preview_box, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        content_frame.addView(preview_scroll, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        state["preview_scroll_ref"][0] = preview_scroll
        state["preview_box_ref"][0] = preview_box

        root.addView(content_frame)

        # 4. Status Bar
        status_bar = LinearLayout(activity)
        status_bar.setOrientation(LinearLayout.HORIZONTAL)
        status_bar.setGravity(Gravity.CENTER_VERTICAL)
        status_bar.setPadding(dp(16), dp(6), dp(16), dp(8))
        status_bar.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite))

        status_tv = TextView(activity)
        status_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 12)
        status_tv.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText))
        status_tv.setText(f"{curr_note['name']} • " + tr("Синхронизировано с GitHub", "Synced with GitHub"))
        state["status_ref"][0] = status_tv
        status_bar.addView(status_tv, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))

        root.addView(status_bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        class SyntaxWatcher(dynamic_proxy(TextWatcher)):
            def __init__(self_obj):
                super().__init__()
                self_obj.is_updating = False

            def beforeTextChanged(self_obj, s, start, count, after):
                pass

            def onTextChanged(self_obj, s, start, before, count):
                pass

            def afterTextChanged(self_obj, editable):
                if self_obj.is_updating:
                    return
                state["modified"] = True
                curr_n = state["notes"][state["idx"]]
                self._note_drafts[curr_n["name"]] = str(editable.toString())
                status_tv.setText(f"{curr_n['name']} • " + tr("Есть несохраненные изменения", "Unsaved changes"))
                self_obj.is_updating = True
                try:
                    MarkdownHighlighter.apply_syntax_highlighting(editable)
                except Exception as e:
                    debug_log(f"Highlighter error: {e}")
                finally:
                    self_obj.is_updating = False

        edit.addTextChangedListener(SyntaxWatcher())

        try:
            MarkdownHighlighter.apply_syntax_highlighting(edit.getText())
        except Exception:
            pass

        def update_mode_views():
            if state["preview_mode"]:
                btn_preview.setImageResource(edit_drawable)
                editor_scroll.setVisibility(View.GONE)
                preview_scroll.setVisibility(View.VISIBLE)
                AndroidUtilities.hideKeyboard(edit)
                render_markdown_preview()
            else:
                btn_preview.setImageResource(preview_drawable)
                preview_scroll.setVisibility(View.GONE)
                editor_scroll.setVisibility(View.VISIBLE)

        def render_markdown_preview():
            preview_box.removeAllViews()
            raw_text = str(edit.getText().toString())
            lines = raw_text.split("\n")

            header_col = Theme.getColor(Theme.key_windowBackgroundWhiteBlueHeader)
            text_col = Theme.getColor(Theme.key_windowBackgroundWhiteBlackText)
            gray_col = Theme.getColor(Theme.key_windowBackgroundWhiteGrayText)
            accent_c = Theme.getColor(Theme.key_featuredStickers_addButton)
            if accent_c == 0:
                accent_c = to_int32(0xFF2AABEE)

            in_code = False
            code_lines = []

            for line_idx, line in enumerate(lines):
                if line.startswith("```"):
                    if not in_code:
                        in_code = True
                        code_lines = []
                    else:
                        in_code = False
                        code_tv = TextView(activity)
                        code_tv.setText("\n".join(code_lines))
                        code_tv.setTypeface(Typeface.MONOSPACE)
                        code_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
                        code_tv.setTextColor(accent_c)
                        code_bg = GradientDrawable()
                        code_bg.setCornerRadius(dp(8))
                        code_bg.setColor(Theme.getColor(Theme.key_chat_messagePanelBackground))
                        code_tv.setBackground(code_bg)
                        code_tv.setPadding(dp(12), dp(8), dp(12), dp(8))
                        clp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                        clp.topMargin = dp(6)
                        clp.bottomMargin = dp(6)
                        preview_box.addView(code_tv, clp)
                    continue

                if in_code:
                    code_lines.append(line)
                    continue

                stripped = line.strip()
                if not stripped:
                    space = View(activity)
                    preview_box.addView(space, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(8)))
                    continue

                if stripped.startswith("# "):
                    tv = TextView(activity)
                    tv.setText(stripped[2:])
                    tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 22)
                    tv.setTypeface(Typeface.DEFAULT_BOLD)
                    tv.setTextColor(header_col)
                    tlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                    tlp.topMargin = dp(14)
                    tlp.bottomMargin = dp(4)
                    preview_box.addView(tv, tlp)
                elif stripped.startswith("## "):
                    tv = TextView(activity)
                    tv.setText(stripped[3:])
                    tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 18)
                    tv.setTypeface(Typeface.DEFAULT_BOLD)
                    tv.setTextColor(header_col)
                    tlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                    tlp.topMargin = dp(12)
                    tlp.bottomMargin = dp(4)
                    preview_box.addView(tv, tlp)
                elif stripped.startswith("### "):
                    tv = TextView(activity)
                    tv.setText(stripped[4:])
                    tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
                    tv.setTypeface(Typeface.DEFAULT_BOLD)
                    tv.setTextColor(header_col)
                    tlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                    tlp.topMargin = dp(10)
                    tlp.bottomMargin = dp(2)
                    preview_box.addView(tv, tlp)
                elif stripped.startswith("- [ ] ") or stripped.startswith("- [x] ") or stripped.startswith("- [X] "):
                    is_done = stripped.startswith("- [x] ") or stripped.startswith("- [X] ")
                    task_text = stripped[6:]

                    task_row = LinearLayout(activity)
                    task_row.setOrientation(LinearLayout.HORIZONTAL)
                    task_row.setGravity(Gravity.CENTER_VERTICAL)
                    task_row.setPadding(dp(2), dp(4), dp(2), dp(4))

                    check_box = TextView(activity)
                    check_box.setText("☑ " if is_done else "☐ ")
                    check_box.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 18)
                    check_box.setTextColor(accent_c if is_done else gray_col)
                    task_row.addView(check_box)

                    item_tv = TextView(activity)
                    item_tv.setText(task_text)
                    item_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                    item_tv.setTextColor(gray_col if is_done else text_col)
                    if is_done:
                        item_tv.setPaintFlags(item_tv.getPaintFlags() | 16)  # STRIKE_THRU_TEXT_FLAG
                    task_row.addView(item_tv, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))

                    def toggle_task(l_idx=line_idx, done=is_done):
                        lines_arr = str(edit.getText().toString()).split("\n")
                        if 0 <= l_idx < len(lines_arr):
                            cur_l = lines_arr[l_idx]
                            if done:
                                lines_arr[l_idx] = cur_l.replace("- [x] ", "- [ ] ").replace("- [X] ", "- [ ] ")
                            else:
                                lines_arr[l_idx] = cur_l.replace("- [ ] ", "- [x] ")
                            new_text = "\n".join(lines_arr)
                            edit.setText(new_text)
                            render_markdown_preview()

                    task_row.setClickable(True)
                    task_row.setFocusable(True)
                    task_row.setOnClickListener(OnClickListenerProxy(lambda v, li=line_idx, d=is_done: toggle_task(li, d)))
                    preview_box.addView(task_row)
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    bullet_row = LinearLayout(activity)
                    bullet_row.setOrientation(LinearLayout.HORIZONTAL)
                    bullet_row.setPadding(dp(4), dp(2), dp(4), dp(2))

                    dot = TextView(activity)
                    dot.setText("• ")
                    dot.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                    dot.setTextColor(accent_c)
                    bullet_row.addView(dot)

                    b_tv = TextView(activity)
                    b_tv.setText(stripped[2:])
                    b_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                    b_tv.setTextColor(text_col)
                    bullet_row.addView(b_tv, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))
                    preview_box.addView(bullet_row)
                elif stripped.startswith("> "):
                    q_row = LinearLayout(activity)
                    q_row.setOrientation(LinearLayout.HORIZONTAL)
                    q_row.setPadding(dp(8), dp(4), dp(8), dp(4))
                    bar = View(activity)
                    bar.setBackgroundColor(accent_c)
                    q_row.addView(bar, LinearLayout.LayoutParams(dp(3), ViewGroup.LayoutParams.MATCH_PARENT))

                    q_tv = TextView(activity)
                    q_tv.setText(stripped[2:])
                    q_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
                    q_tv.setTypeface(Typeface.ITALIC)
                    q_tv.setTextColor(gray_col)
                    q_tv.setPadding(dp(8), 0, 0, 0)
                    q_row.addView(q_tv, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))
                    preview_box.addView(q_row)
                elif stripped == "---" or stripped == "***":
                    div = View(activity)
                    div.setBackgroundColor(Theme.getColor(Theme.key_divider))
                    dlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1))
                    dlp.topMargin = dp(8)
                    dlp.bottomMargin = dp(8)
                    preview_box.addView(div, dlp)
                else:
                    tv = TextView(activity)
                    tv.setText(stripped)
                    tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                    tv.setTextColor(text_col)
                    tlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                    tlp.topMargin = dp(2)
                    tlp.bottomMargin = dp(2)
                    preview_box.addView(tv, tlp)

        def refresh_tabs():
            tab_container.removeAllViews()
            accent = Theme.getColor(Theme.key_featuredStickers_addButton)
            if accent == 0:
                accent = to_int32(0xFF2AABEE)
            inactive_bg = Theme.getColor(Theme.key_chat_messagePanelBackground)
            if inactive_bg == 0:
                inactive_bg = to_int32(0x22FFFFFF) if (Theme.isCurrentThemeDark() if hasattr(Theme, "isCurrentThemeDark") else True) else 0x15000000

            for i, note in enumerate(state["notes"]):
                chip = TextView(activity)
                chip.setText(note["name"])
                chip.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
                chip.setSingleLine(True)
                is_active = (i == state["idx"])

                bg = GradientDrawable()
                bg.setCornerRadius(dp(14))
                if is_active:
                    bg.setColor(accent)
                    chip.setTextColor(to_int32(0xFFFFFFFF))
                    chip.setTypeface(Typeface.DEFAULT_BOLD)
                else:
                    bg.setColor(inactive_bg)
                    bg.setStroke(dp(1), Theme.getColor(Theme.key_divider))
                    chip.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
                    chip.setTypeface(Typeface.DEFAULT)

                chip.setBackground(bg)
                chip.setPadding(dp(12), dp(6), dp(12), dp(6))
                chip.setClickable(True)
                chip.setFocusable(True)
                chip.setOnClickListener(OnClickListenerProxy(lambda v, n_idx=i: switch_to_note(n_idx)))

                lp_c = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                lp_c.rightMargin = dp(6)
                tab_container.addView(chip, lp_c)

            new_chip = TextView(activity)
            new_chip.setText("+ " + tr("Новая", "New"))
            new_chip.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
            new_chip.setTypeface(Typeface.DEFAULT_BOLD)
            new_chip.setTextColor(accent)
            new_bg = GradientDrawable()
            new_bg.setCornerRadius(dp(14))
            new_bg.setColor(inactive_bg)
            new_bg.setStroke(dp(1), accent)
            new_chip.setBackground(new_bg)
            new_chip.setPadding(dp(10), dp(6), dp(10), dp(6))
            new_chip.setClickable(True)
            new_chip.setFocusable(True)
            new_chip.setOnClickListener(OnClickListenerProxy(lambda v: prompt_new_note()))
            tab_container.addView(new_chip)

        def switch_to_note(new_idx: int):
            if new_idx == state["idx"] or new_idx < 0 or new_idx >= len(state["notes"]):
                return

            curr_n = state["notes"][state["idx"]]
            self._note_drafts[curr_n["name"]] = str(edit.getText().toString())

            state["idx"] = new_idx
            target = state["notes"][new_idx]
            title_tv.setText(target["name"])
            refresh_tabs()

            if target["name"] in self._note_drafts:
                edit.setText(self._note_drafts[target["name"]])
                edit.setSelection(edit.length())
                status_tv.setText(f"{target['name']} • " + tr("Черновик", "Local draft"))
                if state["preview_mode"]:
                    render_markdown_preview()
                return

            progress_bar.setVisibility(View.VISIBLE)
            status_tv.setText(f"{target['name']} • " + tr("Загрузка...", "Loading..."))

            def fetch():
                try:
                    c, s = client.get_note_content(target["path"])
                    state["sha"] = s
                    target["sha"] = s
                    self._note_drafts[target["name"]] = c

                    def on_loaded():
                        progress_bar.setVisibility(View.GONE)
                        edit.setText(c)
                        edit.setSelection(edit.length())
                        status_tv.setText(f"{target['name']} • " + tr("Синхронизировано", "Synced"))
                        if state["preview_mode"]:
                            render_markdown_preview()

                    run_on_ui_thread(on_loaded)
                except Exception as e:
                    debug_log(f"fetch note error: {e}")

                    def on_fail():
                        progress_bar.setVisibility(View.GONE)
                        status_tv.setText(f"{target['name']} • " + tr("Ошибка загрузки", "Failed to load"))

                    run_on_ui_thread(on_fail)

            run_on_queue(fetch)

        def prompt_new_note():
            new_edit = EditText(activity)
            new_edit.setHint("ideas.md")
            new_edit.setSingleLine(True)
            new_edit.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)

            def on_create(d, w):
                fname = str(new_edit.getText().toString()).strip()
                if not fname:
                    return
                if not fname.endswith(".md") and not fname.endswith(".txt"):
                    fname += ".md"

                new_note = {"name": fname, "path": f"{client.vault_path}/{fname}", "sha": "", "size": 0}
                state["notes"].append(new_note)
                template_text = f"# {fname.replace('.md', '').capitalize()}\n\n"
                self._note_drafts[fname] = template_text
                state["idx"] = len(state["notes"]) - 1
                state["sha"] = ""
                title_tv.setText(fname)
                edit.setText(template_text)
                edit.setSelection(edit.length())
                refresh_tabs()
                status_tv.setText(f"{fname} • " + tr("Новая заметка (нажмите Пуш)", "New draft (tap Push to save)"))
                d.dismiss()

            bld = AlertDialogBuilder(activity)
            bld.set_title(tr("Новая заметка", "Create New Note"))
            bld.set_view(new_edit)
            bld.set_positive_button(tr("Создать", "Create"), on_create)
            bld.set_negative_button(tr("Отмена", "Cancel"), lambda d, w: d.dismiss())
            bld.show()
            new_edit.requestFocus()
            AndroidUtilities.showKeyboard(new_edit)

        def open_notes_list_sheet():
            picker_bld = BottomSheet.Builder(activity)
            picker_bld.setApplyBottomPadding(False)

            p_root = LinearLayout(activity)
            p_root.setOrientation(LinearLayout.VERTICAL)
            p_root.setPadding(dp(16), dp(12), dp(16), dp(16))

            p_title = TextView(activity)
            p_title.setText(tr("Выберите заметку", "Select Note"))
            p_title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 18)
            p_title.setTypeface(Typeface.DEFAULT_BOLD)
            p_title.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
            p_title.setPadding(0, 0, 0, dp(12))
            p_root.addView(p_title)

            p_scroll = ScrollView(activity)
            p_list = LinearLayout(activity)
            p_list.setOrientation(LinearLayout.VERTICAL)

            p_sheet_ref = [None]

            for i, note in enumerate(state["notes"]):
                row = LinearLayout(activity)
                row.setOrientation(LinearLayout.HORIZONTAL)
                row.setGravity(Gravity.CENTER_VERTICAL)
                row.setPadding(dp(12), dp(10), dp(12), dp(10))
                try:
                    row.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 2))
                except Exception:
                    pass

                icon = ImageView(activity)
                icon.setImageResource(folder_drawable)
                icon.setColorFilter(Theme.getColor(Theme.key_windowBackgroundWhiteGrayIcon))
                row.addView(icon, LinearLayout.LayoutParams(dp(22), dp(22)))

                r_tv = TextView(activity)
                r_tv.setText(note["name"])
                r_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                r_tv.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText))
                if i == state["idx"]:
                    r_tv.setTypeface(Typeface.DEFAULT_BOLD)
                row.addView(r_tv, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0))

                if i == state["idx"]:
                    badge = TextView(activity)
                    badge.setText(tr("Активна", "Active"))
                    badge.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 12)
                    badge.setTextColor(accent_col)
                    row.addView(badge)

                row.setClickable(True)
                row.setFocusable(True)

                def on_pick(idx=i):
                    if p_sheet_ref[0]:
                        p_sheet_ref[0].dismiss()
                    switch_to_note(idx)

                row.setOnClickListener(OnClickListenerProxy(lambda v, ix=i: on_pick(ix)))
                p_list.addView(row)

            new_btn = TextView(activity)
            new_btn.setText("+ " + tr("Создать новую заметку", "Create new note"))
            new_btn.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
            new_btn.setTypeface(Typeface.DEFAULT_BOLD)
            new_btn.setTextColor(accent_col)
            new_btn.setPadding(dp(12), dp(12), dp(12), dp(12))
            new_btn.setClickable(True)
            new_btn.setFocusable(True)

            def on_new_tap():
                if p_sheet_ref[0]:
                    p_sheet_ref[0].dismiss()
                prompt_new_note()

            new_btn.setOnClickListener(OnClickListenerProxy(lambda v: on_new_tap()))
            p_list.addView(new_btn)

            p_scroll.addView(p_list)
            p_root.addView(p_scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(260)))

            picker_bld.setCustomView(p_root)
            p_sheet = picker_bld.create()
            p_sheet_ref[0] = p_sheet
            p_sheet.show()

        def push_current_note():
            curr_text = str(edit.getText().toString())
            curr_n = state["notes"][state["idx"]]
            fname = curr_n["name"]

            progress_bar.setVisibility(View.VISIBLE)
            status_tv.setText(f"{fname} • " + tr("Отправка в Git...", "Pushing to GitHub..."))
            BulletinHelper.show_info(tr(f"Отправка {fname} в GitHub...", f"Pushing {fname} to GitHub..."))

            committer_name = str(self.get_setting("committer_name", DEFAULT_BOT_NAME)).strip()
            committer_email = str(self.get_setting("committer_email", DEFAULT_BOT_EMAIL)).strip()

            def push_worker():
                try:
                    new_sha = client.push_note(
                        filename=fname,
                        content=curr_text,
                        sha=state["sha"] if state["sha"] else None,
                        committer_name=committer_name,
                        committer_email=committer_email,
                    )
                    state["sha"] = new_sha
                    curr_n["sha"] = new_sha
                    state["modified"] = False
                    self._note_drafts[fname] = curr_text

                    def on_push_done():
                        progress_bar.setVisibility(View.GONE)
                        status_tv.setText(f"{fname} • " + tr(f"Запушено в {time.strftime('%H:%M:%S')}", f"Pushed at {time.strftime('%H:%M:%S')}"))
                        BulletinHelper.show_success(tr(f"Заметка {fname} запушена!", f"Pushed {fname} to GitHub!"))

                    run_on_ui_thread(on_push_done)
                except urllib.error.HTTPError as he:
                    err_msg = f"HTTP Error {he.code}"
                    if he.code == 409:
                        err_msg = tr("Конфликт: файл изменился на GitHub!", "Conflict: note changed on GitHub!")

                    def on_push_err():
                        progress_bar.setVisibility(View.GONE)
                        status_tv.setText(f"{fname} • {err_msg}")
                        BulletinHelper.show_error(err_msg)

                    run_on_ui_thread(on_push_err)
                except Exception as e:
                    debug_log(f"push error: {e}")

                    def on_err():
                        progress_bar.setVisibility(View.GONE)
                        status_tv.setText(f"{fname} • " + tr("Ошибка пуша", "Push failed"))
                        BulletinHelper.show_error(f"Push failed: {e}")

                    run_on_ui_thread(on_err)

            run_on_queue(push_worker)

        def on_close_clicked():
            if state["modified"]:
                curr_n = state["notes"][state["idx"]]
                self._note_drafts[curr_n["name"]] = str(edit.getText().toString())
            if state["sheet"]:
                state["sheet"].dismiss()

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
        state["sheet"] = sheet
        refresh_tabs()
        sheet.show()
        self.log("sheet.show() was called successfully!")

    def create_settings(self) -> List[Any]:
        rows: List[Any] = []
        rows.append(Header(tr("Заметки в Git", "Notes Vault")))
        rows.append(
            Divider(
                text=tr(
                    "Редактор заметок в формате Markdown, подключенный к вашему Git-репозиторию.\n\n"
                    "Иконка в строке ввода открывает редактор на весь экран, позволяя редактировать и пушить заметки в пару кликов.",
                    "Markdown notes editor connected directly to your GitHub repository from the chat input bar.\n\n"
                    "Tapping the notes icon in chat opens the fullscreen editor, allowing you to edit and push notes in a couple of clicks.",
                )
            )
        )

        rows.append(Header(tr("Репозиторий GitHub", "GitHub Repository")))
        rows.append(
            Input(
                key="github_token",
                text=tr("Токен GitHub", "GitHub Token"),
                subtext=tr("Personal Access Token с областью 'repo'", "Personal Access Token with 'repo' scope"),
                default="",
                icon="msg_permissions",
            )
        )
        rows.append(
            Input(
                key="github_repo",
                text=tr("Репозиторий", "Repository"),
                subtext="owner/repo",
                default=DEFAULT_REPO,
                icon="msg_link",
            )
        )
        rows.append(
            Input(
                key="github_branch",
                text=tr("Ветка", "Branch"),
                default=DEFAULT_BRANCH,
                icon="msg_folders",
            )
        )
        rows.append(
            Input(
                key="vault_path",
                text=tr("Папка заметок", "Vault Path"),
                subtext=tr("Папка в репозитории (например vault)", "Folder in repository (e.g. vault)"),
                default=DEFAULT_VAULT_PATH,
                icon="msg_folders",
            )
        )
        rows.append(
            Selector(
                key="btn_position",
                text=tr("Положение иконки в чате", "Button Position"),
                items=[
                    tr("Слева (рядом с эмодзи)", "Left (Next to emoji)"),
                    tr("Справа (рядом со скрепкой)", "Right (Next to attachment)"),
                    tr("В шапке чата (ActionBar)", "Chat Header (Top bar)"),
                ],
                default=int(self.get_setting("btn_position", 1)),
                icon="msg_settings",
            )
        )

        rows.append(Header(tr("Автор коммитов", "Git Committer")))
        rows.append(
            Input(
                key="committer_name",
                text=tr("Имя коммиттера", "Committer Name"),
                default=DEFAULT_BOT_NAME,
                icon="msg_contact",
            )
        )
        rows.append(
            Input(
                key="committer_email",
                text=tr("Email коммиттера", "Committer Email"),
                default=DEFAULT_BOT_EMAIL,
                icon="msg_info",
            )
        )

        rows.append(
            Divider(
                text=f"https://github.com/{self.get_setting('github_repo', DEFAULT_REPO)}"
            )
        )

        return rows
