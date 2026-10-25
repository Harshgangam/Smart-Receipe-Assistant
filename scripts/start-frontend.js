const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.join(rootDir, 'frontend');

function checkBackendReady(port = 8000, host = '127.0.0.1', timeout = 8000) {
  const start = Date.now();
  return new Promise((resolve) => {
    function tryConnect() {
      const socket = new net.Socket();
      socket.setTimeout(500);
      socket.on('connect', () => {
        socket.destroy();
        resolve(true);
      });
      socket.on('error', () => {
        socket.destroy();
        if (Date.now() - start > timeout) {
          resolve(false);
        } else {
          setTimeout(tryConnect, 300);
        }
      });
      socket.on('timeout', () => {
        socket.destroy();
        if (Date.now() - start > timeout) {
          resolve(false);
        } else {
          setTimeout(tryConnect, 300);
        }
      });
      socket.connect(port, host);
    }
    tryConnect();
  });
}

async function main() {
  console.log('[FRONTEND] Syncing with FastAPI backend...');
  const ready = await checkBackendReady(8000, '127.0.0.1', 8000);
  if (ready) {
    console.log('[FRONTEND] Backend ready on port 8000. Starting Vite dev server...');
  } else {
    console.log('[FRONTEND] Starting Vite dev server...');
  }

  // Use single command string with shell: true for seamless Windows Node.js compatibility (prevents EINVAL)
  const proc = spawn('npm run dev', {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: true,
  });

  proc.on('exit', (code) => {
    process.exit(code || 0);
  });
}

main();
