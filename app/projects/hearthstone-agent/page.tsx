import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Hearthstone Standard Agent | Ruiyuan",
  description:
    "A desktop Hearthstone Standard assistant with complete current card knowledge, authoritative legal-action tracking, and confidence-aware recommendations.",
  openGraph: {
    title: "Hearthstone Standard Agent",
    description:
      "A desktop Standard assistant with live public-state tracking and explainable recommendations.",
    images: [],
  },
  twitter: {
    card: "summary",
    title: "Hearthstone Standard Agent",
    description:
      "A desktop Standard assistant with live public-state tracking and explainable recommendations.",
    images: [],
  },
};

const capabilities = [
  "1,184 collectible cards across the seven current Standard sets in the validated snapshot",
  "Authoritative legal actions and targets parsed from Power.log OPTIONS packets",
  "Card names, text, cost, type, mechanics and Standard-set membership available to the advisor",
  "Visible one-step and multi-action lethal detection with an explainable action sequence",
  "Effect-aware scoring for damage, healing, draw, summon, buffs, removal, keywords and board pressure",
  "Confidence automatically reduced when a complex card effect is not fully structured",
  "Opponent hand identities hidden behind a public Observation interface",
  "Validated HearthstoneJSON refresh pipeline with rotation-review detection and a coverage report",
  "Top-most desktop chat overlay with read-only Power.log event tracking",
  "Installable desktop control center with explicit start, stop, reopen and exit controls",
  "Practice and friendly-match advice; ladder is restricted to tracking and post-game review",
  "Authentication provider boundary and visible sign-in/register placeholders for a future service",
];

const roadmap = [
  ["V0.1", "Playable research loop and desktop shell", "Complete"],
  ["V0.2", "Current Standard knowledge and authoritative live-action advisor", "Available now"],
  ["V0.3", "Replay evaluation and deeper per-card effect models", "Next"],
  ["V0.5", "Entity Transformer, Policy + Value and information-set search", "Planned"],
  ["V1.0", "Multiple classes, decks and patch-aware opponent modeling", "Goal"],
];

