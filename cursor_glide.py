# -*- coding: utf-8 -*-
"""
Cursor Glide (NeoVide) for exteraGram
Port of Ghostty cursor_glide.glsl shader with stretch trail and smooth interpolation.
"""

import colorsys
import math
import time
import types
import weakref
from typing import Any, Dict, List, Optional, Tuple

from android.graphics import (
    Canvas,
    Color,
    CornerPathEffect,
    LinearGradient,
    Paint,
    Path,
    RectF,
    Shader,
)
from android.util import TypedValue
from android.view import Gravity, View, ViewGroup
from android.widget import LinearLayout
from java import dynamic_proxy, jboolean, jclass
from org.telegram.messenger import AndroidUtilities, LocaleController
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import EditTextBoldCursor, EditTextCaption

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, MethodHook
from hook_utils import find_class
from ui.settings import Custom, Header, Selector, SimpleSettingFactory, Switch

__id__ = "cursor_glide"
__name__ = "Cursor Glide (NeoVide)"
__description__ = "Плавная скользящая анимация курсора с растяжением шлейфа (порт шейдера Ghostty / NeoVide)"
__author__ = "@koresent"
__version__ = "1.0.1"
__icon__ = "exteraPlugins/1"
__category__ = "appearance"

PREVIEW_TAG = "cursor_glide_preview"
PREVIEW_START_MS = 250
PREVIEW_HEIGHT_DP = 64

# Presets from cursor_glide.glsl
DURATIONS = (0.10, 0.15, 0.20, 0.28)  # seconds (default 0.15s like in Ghostty)
SMEARS = (0.0, 0.50, 0.85, 1.0)       # trail smear factor (default 0.85 like in Ghostty)
RADII = (0.0, 1.5, 3.0, 5.0, 12.0)    # corner radius in dp (default 3.0dp like in Ghostty)

DEFAULTS = {
    "enabled": True,
    "speed": 1,           # 0.15s (Ghostty default)
    "smear": 2,           # 0.85 (Ghostty default)
    "corner_radius": 2,   # 3.0 dp (Ghostty default)
    "cursor_shape": 1,    # Normal line
    "cursor_color": 0,    # Theme cursor
    "soft_blink": True,
    "smear_fade": True,
}


def russian() -> bool:
    try:
        return str(LocaleController.getInstance().getCurrentLocale().getLanguage()).startswith("ru")
    except Exception:
        return True


def bare(func, scope=None):
    return types.FunctionType(
        func.__code__,
        scope or {},
        func.__name__,
        func.__defaults__,
        func.__closure__,
    )


def weak(method):
    ref = weakref.WeakMethod(method)

    def call(*args):
        bound = ref()
        if bound is not None:
            bound(*args)

    return bare(call)


def ease_leading(x: float) -> float:
    """Quartic ease out from cursor_glide.glsl: 1.0 - pow(1.0 - x, 4.0)"""
    inv = 1.0 - x
    return 1.0 - inv * inv * inv * inv


def ease_trailing(x: float) -> float:
    """Ease trailing from cursor_glide.glsl: pow(x, 2.2)"""
    return x ** 2.2 if x > 0.0 else 0.0


class CursorState:
    __slots__ = (
        "p0_x", "p0_y", "w0", "h0",
        "p1_x", "p1_y", "w1", "h1",
        "start_time", "last_offset", "last_active",
    )

    def __init__(
        self,
        p0_x: float, p0_y: float, w0: float, h0: float,
        p1_x: float, p1_y: float, w1: float, h1: float,
        start_time: float, last_offset: int, last_active: float,
    ):
        self.p0_x = p0_x
        self.p0_y = p0_y
        self.w0 = w0
        self.h0 = h0
        self.p1_x = p1_x
        self.p1_y = p1_y
        self.w1 = w1
        self.h1 = h1
        self.start_time = start_time
        self.last_offset = last_offset
        self.last_active = last_active


class DrawHook(MethodHook):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

    def before_hooked_method(self, param):
        try:
            if self.plugin.is_active and self.plugin.plugin_enabled:
                view = param.thisObject
                self.plugin.suppress_stock_cursor(view)
        except Exception as e:
            self.plugin.log(f"before_on_draw error: {e}")

    def after_hooked_method(self, param):
        try:
            if self.plugin.is_active and self.plugin.plugin_enabled:
                view = param.thisObject
                canvas = param.args[0]
                self.plugin.render_cursor(view, canvas)
        except Exception as e:
            self.plugin.log(f"after_on_draw error: {e}")


