const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

let pythonCmd = isWin ? 'python' : 'python3';

const venvWin = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
const venvPosix = path.join(rootDir, '.venv', 'bin', 'python');

if (isWin && fs.existsSync(venvWin)) {
  pythonCmd = venvWin;
} else if (!isWin && fs.existsSync(venvPosix)) {
  pythonCmd = venvPosix;
}

const net = require('net');

function isPortAvailable(port, host) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', (err) => {
      resolve(false);
    });
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, host);
  });
}

async function main() {
  const port = parseInt(process.env.PORT || '8000', 10);
  const host = process.env.HOST || '127.0.0.1';

  let available = await isPortAvailable(port, host);
  if (!available) {
    console.log(`[BACKEND] Port ${port} is currently busy. Waiting 2 seconds for previous process to release...`);
    await new Promise((r) => setTimeout(r, 2000));
    available = await isPortAvailable(port, host);
  }

  const args = ['-m', 'uvicorn', 'backend.app.main:app', '--host', host, '--port', String(port), '--reload'];

  console.log(`[BACKEND] Starting FastAPI backend with ${pythonCmd} on http://${host}:${port}...`);

  const proc = spawn(pythonCmd, args, {
    cwd: rootDir,
    stdio: 'inherit',
    env: { ...process.env, PYTHONPATH: rootDir }
  });

  proc.on('exit', (code) => {
    process.exit(code || 0);
  });
}

main();
