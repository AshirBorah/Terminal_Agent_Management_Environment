# Linux Agent Manager (LAM) — Full Technical Specification

## 1. Project Overview

**Name:** Linux Agent Manager (LAM)
**Purpose:** An intelligent terminal multiplexer for managing multiple parallel AI agent sessions with smart monitoring and notifications. Think tmux, but aware that AI agents are running and that they sometimes need your attention.
**Language:** Python 3.11+
**UI Framework:** Textual (TUI)
**Platform:** Linux (uses PTY, `notify-send`, POSIX signals)

### 1.1 Core Concept

LAM does NOT launch or orchestrate agents. Users create terminal sessions, get a shell, and run whatever CLI agent they want (`claude`, `codex`, `aider`, `gemini`, a custom script, etc.). LAM monitors the PTY output of each session using configurable regex patterns and:

- Detects when an agent is **waiting for input** (y/n prompts, approval requests, questions)
- Detects when an agent has **errored** (exit codes, error patterns)
- Detects when a **task completes** (completion patterns, process exit with code 0)
- Detects when a session has gone **idle** (no output for a configurable duration)
- **Notifies the user** via visual highlights, desktop notifications, audio alerts, and in-app toasts

This is the key differentiator from tmux: LAM understands that the processes in its panes are AI agents that periodically need human attention, and it helps you manage that attention across many concurrent sessions.

### 1.2 Design Principles

1. **Tmux mental model** — sessions are shells, not managed processes
2. **Zero-config useful** — works out of the box with sensible defaults; patterns match common agents
3. **Non-invasive monitoring** — pattern matching on PTY output; never modifies or intercepts agent I/O
4. **Fast switching** — Alt+1..9 to jump to any session; sidebar for overview
5. **Notification-first** — the primary value is knowing when to context-switch between sessions

---

## 2. Core Features

### 2.1 Session Management

A **session** in LAM is a PTY-backed shell. When you create a session, you get an interactive shell where you can type commands, run agents, or do anything you'd do in a terminal.

**Session List (Left Sidebar)**
- Clickable session entries with selection highlight
- Visual status indicators per session:
  - `●` ACTIVE — process is running and producing output
  - `○` IDLE — no output for `idle_threshold_seconds`
  - `◉` WAITING — agent detected as waiting for user input (flashes/pulses)
  - `✗` ERROR — process exited with non-zero code or error pattern matched
  - `✓` DONE — process exited with code 0 or completion pattern matched
  - `⏸` PAUSED — process suspended via SIGSTOP
- Session name (user-editable)
- Working directory path (truncated to fit)
- Last activity timestamp (relative: "2m ago", "1h ago")
- Status badge text (e.g., "[y/n]" when waiting for confirmation)

**Session Operations**
- **Create** — opens a new PTY session with user's default shell in a chosen directory
- **Rename** — inline F2 editing of session name
- **Delete** — with confirmation dialog; sends SIGTERM then SIGKILL to running process
- **Duplicate** — create a new session with the same working directory
- **Export logs** — save session output buffer to a text file

### 2.2 Main View (Right Panel)

**Terminal Output Display**
- Full PTY output rendering including ANSI colors and formatting
- Scrollable history (PageUp/PageDown/Home/End)
- Auto-scroll to bottom on new output (stops if user scrolls up)
- Output buffer capped at `max_buffer_lines` (default: 10,000 lines)

**Input Area**
- Text input widget at the bottom of the main view
- Typing in the input area writes to the session's PTY stdin
- Enter sends the line (with newline)
- Supports sending Ctrl+C (SIGINT via PTY) and Ctrl+D (EOF) to the child process
- Input history (Up/Down arrows cycle through previous inputs for this session)

### 2.3 Multi-Session Control

- **Pause All** — SIGSTOP all running session processes
- **Resume All** — SIGCONT all paused sessions
- **Stop All** — SIGTERM then SIGKILL all running sessions (with confirmation)
- **Restart Session** — kill and re-spawn the shell for a single session
- **Batch Select** — toggle multi-select mode to operate on several sessions at once

### 2.4 Pattern Matching (Output Monitoring)

LAM monitors each session's PTY output line-by-line using configurable regex patterns. Patterns are organized by detection category, tested in priority order:

**Priority order:** error → prompt → completion → progress

