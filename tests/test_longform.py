import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.longform import prototype as lf

def test_longform_prototype():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    topic = "Test topic for long-form prototype"
    brief = lf.research_brief(topic, [{"ref": "user-provided", "note": "test source"}])
    assert brief["topic"] == topic
    script = lf.make_script(topic, brief, target_duration=10)
    assert script["duration"] == 10
    audio = str(ROOT / "data" / "work" / "lf_audio.wav")
    os.makedirs(os.path.dirname(audio), exist_ok=True)
    lf.generate_narration(script["script"], audio, cfg)
    assert os.path.exists(audio)
    out = str(ROOT / "data" / "output" / "longform_prototype_test.mp4")
    lf.render_longform(script, audio, out, cfg, str(ROOT / "data" / "work" / "lf"))
    assert os.path.exists(out)
    # ffprobe
    import subprocess, json
    r = subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,width,height","-of","json", out], capture_output=True, text=True)
    info = json.loads(r.stdout)
    vs = [s for s in info["streams"] if s["codec_type"]=="video"]
    assert vs and vs[0]["width"]==1080 and vs[0]["height"]==1920
    print("long-form prototype OK:", out)

if __name__ == "__main__":
    test_longform_prototype()
    print("LONGFORM PROTOTYPE TEST PASS")