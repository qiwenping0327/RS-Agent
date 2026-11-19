const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const { default: pngToIco } = require('png-to-ico');

const SRC_DARK = path.join(__dirname, '../assets/logo-dark-1024.png');
const SRC_LIGHT = path.join(__dirname, '../assets/logo-light-1024.png');
const OUT_ICO = path.join(__dirname, '../resources/icon.ico');
const OUT_ICNS = path.join(__dirname, '../resources/icon.icns');
const OUT_DARK = path.join(__dirname, '../assets/logo-dark.png');
const OUT_LIGHT = path.join(__dirname, '../assets/logo-light.png');

async function generateIco() {
  console.log('Generating icon.ico...');
  
  const tmpDir = path.join(__dirname, '../resources/icon-tmp');
  if (fs.existsSync(tmpDir)) {
    fs.rmSync(tmpDir, { recursive: true });
  }
  fs.mkdirSync(tmpDir, { recursive: true });
  
  const sizes = [256, 128, 64, 48, 32, 16];
  const pngFiles = [];
  
  for (const size of sizes) {
    const pngFile = path.join(tmpDir, `icon_${size}.png`);
    await sharp(SRC_DARK)
      .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png()
      .toFile(pngFile);
    pngFiles.push(pngFile);
    console.log(`  Created: icon_${size}.png`);
  }
  
  const ico = await pngToIco(pngFiles);
  fs.writeFileSync(OUT_ICO, ico);
  
  fs.rmSync(tmpDir, { recursive: true });
  console.log(`  Created: ${OUT_ICO}`);
}

async function generateIcns() {
  console.log('Generating icon.icns...');
  const iconSetDir = path.join(__dirname, '../resources/icon.iconset');
  
  if (fs.existsSync(iconSetDir)) {
    fs.rmSync(iconSetDir, { recursive: true });
  }
  fs.mkdirSync(iconSetDir, { recursive: true });
  
  const sizes = [
    { size: 16, name: 'icon_16x16.png' },
    { size: 32, name: 'icon_16x16@2x.png' },
    { size: 32, name: 'icon_32x32.png' },
    { size: 64, name: 'icon_32x32@2x.png' },
    { size: 128, name: 'icon_128x128.png' },
    { size: 256, name: 'icon_128x128@2x.png' },
    { size: 256, name: 'icon_256x256.png' },
    { size: 512, name: 'icon_256x256@2x.png' },
    { size: 512, name: 'icon_512x512.png' },
    { size: 1024, name: 'icon_512x512@2x.png' },
  ];
  
  for (const { size, name } of sizes) {
    await sharp(SRC_DARK)
      .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png()
      .toFile(path.join(iconSetDir, name));
    console.log(`  Created: ${name}`);
  }
  
  const icns = createIcns(iconSetDir);
  fs.writeFileSync(OUT_ICNS, icns);
  fs.rmSync(iconSetDir, { recursive: true });
  console.log(`  Created: ${OUT_ICNS}`);
}

function createIcns(iconSetDir) {
  const entries = [
    { name: 'icon_16x16.png', type: 'icp4' },
    { name: 'icon_16x16@2x.png', type: 'ic11' },
    { name: 'icon_32x32.png', type: 'icp5' },
    { name: 'icon_32x32@2x.png', type: 'ic12' },
    { name: 'icon_128x128.png', type: 'icp6' },
    { name: 'icon_128x128@2x.png', type: 'ic13' },
    { name: 'icon_256x256.png', type: 'ic07' },
    { name: 'icon_256x256@2x.png', type: 'ic14' },
    { name: 'icon_512x512.png', type: 'ic08' },
    { name: 'icon_512x512@2x.png', type: 'ic15' },
  ];
  
  const header = Buffer.alloc(8);
  header.write('icns', 0, 'ascii');
  header.writeUInt32BE(8, 4);
  
  const parts = [header];
  let totalSize = 8;
  
  for (const { name, type } of entries) {
    const filePath = path.join(iconSetDir, name);
    if (!fs.existsSync(filePath)) continue;
    
    const data = fs.readFileSync(filePath);
    const partHeader = Buffer.alloc(8);
    partHeader.write(type, 0, 'ascii');
    partHeader.writeUInt32BE(8 + data.length, 4);
    
    parts.push(partHeader);
    parts.push(data);
    totalSize += 8 + data.length;
  }
  
  header.writeUInt32BE(totalSize, 4);
  return Buffer.concat(parts);
}

async function generateTrayIcons() {
  console.log('Generating tray icons...');
  
  await sharp(SRC_DARK)
    .resize(256, 256, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toFile(OUT_DARK);
  console.log(`  Created: ${OUT_DARK}`);
  
  await sharp(SRC_LIGHT)
    .resize(256, 256, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toFile(OUT_LIGHT);
  console.log(`  Created: ${OUT_LIGHT}`);
}

async function main() {
  try {
    await generateIco();
    await generateIcns();
    await generateTrayIcons();
    console.log('\n✅ All icons generated successfully!');
  } catch (err) {
    console.error('\n❌ Error generating icons:', err.message);
    console.error(err.stack);
    process.exit(1);
  }
}

main();