**Default patterns (work out of the box for common agents):**

```toml
[patterns.prompt]
# Patterns that indicate the agent is waiting for user input
regexes = [
    '\\[y/n\\]',                           # Common yes/no prompt
    '\\[Y/n\\]',
    '\\[yes/no\\]',
    '\\(a\\)pprove.*\\(d\\)eny',           # Claude Code approval
    'Do you want to (?:continue|proceed)',
    'Press [Ee]nter to continue',
    'Allow .+ to .+\\?',                   # Tool approval
    ':\\s*$',                               # Prompt ending with colon
]

[patterns.error]
regexes = [
    '(?i)error:',
    '(?i)fatal:',
    'Traceback \\(most recent call last\\)',
    '(?i)APIError',
    '(?i)rate.?limit',
    'SIGTERM',
]

[patterns.completion]
regexes = [
    '(?i)task completed',
    '(?i)\\bdone\\.?$',
    '(?i)finished',
]

[patterns.progress]
regexes = [
    '\\d+%',                              # Percentage
    'Step \\d+/\\d+',                      # Step counter
    '(?i)processing|analyzing|thinking',   # Activity indicators
]
```

**How pattern matching drives the UI:**
- **Prompt match** → session status becomes WAITING → sidebar flashes → notification dispatched
- **Error match** → session status becomes ERROR → sidebar turns red → notification dispatched
- **Completion match** → session status becomes DONE → notification dispatched
- **Progress match** → progress indicator shown in sidebar (optional)
- **No output for `idle_threshold_seconds`** → session status becomes IDLE

**Idle-timeout heuristic:** If no output arrives for 3 seconds and there is a partial line in the output buffer (no trailing newline), LAM re-scans the partial line for prompt patterns. Many agents print prompts without a trailing newline, so this catches cases where readline-based detection misses the prompt.

Users can override or extend patterns in their config file. Per-session pattern overrides are also supported.

### 2.5 Notification System

**Event Types and Default Priority:**

| Event | Priority | Desktop | Audio | Toast | Sidebar Flash |
|-------|----------|---------|-------|-------|---------------|
| `input_needed` | high | yes | yes | yes | yes |
| `error` | critical | yes | yes | yes | yes |
| `completed` | medium | yes | yes | yes | no |
| `session_idle` | low | no | no | yes | no |

**Notification Channels:**

1. **Sidebar flash** — session entry pulses/changes color in the sidebar
2. **In-app toast** — small notification overlay in the bottom-right, auto-dismisses after `display_seconds`
3. **Desktop notification** — `notify-send` on Linux with configurable urgency and icon
4. **Audio alert** — sound file playback per event type, with volume control. Backend fallback chain: `pygame.mixer` → `simpleaudio` → terminal bell (`\a`)

**Additional notification features:**
- **Do-not-disturb mode** — toggle to suppress all notifications; also supports a DND schedule (e.g., 22:00–08:00)
- **Notification history** — ring buffer of last N notifications, viewable in a panel
- **Per-event routing** — each event type is independently configurable for which channels fire
- **Per-session overrides** — suppress or customize notifications for specific sessions

### 2.6 Theme System

**Built-in themes:** dark (default), light, solarized-dark, solarized-light, dracula, nord, monokai, gruvbox

**Theme customization via TOML:**
```toml
[theme]
current = "dark"
custom_css_path = ""    # Path to a custom Textual .tcss file

[theme.colors]
# Override individual colors within the active theme
# background = "#1e1e1e"
# foreground = "#d4d4d4"
# sidebar_bg = "#252526"
# active_session = "#4ec9b0"
# waiting_session = "#f48771"
# error_session = "#f44747"
# primary = "#007acc"

[theme.borders]
# style = "rounded"     # rounded, square, double, thick
# color = "#3c3c3c"
```

Themes are implemented as Textual CSS files (`.tcss`). Each built-in theme is a separate `.tcss` file. The `ThemeManager` swaps the active CSS file at runtime.

---

## 3. Architecture

