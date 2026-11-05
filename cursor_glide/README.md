# Cursor Glide

Smooth cursor and caret animation plugin for [exteraGram](https://github.com/exteraSquad/exteraGram).

Replaces the default static text caret with a fluid, animated cursor featuring dynamic trail stretching, custom corner rounding, and full color personalization.

---

## Features

- **Smooth Interpolation**: Non-linear ease-out and trailing curve algorithms that give cursor jumps a satisfying, physical gliding sensation.
- **Dynamic Trail Smearing**: The cursor stretches and elongates along its trajectory when jumping between letters, words, or lines.
- **Custom Color Options**:
  - **Telegram Theme**: Matches the current theme caret color automatically.
  - **Chat Accent**: Adopts the current chat's send/accent tint.
  - **Preset Palettes**: Neon Cyan, Matrix Green, Cyberpunk Pink, Pure White, Amber Gold, Sunset Orange.
  - **Dynamic Rainbow**: Continuous animated HSV color shift.
  - **Custom HEX**: Full support for `#RRGGBB`, `#AARRGGBB`, and `#RGB` hex codes.
- **Multiple Cursor Shapes**:
  - Thin line (1.5 dp)
  - Normal line (2.5 dp)
  - Bold line (4.0 dp)
  - Solid block (terminal-style block matching character width)
  - Underline
- **Visual Polish**:
  - Soft sinusoidal fading blink when idle.
  - Configurable corner smoothing (from sharp edges up to full capsule).
  - Linear gradient fading along the smear trail.
- **Performance Optimized**:
  - Zero allocation in draw loops — reuses static native Android `Paint`, `Path`, and `RectF` buffers.
  - Native 60Hz and 120Hz high-refresh-rate support without frame drops or battery drain.
- **Live Settings Preview**: Embedded auto-typing demo in plugin settings reflecting changes in real time.

---

## Settings

| Setting | Options / Range | Description |
|---|---|---|
| **Enable animation** | Toggle | Master switch to enable or disable the glide animation. |
| **Duration** | Fast (100ms), Balanced (150ms), Smooth (200ms), Slow (280ms) | Interpolation transit time between cursor positions. |
| **Trail smear** | Off (0.0), Subtle (0.5), Pronounced (0.85), Maximum (1.0) | Amount of elongation applied to the cursor body during motion. |
| **Corner radius** | Sharp (0dp), Slight (1.5dp), Medium (3.0dp), Rounded (5.0dp), Capsule | Rounding applied to cursor corners and trail path. |
| **Cursor shape** | Thin, Normal, Bold, Solid block, Underline | Visual geometry of the cursor caret. |
| **Cursor color** | Theme, Accent, Neon palettes, Rainbow, Custom HEX | Color palette or custom color mode. |
| **Custom HEX code** | Text input (`#RRGGBB`) | Specify any custom hex color code when "Custom HEX" is selected. |
| **Soft pulsing blink** | Toggle | Replaces hard on/off blinking with smooth sinusoidal alpha transitions. |
| **Trail gradient fade** | Toggle | Fades the tail end of the smear trail into transparency. |

---

## Installation

1. Download [`cursor_glide.plugin`](cursor_glide.plugin).
2. Open the file in **exteraGram** or send it to your Saved Messages and tap on it.
3. Tap **Install Plugin**.
4. Navigate to **Settings** > **Plugins** and enable **Cursor Glide**.

---

## Compatibility

- **Client**: exteraGram, AyuGram Android, or any Telegram fork supporting the Python Plugins Engine.
- **Architecture**: Universal (supports all ABIs supported by the host client).
