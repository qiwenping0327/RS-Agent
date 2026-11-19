#!/usr/bin/env node
// Fix script: recursively copy all hoisted transitive deps from root node_modules
// into the runtime rsagentui/node_modules directory.

const fs = require('fs');
const path = require('path');

const ROOT = 'D:\\project\\PilotDeck';
const RUNTIME_UI = 'C:\\Users\\giser\\AppData\\Roaming\\RsAgent\\runtime\\0.0.11\\rsagentui';

const uiPkgPath = path.join(RUNTIME_UI, 'package.json');
const uiNodeModules = path.join(RUNTIME_UI, 'node_modules');
const rootNodeModules = path.join(ROOT, 'node_modules');

const visited = new Set();
const missing = [];
const copied = [];

function copyPackage(pkgName) {
  if (visited.has(pkgName)) return;
  visited.add(pkgName);

  const src = path.join(rootNodeModules, ...pkgName.split('/'));
  const dst = path.join(uiNodeModules, ...pkgName.split('/'));

  if (!fs.existsSync(src)) {
    // Maybe it's in a special location (e.g. local file: dep)
    console.log(`  SKIP (not found in root): ${pkgName}`);
    return;
  }

  if (!fs.existsSync(dst)) {
    const dstDir = path.dirname(dst);
    if (!fs.existsSync(dstDir)) fs.mkdirSync(dstDir, { recursive: true });
    // xcopy /E /I /Y equivalent
    fs.cpSync(src, dst, { recursive: true, force: true });
    copied.push(pkgName);
    console.log(`  COPIED: ${pkgName}`);
  } else {
    console.log(`  EXISTS: ${pkgName}`);
  }

  // Read package.json and recursively copy its dependencies
  const pkgJson = path.join(src, 'package.json');
  if (fs.existsSync(pkgJson)) {
    try {
      const pkg = JSON.parse(fs.readFileSync(pkgJson, 'utf8'));
      const allDeps = {
        ...(pkg.dependencies || {}),
        ...(pkg.optionalDependencies || {}),
      };
      for (const dep of Object.keys(allDeps)) {
        copyPackage(dep);
      }
    } catch (e) {
      console.log(`  WARN: could not parse ${pkgJson}: ${e.message}`);
    }
  }
}

// Start from ui's dependencies
const uiPkg = JSON.parse(fs.readFileSync(uiPkgPath, 'utf8'));
const directDeps = Object.keys(uiPkg.dependencies || {});

console.log(`UI direct dependencies: ${directDeps.length}`);
console.log(`Starting recursive copy from ${rootNodeModules} -> ${uiNodeModules}\n`);

for (const dep of directDeps) {
  copyPackage(dep);
}

console.log(`\nDone. Copied ${copied.length} packages.`);
