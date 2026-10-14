"""Send the 10 fictional inquiries to your +inquiries address so the pipeline has something to read.

Run: python tests/send_samples.py [--confirm]
The address comes from "inquiry_address" in config.json. Without --confirm it only lists what it would send.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from common import load_config, load_env, require_env  # noqa: E402
from google_api import Google  # noqa: E402

if __name__ == "__main__":
    to = load_config()["inquiry_address"]
    if "YOUR_ADDRESS" in to:
        sys.exit('Set "inquiry_address" in config.json to your own +inquiries address first.')
    samples = json.loads((ROOT / "tests" / "samples" / "inquiries.json").read_text(encoding="utf-8"))
    if "--confirm" not in sys.argv:
        for i, s in enumerate(samples, 1):
            print(f"{i}. {s['subject']}")
        print(f"\nWould send {len(samples)} emails to {to}. Re-run with --confirm.")
        sys.exit(0)
    load_env()
    require_env("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
    g = Google()
    for s in samples:
        g.send_email(to, s["subject"], s["body"])
        print("sent:", s["subject"])
