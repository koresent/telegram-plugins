# -*- coding: utf-8 -*-
"""
Notes Vault Plugin for exteraGram / AyuGram
Markdown notes editor connected directly to your GitHub repository from the chat input bar.
"""

import base64
import json
import time
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from android.graphics import Color, Typeface
from android.graphics.drawable import GradientDrawable
from android.util import TypedValue
from android.view import Gravity, View, ViewGroup
from android.widget import (
    EditText,
    FrameLayout,
    HorizontalScrollView,
    ImageView,
    LinearLayout,
    ScrollView,
    TextView,
)
from java import dynamic_proxy, jclass
from java.lang import Class as JClass
from org.telegram.messenger import (
    AndroidUtilities,
    ApplicationLoader,
    NotificationCenter,
)
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import LayoutHelper

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MethodHook
from client_utils import get_last_fragment, run_on_queue
from hook_utils import find_class, get_private_field
from ui.alert import AlertDialogBuilder
from ui.bulletin import BulletinHelper
from ui.settings import Divider, Header, Input, Selector

__id__ = "notes_vault"
__name__ = "Notes Vault"
__description__ = "Markdown notes editor connected directly to your GitHub repository from the chat input bar"
__author__ = "@koresent"
__version__ = "1.0.0"
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


class GitHubNotesClient:
    """Handles GitHub REST API operations for the notes vault repository."""

    def __init__(self, token: str, repo: str = DEFAULT_REPO, branch: str = DEFAULT_BRANCH, vault_path: str = DEFAULT_VAULT_PATH):
        self.token = str(token or "").strip()
        self.repo = str(repo or DEFAULT_REPO).strip().strip("/")
        self.branch = str(branch or DEFAULT_BRANCH).strip()
        self.vault_path = str(vault_path or DEFAULT_VAULT_PATH).strip().strip("/")

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ExteraGram-NotesVault/1.0",
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
        self._active_note: Optional[Dict[str, Any]] = None
        self._active_content: str = ""

    def on_plugin_load(self):
        self.is_active = True
        self.log("NotesVaultPlugin loading")
        self._install_hooks()
        # If ChatActivity is already visible, attach button right away
        try:
            frag = get_last_fragment()
            if frag and "ChatActivity" in frag.getClass().getName():
                run_on_ui_thread(lambda: self.attach_button(frag))
        except Exception as e:
            self.log(f"on_plugin_load initial attach error: {e}")
        self.log("NotesVaultPlugin loaded successfully")

    def on_plugin_unload(self):
        self.is_active = False
        for u in self._unhooks:
            try:
                self.unhook_method(u)
            except Exception:
                pass
        self._unhooks.clear()
        # Remove any attached button from open ChatActivity
        try:
            frag = get_last_fragment()
            if frag:
                ev = getattr(frag, "chatActivityEnterView", None) or (
                    frag.getChatActivityEnterView() if hasattr(frag, "getChatActivityEnterView") else None
                )
                if ev:
                    btn = ev.findViewWithTag("notes_vault_btn")
                    if btn and btn.getParent():
                        btn.getParent().removeView(btn)
        except Exception:
            pass
        self.log("NotesVaultPlugin unloaded")

    # ---------- Hooking ChatActivity ----------

    def _install_hooks(self):
        try:
            ChatActivity_cls = find_class("org.telegram.ui.ChatActivity")
            Context_cls = find_class("android.content.Context")
            if not ChatActivity_cls or not Context_cls:
                self.log("ChatActivity or Context class not found")
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

            self.log(f"Installed {len(self._unhooks)} hooks for ChatActivity")
        except Exception as e:
            self.log(f"_install_hooks error: {e}\n{traceback.format_exc()}")

    # ---------- Button Insertion ----------

    def _find_drawable(self, name: str) -> Optional[int]:
        try:
            ctx = ApplicationLoader.applicationContext
            if ctx:
                res = ctx.getResources()
                rid = res.getIdentifier(name, "drawable", ctx.getPackageName())
                if rid:
                    return rid
        except Exception:
            pass
        return None

    def attach_button(self, fragment: Any):
        if not fragment or not self.is_active:
            return
        try:
            ev = getattr(fragment, "chatActivityEnterView", None) or (
                fragment.getChatActivityEnterView() if hasattr(fragment, "getChatActivityEnterView") else None
            )
            if not ev:
                return

            # Avoid duplicate button injection
            if ev.findViewWithTag("notes_vault_btn") is not None:
                return

            pos = int(self.get_setting("btn_position", 0))  # 0: Left (attach bar), 1: Right (send bar)
            host = None
            if pos == 1:
                host = get_private_field(ev, "sendButtonContainer")

            if host is None:
                host = get_private_field(ev, "attachLayout")

            if host is None:
                for fn in ("attachLayout", "sendButtonContainer", "textFieldContainer", "messageEditTextContainer"):
                    cand = get_private_field(ev, fn)
                    if cand is not None and isinstance(cand, ViewGroup):
                        host = cand
                        break

            if host is None:
                return

            ctx = host.getContext()
            btn = FrameLayout(ctx)
            btn.setTag("notes_vault_btn")

            # Oval ripple selector background
            btn.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 1))

            iv = ImageView(ctx)
            rid = self._find_drawable("msg_edit") or self._find_drawable("msg_text") or self._find_drawable("msg_saved")
            if rid:
                iv.setImageResource(rid)

            # Vibrant Telegram Accent Color
            accent_col = Theme.getColor(Theme.key_featuredStickers_addButton)
            iv.setColorFilter(accent_col)

            pad = AndroidUtilities.dp(10)
            btn.setPadding(pad, pad, pad, pad)
            btn.addView(iv, FrameLayout.LayoutParams(AndroidUtilities.dp(24), AndroidUtilities.dp(24), Gravity.CENTER))

            # Click listener
            class _BtnClickListener(dynamic_proxy(View.OnClickListener)):
                def __init__(self_proxy, plugin, frag):
                    super().__init__()
                    self_proxy.plugin = plugin
                    self_proxy.frag = frag

                def onClick(self_proxy, v):
                    self_proxy.plugin.on_button_clicked(self_proxy.frag)

            btn.setOnClickListener(_BtnClickListener(self, fragment))

            lp = LinearLayout.LayoutParams(AndroidUtilities.dp(44), AndroidUtilities.dp(44))
            lp.gravity = Gravity.CENTER_VERTICAL
            if pos == 0 and isinstance(host, LinearLayout):
                host.addView(btn, 0, lp)
            else:
                host.addView(btn, lp)

            self.log("Notes Vault button successfully attached to chat input bar")
        except Exception as e:
            self.log(f"attach_button error: {e}\n{traceback.format_exc()}")

    # ---------- Editor & GitHub Actions ----------

    def _get_client(self) -> GitHubNotesClient:
        token = str(self.get_setting("github_token", "")).strip()
        repo = str(self.get_setting("github_repo", DEFAULT_REPO)).strip() or DEFAULT_REPO
        vault_path = str(self.get_setting("vault_path", DEFAULT_VAULT_PATH)).strip() or DEFAULT_VAULT_PATH
        return GitHubNotesClient(token=token, repo=repo, vault_path=vault_path)

    def on_button_clicked(self, fragment: Any):
        token = str(self.get_setting("github_token", "")).strip()
        if not token:
            self._prompt_token_dialog()
            return
        self._load_and_open_editor(fragment)

    def _prompt_token_dialog(self):
        def build():
            activity = get_activity()
            if not activity:
                return

            layout = LinearLayout(activity)
            layout.setOrientation(LinearLayout.VERTICAL)
            pad_h = AndroidUtilities.dp(24)
            pad_v = AndroidUtilities.dp(16)
            layout.setPadding(pad_h, pad_v, pad_h, pad_v)

            desc = TextView(activity)
            desc.setText(
                "GitHub Personal Access Token is required to access your notes repository.\n\n"
                "Please enter a token with 'repo' scope (from github.com/settings/tokens):"
            )
            desc.setTextSize(14.0)
            desc.setTextColor(Theme.getColor(Theme.key_dialogTextGray2))
            layout.addView(desc)

            token_edit = EditText(activity)
            token_edit.setHint("ghp_... or gho_...")
            token_edit.setSingleLine(True)
            token_edit.setTextSize(15.0)
            token_edit.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
            token_edit.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))
            layout.addView(token_edit)

            def on_save(dialog, which):
                new_tok = str(token_edit.getText().toString()).strip()
                if new_tok:
                    self.set_setting("github_token", new_tok, reload_settings=True)
                    BulletinHelper.show_success("GitHub Token saved!")
                    self.on_button_clicked(get_last_fragment())
                dialog.dismiss()

            builder = AlertDialogBuilder(activity)
            builder.set_title("GitHub Token Required")
            builder.set_view(layout)
            builder.set_positive_button("Save", on_save)
            builder.set_negative_button("Cancel", lambda d, w: d.dismiss())
            builder.show()

            token_edit.requestFocus()
            AndroidUtilities.showKeyboard(token_edit)

        run_on_ui_thread(build)

    def _load_and_open_editor(self, fragment: Any):
        client = self._get_client()
        BulletinHelper.show_info("Connecting to GitHub...")

        def worker():
            try:
                notes = client.list_notes()
                if not notes:
                    # Provide default note if empty
                    notes = [{"name": "home.md", "path": f"{client.vault_path}/home.md", "sha": "", "size": 0}]

                self._cached_notes = notes
                first_note = notes[0]
                content = ""
                sha = first_note.get("sha", "")
                if sha:
                    try:
                        content, sha = client.get_note_content(first_note["path"])
                    except Exception as e:
                        debug_log(f"Failed to fetch content for {first_note['name']}: {e}")

                first_note["sha"] = sha
                run_on_ui_thread(lambda: self._show_editor_dialog(notes, 0, content, sha, fragment))
            except urllib.error.HTTPError as he:
                msg = f"GitHub API Error {he.code}"
                if he.code == 401:
                    msg = "Invalid GitHub Token (401 Unauthorized)"
                elif he.code == 404:
                    msg = f"Repo {client.repo}/{client.vault_path} not found (404)"
                run_on_ui_thread(lambda: BulletinHelper.show_error(msg))
            except Exception as e:
                debug_log(f"worker error: {e}\n{traceback.format_exc()}")
                run_on_ui_thread(lambda: BulletinHelper.show_error(f"Failed to connect: {e}"))

        run_on_queue(worker)

    def _show_editor_dialog(
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
        state = {
            "notes": list(notes),
            "idx": current_idx,
            "sha": current_sha,
            "dialog": None,
            "modified": False,
        }

        root = LinearLayout(activity)
        root.setOrientation(LinearLayout.VERTICAL)
        pad_h = AndroidUtilities.dp(16)
        pad_v = AndroidUtilities.dp(8)
        root.setPadding(pad_h, pad_v, pad_h, pad_v)

        # 1. Notes Tab Selector
        scroll_tabs = HorizontalScrollView(activity)
        scroll_tabs.setHorizontalScrollBarEnabled(False)
        tab_container = LinearLayout(activity)
        tab_container.setOrientation(LinearLayout.HORIZONTAL)
        tab_container.setGravity(Gravity.CENTER_VERTICAL)
        scroll_tabs.addView(tab_container)
        root.addView(scroll_tabs, LayoutHelper.createLinear(-1, -2, 0, 0, 0, 8))

        # 2. Main Markdown Text Editor
        editor_scroll = ScrollView(activity)
        editor_scroll.setFillViewport(True)

        edit = EditText(activity)
        edit.setText(initial_content)
        edit.setHint("Write markdown notes here...")
        edit.setTextSize(14.5)
        edit.setTypeface(Typeface.MONOSPACE)
        edit.setGravity(Gravity.TOP | Gravity.START)
        edit.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
        edit.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))

        # Styling editor card background
        card_bg = GradientDrawable()
        card_bg.setCornerRadius(AndroidUtilities.dp(8))
        card_bg.setColor(Theme.getColor(Theme.key_chat_messagePanelBackground))
        card_bg.setStroke(AndroidUtilities.dp(1), Theme.getColor(Theme.key_divider))
        edit.setBackground(card_bg)
        edit_pad = AndroidUtilities.dp(12)
        edit.setPadding(edit_pad, edit_pad, edit_pad, edit_pad)
        edit.setMinLines(12)

        editor_scroll.addView(edit, LayoutHelper.createFrame(-1, -1))
        # Fixed height for editor box inside dialog
        root.addView(editor_scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, AndroidUtilities.dp(260)))

        # 3. Status Bar
        status_tv = TextView(activity)
        status_tv.setTextSize(12.0)
        status_tv.setTextColor(Theme.getColor(Theme.key_dialogTextGray2))
        status_tv.setPadding(0, AndroidUtilities.dp(6), 0, 0)
        root.addView(status_tv)

        def update_status(text: str):
            curr_note = state["notes"][state["idx"]]
            status_tv.setText(f"{curr_note['name']} • {text}")

        update_status("Synced with GitHub")

        # Function to rebuild note chips
        def refresh_tabs():
            tab_container.removeAllViews()
            accent_col = Theme.getColor(Theme.key_featuredStickers_addButton)
            inactive_bg = Theme.getColor(Theme.key_chat_messagePanelBackground)

            for i, note in enumerate(state["notes"]):
                chip = TextView(activity)
                chip.setText(note["name"])
                chip.setTextSize(13.5)
                chip.setSingleLine(True)
                is_active = (i == state["idx"])

                bg = GradientDrawable()
                bg.setCornerRadius(AndroidUtilities.dp(16))
                if is_active:
                    bg.setColor(accent_col)
                    chip.setTextColor(0xFFFFFFFF)
                    chip.setTypeface(AndroidUtilities.bold())
                else:
                    bg.setColor(inactive_bg)
                    bg.setStroke(AndroidUtilities.dp(1), Theme.getColor(Theme.key_divider))
                    chip.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))

                chip.setBackground(bg)
                chip_pad_h = AndroidUtilities.dp(12)
                chip_pad_v = AndroidUtilities.dp(6)
                chip.setPadding(chip_pad_h, chip_pad_v, chip_pad_h, chip_pad_v)

                class _ChipClick(dynamic_proxy(View.OnClickListener)):
                    def __init__(self_obj, note_idx):
                        super().__init__()
                        self_obj.note_idx = note_idx

                    def onClick(self_obj, v):
                        switch_to_note(self_obj.note_idx)

                chip.setOnClickListener(_ChipClick(i))
                lp_chip = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lp_chip.rightMargin = AndroidUtilities.dp(6)
                tab_container.addView(chip, lp_chip)

            # "+ New" Chip
            new_chip = TextView(activity)
            new_chip.setText("+ New")
            new_chip.setTextSize(13.5)
            new_chip.setTypeface(AndroidUtilities.bold())
            new_chip.setTextColor(accent_col)
            new_bg = GradientDrawable()
            new_bg.setCornerRadius(AndroidUtilities.dp(16))
            new_bg.setColor(inactive_bg)
            new_bg.setStroke(AndroidUtilities.dp(1), accent_col)
            new_chip.setBackground(new_bg)
            new_chip.setPadding(AndroidUtilities.dp(10), AndroidUtilities.dp(6), AndroidUtilities.dp(10), AndroidUtilities.dp(6))

            class _NewClick(dynamic_proxy(View.OnClickListener)):
                def onClick(self_obj, v):
                    prompt_new_note()

            new_chip.setOnClickListener(_NewClick())
            tab_container.addView(new_chip)

        def switch_to_note(new_idx: int):
            if new_idx == state["idx"]:
                return
            state["idx"] = new_idx
            refresh_tabs()
            target_note = state["notes"][new_idx]
            update_status("Loading...")

            def fetch():
                try:
                    c, s = client.get_note_content(target_note["path"])
                    state["sha"] = s
                    target_note["sha"] = s

                    def update():
                        edit.setText(c)
                        edit.setSelection(edit.length())
                        update_status("Synced")

                    run_on_ui_thread(update)
                except Exception as e:
                    debug_log(f"fetch error: {e}")
                    run_on_ui_thread(lambda: update_status("Failed to load"))

            run_on_queue(fetch)

        def prompt_new_note():
            new_edit = EditText(activity)
            new_edit.setHint("note_name.md")
            new_edit.setSingleLine(True)

            def on_create(d, w):
                fname = str(new_edit.getText().toString()).strip()
                if not fname:
                    return
                if not fname.endswith(".md") and not fname.endswith(".txt"):
                    fname += ".md"
                new_obj = {"name": fname, "path": f"{client.vault_path}/{fname}", "sha": "", "size": 0}
                state["notes"].append(new_obj)
                state["idx"] = len(state["notes"]) - 1
                state["sha"] = ""
                edit.setText(f"# {fname.replace('.md', '').capitalize()}\n\n")
                refresh_tabs()
                update_status("New local draft (Push to create)")
                d.dismiss()

            bld = AlertDialogBuilder(activity)
            bld.set_title("Create New Note")
            bld.set_view(new_edit)
            bld.set_positive_button("Create", on_create)
            bld.set_negative_button("Cancel", lambda d, w: d.dismiss())
            bld.show()

        # 4. Action Handlers
        def on_push_clicked(dialog, which):
            curr_text = str(edit.getText().toString())
            curr_note = state["notes"][state["idx"]]
            fname = curr_note["name"]
            update_status("Pushing to GitHub...")
            BulletinHelper.show_info(f"Pushing {fname} to GitHub...")

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
                    curr_note["sha"] = new_sha

                    def on_success():
                        update_status(f"Pushed at {time.strftime('%H:%M:%S')}")
                        BulletinHelper.show_success(f"Pushed {fname} to GitHub!")

                    run_on_ui_thread(on_success)
                except urllib.error.HTTPError as he:
                    err_msg = f"Push failed: HTTP {he.code}"
                    if he.code == 409:
                        err_msg = "Conflict: note changed on GitHub! Switch note to reload."
                    run_on_ui_thread(lambda: BulletinHelper.show_error(err_msg))
                    run_on_ui_thread(lambda: update_status("Push conflict or error"))
                except Exception as e:
                    debug_log(f"push error: {e}")
                    run_on_ui_thread(lambda: BulletinHelper.show_error(f"Push failed: {e}"))
                    run_on_ui_thread(lambda: update_status("Push failed"))

            run_on_queue(push_worker)

        def on_insert_to_chat(dialog, which):
            try:
                curr_text = str(edit.getText().toString())
                if curr_text and fragment:
                    ev = getattr(fragment, "chatActivityEnterView", None) or (
                        fragment.getChatActivityEnterView() if hasattr(fragment, "getChatActivityEnterView") else None
                    )
                    if ev:
                        msg_edit = get_private_field(ev, "messageEditText")
                        if msg_edit:
                            msg_edit.setText(curr_text)
                            msg_edit.setSelection(msg_edit.length())
                            AndroidUtilities.showKeyboard(msg_edit)
                            BulletinHelper.show_success("Inserted into chat input")
                            dialog.dismiss()
            except Exception as e:
                debug_log(f"insert error: {e}")

        # Build AlertDialog
        builder = AlertDialogBuilder(activity)
        builder.set_title("Notes Vault")
        builder.set_view(root)
        builder.set_positive_button("Push", on_push_clicked)
        builder.set_neutral_button("Insert in chat", on_insert_to_chat)
        builder.set_negative_button("Close", lambda d, w: d.dismiss())

        state["dialog"] = builder.show()
        refresh_tabs()

    # ---------- Settings UI ----------

    def create_settings(self) -> List[Any]:
        rows: List[Any] = []
        rows.append(Header("Notes Vault"))
        rows.append(
            Divider(
                text="Markdown notes editor connected directly to your GitHub repository from the chat input bar.\n\n"
                     "Tapping the notes icon in chat opens the editor, allowing you to edit and push notes "
                     "in a couple of clicks without typing commit messages."
            )
        )

        rows.append(Header("GitHub Repository"))
        rows.append(
            Input(
                key="github_token",
                text="GitHub Token",
                subtext="Personal Access Token with 'repo' scope",
                default="",
                icon="msg_permissions",
            )
        )
        rows.append(
            Input(
                key="github_repo",
                text="Repository",
                subtext="Format: owner/repo",
                default=DEFAULT_REPO,
                icon="msg_link",
            )
        )
        rows.append(
            Input(
                key="vault_path",
                text="Vault Path",
                subtext="Folder in repository where notes are stored",
                default=DEFAULT_VAULT_PATH,
                icon="msg_folders",
            )
        )
        rows.append(
            Selector(
                key="btn_position",
                text="Button Position",
                items=["Left (Attach bar)", "Right (Send bar)"],
                default=int(self.get_setting("btn_position", 0)),
                icon="msg_settings",
            )
        )

        rows.append(Header("Git Committer"))
        rows.append(
            Input(
                key="committer_name",
                text="Committer Name",
                default=DEFAULT_BOT_NAME,
                icon="msg_contact",
            )
        )
        rows.append(
            Input(
                key="committer_email",
                text="Committer Email",
                default=DEFAULT_BOT_EMAIL,
                icon="msg_info",
            )
        )

        rows.append(
            Divider(
                text=f"Auto-commit format: 'sync: auto-commit YYYY-MM-DD HH:MM'\n"
                     f"Repository: https://github.com/{self.get_setting('github_repo', DEFAULT_REPO)}"
            )
        )

        return rows
