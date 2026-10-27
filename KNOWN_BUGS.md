# KNOWN_BUGS

- Caption rendering uses cv2 (basic); no libass, so advanced ASS styling unavailable.
- Haar face tracking (basic, sparse); may miss faces or track wrong subject.
- Moment selection picks first high-scoring window; no semantic selection yet.
- Beat detection implemented; zoom sync applied, but beat-synced cuts not in renderer.
- Music/SFX mixer wired and tested with synthetic assets only (no licensed music).
- Title generation is filename-based.
- av pin (12.3.0) in requirements.txt; check-deps verifies version.
- No thumbnails auto in cmd_run? Actually integrated; verify path.
- Caption word emphasis keyword-based, not semantic.
- ~2 min render for 22s/60fps source.
- No YouTube publishing (no credentials).
- Clipping detected on most sources (stream audio loud); handled by normalization.