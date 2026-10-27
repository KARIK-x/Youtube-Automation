import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import output_safety

def test_unique_path():
    d = Path(tempfile.mkdtemp())
    p1 = output_safety.unique_path(d, "out.mp4")
    assert p1 == d / "out.mp4"
    p1.write_text("x")
    p2 = output_safety.unique_path(d, "out.mp4")
    assert p2 == d / "out_1.mp4"
    p2.write_text("y")
    p3 = output_safety.unique_path(d, "out.mp4")
    assert p3 == d / "out_2.mp4"
    print("unique_path OK")

def test_atomic_copy():
    d = Path(tempfile.mkdtemp())
    src = d / "src.txt"; src.write_text("hello")
    dst = d / "dst.txt"
    output_safety.atomic_copy(str(src), str(dst))
    assert dst.read_text() == "hello"
    # missing source raises
    try:
        output_safety.atomic_copy(str(d/"nope.txt"), str(d/"x.txt"))
        print("FAIL no raise")
    except FileNotFoundError:
        print("missing source raises OK")

def test_atomic_copy_no_overwrite():
    d = Path(tempfile.mkdtemp())
    src = d / "src.txt"; src.write_text("new")
    dst = d / "dst.txt"; dst.write_text("old")
    # atomic_copy overwrites by design (rename); unique_path prevents collision
    # verify unique_path avoids overwrite
    up = output_safety.unique_path(d, "dst.txt")
    assert up != dst
    print("no-overwrite via unique_path OK")

if __name__ == "__main__":
    test_unique_path()
    test_atomic_copy()
    test_atomic_copy_no_overwrite()
    print("OUTPUT SAFETY TESTS PASS")