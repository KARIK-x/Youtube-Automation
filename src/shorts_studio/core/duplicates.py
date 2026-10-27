"""Duplicate detection: URL canonicalization, file hash, metadata similarity."""
import hashlib, os, json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def canonicalize_url(url):
    if not url:
        return None
    p = urlparse(url)
    # strip tracking params
    q = {k:v for k,v in parse_qs(p.query).items() if k not in ("utm_source","utm_medium","utm_campaign","si","feature")}
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", urlencode(q, doseq=True), ""))

def file_hash(path, chunk=65536):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def text_similarity(a, b):
    """Jaccard similarity on word sets."""
    if not a or not b:
        return 0.0
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def check_duplicate(candidate, existing, url_threshold=1.0, text_threshold=0.8, hash_threshold=1.0):
    """Return (is_dup: bool, reason: str, kind: exact|near|none)."""
    # exact URL
    cu = canonicalize_url(candidate.get("source_url"))
    for e in existing:
        if cu and canonicalize_url(e.get("source_url")) == cu:
            return True, "exact URL match", "exact"
    # file hash
    if candidate.get("file_hash"):
        for e in existing:
            if e.get("file_hash") == candidate["file_hash"]:
                return True, "exact file hash match", "exact"
    # near-duplicate by title similarity
    for e in existing:
        sim = text_similarity(candidate.get("topic",""), e.get("topic",""))
        if sim >= text_threshold:
            return True, f"high topic similarity ({sim:.2f})", "near"
    return False, "no duplicate", "none"
