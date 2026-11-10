# -*- coding: utf-8 -*-
"""
Plugin Updater for exteraGram / AyuGram.
Automatically checks for updates and installs newer versions of plugins
from the GitHub repository without requiring user confirmation.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from base_plugin import BasePlugin
from ui.bulletin import BulletinHelper
from ui.settings import Divider, Header, Selector, Switch, Text

try:
    from android_utils import run_on_ui_thread
except Exception:
    try:
        from org.telegram.messenger import AndroidUtilities

        def run_on_ui_thread(action, delay=0):
            if delay > 0:
                AndroidUtilities.runOnUIThread(action, delay)
            else:
                AndroidUtilities.runOnUIThread(action)
    except Exception:
        def run_on_ui_thread(action, delay=0):
            action()

try:
    from org.telegram.messenger import ApplicationLoader, Utilities
    from java import dynamic_proxy, jclass
except Exception:
    ApplicationLoader = None
    Utilities = None
    dynamic_proxy = None
    jclass = None

__id__ = "plugin_updater"
__name__ = "Plugin Updater"
__description__ = "Automatically updates installed repository plugins in the background without user confirmation."
__author__ = "@koresent"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__category__ = ["tools"]
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"

# Setting Keys
KEY_INTERVAL_IDX = "update_interval_idx"
KEY_NOTIFICATIONS = "notify_on_update"
KEY_REPO = "github_repo"
KEY_BRANCH = "github_branch"
KEY_LAST_CHECK_TS = "last_check_ts"
KEY_LAST_STATUS = "last_check_status"

DEFAULT_REPO = "koresent/telegram-plugins"
DEFAULT_BRANCH = "main"

INTERVAL_CHOICES: List[Tuple[str, int]] = [
    ("1 Hour", 3600),
    ("3 Hours", 10800),
    ("6 Hours", 21600),
    ("12 Hours (Default)", 43200),
    ("24 Hours", 86400),
]
INTERVAL_LABELS: List[str] = [item[0] for item in INTERVAL_CHOICES]
DEFAULT_INTERVAL_IDX = 3  # 12 Hours

FALLBACK_REPO_PLUGINS = [
    "avatar_online_ring",
    "bot_web_tabs",
    "chat_web_tabs",
    "cursor_glide",
    "local_rename",
    "notes_vault",
    "plugin_updater",
]


def log(msg: str) -> None:
    print(f"[{__name__}] {msg}")


# Java Callback proxy for PluginsController operations
if Utilities is not None and dynamic_proxy is not None:
    try:
        class PluginCallback(dynamic_proxy(Utilities.Callback)):
            def __init__(self, callback_fn):
                super().__init__()
                self._callback_fn = callback_fn

            def run(self, error):
                if self._callback_fn:
                    try:
                        self._callback_fn(error)
                    except Exception as err:
                        log(f"Error in PluginCallback: {err}")
    except Exception:
        PluginCallback = None
else:
    PluginCallback = None


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Extracts numeric semver components from a version string."""
    parts = re.findall(r"\d+", str(v_str or ""))
    return tuple(int(x) for x in parts) if parts else (0,)


def is_newer_version(remote_ver: str, local_ver: str) -> bool:
    """Returns True if remote_ver is strictly newer than local_ver."""
    r = parse_version(remote_ver)
    l = parse_version(local_ver)
    max_len = max(len(r), len(l))
    r_pad = r + (0,) * (max_len - len(r))
    l_pad = l + (0,) * (max_len - len(l))
    return r_pad > l_pad


def get_installed_plugins_info() -> Dict[str, Dict[str, Any]]:
    """Returns mapping of plugin_id -> {'version': str, 'name': str, 'enabled': bool}."""
    result: Dict[str, Dict[str, Any]] = {}
    try:
        from com.exteragram.messenger.plugins import PluginsController

        controller = PluginsController.getInstance()
        if not controller:
            return result

        plugins_map = getattr(controller, "plugins", None)
        if not plugins_map:
            return result

        entries = []
        if hasattr(plugins_map, "entrySet"):
            it = plugins_map.entrySet().iterator()
            while it.hasNext():
                e = it.next()
                entries.append((str(e.getKey()), e.getValue()))
        elif isinstance(plugins_map, dict):
            entries = list(plugins_map.items())

        for pid, p_obj in entries:
            ver = ""
            name = pid
            enabled = True

            if hasattr(p_obj, "getVersion"):
                ver = str(p_obj.getVersion() or "")
            elif hasattr(p_obj, "version"):
                ver = str(p_obj.version or "")

            if hasattr(p_obj, "getName"):
                name = str(p_obj.getName() or pid)
            elif hasattr(p_obj, "name"):
                name = str(p_obj.name or pid)

            if hasattr(p_obj, "isEnabled"):
                enabled = bool(p_obj.isEnabled())
            elif hasattr(p_obj, "enabled"):
                enabled = bool(p_obj.enabled)

            result[pid] = {
                "version": ver.strip(),
                "name": name.strip(),
                "enabled": enabled,
            }
    except Exception as exc:
        log(f"Failed to enumerate installed plugins: {exc}")
    return result


