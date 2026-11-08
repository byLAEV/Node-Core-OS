# NODE CORE OS Lobby Installer (Android)

Small launcher only. It does not bundle or install the full Node Core OS runtime. It sends one command to Termux through the official RUN_COMMAND interface. The command fetches a pinned repository snapshot, installs only `termux-lobby/`, and starts the local HTTP lobby.

## Requirements
- Termux installed from a compatible distribution.
- Grant NODE the Android permission **Run commands in Termux environment**.
- In Termux, set `allow-external-apps=true` in `~/.termux/termux.properties`, then restart Termux.
- Android may restrict foreground service/session launch until the user opens Termux. Follow the notification or prompt if shown.

## Build
Use JDK 17 and Android SDK 35:
`gradle :app:assembleDebug`
APK: `app/build/outputs/apk/debug/app-debug.apk`.

The launcher pins source commit `87fde3334fffcf552996c857691fa6852e7dfc76`. Update that pin deliberately when publishing a new Lobby release. Verify downloaded artifacts and test on physical Android/Termux before distributing.
