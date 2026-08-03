# Usage

Everyday BinaryPilot flows. See [`cli.md`](cli.md) for the full flag reference.

## Solve a challenge

```bash
binarypilot --challenge <name-or-url> [--platform flagyard|htb]
```

- URL infers the platform from the hostname (ctf.flagyard.com / app.hackthebox.com).
- Name uses the platform's search API; exact match or loud failure on ambiguity.

Names have to come through `--platform`:

```bash
binarypilot --challenge "Lame" --platform htb
binarypilot --challenge "Forensics 101" --platform flagyard
binarypilot --challenge "Blue" --platform htb
```

URLs don't:

```bash
binarypilot --challenge https://app.hackthebox.com/challenges/15
binarypilot --challenge https://app.hackthebox.com/machines/Lame
binarypilot --challenge https://ctf.flagyard.com/labs/12/challenges/34
```

Lab-only URL (FlagYard) starts the lab's default challenge — same flow with the first incomplete challenge in the lab.

## Steer the solve

`--instruction "short hint"` passes a free-text message to the root agent. Use it to bias the approach (categories to try first, creds you know, bypasses to skip).

`--instruction-file ./path/to/file.md` reads a longer play. Good for ROE scope or extended background on a challenge family.

## Scan modes as solve intensity

- `--scan-mode quick` — single solver agent, minimal delegation, first-obvious-vector priority. Use for easy challenges or CI.
- `--scan-mode standard` — small team per phase; the balanced default.
- `--scan-mode deep` — full tree, vector coverage, verification before submit. Use for hard challenges.

## Resume a run

The TUI prints a `--resume <run-name>` hint on exit. Pick up where a run left off — chat state, notes, todos, the artifacts already on disk:

```bash
binarypilot --resume 2026-08-03-lame
```

## Browser the results

```bash
binarypilot view               # latest run
binarypilot view lame-2026-08  # specific run
```

Local-only web UI at `127.0.0.1` on a random port with a tokened URL. Artifacts visible: writeups, run.json, vulnerabilities, agent transcript.

## Steer mid-run

Agents listen to `respond_to_user` — type at the TUI prompt or the web view. `wait_for_agents` parks when the dispatcher is working; `finish_scan`/`finish_solve` are the only ways the root agent ends the run.

## Batch jobs

```bash
binarypilot -n --challenge https://app.hackthebox.com/challenges/15
```

- No TUI, exits non-zero on failure (infra, budget, or unaccepted flag).
- stdout: progress + the final report.
- On-disk writeups still land in `binarypilot_runs/<run>/writeups/`.

For a list of challenges, shell out per challenge (no batch flag currently — the lazy shape), and tee the logs:

```bash
for url in challenge-a challenge-b challenge-c; do
  binarypilot -n --challenge "$url" 2>&1 | tee -a /var/log/binarypilot.log
done
```
