"""Beat synchronization helpers."""
def snap_to_beat(t, beats, max_snap=0.25):
    """Snap time t to nearest beat if within max_snap seconds."""
    if not beats:
        return t
    nearest = min(beats, key=lambda b: abs(b - t))
    if abs(nearest - t) <= max_snap:
        return round(float(nearest), 3)
    return round(float(t), 3)

def sync_zooms(zooms, beats):
    out = []
    for z in zooms:
        nz = dict(z)
        nz["start"] = snap_to_beat(z["start"], beats)
        nz["end"] = snap_to_beat(z["end"], beats)
        if nz["end"] <= nz["start"]:
            nz["end"] = nz["start"] + 0.5
        out.append(nz)
    return out
