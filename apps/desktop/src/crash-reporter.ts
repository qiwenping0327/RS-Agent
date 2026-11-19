import { crashReporter, app } from "electron";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

const isDev = !app.isPackaged;

export class CrashReporterManager {
  private crashesDir = "";

  init(): void {
    const rsagentDir = path.join(
      process.env.PILOT_HOME || path.join(os.homedir(), ".rsagent"),
    );
    this.crashesDir = path.join(rsagentDir, "crashes");

    if (!fs.existsSync(this.crashesDir)) {
      try {
        fs.mkdirSync(this.crashesDir, { recursive: true });
      } catch {
        console.warn("[CrashReporter] Failed to create crashes directory");
      }
    }

    try {
      app.setPath("crashDumps", this.crashesDir);
    } catch {
      console.warn("[CrashReporter] Failed to set crash dumps path");
    }

    crashReporter.start({
      productName: "RsAgent",
      companyName: "RsAgent Contributors",
      submitURL: "",
      uploadToServer: false,
      ignoreSystemCrashHandler: false,
    });

    crashReporter.addExtraParameter("version", app.getVersion());
    crashReporter.addExtraParameter("platform", process.platform);
    crashReporter.addExtraParameter("arch", process.arch);
    crashReporter.addExtraParameter("env", isDev ? "development" : "production");

    console.log("[CrashReporter] Crash reporter initialized");
    console.log(`[CrashReporter] Crashes directory: ${this.crashesDir}`);
  }

  getCrashesDir(): string {
    return this.crashesDir;
  }

  getLatestCrashReport(): string | null {
    if (!fs.existsSync(this.crashesDir)) return null;

    try {
      const files = fs.readdirSync(this.crashesDir)
        .filter((f) => f.endsWith(".dmp") || f.endsWith(".txt"))
        .map((f) => ({
          name: f,
          time: fs.statSync(path.join(this.crashesDir, f)).mtime.getTime(),
        }))
        .sort((a, b) => b.time - a.time);

      if (files.length === 0) return null;
      return path.join(this.crashesDir, files[0].name);
    } catch {
      return null;
    }
  }
}

export const crashReporterManager = new CrashReporterManager();