### 3.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Linux Agent Manager (LAM)                     │
│                                                                 │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ ConfigManager│   │ ThemeManager │   │  KeybindManager    │   │
│  │ (TOML)      │   │ (.tcss swap) │   │  (conflict detect) │   │
│  └──────┬──────┘   └──────────────┘   └────────────────────┘   │
│         │                                                       │
│  ┌──────▼──────────────────────────────────────────────────┐    │
│  │                    LAMApp (Textual App)                   │   │
│  │  ┌────────────┐ ┌──────────────────┐ ┌──────────────┐   │   │
│  │  │ HeaderBar  │ │  SessionViewer   │ │  StatusBar   │   │   │
│  │  ├────────────┤ │  (ANSI output)   │ └──────────────┘   │   │
│  │  │ Sidebar    │ │  ┌────────────┐  │                     │   │
│  │  │ (sessions) │ │  │ InputArea  │  │                     │   │
│  │  └────────────┘ │  └────────────┘  │                     │   │
│  │                 └──────────────────┘                      │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │                  SessionManager                           │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Session 1          Session 2         Session N     │ │   │
│  │  │  ┌──────────┐      ┌──────────┐     ┌──────────┐  │ │   │
│  │  │  │ PTY      │      │ PTY      │     │ PTY      │  │ │   │
│  │  │  │ master_fd│      │ master_fd│     │ master_fd│  │ │   │
│  │  │  │ ↕ shell  │      │ ↕ shell  │     │ ↕ shell  │  │ │   │
│  │  │  └──────────┘      └──────────┘     └──────────┘  │ │   │
│  │  │  OutputBuffer      OutputBuffer     OutputBuffer   │ │   │
│  │  │  PatternMatcher    PatternMatcher   PatternMatcher │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │              NotificationEngine                           │   │
│  │  DesktopNotifier │ AudioNotifier │ ToastOverlay │ History │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Descriptions

**ConfigManager** — loads `~/.config/lam/config.toml`, validates schema, provides typed access to all settings. Creates default config on first run.

**LAMApp** — the Textual `App` subclass. Composition root that wires all components. Handles global keybindings and routes custom Messages between widgets.

**SessionManager** — owns all `Session` objects. Handles creation, deletion, batch operations, and the monitoring loop. Posts Textual Messages when sessions change state.

**Session** — a single PTY-backed shell session. Contains:
- PTY master file descriptor
- Child process PID
- `OutputBuffer` (ring buffer of output lines)
- `PatternMatcher` (evaluates output against regex patterns)
- Session metadata (name, working dir, status, timestamps)

**NotificationEngine** — central dispatcher. Receives events from SessionManager, checks DND/routing config, dispatches to enabled channels.

**ThemeManager** — loads `.tcss` files, applies them to the Textual app, supports runtime switching.

**KeybindManager** — loads keybinding config, detects conflicts, provides context-aware binding lookup.

### 3.3 Event Flow

```
PTY output (bytes from master_fd)
    │
    ├── asyncio.add_reader(fd, callback)    [zero-overhead epoll integration]
    │
    ▼
PTYReader._on_readable()
    │── os.read(master_fd, 65536)
    │── decode UTF-8
    │── OutputBuffer.append_data(text)
    │── PatternMatcher.scan(new_lines)
    │
    ├── app.post_message(SessionOutput(...))        → SessionViewer renders output
    │
    ├── if prompt detected:
    │   ├── session.status = WAITING
    │   ├── app.post_message(SessionStatusChanged)  → Sidebar updates
    │   └── NotificationEngine.dispatch(INPUT_NEEDED) → Desktop + Audio + Toast
    │
    ├── if error detected:
    │   ├── session.status = ERROR
    │   └── NotificationEngine.dispatch(ERROR)
    │
    └── if completion detected:
        ├── session.status = DONE
        └── NotificationEngine.dispatch(COMPLETED)
```

### 3.4 PTY Design Decision

**PTY (pseudo-terminal) is used instead of subprocess.PIPE.** Rationale:

| Concern | PTY | PIPE |
|---------|-----|------|
| `isatty()` | True — agents emit colors, prompts | False — stripped-down output |
| Buffering | Line-buffered (real-time) | Block-buffered (4KB+ delayed chunks) |
| Prompts without `\n` | Readable immediately | `readline()` blocks forever |
| Ctrl+C/Ctrl+D | Native terminal signals | Must send signals manually |
| stdout/stderr | Combined (single stream) | Separate streams |
| Platform | Linux/macOS only | Cross-platform |

The combined stdout/stderr stream is acceptable because: (a) agents interleave them anyway, (b) the UI shows a single output, (c) error detection uses pattern matching, not stream identity.

