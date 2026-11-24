#!/usr/bin/env python3
"""Check source integrity, local import portability and the published catalogue."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "education/scripts"))
import education_resources as education


def public_paths():
    """Apply Git's ignore rules without modifying or initialising this checkout."""
    git = shutil.which("git")
    if git is None:
        return None
    with tempfile.TemporaryDirectory(prefix="icareonto-file-scope-") as temporary:
        probe = Path(temporary) / "probe"
        subprocess.run([git, "-c", "init.defaultBranch=main", "init", "--quiet", str(probe)], check=True, capture_output=True)
        content = subprocess.check_output([git, "--git-dir=" + str(probe / ".git"), "--work-tree=" + str(ROOT),
                                           "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    return [ROOT / name for name in content.decode().split("\0") if name and Path(name).name != "CONTRIBUTING.md" and ".git" not in Path(name).parts]


def check_publication():
    checks = []
    def require(condition, message):
        if not condition:
            raise ValueError(message)
        checks.append(message)
    manifest = json.loads((ROOT / "sources/manifest.json").read_text())
    for name, details in manifest["files"].items():
        path = (ROOT / "sources" / name).resolve()
        require(path.is_relative_to(ROOT / "sources") and path.is_file(), "Source exists: " + name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == details["sha256"], "Source hash matches: " + name)
    for name in ("LICENSE.md", "LICENSES/CC-BY-4.0.txt", "LICENSES/MIT.txt", "THIRD_PARTY_NOTICES.md"):
        require((ROOT / name).is_file() and (ROOT / name).stat().st_size > 100, "Licence document present: " + name)
    scope = (ROOT / "LICENSE.md").read_text()
    require("CC BY 4.0" in scope and "MIT" in scope and "Third-party" in scope, "Split licence scope and exclusions documented")
    mit = (ROOT / "LICENSES/MIT.txt").read_text()
    require("Copyright (c) 2026 Robert Gordon University and contributing MAYA consortium partners, for their respective contributions." in mit
            and "<year>" not in mit and "<copyright holders>" not in mit,
            "MIT copyright attribution completed")
    require("Developed by Robert Gordon University, with contributions from MAYA consortium partners." in scope,
            "Contributor acknowledgement is separate from copyright notice")
    ontology = Graph().parse(ROOT / "serialisation/icareonto.ttl", format="turtle")
    require((URIRef("https://w3id.org/icareonto/"), DCTERMS.license,
             URIRef("https://creativecommons.org/licenses/by/4.0/")) in ontology, "Ontology licence is machine-readable")
    catalogues = [ROOT / "serialisation/catalog-v001.xml", ROOT / "validation/catalog-v001.xml", ROOT / "validation/cq-tests/catalog-v001.xml", ROOT / "education/examples/demo/catalog-v001.xml"]
    data = ROOT / "education/data/catalogue"
    catalogue = education.load_release(data)
    catalogues.append(Path(catalogue["release_directory"]) / "catalog-v001.xml")
    require(len(list((data / "releases").iterdir())) == 1, "One reviewed catalogue release is distributed")
    rows, _ = education.worksheet_records(education.DEFAULT_WORKBOOK, "Release resources")
    eligible = {r["Resource ID"] for r in rows if r.get("Curation status", "").casefold() == "approved" and r.get("Completion status", "").casefold() == "complete"}
    require({r["id"] for r in catalogue["records"]} == eligible, "Catalogue matches all currently approved and complete source entries")
    for path in catalogues:
        for entry in ET.parse(path).getroot():
            target = (path.parent / entry.attrib["uri"]).resolve()
            require(target.is_relative_to(ROOT) and target.is_file(), "Portable import: " + entry.attrib["name"])
    paths = public_paths()
    literal_home = re.compile(r"(?<![\w:/])/(?:Users|home)/[A-Za-z0-9_.-]+/|\b[A-Za-z]:\\Users\\[A-Za-z0-9_. -]+\\")
    for path in paths or []:
        require(not path.is_symlink(), "Self-contained file: " + str(path.relative_to(ROOT)))
        if path.suffix in (".py", ".md", ".json", ".xml", ".tsv"):
            text = path.read_text()
            require(not literal_home.search(text), "No literal user-home path: " + str(path.relative_to(ROOT)))
    return {"status": "PASS", "checks": len(checks), "catalogue_resources": len(catalogue["records"]),
            "scope": "Release-source hashes, required import paths and packaged catalogue; local ignored runs are excluded.",
            "public_file_audit": "PASS" if paths is not None else "NOT_RUN: Git is unavailable; source and import checks still ran",
            "licence_status": "CC-BY-4.0 for original ontology/content; MIT for supporting software; third-party terms retained"}


if __name__ == "__main__":
    report = check_publication()
    folder = ROOT / "validation/reports"; folder.mkdir(exist_ok=True)
    (folder / "publication-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
