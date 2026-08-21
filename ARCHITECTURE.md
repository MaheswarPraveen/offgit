# offGIT — System Architecture & Specification

## 1. Architectural Philosophy

1. **Unified Core Engine**: Core orchestration (`get_diff`, `summarize_with_llm`, `write_devlog`, `update_context_md`, `commit_and_push`, `maybe_scaffold_repo`) resides entirely within `sync_engine.py`. IDE hooks and filesystem watchers function strictly as lightweight trigger interfaces.
2. **Deterministic Source of Truth**: The unified Git diff (`git diff HEAD`) serves as the definitive source of truth for all code modifications. Interaction logs serve exclusively as contextual enrichment.
3. **Decoupled Performance Model**: Interactive prompt logging and local context writes occur in memory and local storage (< 1ms). Remote network roundtrips and Git commit operations are batched onto a periodic 10-minute cadence.
4. **Frictionless Cross-Tool Handoff**: Tool transitions are handled passively. By leveraging native IDE configuration files pointing to `CONTEXT.md`, any incoming tool ingests active state on session startup without specialized inter-process communication.

---

## 2. Data Flow Architecture

```
[Developer & AI Interaction]
         │
         ▼ (Instant Local Write < 1ms)
[.offgit/prompt-log.jsonl] ───► [CONTEXT.md]
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         │                                                       │
         ▼ (10-Minute Batch Loop)                                ▼ (Inception Check: 5, 15, 30, 60)
[sync_engine.py]                                        [prompt_counter.py]
  ├── Evaluates git diff HEAD                             ├── Evaluates prompt count
  ├── Invokes Headless LLM Summarizer                     ├── Prompts for Repository Name
  ├── Appends to DEVLOG.md                                └── Executes gh repo create
  ├── Overwrites CONTEXT.md                                    & Scaffolding
  └── Commits & Pushes to Remote
```

---

## 3. Component Reference

| Module | Primary Responsibility |
| :--- | :--- |
| `sync_engine.py` | Orchestrates diff extraction, LLM summarization, devlog generation, context snapshots, and Git operations. |
| `prompt_counter.py` | Handles prompt telemetry logging, local context updates, and milestone inception gates. |
| `debounce_trigger.py` | Provides debouncing logic for high-frequency IDE file modification events. |
| `watcher.py` | Watchdog filesystem observer and host for the 10-minute batch synchronization loop. |
| `install_and_launch.py` | Automated dependency resolver and Windows Task Scheduler autostart registrar. |
| `config.yaml` | Centralized configuration for runtime thresholds, tool selection, and monitoring paths. |
