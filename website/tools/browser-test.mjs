// Own the exact Python process directly (no Windows shell/descendant teardown).
import { spawn } from "node:child_process";
import { once } from "node:events";
import { delimiter, resolve } from "node:path";

const env = { ...process.env, PYTHON_DOTENV_DISABLED: "1", RECORD_AUDIO: "false", FOODEASE_EVIDENCE_KIND: "offline_browser_fixture",
  FOODEASE_SESSION_API: "http://127.0.0.1:8186", HF_HUB_OFFLINE: "1", TRANSFORMERS_OFFLINE: "1",
  PYTHONPATH: ["tests", "src", "../voice-agent/src", "../contracts/src"].join(delimiter) };
for (const key of ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
                   "CARTESIA_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"]) delete env[key];
if (await fetch("http://127.0.0.1:8186/healthz").then(() => true, () => false)) {
  throw new Error("Port 8186 is already in use; refusing to reuse an unknown test server.");
}
const python = resolve("../voice-agent/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const server = spawn(python, ["-m", "uvicorn", "browser_server:app", "--host", "127.0.0.1", "--port", "8186",
                              "--log-level", "warning"], { env, stdio: ["ignore", "inherit", "inherit"], windowsHide: true });
let exited = false;
server.once("exit", () => { exited = true; });
try {
  const deadline = Date.now() + 60000;
  while (!await fetch("http://127.0.0.1:8186/healthz").then((r) => r.ok, () => false)) {
    if (exited || Date.now() > deadline) throw new Error("The offline browser fixture did not start.");
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  const tests = spawn(process.execPath, ["node_modules/@playwright/test/cli.js", "test", ...process.argv.slice(2)],
    { env, stdio: "inherit", windowsHide: true });
  const [code] = await once(tests, "exit");
  process.exitCode = code ?? 1;
} finally {
  if (!exited) {
    const stopped = once(server, "exit");
    server.kill("SIGTERM");
    await stopped;
  }
}
