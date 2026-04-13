import { NextRequest, NextResponse } from "next/server";
import path from "node:path";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// This route spawns the Python briefing-agent as a child process. That only
// works in local dev where the creative-generator tree is on disk. In deployed
// environments (Vercel) we return a 503 with a helpful message instead of
// crashing — the regenerate button is hidden in the UI via a feature flag so
// this is a defense-in-depth guard only.
const LOCAL_SKILLS_ENABLED =
  process.env.ENABLE_LOCAL_SKILLS === "true" ||
  process.env.NEXT_PUBLIC_ENABLE_LOCAL_SKILLS === "true";

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

  if (!LOCAL_SKILLS_ENABLED) {
    return NextResponse.json(
      {
        error:
          "Regenerate is only available in local development. Trigger the briefing-agent from Claude Code instead: `python3 .claude/skills/briefing-agent/scripts/main.py <creative_id>`",
      },
      { status: 503 }
    );
  }

  // Lazy import so deployed bundles don't try to resolve node:child_process
  // when the feature is disabled.
  const { execFile } = await import("node:child_process");
  const { promisify } = await import("node:util");
  const execFileAsync = promisify(execFile);

  const PROJECT_ROOT = path.resolve(process.cwd(), "..");
  const CREATIVE_GEN_DIR = path.join(PROJECT_ROOT, "creative generator");
  const BRIEFING_AGENT = path.join(
    CREATIVE_GEN_DIR,
    ".claude/skills/briefing-agent/scripts/main.py"
  );

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
