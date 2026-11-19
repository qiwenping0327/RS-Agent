#!/usr/bin/env node
/**
 * Recursively copy all workspace-hoisted dependencies (including transitive)
 * from the repo root node_modules into the ui/node_modules directory.
 *
 * Usage: node copy-hoisted-deps.cjs <root_node_modules> <ui_node_modules> <ui_package_json>
 */
const fs = require('fs');
const path = require('path');

const [, , rootNM, uiNM, uiPkgJson] = process.argv;
if (!rootNM || !uiNM || !uiPkgJson) {
  console.error('Usage: node copy-hoisted-deps.cjs <root_node_modules> <ui_node_modules> <ui_package_json>');
  process.exit(1);
}

const visited = new Set();
let copied = 0;
let existed = 0;

function packagePath(pkgName, baseDir) {
  return path.join(baseDir, ...pkgName.split('/'));
}

function copyPackage(pkgName) {
  if (visited.has(pkgName)) return;
  visited.add(pkgName);

  const src = packagePath(pkgName, rootNM);
  const dst = packagePath(pkgName, uiNM);

  if (!fs.existsSync(src)) {
    // Package not in root node_modules — may be a local file: dep or not hoisted.
    // Skip silently; ui's own node_modules may already contain it.
    if (!fs.existsSync(dst)) {
      console.log(`  [SKIP] ${pkgName} (not in root, not in ui)`);
    }
    return;
  }

  if (fs.existsSync(dst)) {
    existed++;
  } else {
    const dstDir = path.dirname(dst);
    if (!fs.existsSync(dstDir)) fs.mkdirSync(dstDir, { recursive: true });
    try {
      fs.cpSync(src, dst, { recursive: true, force: true });
      copied++;
      console.log(`  [COPY] ${pkgName}`);
    } catch (e) {
      console.error(`  [FAIL] ${pkgName}: ${e.message}`);
    }
  }

  // Recurse into transitive dependencies
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
      console.warn(`  [WARN] parse ${pkgJson}: ${e.message}`);
    }
  }
}

const uiPkg = JSON.parse(fs.readFileSync(uiPkgJson, 'utf8'));
const directDeps = Object.keys(uiPkg.dependencies || {});

console.log(`UI direct dependencies: ${directDeps.length}`);
console.log(`Root node_modules: ${rootNM}`);
console.log(`UI node_modules: ${uiNM}`);
console.log('');

for (const dep of directDeps) {
  copyPackage(dep);
}

console.log(`\nDone. Copied ${copied}, already present ${existed}.`);
