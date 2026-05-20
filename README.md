# PhishCoach

**An adaptive phishing detection trainer for students.** Three LLM agents work together to teach humans to spot phishing through personalized, evolving attacks — and a per-learner weakness model that makes the training stop being effective the moment attacks become predictable, so it can't be.

> ⚠️ **Educational research artifact.** This is a security-awareness training prototype. It generates simulated phishing artifacts for use against a consenting human learner inside a sandboxed UI. It is not a jailbreak toolkit, not a generator of attacks against production systems, and not a substitute for an organization's security program. See [Safety & Scope](#safety--scope) below.

---

## Why this exists

Static phishing training (commercial platforms ship pre-written template libraries) plateaus as soon as learners pattern-match the templates. Detection rates flatline; the training stops teaching anything.

LLMs unlock something static templates can't: **novel attacks generated on-demand, targeted to a specific learner's demonstrated blind spots.** The system stops being effective the moment its attacks become predictable — so it has to keep evolving. That pressure is the pedagogy.

## How it works

Three agents, one loop:

```
              ┌──────────────┐
              │ Orchestrator │  (LangGraph StateGraph)
              └──────┬───────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
  ┌─────────┐  ┌──────────┐  ┌─────────┐
  │ Phishing│  │  Student │  │  Coach  │
  │ Author  │  │  (human) │  │         │
  └─────────┘  └──────────┘  └─────────┘
       ▲                          │
       └── weakness model ◄───────┘
```

- **Phishing Author** (Claude Sonnet 4.6) generates a phishing artifact — email, SMS, fake login page, OAuth consent screen — targeted to the learner's stated persona and known blind spots.
- **Student** (the human user) judges the artifact as phish or legit and explains their reasoning.
- **Coach** (Claude Opus 4.7) audits the student's reasoning, highlights the tells they missed, and updates a per-learner weakness model that quietly steers the next round's attack toward their weakest categories.

Orchestrated as a LangGraph `StateGraph` with conditional edges for the adaptive loop and human-in-the-loop interrupts for student input.

## Attack categories (v1 target: 5-6)

- **Authority impersonation** — Dean's Office, IT Help Desk, employer, parent/guardian
- **Urgency + scarcity** — account deletion, scholarship deadlines, expiring offers
- **Pretexting** — plausible context built from public-feeling details
- **Lookalike domains** — homoglyphs, typosquats, subdomain abuse
- **OAuth / consent phishing** — "sign in with Google to view" leading to scope grant
- **Trust-stack abuse** — real Google Docs / Notion links containing the actual phish
- **(Stretch)** Smishing / vishing transcripts, MFA fatigue scenarios

Each is a tag the Coach uses to track which categories a given learner reliably catches vs. misses.

## Pedagogical layer

After each round, the Coach surfaces four things:

1. **The tells** — the specific tokens in the artifact that should have flagged it (highlighted in the UI)
2. **Reasoning audit** — what the learner's explanation got right, what was weak (e.g. "you said 'the logo looked official' — logos are trivial to copy; stronger signals are X")
3. **The running pattern** — the per-learner weakness map across all rounds in the session
4. **Transfer tests** — periodic combined-category attacks to probe whether learning generalizes

This is the layer that makes the project educational rather than a tech demo.

## Stack