class CursorAllowHook(MethodHook):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

    def before_hooked_method(self, param):
        try:
            if self.plugin.is_active and self.plugin.plugin_enabled:
                param.args[0] = False
        except Exception as e:
            self.plugin.log(f"before_set_allow error: {e}")


class Watch(dynamic_proxy(View.OnAttachStateChangeListener)):
    def __init__(self, start):
        super().__init__()
        self.start = start
        self.token = 0

    def onViewAttachedToWindow(self, view):
        self.token += 1
        self.start(view, self.token)

    def onViewDetachedFromWindow(self, view):
        self.token += 1


class CursorGlidePlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.is_active = False
        self.generation = 0
        self.changed = weak(self.sync)
        self.factory = None

        # Cached settings
        self.plugin_enabled: bool = True
        self.duration: float = 0.15
        self.trail_smear: float = 0.85
        self.corner_radius_dp: float = 3.0
        self.cursor_shape: int = 1
        self.cursor_color_mode: int = 0
        self.blink_enabled: bool = True
        self.smear_fade_enabled: bool = True

        # Per-view state tracking (weak keys to prevent any memory leak)
        self._states = weakref.WeakKeyDictionary()

        # Reusable Android graphics objects to eliminate GC allocations during 60/120fps draw calls
        self._paint = Paint(Paint.ANTI_ALIAS_FLAG)
        self._paint.setStyle(Paint.Style.FILL)
        self._rect = RectF()
        self._path = Path()

        # Reflection handles
        self._field_allow_draw_cursor = None
        self._hook_objects = []

    def on_plugin_load(self):
        self.sync()
        self.is_active = True
        self._install_hooks()
        self.log("CursorGlide loaded successfully")

    def on_plugin_unload(self):
        self.generation += 1
        self.is_active = False

        # Release settings preview factory
        factory, self.factory = self.factory, None
        if factory is not None:
            try:
                factory.release()
            except Exception as error:
                self.log(f"Factory release error: {error}")

        # Restore default cursor on active views
        for view in list(self._states.keys()):
            try:
                if self._field_allow_draw_cursor is not None:
                    self._field_allow_draw_cursor.setBoolean(view, True)
                if hasattr(view, "setAllowDrawCursor"):
                    view.setAllowDrawCursor(True)
                view.invalidate()
            except Exception:
                pass

        self._states.clear()
        self.log("CursorGlide unloaded")

    def _install_hooks(self):
        canvas_cls = find_class("android.graphics.Canvas")
        draw_hook = DrawHook(self)
        cursor_hook = CursorAllowHook(self)

        classes_to_hook = [
            "org.telegram.ui.Components.EditTextBoldCursor",
            "org.telegram.ui.Components.EditTextCaption",
            "org.telegram.ui.Components.EditTextEffects",
        ]

        hooked_count = 0
        for class_name in classes_to_hook:
            try:
                target_cls = find_class(class_name)
                if target_cls is None:
                    continue

                # 1. Hook onDraw(Canvas)
                try:
                    on_draw = target_cls.getDeclaredMethod("onDraw", canvas_cls)
                    on_draw.setAccessible(True)
                    unhook = self.hook_method(on_draw, draw_hook)
                    if unhook:
                        self._hook_objects.append(unhook)
                        hooked_count += 1
                        self.log(f"Hooked onDraw on {class_name}")
                except Exception as e:
                    self.log(f"No onDraw on {class_name}: {e}")

                # 2. Hook setAllowDrawCursor(boolean)
                try:
                    set_allow = target_cls.getDeclaredMethod("setAllowDrawCursor", jboolean)
                    set_allow.setAccessible(True)
                    unhook = self.hook_method(set_allow, cursor_hook)
                    if unhook:
                        self._hook_objects.append(unhook)
                        self.log(f"Hooked setAllowDrawCursor on {class_name}")
                except Exception as e:
                    pass

                # Find allowDrawCursor field if not yet found
                if self._field_allow_draw_cursor is None:
                    try:
                        field = target_cls.getDeclaredField("allowDrawCursor")
                        field.setAccessible(True)
                        self._field_allow_draw_cursor = field
                        self.log(f"Found allowDrawCursor field on {class_name}")
                    except Exception:
                        pass

            except Exception as e:
                self.log(f"Error inspecting {class_name}: {e}")

        self.log(f"Total onDraw hooks installed: {hooked_count}")

    def suppress_stock_cursor(self, view):
        if self._field_allow_draw_cursor is not None:
            try:
                self._field_allow_draw_cursor.setBoolean(view, False)
            except Exception:
                pass
        try:
            if hasattr(view, "setAllowDrawCursor"):
                view.setAllowDrawCursor(False)
        except Exception:
            pass

    def option(self, key: str):
        return self.get_setting(key, DEFAULTS[key])

    def index(self, key: str, size: int) -> int:
        try:
            value = int(self.option(key))
        except (TypeError, ValueError):
            value = DEFAULTS[key]
        return max(0, min(size - 1, value))

    def sync(self, *_):
        self.plugin_enabled = bool(self.option("enabled"))
        self.duration = DURATIONS[self.index("speed", len(DURATIONS))]
        self.trail_smear = SMEARS[self.index("smear", len(SMEARS))]
        self.corner_radius_dp = RADII[self.index("corner_radius", len(RADII))]
        self.cursor_shape = self.index("cursor_shape", 5)
        self.cursor_color_mode = self.index("cursor_color", 5)
        self.blink_enabled = bool(self.option("soft_blink"))
        self.smear_fade_enabled = bool(self.option("smear_fade"))

        for view in list(self._states.keys()):
            try:
                view.invalidate()
            except Exception:
                pass

    def get_cursor_color(self, view: View) -> int:
        mode = self.cursor_color_mode
        if mode == 1:  # Accent
            try:
                provider = getattr(view, "resourcesProvider", None)
                return Theme.getColor(Theme.key_chat_messagePanelSend, provider) if provider else Theme.getColor(Theme.key_chat_messagePanelSend)
            except Exception:
                return 0xFF2AABEE
        elif mode == 2:  # Neon Cyan (classic terminal / NeoVide vibe)
            return 0xFF00E5FF
        elif mode == 3:  # Pure White
            return 0xFFFFFFFF
        elif mode == 4:  # Rainbow
            hue = (time.perf_counter() * 100.0) % 360.0
            r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 0.85, 1.0)
            return (0xFF << 24) | (int(r * 255) << 16) | (int(g * 255) << 8) | int(b * 255)
        else:  # Theme
            try:
                provider = getattr(view, "resourcesProvider", None)
                color = Theme.getColor(Theme.key_chat_messagePanelCursor, provider) if provider else Theme.getColor(Theme.key_chat_messagePanelCursor)
                if color != 0:
                    return color
            except Exception:
                pass
            try:
                return view.getCurrentTextColor()
            except Exception:
                return 0xFF2AABEE

    def render_cursor(self, view, canvas: Canvas):
        if not view.isShown():
            return

        is_preview = False
        try:
            tag = view.getTag()
            if tag is not None and str(tag) == PREVIEW_TAG:
                is_preview = True
        except Exception:
            pass

        # In normal dialogs, cursor is drawn only when focused and cursor is visible
        if not is_preview:
            if not view.isFocused():
                return
            try:
                if not view.isCursorVisible():
                    return
            except Exception:
                pass

        sel_start = view.getSelectionStart()
        sel_end = view.getSelectionEnd()
        if sel_start != sel_end or sel_start < 0:
            return

        layout = view.getLayout()
        if layout is None:
            return

        text = layout.getText()
        text_len = text.length() if text is not None else 0
        if sel_start > text_len:
            return

        # Coordinate computation in view space
        line = layout.getLineForOffset(sel_start)
        primary_x = float(layout.getPrimaryHorizontal(sel_start))

        compound_left = float(view.getCompoundPaddingLeft())
        scroll_x = float(view.getScrollX())
        cx = primary_x + compound_left - scroll_x

        baseline = float(layout.getLineBaseline(line))
        padding_top = float(view.getTotalPaddingTop())
        scroll_y = float(view.getScrollY())
        line_baseline = baseline + padding_top - scroll_y

        paint = view.getPaint()
        fm = paint.getFontMetrics()
        ascent = float(fm.ascent)
        descent = float(fm.descent)

        cy_top = line_baseline + ascent
        cy_bottom = line_baseline + descent
        line_h = max(1.0, cy_bottom - cy_top)
        cy = (cy_top + cy_bottom) * 0.5

        dp = AndroidUtilities.dp

        # Determine dimensions and target center based on selected shape
        shape = self.cursor_shape
        if shape == 0:  # Thin Line
            w = float(dp(1.5))
            h = line_h
            target_cx = cx
            target_cy = cy
        elif shape == 1:  # Normal Line
            w = float(dp(2.5))
            h = line_h
            target_cx = cx
            target_cy = cy
        elif shape == 2:  # Bold Line
            w = float(dp(4.0))
            h = line_h
            target_cx = cx
            target_cy = cy
        elif shape == 3:  # Block (Terminal / NeoVide)
            char_w = 0.0
            if sel_start < text_len:
                next_x = float(layout.getPrimaryHorizontal(sel_start + 1))
                char_w = abs(next_x - primary_x)
            if char_w < 1.0:
                char_w = float(paint.measureText(" "))
            char_w = max(float(dp(8)), min(float(dp(32)), char_w))
            w = char_w
            h = line_h
            target_cx = cx + char_w * 0.5
            target_cy = cy
        elif shape == 4:  # Underline
            char_w = 0.0
            if sel_start < text_len:
                next_x = float(layout.getPrimaryHorizontal(sel_start + 1))
                char_w = abs(next_x - primary_x)
            if char_w < 1.0:
                char_w = float(paint.measureText(" "))
            char_w = max(float(dp(8)), min(float(dp(32)), char_w))
            w = char_w
            h = float(dp(2.5))
            target_cx = cx + char_w * 0.5
            target_cy = cy_bottom - h * 0.5
        else:
            w = float(dp(2.5))
            h = line_h
            target_cx = cx
            target_cy = cy

        now = time.perf_counter()
        state = self._states.get(view)

        if state is None:
            state = CursorState(
                p0_x=target_cx,
                p0_y=target_cy,
                w0=w,
                h0=h,
                p1_x=target_cx,
                p1_y=target_cy,
                w1=w,
                h1=h,
                start_time=now,
                last_offset=sel_start,
                last_active=now,
            )
            self._states[view] = state

        # Detect cursor movement or selection offset shift
        moved = (
            abs(target_cx - state.p1_x) > 0.5
            or abs(target_cy - state.p1_y) > 0.5
            or sel_start != state.last_offset
        )

        if moved:
            # If in flight, smoothly capture current interpolated head position as new p0
            t_prev = (now - state.start_time) / self.duration if self.duration > 0 else 1.0
            t_prev = min(1.0, max(0.0, t_prev))
            if t_prev < 1.0:
                t_lead_prev = ease_leading(t_prev)
                curr_cx = state.p0_x + (state.p1_x - state.p0_x) * t_lead_prev
                curr_cy = state.p0_y + (state.p1_y - state.p0_y) * t_lead_prev
                curr_w = state.w0 + (state.w1 - state.w0) * t_lead_prev
                curr_h = state.h0 + (state.h1 - state.h0) * t_lead_prev
            else:
                curr_cx = state.p1_x
                curr_cy = state.p1_y
                curr_w = state.w1
                curr_h = state.h1

            state.p0_x = curr_cx
            state.p0_y = curr_cy
            state.w0 = curr_w
            state.h0 = curr_h
            state.p1_x = target_cx
            state.p1_y = target_cy
            state.w1 = w
            state.h1 = h
            state.start_time = now
            state.last_offset = sel_start
            state.last_active = now

        t = (now - state.start_time) / self.duration if self.duration > 0 else 1.0
        t = min(1.0, max(0.0, t))
        move_dist = math.hypot(state.p1_x - state.p0_x, state.p1_y - state.p0_y)

        # Base opacity (block cursor is slightly translucent so text underneath remains legible)
        base_alpha = int(255 * 0.75) if shape == 3 else 255

        # Blinking calculation when stationary
        if t >= 1.0 or move_dist < 1.0:
            idle_time = now - state.last_active
            if self.blink_enabled and idle_time > 0.5:
                # 1.0s blink cycle (500ms on, 500ms soft pulse)
                phase = (idle_time - 0.5) % 1.0
                pulse = 0.5 + 0.5 * math.cos(phase * 2.0 * math.pi)
                alpha = max(0, min(255, int(base_alpha * pulse)))
            else:
                alpha = base_alpha
        else:
            alpha = base_alpha

        if alpha <= 0:
            if self.blink_enabled and (now - state.last_active) < 15.0:
                view.postInvalidateOnAnimation()
            return

        color_int = self.get_cursor_color(view)
        self._paint.setColor(color_int)
        self._paint.setAlpha(alpha)

        corner_radius_px = float(dp(self.corner_radius_dp))

        if t >= 1.0 or move_dist < 1.0:
            # Stationary cursor at target p1
            half_w = state.w1 * 0.5
            half_h = state.h1 * 0.5
            r = min(corner_radius_px, min(half_w, half_h))
            self._rect.set(
                state.p1_x - half_w,
                state.p1_y - half_h,
                state.p1_x + half_w,
                state.p1_y + half_h,
            )
            self._paint.setShader(None)
            self._paint.setPathEffect(None)
            canvas.drawRoundRect(self._rect, r, r, self._paint)
        else:
            # In motion: compute leading and trailing interpolated positions
            t_lead = ease_leading(t)
            t_trail_raw = ease_trailing(t)
            t_trail = t_lead * (1.0 - self.trail_smear) + t_trail_raw * self.trail_smear

            lead_cx = state.p0_x + (state.p1_x - state.p0_x) * t_lead
            lead_cy = state.p0_y + (state.p1_y - state.p0_y) * t_lead
            trail_cx = state.p0_x + (state.p1_x - state.p0_x) * t_trail
            trail_cy = state.p0_y + (state.p1_y - state.p0_y) * t_trail

            lead_hw = (state.w0 + (state.w1 - state.w0) * t_lead) * 0.5
            lead_hh = (state.h0 + (state.h1 - state.h0) * t_lead) * 0.5
            trail_hw = (state.w0 + (state.w1 - state.w0) * t_trail) * 0.5
            trail_hh = (state.h0 + (state.h1 - state.h0) * t_trail) * 0.5

            r = min(corner_radius_px, min(lead_hw, lead_hh))

            # Optional trail smear gradient fade along the movement vector
            if self.smear_fade_enabled and move_dist > dp(4):
                tail_alpha = int(alpha * 0.70)
                tail_color = (tail_alpha << 24) | (color_int & 0x00FFFFFF)
                head_color = (alpha << 24) | (color_int & 0x00FFFFFF)
                shader = LinearGradient(
                    trail_cx, trail_cy, lead_cx, lead_cy,
                    tail_color, head_color, Shader.TileMode.CLAMP,
                )
                self._paint.setShader(shader)
            else:
                self._paint.setShader(None)

            # Check horizontal vs vertical vs 2D polygon movement
            if abs(lead_cy - trail_cy) < 1.0:
                # Same-line horizontal glide: stretch into a smooth dynamic capsule
                left = min(trail_cx - trail_hw, lead_cx - lead_hw)
                right = max(trail_cx + trail_hw, lead_cx + lead_hw)
                top = lead_cy - lead_hh
                bottom = lead_cy + lead_hh
                self._rect.set(left, top, right, bottom)
                self._paint.setPathEffect(None)
                canvas.drawRoundRect(self._rect, r, r, self._paint)
            elif abs(lead_cx - trail_cx) < 1.0:
                # Vertical line jump
                left = lead_cx - lead_hw
                right = lead_cx + lead_hw
                top = min(trail_cy - trail_hh, lead_cy - lead_hh)
                bottom = max(trail_cy + trail_hh, lead_cy + lead_hh)
                self._rect.set(left, top, right, bottom)
                self._paint.setPathEffect(None)
                canvas.drawRoundRect(self._rect, r, r, self._paint)
            else:
                # 2D diagonal / line-wrapping convex hull connecting trail and lead rectangles
                self._path.reset()
                dx = lead_cx - trail_cx
                dy = lead_cy - trail_cy
                if dx >= 0 and dy >= 0:
                    self._path.moveTo(trail_cx - trail_hw, trail_cy - trail_hh)
                    self._path.lineTo(lead_cx - lead_hw, lead_cy - lead_hh)
                    self._path.lineTo(lead_cx + lead_hw, lead_cy - lead_hh)
                    self._path.lineTo(lead_cx + lead_hw, lead_cy + lead_hh)
                    self._path.lineTo(trail_cx + trail_hw, trail_cy + trail_hh)
                    self._path.lineTo(trail_cx - trail_hw, trail_cy + trail_hh)
                elif dx >= 0 and dy < 0:
                    self._path.moveTo(trail_cx - trail_hw, trail_cy + trail_hh)
                    self._path.lineTo(lead_cx - lead_hw, lead_cy + lead_hh)
                    self._path.lineTo(lead_cx + lead_hw, lead_cy + lead_hh)
                    self._path.lineTo(lead_cx + lead_hw, lead_cy - lead_hh)
                    self._path.lineTo(trail_cx + trail_hw, trail_cy - trail_hh)
                    self._path.lineTo(trail_cx - trail_hw, trail_cy - trail_hh)
                elif dx < 0 and dy >= 0:
                    self._path.moveTo(trail_cx + trail_hw, trail_cy - trail_hh)
                    self._path.lineTo(lead_cx + lead_hw, lead_cy - lead_hh)
                    self._path.lineTo(lead_cx - lead_hw, lead_cy - lead_hh)
                    self._path.lineTo(lead_cx - lead_hw, lead_cy + lead_hh)
                    self._path.lineTo(trail_cx - trail_hw, trail_cy + trail_hh)
                    self._path.lineTo(trail_cx + trail_hw, trail_cy + trail_hh)
                else:
                    self._path.moveTo(trail_cx + trail_hw, trail_cy + trail_hh)
                    self._path.lineTo(lead_cx + lead_hw, lead_cy + lead_hh)
                    self._path.lineTo(lead_cx - lead_hw, lead_cy + lead_hh)
                    self._path.lineTo(lead_cx - lead_hw, lead_cy - lead_hh)
                    self._path.lineTo(trail_cx - trail_hw, trail_cy - trail_hh)
                    self._path.lineTo(trail_cx + trail_hw, trail_cy - trail_hh)
                self._path.close()

                if r > 0.5:
                    self._paint.setPathEffect(CornerPathEffect(r))
                else:
                    self._paint.setPathEffect(None)
                canvas.drawPath(self._path, self._paint)
                self._paint.setPathEffect(None)

            self._paint.setShader(None)

        # Invalidate for next animation frame
        if t < 1.0:
            view.postInvalidateOnAnimation()
        elif self.blink_enabled and (now - state.last_active) < 15.0:
            view.postInvalidateOnAnimation()

    def create_settings(self) -> List[Any]:
        ru = russian()

        def tr(ru_text: str, en_text: str) -> str:
            return ru_text if ru else en_text

        def switch(key: str, ru_text: str, en_text: str, icon: str):
            return Switch(
                key=key,
                text=tr(ru_text, en_text),
                default=DEFAULTS[key],
                icon=icon,
                on_change=self.changed,
            )

        def selector(key: str, ru_text: str, en_text: str, items, icon: str):
            return Selector(
                key=key,
                text=tr(ru_text, en_text),
                default=DEFAULTS[key],
                items=[tr(item_ru, item_en) for item_ru, item_en in items],
                icon=icon,
                on_change=self.changed,
            )

        return [
            Header(tr("предпросмотр", "preview")),
            self.preview(),
            Header(tr("основное", "general")),
            switch("enabled", "включить анимацию", "enable animation", "msg_edit"),
            Header(tr("анимация", "animation")),
            selector("speed", "длительность", "duration", (
                ("быстро (100 мс)", "fast (100 ms)"),
                ("как в Ghostty (150 мс)", "Ghostty default (150 ms)"),
                ("плавно (200 мс)", "smooth (200 ms)"),
                ("медленно (280 мс)", "slow (280 ms)"),
            ), "msg_speed"),
            selector("smear", "растяжение шлейфа", "trail smear", (
                ("без шлейфа (0.0)", "no smear (0.0)"),
                ("умеренное (0.5)", "subtle (0.5)"),
                ("как в Ghostty (0.85)", "Ghostty default (0.85)"),
                ("максимальное (1.0)", "maximum (1.0)"),
            ), "msg_blur_linear"),
            selector("corner_radius", "скругление углов", "corner radius", (
                ("без скругления (0 dp)", "sharp (0 dp)"),
                ("легкое (1.5 dp)", "slight (1.5 dp)"),
                ("как в Ghostty (3.0 dp)", "Ghostty default (3.0 dp)"),
                ("закругленное (5.0 dp)", "rounded (5.0 dp)"),
                ("капсула", "capsule"),
            ), "msg_photo_curve"),
            Header(tr("курсор", "cursor")),
            selector("cursor_shape", "форма курсора", "cursor shape", (
                ("тонкая линия (1.5 dp)", "thin line (1.5 dp)"),
                ("обычная линия (2.5 dp)", "normal line (2.5 dp)"),
                ("жирная линия (4.0 dp)", "bold line (4.0 dp)"),
                ("блок (NeoVide / Терминал)", "block (NeoVide / Terminal)"),
                ("подчёркивание", "underline"),
            ), "msg_photoeditor"),
            selector("cursor_color", "цвет курсора", "cursor color", (
                ("из темы Telegram", "Telegram theme"),
                ("акцентный", "accent"),
                ("неоновый бирюзовый", "neon cyan"),
                ("белый", "white"),
                ("переливающийся (Rainbow)", "rainbow"),
            ), "msg_palette"),
            switch("soft_blink", "мягкое мигание", "soft pulsing blink", "msg_autodelete"),
            switch("smear_fade", "затухание шлейфа", "trail gradient fade", "msg_blur_radial"),
        ]

    def preview(self):
        if self.factory is None:
            ref = weakref.ref(self)

            def create_view(context, list_view, account, guid, provider):
                plugin = ref()
                return plugin.build(context, provider) if plugin is not None else View(context)

            def bind_view(view, item, divider, adapter, list_view):
                return None

            self.factory = SimpleSettingFactory(
                bare(create_view, {"View": View}),
                bare(bind_view),
                is_clickable=False,
                is_shadow=False,
            )
        return Custom(factory=self.factory.instance.java)

    def build(self, context, provider):
        dp = AndroidUtilities.dp
        ru = russian()

        def color(key):
            return Theme.getColor(key, provider) if provider is not None else Theme.getColor(key)

        match = ViewGroup.LayoutParams.MATCH_PARENT
        root = LinearLayout(context)
        root.setOrientation(LinearLayout.VERTICAL)
        root.setPadding(dp(21), dp(4), dp(21), dp(4))
        root.setBackgroundColor(color(Theme.key_windowBackgroundWhite))
        root.setLayoutParams(ViewGroup.LayoutParams(match, ViewGroup.LayoutParams.WRAP_CONTENT))

        edit = EditTextCaption(context, provider)
        edit.setTag(PREVIEW_TAG)
        edit.setFocusable(False)
        edit.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO)
        edit.setSingleLine(False)
        edit.setMaxLines(2)
        edit.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 18)
        edit.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL)
        edit.setPadding(0, 0, 0, 0)
        edit.setBackground(None)
        edit.setTextColor(color(Theme.key_chat_messagePanelText))
        edit.setHintTextColor(color(Theme.key_chat_messagePanelHint))
        edit.setHintText("Сообщение" if ru else "Message")
        edit.setCursorColor(color(Theme.key_chat_messagePanelCursor))
        edit.setCursorWidth(2.5)
        edit.setCursorSize(dp(24))
        root.addView(edit, LinearLayout.LayoutParams(match, dp(PREVIEW_HEIGHT_DP)))

        self.play(edit, self.frames(ru))
        return root

    def play(self, edit, frames):
        ref = weakref.ref(self)
        generation = self.generation

        def tick(view, token: int, index: int):
            plugin = ref()
            if plugin is None or token != watch.token or generation != plugin.generation:
                return
            text, delay, *marks = frames[index]
            start, end = marks or (len(text), len(text))
            try:
                view.setText(text)
                view.setSelection(start, end)
            except Exception as error:
                plugin.log(f"preview stopped: {error}")
                return
            run_on_ui_thread(lambda: tick(view, token, (index + 1) % len(frames)), delay=delay)

        def start(view, token: int):
            run_on_ui_thread(lambda: tick(view, token, 0), delay=PREVIEW_START_MS)

        watch = Watch(start)
        edit.addOnAttachStateChangeListener(watch)
        if edit.isAttachedToWindow():
            watch.onViewAttachedToWindow(edit)

    @staticmethod
    def frames(ru: bool):
        first = "Печатаю с анимацией" if ru else "Smooth cursor glide"
        second = "Как в Ghostty и NeoVide!" if ru else "Like Ghostty & NeoVide!"
        cut = first.rfind(" ")
        head = first[:cut] + "\n"
        frames = [(first[:count], 140) for count in range(1, len(first) + 1)]
        frames.append((first, 800))
        frames.append((first, 1000, cut, len(first)))
        frames.append((first[:cut], 600))
        frames += [(head + second[:count], 130) for count in range(len(second) + 1)]
        frames.append((head + second, 1200))
        frames.append(("", 900))
        return frames