### 3.5 Async I/O Architecture

The Textual event loop is asyncio-based. LAM integrates PTY reading via `loop.add_reader(master_fd, callback)` which uses the kernel's `epoll` — zero-thread, zero-overhead monitoring of all session file descriptors from a single event loop.

```python
# Core I/O bridge (simplified)
class PTYReader:
    def start(self):
        loop = asyncio.get_running_loop()
        os.set_blocking(self._master_fd, False)
        loop.add_reader(self._master_fd, self._on_readable)

    def _on_readable(self):
        data = os.read(self._master_fd, 65536)
        if not data:      # EOF (child exited)
            self.stop()
            return
        decoded = data.decode("utf-8", errors="replace")
        self._on_data(self._session_id, decoded)
```

When a child process exits and closes the PTY slave, reading the master fd raises `OSError(errno=5)` (EIO). This is normal PTY behavior and is treated as EOF.

### 3.6 Process Lifecycle

Each session's shell process follows this state machine:

```
    create_session()
         │
         ▼
     [ CREATED ]
         │ start()
         ▼
     [ STARTING ] ──(first output)──▶ [ ACTIVE ]
                                        │    ▲
                              pause()   │    │ resume()
                                ▼       │    │
                           [ PAUSED ]   │    │
                                        │    │
                         (prompt match) │    │ (user input sent)
                                ▼       │    │
                         [ WAITING ] ───┘    │
                                             │
                         (process exits)     │
                              │    │         │
                              ▼    ▼         │
                      [ DONE ] [ ERROR ]     │
                              │              │
                          restart() ─────────┘
```

**Signal handling:**
- **Pause:** `os.killpg(pgid, SIGSTOP)` — stops the entire process group
- **Resume:** `os.killpg(pgid, SIGCONT)`
- **Stop:** `SIGTERM` → wait 3s → `SIGKILL` if still running
- **Process groups:** `start_new_session=True` ensures each session is a separate process group, so signals affect the shell and all its child processes

**Zombie prevention:** A background `asyncio.Task` calls `await process.wait()` for each session, reaping the exit status.

---

## 4. UI Layout

### 4.1 Visual Layout

```
Terminal (minimum 80x24)
+==============================================================================+
│ LAM  Linux Agent Manager          [▶ Resume All] [⏸ Pause All]   CPU:12% 2.1G│
+========================+=====================================================+
│  [🔍 Search...        ]│  Session: "api-refactor"                             │
│  ───────────────────── │  Dir: ~/projects/api │ PID: 12345 │ 14m ago          │
│  ● api-refactor   ACT  │  ──────────────────────────────────────────────────  │
│  ○ frontend-fix   IDLE │  $ claude                                            │
│  ◉ db-migration   WAIT │  > Analyzing the codebase structure...               │
│  ✓ test-suite     DONE │  > Found 47 files matching pattern                   │
│  ✗ infra-setup    ERR  │  > I'll refactor the authentication module.          │
│                        │  > Here's my plan:                                   │
│                        │  > 1. Extract auth middleware                        │
│                        │  > 2. Create JWT service                             │
│                        │  > ...                                               │
│                        │  > Do you want me to proceed? [Y/n]                  │
│                        │  ──────────────────────────────────────────────────  │
│  ───────────────────── │  > _                                                 │
│  [+ New Session]       │                                                      │
+========================+=====================================================+
│ Sessions: 5 │ Active: 1 │ Waiting: 1 │ Errors: 1 │ Ctrl+N New │ Ctrl+Q Quit │
+==============================================================================+
```

### 4.2 Widget Hierarchy

```
LAMApp
├── HeaderBar              # Title, global control buttons, resource indicators
│   ├── Static (title)
│   ├── Button (Resume All)
│   ├── Button (Pause All)
│   └── ResourceIndicator  # CPU/MEM sparkline
│
├── Horizontal (main content)
│   ├── SessionSidebar     # Left panel
│   │   ├── Input (search/filter)
│   │   ├── ListView (session list)
│   │   │   └── SessionListItem (per session)
│   │   └── Button (+ New Session)
│   │
│   └── Vertical (right panel)
│       ├── SessionHeader  # Name, dir, PID, duration
│       ├── SessionViewer  # Scrollable ANSI output
│       └── InputArea      # Text input for PTY stdin
│
├── StatusBar              # Aggregate stats, keybinding hints
└── ToastOverlay           # Floating notification toasts
```

