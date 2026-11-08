package bylaev.node.lobbyinstaller;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.widget.TextView;

/** NODE sends the Lobby installation command to Termux. */
public final class MainActivity extends Activity {
    private TextView status;

    private static final String SOURCE_COMMIT = "31d0669886adc9c5858d24ca304d94188459fa85";
    private static final String INSTALL_COMMAND =
        "set -Eeuo pipefail; " +
        "APP_DIR=\"$HOME/.node-core/lobby\"; " +
        "if [ -x \"$PREFIX/bin/node-lobby\" ] && [ -f \"$APP_DIR/server.py\" ]; then " +
            "node-lobby; " +
        "else " +
            "pkg update -y && " +
            "pkg install -y curl tar python && " +
            "WORK=\"$" + "{TMPDIR:-$PREFIX/tmp}/node-core-lobby-installer\" && " +
            "mkdir -p \"$WORK\" && " +
            "curl -fL --retry 3 " +
                "\"https://github.com/byLAEV/Node-Core-OS/archive/" + SOURCE_COMMIT + ".tar.gz\" " +
                "-o \"$WORK/source.tar.gz\" && " +
            "tar -xzf \"$WORK/source.tar.gz\" -C \"$WORK\" && " +
            "bash \"$WORK/Node-Core-OS-" + SOURCE_COMMIT + "/termux-lobby/install.sh\"; " +
        "fi";

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setBackgroundColor(Color.rgb(16, 19, 24));
        status.setTextSize(18);
        status.setGravity(Gravity.CENTER);
        status.setPadding(28, 28, 28, 28);
        status.setText("NODE CORE OS\nLOBBY INSTALLER\n\nEnviando instalador a Termux…");
        setContentView(status);
        sendCommandToTermux();
    }

    private void sendCommandToTermux() {
        try {
            getPackageManager().getPackageInfo("com.termux", 0);
        } catch (PackageManager.NameNotFoundException missing) {
            status.setText("Termux no está instalado. Instala Termux y vuelve a abrir NODE.");
            return;
        }

        if (checkSelfPermission("com.termux.permission.RUN_COMMAND")
                != PackageManager.PERMISSION_GRANTED) {
            status.setText("Falta autorizar NODE para ejecutar comandos en Termux. Abriendo los permisos de NODE…");
            Intent settings = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
            settings.setData(Uri.parse("package:" + getPackageName()));
            startActivity(settings);
            return;
        }

        Intent command = new Intent();
        command.setClassName("com.termux", "com.termux.app.RunCommandService");
        command.setAction("com.termux.RUN_COMMAND");
        command.putExtra("com.termux.RUN_COMMAND_PATH",
                "/data/data/com.termux/files/usr/bin/bash");
        command.putExtra("com.termux.RUN_COMMAND_ARGUMENTS",
                new String[]{"-lc", INSTALL_COMMAND});
        command.putExtra("com.termux.RUN_COMMAND_WORKDIR",
                "/data/data/com.termux/files/home");
        command.putExtra("com.termux.RUN_COMMAND_BACKGROUND", false);
        command.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");
        command.putExtra("com.termux.RUN_COMMAND_COMMAND_LABEL",
                "Install NODE CORE OS Lobby");

        try {
            startService(command);
            status.setText("Termux recibió el comando. La instalación y el inicio del Lobby se ejecutan allí.");
        } catch (Exception error) {
            status.setText("No fue posible enviar el comando a Termux.\n\n" +
                    error.getMessage() +
                    "\n\nComprueba RUN_COMMAND y allow-external-apps=true en Termux.");
        }
    }
}
