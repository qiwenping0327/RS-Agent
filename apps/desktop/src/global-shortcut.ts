import { globalShortcut, app, BrowserWindow } from "electron";

export class GlobalShortcutManager {
  private mainWindow: BrowserWindow | null = null;
  private registered = false;

  setMainWindow(win: BrowserWindow | null): void {
    this.mainWindow = win;
  }

  registerAll(): void {
    if (this.registered) return;

    const toggleWindowAccelerator = process.platform === "darwin"
      ? "Command+Shift+P"
      : "Control+Shift+P";

    const toggleRegistered = globalShortcut.register(toggleWindowAccelerator, () => {
      this.toggleMainWindow();
    });

    if (!toggleRegistered) {
      console.warn(`[GlobalShortcut] Failed to register toggle window shortcut: ${toggleWindowAccelerator}`);
    }

    this.registered = true;
    console.log("[GlobalShortcut] Global shortcuts registered");
  }

  unregisterAll(): void {
    if (!this.registered) return;
    globalShortcut.unregisterAll();
    this.registered = false;
    console.log("[GlobalShortcut] Global shortcuts unregistered");
  }

  private toggleMainWindow(): void {
    const win = this.mainWindow;
    if (!win || win.isDestroyed()) return;

    if (win.isVisible()) {
      if (win.isMinimized()) {
        win.restore();
        win.focus();
      } else {
        win.hide();
      }
    } else {
      win.show();
      win.focus();
    }
  }
}

export const globalShortcutManager = new GlobalShortcutManager();
