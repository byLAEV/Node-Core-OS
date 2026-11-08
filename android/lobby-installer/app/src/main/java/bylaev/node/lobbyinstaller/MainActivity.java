package bylaev.node.lobbyinstaller;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private static final int REQ_TERMUX_PERMISSION = 41;
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setBackgroundColor(Color.rgb(16,19,24));
        status.setTextSize(18);
        status.setGravity(Gravity.CENTER);
        status.setPadding(28,28,28,28);
        status.setText("NODE CORE OS LOBBY INSTALLER\n\nPreparing Termux…");
        setContentView(status);
        launchLobby();
    }

    private void launchLobby() {
        if (getPackageManager().getPackageInfo("com.termux", 0) == null) {
            status.setText("Termux no está instalado. Instala Termux y vuelve a abrir NODE.");
            return;
        }
        if (checkSelfPermission("com.termux.permission.RUN_COMMAND") != PackageManager.PERMISSION_GRANTED) {
            status.setText("Autoriza “Run commands in Termux environment” en los permisos de NODE y vuelve a abrir la aplicación.");
            return;
        }
        Intent intent = new Intent();
        intent.setClassName("com.termux", "com.termux.app.RunCommandService");
        intent.setAction("com.termux.RUN_COMMAND");
        intent.putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash");
        intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{"-lc",
            "set -e; mkdir -p \"$HOME/.node-core\"; " +
            "if [ ! -f \"$HOME/.node-core/lobby/server.py\" ]; then " +
            "pkg install -y curl tar python; " +
            "tmp=\"$TMPDIR/node-core-lobby.tar.gz\"; " +
            "curl -fL --retry 3 'https://github.com/byLAEV/Node-Core-OS/archive/87fde3334fffcf552996c857691fa6852e7dfc76.tar.gz' -o \"$tmp\"; " +
            "mkdir -p \"$TMPDIR/node-core-lobby-src\"; tar -xzf \"$tmp\" -C \"$TMPDIR/node-core-lobby-src\"; " +
            "src=\"$TMPDIR/node-core-lobby-src/Node-Core-OS-87fde3334fffcf552996c857691fa6852e7dfc76/termux-lobby\"; " +
            "bash \"$src/install.sh\"; " +
            "else node-lobby; fi"});
        intent.putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home");
        intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", false);
        intent.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");
        intent.putExtra("com.termux.RUN_COMMAND_COMMAND_LABEL", "Install / launch NODE CORE OS Lobby");
        try {
            startService(intent);
            status.setText("Comando enviado a Termux. Sigue las instrucciones de instalación y autorización que aparezcan allí.");
        } catch (Exception e) {
            status.setText("No se pudo iniciar Termux: " + e.getMessage() +
                "\n\nComprueba allow-external-apps=true en ~/.termux/termux.properties y reinicia Termux.");
        }
    }
}
