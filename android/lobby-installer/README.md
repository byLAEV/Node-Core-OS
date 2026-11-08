# NODE CORE OS Lobby Installer (Android)

The APK has exactly one job: send the Lobby bootstrap command to the already-installed Termux app.

When the user opens NODE, it sends a foreground `RUN_COMMAND` intent to Termux. Termux opens a terminal session and executes a fixed Bash command that:

1. Checks whether the standalone Lobby is already installed.
2. If not installed, refreshes package indexes and installs only `curl`, `tar`, and `python`.
3. Downloads this repository at the pinned source commit `31d0669886adc9c5858d24ca304d94188459fa85`.
4. Runs only `termux-lobby/install.sh`.
5. Starts the local Lobby at `http://127.0.0.1:8765/`.

The APK does not install the full Node Core OS runtime, does not manage nodes, and does not perform Lobby administration. Those operations remain inside Termux and the Lobby.

## One-time Android/Termux authorization

Termux must already be installed. Android and Termux require the user to authorize third-party command execution:
- Grant NODE the Android permission **Run commands in Termux environment**.
- In Termux, set `allow-external-apps=true` in `~/.termux/termux.properties`, then restart Termux.
- Android may require Termux's **Display over other apps** permission before it can automatically bring its terminal session to the foreground.

These are platform security controls and cannot be bypassed by the APK.

## Build

Use JDK 17 and Android SDK 35:

```bash
gradle --no-daemon :app:assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`.

The source commit is deliberately pinned in `MainActivity.java`. Update it deliberately when publishing a new Lobby installer.
