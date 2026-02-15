from __future__ import annotations

DEFAULT_CONFIG: dict = {
    "general": {
        "state_file": "~/.local/share/lam/state.db",
        "log_file": "~/.local/share/lam/lam.log",
        "log_level": "INFO",
        "max_buffer_lines": 10000,
        "autosave_interval_seconds": 60,
        "resource_poll_seconds": 5,
    },
    "sessions": {
        "auto_resume": False,
        "default_working_directory": "",
        "default_shell": "",
        "max_concurrent_sessions": 0,
        "idle_threshold_seconds": 300,
    },
    "patterns": {
        "prompt": {
            "regexes": [
                r'\[y/n\]',
                r'\[Y/n\]',
                r'\[yes/no\]',
                r'\(a\)pprove.*\(d\)eny',
                r'Do you want to (?:continue|proceed)',
                r'Press [Ee]nter to continue',
                r'Allow .+ to .+\?',
            ]
        },
        "error": {
            "regexes": [
                r'(?i)error:',
                r'(?i)fatal:',
                r'Traceback \(most recent call last\)',
                r'(?i)APIError',
                r'(?i)rate.?limit',
            ]
        },
        "completion": {
            "regexes": [
                r'(?i)task completed',
                r'(?i)\bdone\.?$',
                r'(?i)finished',
            ]
        },
        "progress": {
            "regexes": [
                r'\d+%',
                r'Step \d+/\d+',
            ]
        },
        "idle_prompt_timeout": 3.0,
    },
    "theme": {
        "current": "dark",
        "custom_css_path": "",
        "colors": {},
        "borders": {},
    },
    "notifications": {
        "enabled": True,
        "do_not_disturb": False,
        "dnd_start": "",
        "dnd_end": "",
        "history_max": 500,
        "desktop": {
            "enabled": True,
            "urgency": "normal",
            "icon_path": "",
            "timeout_ms": 5000,
        },
        "audio": {
            "enabled": True,
            "volume": 0.7,
            "backend_preference": ["pygame", "simpleaudio", "bell"],
            "sounds": {
                "input_needed": "",
                "error": "",
                "completed": "",
                "default": "",
            },
        },
        "toast": {
            "enabled": True,
            "display_seconds": 5,
            "max_visible": 3,
        },
        "routing": {
            "input_needed": {"priority": "high", "desktop": True, "audio": True, "toast": True, "sidebar_flash": True},
            "error": {"priority": "critical", "desktop": True, "audio": True, "toast": True, "sidebar_flash": True},
            "completed": {"priority": "medium", "desktop": True, "audio": True, "toast": True, "sidebar_flash": False},
            "session_idle": {"priority": "low", "desktop": False, "audio": False, "toast": True, "sidebar_flash": False},
        },
    },
    "keybindings": {
        "new_session": "ctrl+n",
        "delete_session": "ctrl+d",
        "rename_session": "f2",
        "next_session": "ctrl+down",
        "prev_session": "ctrl+up",
        "resume_all": "ctrl+r",
        "pause_all": "ctrl+p",
        "stop_all": "ctrl+shift+q",
        "toggle_sidebar": "ctrl+b",
        "focus_search": "/",
        "focus_input": "ctrl+l",
        "save_state": "ctrl+s",
        "toggle_theme": "ctrl+t",
        "export_session_log": "ctrl+e",
        "quit": "ctrl+q",
        "session_1": "alt+1",
        "session_2": "alt+2",
        "session_3": "alt+3",
        "session_4": "alt+4",
        "session_5": "alt+5",
        "session_6": "alt+6",
        "session_7": "alt+7",
        "session_8": "alt+8",
        "session_9": "alt+9",
    },
}