| Concern              | Choice                                                                 |
|----------------------|------------------------------------------------------------------------|
| Orchestration        | [LangGraph](https://langchain-ai.github.io/langgraph/) (StateGraph)   |
| Models               | Anthropic Claude — Sonnet 4.6 (Author), Opus 4.7 (Coach + Judge)      |
| State / checkpoints  | LangGraph SQLite checkpointer locally, Postgres if deployed           |
| Schemas              | Pydantic everywhere (graph state, agent I/O, scenarios)               |
| Observability        | Langfuse — provider-agnostic; decided in Weekend 1                    |
| UI                   | Streamlit, three-pane (artifact \| reasoning \| coach feedback)        |
| Deploy               | Fly.io or Railway                                                      |

Anthropic-only for simplicity at this project size. Prompt caching on the Coach's stable system prompt + learner weakness model — highest-leverage cost optimization, turned on in Weekend 2.

## Evaluation

The headline number lives in a cohort study, not synthetic benchmarks.

- **Sample:** 10-15 testers, mixed technical / non-technical
- **Protocol:** 30-min session per tester, pre/post detection-rate measurement, 1-week follow-up retention test
- **Primary metric:** detection rate before vs. after (target: meaningful delta on a held-out test set)
- **Secondary metrics:**
  - Category coverage — does improvement generalize across attack types?
  - Calibration — when learners are confident, are they actually right?
  - Adaptive validation — does the Author measurably exploit the categories the Coach has tagged as weak?

LLM-judge eval (Claude Opus) is used to grade artifact quality and coach analysis depth, with human spot-checks on a 100-sample subset to compute Cohen's kappa. Boring but it's the bit that makes the eval credible.

## Repo layout

```
src/phishcoach/
  agents/          # Author, Coach, Judge agent definitions
  graph/           # LangGraph StateGraph wiring + checkpointing
  schemas/         # Pydantic models — Scenario, ArtifactGen, etc.
  mcp_servers/     # Lookalike Asset, Pretext Context, Progress
  prompts/         # System prompts per agent
tests/             # Unit + golden-set tests
evals/             # Eval harness, cohort study scripts, results
docs/              # Threat model, safety policy, study protocol
```

## Status

🚧 In active build — 3-weekend ship target. **Weekend 1 in progress.**

- [~] Weekend 1 — LangGraph core loop, 3 attack categories, CLI runner, schemas locked
- [ ] Weekend 2 — adaptive Author prompting, Streamlit UI, prompt caching, eval harness, more attack categories
- [ ] Weekend 3 — Cohort study (n=14), Fly.io / Railway deploy, README v2 with results, blog post

### Weekend 1 progress

The end-to-end loop, CLI-driven, with the author as the test learner. Three
attack categories in scope this weekend: authority impersonation, urgency +
scarcity, lookalike domains.

- ✅ Locked Pydantic schemas — persona, weakness model, artifacts, coach analysis
- ✅ Author and Coach system prompts — Author safety guardrails baked in (no real
  entities, reserved `.example` namespace, persona treated as untrusted input)
- ✅ LangGraph `StateGraph` — Author → Student → Coach loop with a human-in-the-loop
  interrupt before student input; local SQLite checkpointer
- ✅ Author node — Anthropic tool-use for structured output; deterministic category
  targeting driven by the weakness model
- ⬜ Coach node + deterministic weakness-model reducer
- ⬜ CLI driver — interrupt handling, artifact rendering, response capture
- ⬜ Langfuse tracing · tests · `make demo` target

The weakness model is updated by a deterministic reducer, never regenerated by an
LLM — so the per-learner skill map can't silently drift.

## Safety & Scope

This project generates realistic phishing artifacts. That power is the point — static templates don't teach. But it means the boundaries have to be tight:

- **No real organizations.** All sender domains, brands, and contexts use reserved/fictional namespaces (`*.school-sim.example` or an owned testing domain). No real bank, school, or company is impersonated.
- **No real people.** Personas are role-played by the learner ("I'm a CS major at a fictional university") — never ingested as real identity.
- **No PII collection.** Learner profiles are session-scoped fictions; nothing leaves the local DB.
- **No artifact export.** Generated phish stays inside the simulator UI. Copy / share is disabled.
- **Minors.** Default to the 16+ demographic for a portfolio prototype; younger learners require mediation flows this prototype does not implement.
- **Research framing.** This repo is a learning artifact for the author and a portfolio piece. It is not a security product, makes no claim of efficacy outside the cohort study reported in this README, and should not be deployed inside an organization's training program without the safeguards a real security-awareness vendor builds.

If you find a safety concern with the design or generated outputs, please open an issue.

## Acknowledgments

Inspired by the multi-agent debate / adversarial agent literature, Microsoft's *Spotlighting* paper (Hines et al.), Greshake et al.'s indirect-injection taxonomy, and the broader security-awareness training literature on why static template training underperforms over time.

## License

MIT — see [LICENSE](LICENSE).
