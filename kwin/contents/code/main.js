// Reports the focused window's app id to chiaki-kbm (window title is not sent).
function report() {
    var w = workspace.activeWindow;
    var info = w ? (String(w.resourceClass) + "|" + String(w.resourceName)) : "";
    callDBus("io.github.chiakikbm", "/", "io.github.chiakikbm", "SetFocus", info);
}
workspace.windowActivated.connect(report);
// also re-send periodically so a freshly (re)started chiaki-kbm learns the state
var timer = new QTimer();
timer.interval = 2000;
timer.timeout.connect(report);
timer.start();
report();