### 4.3 Responsive Layout

- **Sidebar width:** fixed 28 columns by default, collapsible via Ctrl+B
- **When sidebar is collapsed:** sessions accessible via Alt+1..9 or Ctrl+Up/Down
- **Small terminals (<100 cols):** sidebar auto-collapses, showing only icons
- **Large terminals (>160 cols):** sidebar expands to show more detail (full paths, timestamps)

### 4.4 Session Viewer (Terminal Rendering)

The SessionViewer widget renders PTY output with ANSI escape code support. It uses a `RichLog`-style widget (Textual's built-in) or a custom widget based on `pyte` (a Python terminal emulator library) for full VT100 compatibility.

**Options for terminal rendering (implementation choice):**

1. **Textual RichLog + Rich ANSI parsing** — simpler, handles colors and basic formatting. May not handle cursor movement, alternate screen, or full VT100 sequences.
2. **pyte terminal emulator** — full VT100/xterm emulation. Maintains a virtual screen buffer. More complex but handles agents that use ncurses, progress bars, etc.

**Recommendation:** Start with RichLog for v1 (handles 90% of cases). Evaluate pyte for v2 if users report rendering issues.

---

## 5. Session State Persistence

Session persistence is handled via **tmux integration**. When `sessions.start_in_tmux = true` (default), each session runs inside a tmux session prefixed with `tame-`. Sessions survive TAME restarts and are automatically rediscovered on startup via `restore_tmux_sessions_on_startup`.

---

## 6. Configuration

### 6.1 Config File Location

`~/.config/lam/config.toml`

Created with defaults on first run. LAM also respects `$XDG_CONFIG_HOME/lam/config.toml`.

### 6.2 Complete Config Schema

```toml
# =============================================================================
# Linux Agent Manager (LAM) Configuration
# =============================================================================

# ── General ──────────────────────────────────────────────────────────────────

[general]
log_file = "~/.local/share/lam/lam.log"         # Log file (empty = stderr only)
log_level = "INFO"                               # DEBUG, INFO, WARNING, ERROR
max_buffer_lines = 10000                         # Max output lines per session
autosave_interval_seconds = 60                   # 0 = disabled
resource_poll_seconds = 5                        # System resource monitor interval

# ── Sessions ─────────────────────────────────────────────────────────────────

[sessions]
auto_resume = false                              # Resume active sessions on startup
default_working_directory = ""                   # Empty = $HOME
default_shell = ""                               # Empty = $SHELL or /bin/bash
max_concurrent_sessions = 0                      # 0 = unlimited
idle_threshold_seconds = 300                     # No output → IDLE status

# ── Pattern Matching ─────────────────────────────────────────────────────────

[patterns.prompt]
regexes = [
    '\\[y/n\\]',
    '\\[Y/n\\]',
    '\\[yes/no\\]',
    '\\(a\\)pprove.*\\(d\\)eny',
    'Do you want to (?:continue|proceed)',
    'Press [Ee]nter to continue',
    'Allow .+ to .+\\?',
]

[patterns.error]
regexes = [
    '(?i)error:',
    '(?i)fatal:',
    'Traceback \\(most recent call last\\)',
    '(?i)APIError',
    '(?i)rate.?limit',
]

[patterns.completion]
regexes = [
    '(?i)task completed',
    '(?i)\\bdone\\.?$',
    '(?i)finished',
]

[patterns.progress]
regexes = [
    '\\d+%',
    'Step \\d+/\\d+',
]

# Seconds of no output before checking partial line for prompt patterns
idle_prompt_timeout = 3.0

# ── Theme ────────────────────────────────────────────────────────────────────

[theme]
current = "dark"
custom_css_path = ""

[theme.colors]
# Override individual colors (uncomment to customize)
# background = "#1e1e1e"
# foreground = "#d4d4d4"
# sidebar_bg = "#252526"
# active_session = "#4ec9b0"
# waiting_session = "#f48771"
# error_session = "#f44747"
# primary = "#007acc"

[theme.borders]
# style = "rounded"
# color = "#3c3c3c"

# ── Notifications ────────────────────────────────────────────────────────────

[notifications]
enabled = true
do_not_disturb = false
dnd_start = ""                                   # e.g., "22:00"
dnd_end = ""                                     # e.g., "08:00"
history_max = 500

[notifications.desktop]
enabled = true
urgency = "normal"                               # low, normal, critical
icon_path = ""
timeout_ms = 5000

[notifications.audio]
enabled = true
volume = 0.7
backend_preference = ["pygame", "simpleaudio", "bell"]

[notifications.audio.sounds]
input_needed = ""                                # Path to .wav/.mp3/.ogg
error = ""
completed = ""
default = ""

[notifications.toast]
enabled = true
display_seconds = 5
max_visible = 3

# Per-event routing (which channels fire for each event type)
[notifications.routing.input_needed]
priority = "high"
desktop = true
audio = true
toast = true
sidebar_flash = true

[notifications.routing.error]
priority = "critical"
desktop = true
audio = true
toast = true
sidebar_flash = true

[notifications.routing.completed]
priority = "medium"
desktop = true
audio = true
toast = true
sidebar_flash = false

[notifications.routing.session_idle]
priority = "low"
desktop = false
audio = false
toast = true
sidebar_flash = false

# ── Keybindings ──────────────────────────────────────────────────────────────

[keybindings]
new_session = "ctrl+n"
delete_session = "ctrl+d"
rename_session = "f2"
next_session = "ctrl+down"
prev_session = "ctrl+up"
resume_all = "ctrl+r"
pause_all = "ctrl+p"
stop_all = "ctrl+shift+q"
toggle_sidebar = "ctrl+b"
focus_search = "/"
focus_input = "ctrl+l"
save_state = "ctrl+s"
toggle_theme = "ctrl+t"
export_session_log = "ctrl+e"
quit = "ctrl+q"
session_1 = "alt+1"
session_2 = "alt+2"
session_3 = "alt+3"
session_4 = "alt+4"
session_5 = "alt+5"
session_6 = "alt+6"
session_7 = "alt+7"
session_8 = "alt+8"
session_9 = "alt+9"
```

---

## 7. Keybindings

### 7.1 Default Keybindings

**Global (available everywhere):**

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Quit application |
| `Ctrl+N` | Create new session |
| `Ctrl+S` | Save all state now |
| `Ctrl+T` | Cycle theme |
| `Ctrl+B` | Toggle sidebar visibility |
| `Ctrl+R` | Resume all sessions |
| `Ctrl+P` | Pause all sessions |
| `Ctrl+Shift+Q` | Stop all sessions |
| `Ctrl+Up` | Previous session |
| `Ctrl+Down` | Next session |
| `Alt+1` — `Alt+9` | Jump to session N |

**Sidebar-focused:**

| Key | Action |
|-----|--------|
| `Up`/`Down` | Navigate session list |
| `Enter` | Select/switch to session |
| `/` | Focus search input |
| `Escape` | Clear search |
| `F2` | Rename selected session |
| `Ctrl+D` | Delete selected session |
| `Ctrl+E` | Export session log |

**Main viewer-focused:**

| Key | Action |
|-----|--------|
| `PageUp`/`PageDown` | Scroll output |
| `Home`/`End` | Scroll to top/bottom |
| `Ctrl+L` | Focus input area |

**Input area-focused:**

| Key | Action |
|-----|--------|
| `Enter` | Send input to session PTY |
| `Escape` | Blur input, return to viewer |
| `Up`/`Down` | Input history navigation |

### 7.2 Customization

All keybindings are customizable via the `[keybindings]` section in config.toml. The `KeybindManager` validates user overrides at startup and raises a warning on conflicts (same key bound to multiple actions in the same context).

---

## 8. Project Structure

```
lam/
├── __init__.py
├── __main__.py                    # Entry point, CLI arg parsing
├── app.py                         # LAMApp (Textual App subclass)
│
├── config/
│   ├── __init__.py
│   ├── manager.py                 # ConfigManager: TOML loading, validation
│   └── defaults.py                # Default config values
│
├── session/
│   ├── __init__.py
│   ├── manager.py                 # SessionManager: CRUD, batch ops, monitoring loop
│   ├── session.py                 # Session dataclass
│   ├── pty_process.py             # PTY spawning, PTYReader (add_reader I/O)
│   ├── output_buffer.py           # Ring buffer (deque-based)
│   ├── pattern_matcher.py         # Regex pattern matching for output monitoring
│   └── state.py                   # SessionState enum
│
├── ui/
│   ├── __init__.py
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── header_bar.py          # Top bar: title, buttons, resource indicator
│   │   ├── session_sidebar.py     # Left sidebar: session list, search, new button
│   │   ├── session_list_item.py   # Individual session entry in sidebar
│   │   ├── session_viewer.py      # Main panel: ANSI output display
│   │   ├── session_header.py      # Session info bar (name, dir, PID)
│   │   ├── input_area.py          # Text input for PTY stdin
│   │   ├── status_bar.py          # Bottom bar: stats, keybinding hints
│   │   └── toast_overlay.py       # Floating notification toasts
│   ├── events.py                  # Custom Textual Messages
│   ├── themes/
│   │   ├── __init__.py
│   │   ├── manager.py             # ThemeManager
│   │   └── builtin/
│   │       ├── dark.tcss
│   │       ├── light.tcss
│   │       ├── dracula.tcss
│   │       ├── nord.tcss
│   │       ├── monokai.tcss
│   │       ├── gruvbox.tcss
│   │       ├── solarized_dark.tcss
│   │       └── solarized_light.tcss
│   └── keys/
│       ├── __init__.py
│       └── manager.py             # KeybindManager with conflict detection
│
├── notifications/
│   ├── __init__.py
│   ├── engine.py                  # NotificationEngine: central dispatcher
│   ├── models.py                  # NotificationEvent, Priority, EventType
│   ├── desktop.py                 # DesktopNotifier (notify-send)
│   ├── audio.py                   # AudioNotifier (pygame → simpleaudio → bell)
│   └── history.py                 # NotificationHistory ring buffer
│
└── utils/
    ├── __init__.py
    └── logger.py                  # Logging setup
```

---

## 9. Data Models

### 9.1 Session

```python
@dataclass
class Session:
    id: str                          # UUID
    name: str                        # User-editable display name
    working_dir: Path                # CWD for the shell
    status: SessionState             # CREATED, ACTIVE, IDLE, WAITING, ERROR, DONE, PAUSED
    pid: int | None                  # Shell process PID
    master_fd: int | None            # PTY master file descriptor
    exit_code: int | None            # Process exit code (None if running)
    created_at: datetime
    last_activity: datetime          # Timestamp of last output
    output_buffer: OutputBuffer      # Ring buffer of output lines
    pattern_matcher: PatternMatcher  # Regex engine for this session
    input_history: list[str]         # Per-session input history
    metadata: dict[str, Any]         # Extensible metadata
```

### 9.2 SessionState

```python
class SessionState(Enum):
    CREATED = "created"
    STARTING = "starting"
    ACTIVE = "active"
    IDLE = "idle"
    WAITING = "waiting"          # Agent needs input
    PAUSED = "paused"            # SIGSTOP'd
    DONE = "done"                # Exited with code 0
    ERROR = "error"              # Exited with non-zero or error pattern
```

### 9.3 OutputBuffer

```python
@dataclass
class OutputBuffer:
    max_lines: int = 10_000
    _lines: deque[str]           # Ring buffer with maxlen
    _partial_line: str = ""      # Incomplete line (no trailing \n yet)
    total_lines_received: int = 0
    total_bytes_received: int = 0
```

### 9.4 PatternMatcher

```python
@dataclass
class PatternMatch:
    category: str                # "prompt", "error", "completion", "progress"
    pattern_name: str            # Identifier for which regex matched
    matched_text: str            # The text that matched
    line: str                    # Full line that was scanned

class PatternMatcher:
    """Tests output lines against configured regex patterns."""
    # Organized by category, tested in priority: error → prompt → completion → progress
    def scan(self, line: str) -> PatternMatch | None: ...
```

---

## 10. Dependencies

```toml
[project]
name = "linux-agent-manager"
requires-python = ">=3.11"

[project.dependencies]
textual = ">=0.47.0"             # TUI framework
rich = ">=13.0.0"                # Terminal formatting (Textual dependency)
tomli = ">=2.0.0"                # TOML parsing (stdlib in 3.11+ but tomli for compat)
psutil = ">=5.9.0"               # Process/resource monitoring

[project.optional-dependencies]
audio = [
    "pygame>=2.5.0",             # Audio playback (preferred)
    "simpleaudio>=1.0.4",        # Audio fallback
]

[project.scripts]
lam = "lam.__main__:main"
```

---

## 11. Development Roadmap

### Phase 1: Core Shell Multiplexer (Week 1–2)
- [ ] Project scaffolding (pyproject.toml, package structure)
- [ ] PTY process spawning and I/O (pty_process.py)
- [ ] Output buffer with ring buffer
- [ ] Basic Textual TUI: sidebar + viewer + input area
- [ ] Session CRUD (create, select, delete)
- [ ] Input routing (type in input area → PTY stdin)

### Phase 2: Pattern Matching & Notifications (Week 3–4)
- [ ] PatternMatcher with configurable regexes
- [ ] Session status transitions based on pattern matches
- [ ] Sidebar status indicators (colors, icons)
- [ ] Desktop notifications (notify-send)
- [ ] Audio notifications (pygame with fallback)
- [ ] In-app toast overlay

### Phase 3: Persistence & Config (Week 5)
- [x] TOML config loading with defaults
- [x] Tmux-based session persistence and auto-restore on startup
- [x] Keybinding system with conflict detection

### Phase 4: Polish (Week 6)
- [ ] Theme system (8 built-in themes, TCSS-based)
- [ ] Session search/filter in sidebar
- [ ] Resource monitoring (CPU/MEM in header)
- [ ] Input history per session
- [ ] Export session logs
- [ ] Batch operations (pause all, resume all, stop all)

### Phase 5: Future (v2)
- [ ] Docker integration (run sessions inside containers)
- [ ] Full VT100 terminal emulation (pyte)
- [ ] Session templates / quick-launch profiles
- [ ] Plugin system for custom pattern matchers
- [ ] Web UI alternative
- [ ] Tmux-style pane splitting (multiple sessions visible simultaneously)

---

## 12. Installation & Usage

```bash
# Install from PyPI (future)
pip install linux-agent-manager

# Install from source
git clone https://github.com/user/linux-agent-manager
cd linux-agent-manager
pip install -e .

# Run
lam

# Or with options
lam --config ~/.config/lam/config.toml
lam --theme dracula
lam --verbose
```

**First run experience:**
1. LAM creates `~/.config/lam/config.toml` with defaults
2. Empty sidebar with "[+ New Session]" button
3. Press Ctrl+N → enter session name and working directory → shell spawns
4. Type your agent command (e.g., `claude`, `codex`, `aider`) in the session
5. Switch between sessions with Alt+1..9 or sidebar clicks
6. Get notified when any session needs attention

---

## 13. Testing Strategy

### Unit Tests
- `test_output_buffer.py` — append, ring buffer eviction, partial lines, line counting
- `test_pattern_matcher.py` — each default pattern against known agent outputs
- `test_session_state.py` — state transition validation
- `test_config_manager.py` — TOML loading, defaults, overrides
- `test_keybind_manager.py` — conflict detection, context filtering
- `test_notification_engine.py` — routing, DND, priority filtering

### Integration Tests
- `test_pty_process.py` — spawn shell, write input, read output, signal handling
- `test_session_manager.py` — create/delete sessions, batch operations
- `test_tmux_restore.py` — tmux session discovery and restore

### End-to-End Tests (Textual Pilot)
- `test_app.py` — use Textual's `pilot` testing framework to simulate:
  - Creating a session
  - Seeing output appear
  - Pattern detection triggering sidebar flash
  - Input submission
  - Session switching
  - Theme cycling
  - Keybinding actions

---

## Verification

After implementing, verify the refined specs work by:

1. `pip install -e .` — install in development mode
2. `lam` — app launches with empty sidebar
3. Create a session → shell spawns in chosen directory
4. Run `echo "Do you want to proceed? [y/n]"` → verify pattern match triggers WAITING status and notification
5. Type `y` in input area → verify it's sent to the shell
6. Run `exit 1` in a session → verify ERROR status
7. Run `exit 0` → verify DONE status
8. Check `~/.config/lam/config.toml` was created
9. Restart TAME → verify tmux sessions are rediscovered and restored
10. Test keybindings: Ctrl+N, Alt+1..9, Ctrl+B, Ctrl+Q
