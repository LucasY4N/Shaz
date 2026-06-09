const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('Starting Shaz OS Electron build process...');

const srcHtml = path.join(__dirname, '..', 'shaz-terminal.html');
const destHtml = path.join(__dirname, 'shaz-terminal.html');

// 1. Copy shaz-terminal.html to local directory
console.log('Copying shaz-terminal.html to electron directory...');
try {
  fs.copyFileSync(srcHtml, destHtml);
} catch (err) {
  console.error('Failed to copy shaz-terminal.html:', err.message);
  process.exit(1);
}

try {
  // 2. Check if icon exists
  const iconPath = path.join(__dirname, 'assets', 'icon.ico');
  const iconArg = fs.existsSync(iconPath) ? ' --icon=assets/icon.ico' : '';

  // 3. Run electron-packager
  console.log('Running electron-packager...');
  const cmd = `npx electron-packager . "Shaz OS" --platform=win32 --arch=x64 --out=dist --overwrite${iconArg}`;
  console.log('Command:', cmd);
  execSync(cmd, {
    stdio: 'inherit',
    cwd: __dirname
  });
  console.log('Build completed successfully!');
} catch (error) {
  console.error('Error during build:', error.message);
  process.exit(1);
} finally {
  // 4. Clean up copied HTML file
  if (fs.existsSync(destHtml)) {
    console.log('Cleaning up temporary shaz-terminal.html...');
    fs.unlinkSync(destHtml);
  }
}