export default function HearthstoneAgentPage() {
  return (
    <main className="min-h-screen bg-[#f7f4ed] px-6 py-16 text-[#171714] sm:px-8 sm:py-20">
      <article className="mx-auto max-w-5xl">
        <Link
          href="/projects"
          className="text-sm font-medium text-stone-600 underline decoration-stone-300 underline-offset-4 hover:text-black"
        >
          ← All projects
        </Link>

        <header className="mt-10 border-b border-stone-300 pb-12">
          <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em]">
            <span className="rounded-full bg-[#171714] px-3 py-1.5 text-white">V0.2 live</span>
            <span className="text-stone-500">Desktop assistant · Game AI</span>
          </div>
          <h1 className="mt-6 max-w-4xl text-5xl font-bold tracking-[-0.04em] sm:text-7xl">
            Hearthstone
            <br />
            Standard Agent
          </h1>
          <p className="mt-7 max-w-3xl text-lg leading-8 text-stone-700 sm:text-xl">
            A desktop assistant that follows the public game state, reads the legal actions Hearthstone
            exposes to its client, and explains the strongest visible move without controlling the game.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <a
              href="https://github.com/nieruiyuanpdskd2007-commits/my-website/tree/main/projects/hearthstone-standard-agent"
              className="rounded-full bg-[#171714] px-6 py-3 text-sm font-semibold text-white hover:bg-stone-700"
            >
              View source on GitHub
            </a>
            <a
              href="#run"
              className="rounded-full border border-stone-400 px-6 py-3 text-sm font-semibold hover:bg-white"
            >
              Run it locally
            </a>
          </div>
        </header>

        <section className="grid border-b border-stone-300 py-10 sm:grid-cols-3">
          {[
            ["1,184", "collectible cards in the current seven-set Standard catalogue"],
            ["20", "regression tests covering live actions, privacy, data validation and game flow"],
            ["60.6%", "average structured-effect coverage; uncertainty remains visible"],
          ].map(([value, label]) => (
            <div key={label} className="border-stone-300 py-4 sm:border-l sm:px-6 first:sm:border-l-0 first:sm:pl-0">
              <p className="text-4xl font-bold tracking-tight">{value}</p>
              <p className="mt-2 max-w-xs text-sm leading-6 text-stone-600">{label}</p>
            </div>
          ))}
        </section>

        <section className="grid gap-10 border-b border-stone-300 py-14 md:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">The loop</p>
            <h2 className="mt-3 text-3xl font-bold">Legal moves come from the client, not guesswork.</h2>
          </div>
          <div className="grid gap-3">
            {["Validated Standard catalogue", "Public-state tracker", "Client legal actions", "Effect-aware scoring", "Lethal search", "Desktop overlay"].map(
              (step, index) => (
                <div key={step} className="flex items-center gap-4 rounded-xl border border-stone-300 bg-white/60 px-5 py-4">
                  <span className="font-mono text-xs text-stone-400">{String(index + 1).padStart(2, "0")}</span>
                  <span className="font-semibold">{step}</span>
                </div>
              ),
            )}
          </div>
        </section>

        <section className="grid gap-10 border-b border-stone-300 py-14 md:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">Implemented</p>
            <h2 className="mt-3 text-3xl font-bold">The V0.2 live-advice pipeline</h2>
          </div>
          <ul className="space-y-4 text-stone-700">
            {capabilities.map((capability) => (
              <li key={capability} className="flex gap-3 leading-7">
                <span aria-hidden="true" className="mt-1 font-bold text-black">✓</span>
                <span>{capability}</span>
              </li>
            ))}
          </ul>
        </section>

        <section id="run" className="border-b border-stone-300 py-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">Try it</p>
          <h2 className="mt-3 text-3xl font-bold">Run an automated match</h2>
          <div className="mt-7 overflow-x-auto rounded-2xl bg-[#171714] p-6 font-mono text-sm leading-7 text-stone-200">
            <code>
              git clone https://github.com/nieruiyuanpdskd2007-commits/my-website.git
              <br />
              cd my-website/projects/hearthstone-standard-agent
              <br />
              python3 main.py --agent-a rule --agent-b random --verbose
              <br />
              python3 desktop_main.py
              <br />
              python3 -m live.main --mode practice --demo
            </code>
          </div>
          <p className="mt-5 max-w-3xl leading-7 text-stone-600">
            The simulator and live parser are intentionally dependency-free. Generate JSONL training samples with
            <code className="mx-1 rounded bg-white px-1.5 py-0.5 text-sm">--replay</code>
            or run batch evaluation with
            <code className="mx-1 rounded bg-white px-1.5 py-0.5 text-sm">--games 100</code>.
          </p>
        </section>

        <section className="py-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">Roadmap</p>
          <div className="mt-6 divide-y divide-stone-300 border-y border-stone-300">
            {roadmap.map(([version, scope, status]) => (
              <div key={version} className="grid gap-2 py-5 sm:grid-cols-[5rem_1fr_7rem] sm:items-center">
                <span className="font-mono text-sm text-stone-500">{version}</span>
                <span className="font-semibold">{scope}</span>
                <span className="text-sm text-stone-500 sm:text-right">{status}</span>
              </div>
            ))}
          </div>
          <aside className="mt-8 rounded-2xl border border-amber-700/20 bg-amber-100/50 p-6 text-sm leading-7 text-amber-950">
            <strong>Accuracy boundary:</strong> V0.2 knows every card in the configured current Standard
            catalogue and uses the client&apos;s own action and target list for legality. Its strategic ranking
            is still an explainable estimate: structured-effect coverage currently averages 60.6%, and
            confidence is reduced for unmodeled complex text. The overlay never controls game input or reads
            hidden information; ladder mode deliberately disables in-match move recommendations.
          </aside>
        </section>
      </article>
    </main>
  );
}
