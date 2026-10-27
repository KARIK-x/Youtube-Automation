# SESSION_HANDOFF

## State
Working local Shorts pipeline verified. All tests pass.

## Next session priorities
1. Add beat detection (librosa) + beat-synced cuts/zooms.
2. Integrate licensed music library + ducking.
3. Implement candidate selection/scoring.
4. Port YouTube publishing adapter in dry-run mode.
5. Add thumbnail generation step.
6. Add caption word emphasis.

## Run commands
```
PYTHONPATH=src python3 -m shorts_studio.cli.main check-deps
PYTHONPATH=src python3 -m shorts_studio.cli.main run --profile chaos
PYTHONPATH=src python3 -m shorts_studio.cli.main qc data/output/<file>.mp4
```

## Credentials needed for publishing
Google Cloud project + OAuth client_secret.json (youtube.upload + youtube scopes), Pexels key for original mode.
