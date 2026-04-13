import { NextRequest, NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const CREATIVE_GEN_DIR = path.join(PROJECT_ROOT, "creative generator");
const BRIEFING_AGENT = path.join(
  CREATIVE_GEN_DIR,
  ".claude/skills/briefing-agent/scripts/main.py"
);

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request: NextRequest) {
  let body: { creative_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const creativeId = body.creative_id;
  if (!creativeId || !UUID_RE.test(creativeId)) {
    return NextResponse.json({ error: "Invalid creative_id" }, { status: 400 });
  }

  try {
    const { stdout, stderr } = await execFileAsync(
      "python3",
      [BRIEFING_AGENT, creativeId],
      { cwd: CREATIVE_GEN_DIR, timeout: 120_000 }
    );
    return NextResponse.json({ ok: true, stdout, stderr });
  } catch (err) {
    const e = err as { stdout?: string; stderr?: string; message?: string };
    return NextResponse.json(
      {
        error: e.stderr?.trim() || e.message || "briefing-agent failed",
        stdout: e.stdout,
      },
      { status: 500 }
    );
  }
}
