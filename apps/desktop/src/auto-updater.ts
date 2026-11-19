import { BrowserWindow, dialog, app } from "electron";
import { autoUpdater } from "electron-updater";
import * as path from "node:path";

const isDev = !app.isPackaged;

export class AutoUpdaterManager {
  private mainWindow: BrowserWindow | null = null;
  private updateAvailable = false;
  private downloadedUpdate = false;

  setMainWindow(win: BrowserWindow | null): void {
    this.mainWindow = win;
  }

  init(): void {
    if (isDev) {
      return;
    }

    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on("checking-for-update", () => {
      console.log("[AutoUpdater] Checking for updates...");
    });

    autoUpdater.on("update-available", (info) => {
      console.log("[AutoUpdater] Update available:", info.version);
      this.updateAvailable = true;
      this.notifyUpdateAvailable(info.version);
    });

    autoUpdater.on("update-not-available", (info) => {
      console.log("[AutoUpdater] Update not available:", info.version);
      this.updateAvailable = false;
    });

    autoUpdater.on("download-progress", (progressObj) => {
      const message = `下载速度: ${this.formatBytes(progressObj.bytesPerSecond)}/s\n` +
        `已下载: ${this.formatBytes(progressObj.transferred)} / ${this.formatBytes(progressObj.total)}\n` +
        `进度: ${progressObj.percent.toFixed(2)}%`;
      console.log("[AutoUpdater] Download progress:", message);
    });

    autoUpdater.on("update-downloaded", (info) => {
      console.log("[AutoUpdater] Update downloaded:", info.version);
      this.downloadedUpdate = true;
      this.notifyUpdateDownloaded(info.version);
    });

    autoUpdater.on("error", (err) => {
      console.error("[AutoUpdater] Error:", err.message);
    });
  }

  async checkForUpdates(): Promise<void> {
    if (isDev) {
      console.log("[AutoUpdater] Skipping update check in dev mode");
      return;
    }

    try {
      await autoUpdater.checkForUpdates();
    } catch (err) {
      console.error("[AutoUpdater] Check for updates failed:", err);
    }
  }

  async downloadUpdate(): Promise<void> {
    if (!this.updateAvailable) return;

    try {
      await autoUpdater.downloadUpdate();
    } catch (err) {
      console.error("[AutoUpdater] Download update failed:", err);
      dialog.showErrorBox(
        "更新下载失败",
        `下载更新时发生错误：${err instanceof Error ? err.message : String(err)}`,
      );
    }
  }

  quitAndInstall(): void {
    if (this.downloadedUpdate) {
      autoUpdater.quitAndInstall();
    }
  }

  private notifyUpdateAvailable(version: string): void {
    const win = this.mainWindow;
    if (!win || win.isDestroyed()) return;

    dialog.showMessageBox(win, {
      type: "info",
      title: "发现新版本",
      message: `RsAgent v${version} 可用`,
      detail: "是否现在下载更新？",
      buttons: ["立即下载", "稍后提醒"],
      defaultId: 0,
      cancelId: 1,
    }).then((result) => {
      if (result.response === 0) {
        void this.downloadUpdate();
      }
    });
  }

  private notifyUpdateDownloaded(version: string): void {
    const win = this.mainWindow;
    if (!win || win.isDestroyed()) return;

    dialog.showMessageBox(win, {
      type: "info",
      title: "更新已就绪",
      message: `RsAgent v${version} 已下载完成`,
      detail: "退出应用时将自动安装更新。是否现在重启安装？",
      buttons: ["立即重启安装", "稍后安装"],
      defaultId: 0,
      cancelId: 1,
    }).then((result) => {
      if (result.response === 0) {
        this.quitAndInstall();
      }
    });
  }

  private formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  }
}

export const autoUpdaterManager = new AutoUpdaterManager();