def fetch_repo_plugins(repo: str, branch: str) -> List[Dict[str, Any]]:
    """
    Fetches plugin manifest from extera-plugins.json in the repository.
    Falls back to querying individual plugin headers if extera-plugins.json is unavailable.
    """
    # 1. Fetch extera-plugins.json
    index_url = f"https://raw.githubusercontent.com/{repo}/{branch}/extera-plugins.json"
    try:
        req = urllib.request.Request(
            index_url,
            headers={"User-Agent": f"exteraGram-PluginUpdater/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and "plugins" in data:
                    return data["plugins"]
    except Exception as e:
        log(f"extera-plugins.json not available or failed to load: {e}")

    # 2. Fallback: inspect known repository plugins
    plugins_meta = []
    for pid in FALLBACK_REPO_PLUGINS:
        file_path = f"{pid}/{pid}.plugin"
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": f"exteraGram-PluginUpdater/{__version__}",
                    "Range": "bytes=0-3072",
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                m_ver = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
                m_name = re.search(r'__name__\s*=\s*["\']([^"\']+)["\']', text)
                if m_ver:
                    plugins_meta.append({
                        "id": pid,
                        "name": m_name.group(1) if m_name else pid,
                        "version": m_ver.group(1),
                        "file": file_path,
                    })
        except Exception:
            pass

    return plugins_meta


def get_cache_directory() -> str:
    """Returns a writable cache directory path."""
    try:
        if ApplicationLoader and ApplicationLoader.applicationContext:
            return str(ApplicationLoader.applicationContext.getCacheDir().getAbsolutePath())
    except Exception:
        pass
    import tempfile
    return tempfile.gettempdir()


def download_plugin_file(url: str, dest_path: str) -> bool:
    """Downloads plugin binary content to dest_path."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"exteraGram-PluginUpdater/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            if not content or len(content) < 50:
                return False
            # Quick integrity check: ensure it looks like a valid python plugin
            head = content[:2048].decode("utf-8", errors="ignore")
            if "__id__" not in head:
                log("Downloaded file does not contain __id__ metadata.")
                return False
            with open(dest_path, "wb") as f:
                f.write(content)
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0
    except Exception as exc:
        log(f"Download failed for {url}: {exc}")
        return False


def execute_plugin_install(temp_path: str, on_finish) -> None:
    """Loads and hot-reloads the plugin using PluginsController."""
    cb = PluginCallback(on_finish) if PluginCallback else None

    def _do_install():
        try:
            from com.exteragram.messenger.plugins import PluginsController, PluginsConstants

            pc = PluginsController.getInstance()
            if not pc:
                if on_finish:
                    on_finish("PluginsController instance is null")
                return

            # Direct method: PluginsController.getInstance().loadPluginFromFile(path, callback)
            if hasattr(pc, "loadPluginFromFile"):
                try:
                    pc.loadPluginFromFile(str(temp_path), cb)
                    return
                except Exception:
                    pass

            # Engine method: Engines.get("python").loadPluginFromFile(path, null, callback)
            engines = getattr(pc, "engines", None)
            if engines:
                py_key = getattr(PluginsConstants, "PYTHON", "python") if PluginsConstants else "python"
                py_engine = engines.get(py_key)
                if py_engine and hasattr(py_engine, "loadPluginFromFile"):
                    py_engine.loadPluginFromFile(str(temp_path), None, cb)
                    return

            if on_finish:
                on_finish("Could not invoke loadPluginFromFile on engine")
        except Exception as exc:
            if on_finish:
                on_finish(str(exc))

    plugins_queue = getattr(Utilities, "pluginsQueue", None)
    runnable_cls = None
    try:
        if jclass is not None:
            runnable_cls = jclass("java.lang.Runnable")
    except Exception:
        pass

    if plugins_queue and hasattr(plugins_queue, "postRunnable") and runnable_cls and dynamic_proxy:
        class _InstallRunnable(dynamic_proxy(runnable_cls)):
            def run(self):
                _do_install()

        plugins_queue.postRunnable(_InstallRunnable())
    else:
        run_on_ui_thread(_do_install)


def ensure_plugin_enabled(plugin_id: str) -> None:
    """Ensures that the updated plugin remains enabled."""
    try:
        from com.exteragram.messenger.plugins import PluginsController

        pc = PluginsController.getInstance()
        if pc and hasattr(pc, "setPluginEnabled"):
            cb = PluginCallback(lambda _: None) if PluginCallback else None
            pc.setPluginEnabled(str(plugin_id), True, cb)
    except Exception as exc:
        log(f"Failed to re-enable {plugin_id}: {exc}")


class PluginUpdaterPlugin(BasePlugin):
    """Plugin implementation for automated background updates of repository plugins."""

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._is_checking = False

        # Cached settings
        self._cfg_interval_idx = DEFAULT_INTERVAL_IDX
        self._cfg_notifications = True
        self._cfg_repo = DEFAULT_REPO
        self._cfg_branch = DEFAULT_BRANCH
        self._last_status = "Not checked yet"

    def on_plugin_load(self):
        self._load_settings()
        self._stop_event.clear()
        self._start_worker()

    def on_plugin_unload(self):
        self._stop_event.set()
        self._worker_thread = None

    def _load_settings(self):
        self._cfg_interval_idx = int(self.get_setting(KEY_INTERVAL_IDX, DEFAULT_INTERVAL_IDX))
        if self._cfg_interval_idx < 0 or self._cfg_interval_idx >= len(INTERVAL_CHOICES):
            self._cfg_interval_idx = DEFAULT_INTERVAL_IDX

        self._cfg_notifications = bool(self.get_setting(KEY_NOTIFICATIONS, True))
        self._cfg_repo = str(self.get_setting(KEY_REPO, DEFAULT_REPO) or DEFAULT_REPO).strip()
        self._cfg_branch = str(self.get_setting(KEY_BRANCH, DEFAULT_BRANCH) or DEFAULT_BRANCH).strip()
        self._last_status = str(self.get_setting(KEY_LAST_STATUS, "Not checked yet") or "Not checked yet")

    def _get_interval_seconds(self) -> int:
        idx = self._cfg_interval_idx
        if 0 <= idx < len(INTERVAL_CHOICES):
            return INTERVAL_CHOICES[idx][1]
        return INTERVAL_CHOICES[DEFAULT_INTERVAL_IDX][1]

    def _start_worker(self):
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self._worker_thread = threading.Thread(target=self._worker_loop, name="PluginUpdaterWorker", daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        # Initial sleep on startup to let exteraGram finish initializing
        if self._stop_event.wait(15.0):
            return

        while not self._stop_event.is_set():
            try:
                last_ts = float(self.get_setting(KEY_LAST_CHECK_TS, 0) or 0)
            except Exception:
                last_ts = 0

            interval = self._get_interval_seconds()
            now = time.time()

            if now - last_ts >= interval:
                self.check_and_update(manual=False)

            # Wait for next cycle or cancellation
            if self._stop_event.wait(float(interval)):
                break

    def check_and_update(self, manual: bool = False) -> None:
        """Runs the update check against the repository and applies any found updates."""
        if self._is_checking:
            if manual:
                BulletinHelper.show_info("Update check is already in progress.")
            return

        def _task():
            self._is_checking = True
            try:
                if manual:
                    BulletinHelper.show_info("Checking for plugin updates...")

                self._load_settings()
                installed = get_installed_plugins_info()
                if not installed:
                    msg = "No plugins detected in PluginsController."
                    self._update_status(msg)
                    if manual:
                        BulletinHelper.show_info(msg)
                    return

                remote_plugins = fetch_repo_plugins(self._cfg_repo, self._cfg_branch)
                if not remote_plugins:
                    msg = "Could not fetch repository plugin list."
                    self._update_status(msg)
                    if manual:
                        BulletinHelper.show_error(msg)
                    return

                to_update: List[Tuple[str, Dict[str, Any], str, str]] = []
                for r_plug in remote_plugins:
                    pid = r_plug.get("id")
                    if not pid or pid not in installed:
                        continue
                    local_ver = installed[pid]["version"]
                    remote_ver = str(r_plug.get("version", "")).strip()
                    if is_newer_version(remote_ver, local_ver):
                        to_update.append((pid, r_plug, local_ver, remote_ver))

                now_ts = time.time()
                self.set_setting(KEY_LAST_CHECK_TS, now_ts)

                if not to_update:
                    status_text = "All plugins are up to date."
                    self._update_status(status_text)
                    if manual:
                        BulletinHelper.show_info(status_text)
                    return

                # If plugin_updater itself is in the list, update it last
                to_update.sort(key=lambda item: 1 if item[0] == __id__ else 0)

                cache_dir = get_cache_directory()
                updated_names: List[str] = []

                for pid, r_plug, local_ver, remote_ver in to_update:
                    rel_file = r_plug.get("file", f"{pid}/{pid}.plugin")
                    if rel_file.startswith("http://") or rel_file.startswith("https://"):
                        dl_url = rel_file
                    else:
                        dl_url = f"https://raw.githubusercontent.com/{self._cfg_repo}/{self._cfg_branch}/{rel_file}"

                    temp_file = os.path.join(cache_dir, f"{pid}_update.plugin")
                    log(f"Downloading update for {pid}: {local_ver} -> {remote_ver} from {dl_url}")

                    download_ok = download_plugin_file(dl_url, temp_file)
                    if not download_ok:
                        log(f"Failed to download update file for {pid}")
                        continue

                    # Install via PluginsController
                    done_event = threading.Event()
                    error_box = [None]

                    def on_finish(err):
                        error_box[0] = err
                        done_event.set()

                    execute_plugin_install(temp_file, on_finish)

                    # Wait for installation callback
                    if not done_event.wait(timeout=15.0):
                        log(f"Installation timed out for {pid}")
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except Exception:
                            pass
                        continue

                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception:
                        pass

                    if error_box[0]:
                        log(f"Failed to install {pid}: {error_box[0]}")
                        continue

                    # Success: ensure enabled if previously enabled
                    if installed[pid].get("enabled", True):
                        ensure_plugin_enabled(pid)

                    display_name = r_plug.get("name", installed[pid].get("name", pid))
                    updated_names.append(f"{display_name} (v{remote_ver})")
                    log(f"Successfully updated {pid} to v{remote_ver}")

                if updated_names:
                    msg = f"Updated: {', '.join(updated_names)}"
                    self._update_status(msg)
                    if manual or self._cfg_notifications:
                        BulletinHelper.show_success(msg)
                else:
                    msg = "Update check finished (could not apply updates)."
                    self._update_status(msg)
                    if manual:
                        BulletinHelper.show_error("Could not install updates.")

            except Exception as e:
                log(f"Error during check_and_update: {e}")
                err_text = f"Check failed: {e}"
                self._update_status(err_text)
                if manual:
                    BulletinHelper.show_error(err_text)
            finally:
                self._is_checking = False

        threading.Thread(target=_task, name="PluginUpdaterTask", daemon=True).start()

    def _update_status(self, text: str):
        self._last_status = text
        self.set_setting(KEY_LAST_STATUS, text)

    def _format_last_check(self) -> str:
        try:
            ts = float(self.get_setting(KEY_LAST_CHECK_TS, 0) or 0)
            if ts <= 0:
                return "Never"
            diff = int(time.time() - ts)
            if diff < 60:
                return f"{diff}s ago ({self._last_status})"
            if diff < 3600:
                return f"{diff // 60}m ago ({self._last_status})"
            return f"{diff // 3600}h ago ({self._last_status})"
        except Exception:
            return self._last_status

    # ---------- Settings Interface ----------

    def create_settings(self) -> List[Any]:
        self._load_settings()

        def on_interval_change(new_idx: int):
            self._cfg_interval_idx = new_idx
            self.set_setting(KEY_INTERVAL_IDX, new_idx)

        def on_notifications_change(enabled: bool):
            self._cfg_notifications = enabled
            self.set_setting(KEY_NOTIFICATIONS, enabled)

        def on_manual_click(*args):
            self.check_and_update(manual=True)

        rows: List[Any] = []
        rows.append(Header("Plugin Updater"))
        rows.append(
            Divider(
                text="Automatically checks for newer versions of your installed plugins "
                     "from the repository and updates them in the background without manual confirmation."
            )
        )

        rows.append(Header("Schedule & Behavior"))
        rows.append(
            Selector(
                key=KEY_INTERVAL_IDX,
                text="Check Interval",
                default=DEFAULT_INTERVAL_IDX,
                items=INTERVAL_LABELS,
                icon="msg_schedule",
                on_change=on_interval_change,
            )
        )
        rows.append(
            Switch(
                key=KEY_NOTIFICATIONS,
                text="Update Notifications",
                default=True,
                subtext="Display a popup notification when a plugin is successfully updated",
                icon="msg_notifications",
                on_change=on_notifications_change,
            )
        )

        rows.append(Header("Manual Actions & Status"))
        rows.append(
            Text(
                text="Check for Updates Now",
                subtext=f"Last checked: {self._format_last_check()}",
                icon="msg_retry",
                on_click=on_manual_click,
            )
        )
        rows.append(
            Divider(
                text=f"Connected repository:\nhttps://github.com/{self._cfg_repo} (branch: {self._cfg_branch})"
            )
        )

        return rows
