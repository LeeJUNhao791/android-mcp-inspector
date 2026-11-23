"""Generate the README's synthetic APK and candidate AARs."""

import argparse
import json
import struct
import sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/apk-page-size-check/tests"))
from test_cli import ARM, elf
sys.path.pop(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="New directory for the synthetic archives")
    output = parser.parse_args().output_dir
    if output.exists():
        parser.error(f"choose a new output directory: {output}")
    output.mkdir(parents=True)

    payload = elf(alignment=4096)
    manifest_entry = ZipInfo("AndroidManifest.xml")
    manifest_payload = b"synthetic trial manifest"
    with ZipFile(output / "trial.apk", "w") as apk:
        apk.writestr(manifest_entry, manifest_payload)
        native = ZipInfo(ARM)
        # Include the local header and extra-field header when padding the stored entry.
        data_start = apk.fp.tell() + 30 + len(ARM.encode("utf-8")) + 4
        padding = -data_start % 16384
        native.extra = struct.pack("<HH", 0xCAFE, padding) + bytes(padding)
        apk.writestr(native, payload)

    aar_entry = "jni/" + ARM.removeprefix("lib/")
    artifacts = []
    for name, data in (("device", payload), ("decoy", elf())):
        filename = f"{name}.aar"
        with ZipFile(output / filename, "w") as aar:
            aar.writestr(ZipInfo("AndroidManifest.xml"), manifest_payload)
            aar.writestr(ZipInfo(aar_entry), data)
        artifacts.append({"coordinate": f"example:{name}-native:1", "path": filename})

    manifest = {"consumer_configuration": ":app:trialDebugRuntimeClasspath", "artifacts": artifacts}
    (output / "aar-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
