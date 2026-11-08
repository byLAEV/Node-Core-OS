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
    private static final String OPEN_TERMINAL_COMMAND =
        "if [ ! -d \"$HOME/Node-Core-OS-Lobby\" ]; then echo \"ERROR: No existe $HOME/Node-Core-OS-Lobby\"; exec bash -i; fi; " +
        "if [ ! -f \"$HOME/Node-Core-OS-Lobby/server.py\" ]; then echo \"ERROR: No existe server.py en $HOME/Node-Core-OS-Lobby\"; exec bash -i; fi; " +
        "cd \"$HOME/Node-Core-OS-Lobby\" && python server.py; " +
        "RESULT=$?; echo \"\\nNode Core OS Lobby terminó con código $RESULT. Terminal interactiva disponible.\"; exec bash -i";

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
        setContentView(status);
        boolean openTerminal = getIntent() != null && "nodecoreos".equals(getIntent().getScheme())
                && "open-terminal".equals(getIntent().getHost());
        if (openTerminal) {
            status.setText("NODE CORE OS\nOPEN TERMINAL\n\nComprobando $HOME/Node-Core-OS-Lobby…");
            sendCommandToTermux(OPEN_TERMINAL_COMMAND, "Open Node Core Os");
        } else {
            status.setText("NODE CORE OS\nLOBBY INSTALLER\n\nEnviando instalador a Termux…");
            sendCommandToTermux(INSTALL_COMMAND, "Install NODE CORE OS Lobby");
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 41 && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            boolean openTerminal = getIntent() != null && "nodecoreos".equals(getIntent().getScheme())
                    && "open-terminal".equals(getIntent().getHost());
            sendCommandToTermux(openTerminal ? OPEN_TERMINAL_COMMAND : INSTALL_COMMAND,
                    openTerminal ? "Open Node Core Os" : "Install NODE CORE OS Lobby");
        } else if (requestCode == 41) {
            status.setText("Autorización denegada. Activa “Run commands in Termux environment” en los permisos de NODE y vuelve a abrirlo.");
            Intent settings = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
            settings.setData(Uri.parse("package:" + getPackageName()));
            startActivity(settings);
        }
    }

    private void sendCommandToTermux(String shellCommand, String label) {
        try {
            getPackageManager().getPackageInfo("com.termux", 0);
        } catch (PackageManager.NameNotFoundException missing) {
            status.setText("Termux no está instalado. Instala Termux y vuelve a abrir NODE.");
            return;
        }

        if (checkSelfPermission("com.termux.permission.RUN_COMMAND")
                != PackageManager.PERMISSION_GRANTED) {
            status.setText("Solicitando autorización para ejecutar comandos en Termux…");
            requestPermissions(new String[]{"com.termux.permission.RUN_COMMAND"}, 41);
            return;
        }

        Intent command = new Intent();
        command.setClassName("com.termux", "com.termux.app.RunCommandService");
        command.setAction("com.termux.RUN_COMMAND");
        command.putExtra("com.termux.RUN_COMMAND_PATH",
                "/data/data/com.termux/files/usr/bin/bash");
        command.putExtra("com.termux.RUN_COMMAND_ARGUMENTS",
                new String[]{"-lc", shellCommand});
        command.putExtra("com.termux.RUN_COMMAND_WORKDIR",
                "/data/data/com.termux/files/home");
        command.putExtra("com.termux.RUN_COMMAND_BACKGROUND", false);
        command.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");
        command.putExtra("com.termux.RUN_COMMAND_COMMAND_LABEL",
                label);

        try {
            startService(command);
            status.setText("Termux recibió el comando. La sesión de terminal se abrirá en primer plano.");
        } catch (Exception error) {
            status.setText("No fue posible enviar el comando a Termux.\n\n" +
                    error.getMessage() +
                    "\n\nComprueba RUN_COMMAND y allow-external-apps=true en Termux.");
        }
    }
}
