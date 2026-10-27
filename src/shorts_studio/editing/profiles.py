"""Editing profiles with meaningful, distinct decisions."""
PROFILES = {
    "chaos": {
        "zoom_factor": 1.35, "contrast": 1.15, "sharpen": True,
        "caption_emphasis": True, "emphasis_color": (0, 200, 255),
        "sfx_density": "high", "cut_density": "high",
        "caption_size": 78, "music_mood": "hype",
        "transition": "hard_cut", "speed_ramp": "fast",
    },
    "wholesome": {
        "zoom_factor": 1.1, "contrast": 1.0, "sharpen": False,
        "caption_emphasis": False, "emphasis_color": (255, 255, 255),
        "sfx_density": "low", "cut_density": "low",
        "caption_size": 72, "music_mood": "soft",
        "transition": "fade", "speed_ramp": "none",
    },
    "aura": {
        "zoom_factor": 1.4, "contrast": 1.2, "sharpen": True,
        "caption_emphasis": True, "emphasis_color": (0, 255, 120),
        "sfx_density": "medium", "cut_density": "medium",
        "caption_size": 80, "music_mood": "epic",
        "transition": "zoom", "speed_ramp": "slowmo_payoff",
    },
    "dramatic": {
        "zoom_factor": 1.15, "contrast": 1.2, "sharpen": True,
        "caption_emphasis": True, "emphasis_color": (255, 80, 80),
        "sfx_density": "medium", "cut_density": "medium",
        "caption_size": 74, "music_mood": "tense",
        "transition": "fade", "speed_ramp": "slowmo",
    },
    "gaming": {
        "zoom_factor": 1.3, "contrast": 1.12, "sharpen": True,
        "caption_emphasis": True, "emphasis_color": (255, 200, 0),
        "sfx_density": "high", "cut_density": "high",
        "caption_size": 76, "music_mood": "energetic",
        "transition": "hard_cut", "speed_ramp": "fast",
    },
}

EMPHASIS_KEYWORDS = {
    "chaos": ["bro", "what", "no", "crazy", "insane", "💀", "😭"],
    "wholesome": ["love", "respect", "thank", "❤️", "😭"],
    "aura": ["w", "insane", "crazy", "🔥", "💀"],
    "dramatic": ["no", "wait", "stop", "why"],
    "gaming": ["win", "gg", "clutch", "insane"],
}

def get_profile(name):
    return PROFILES.get(name, PROFILES["chaos"])

def emphasis_words(profile, text):
    kws = EMPHASIS_KEYWORDS.get(profile, [])
    words = (text or "").split()
    return [w for w in words if w.strip(".,!?").lower() in [k.lower() for k in kws]]
