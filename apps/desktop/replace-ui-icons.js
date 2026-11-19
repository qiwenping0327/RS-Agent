const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const SRC_DARK = path.join(__dirname, 'assets/logo-dark-1024.png');
const SRC_LIGHT = path.join(__dirname, 'assets/logo-light-1024.png');
const DEST_DIR = path.join(__dirname, 'temp-ui/dist');

async function main() {
  await sharp(SRC_DARK).resize(128, 128, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(path.join(DEST_DIR, 'logo-128.png'));
  console.log('Created: logo-128.png');
  
  await sharp(SRC_DARK).resize(256, 256, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(path.join(DEST_DIR, 'logo-256.png'));
  console.log('Created: logo-256.png');
  
  await sharp(SRC_DARK).resize(32, 32, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(path.join(DEST_DIR, 'favicon.png'));
  console.log('Created: favicon.png');
  
  await sharp(SRC_DARK).resize(16, 16, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(path.join(DEST_DIR, 'icons/favicon-16x16.png'));
  console.log('Created: favicon-16x16.png');
  
  await sharp(SRC_DARK).resize(32, 32, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(path.join(DEST_DIR, 'icons/favicon-32x32.png'));
  console.log('Created: favicon-32x32.png');
  
  console.log('\n✅ All UI icons replaced!');
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});