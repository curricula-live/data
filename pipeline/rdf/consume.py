"""Validate and materialize the Curricula RDF release without database dependencies."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import urlopen
from rdflib import Dataset, Graph, URIRef

ORIGIN = "https://raw.githubusercontent.com/curricula-live/ontology-formal-sciences"
GRAPH = "https://curricula.live/id/formal-sciences/graph/"
FILES = {"formal-sciences.ttl","formal-sciences.nq","formal-sciences.trig",
         "source-alignments.trig","validation-report.json"}


def verify(directory):
    manifest = json.loads((directory/"manifest.json").read_text())
    if manifest.get("contract")!="curricula.rdf-release/v1" or manifest["conforms"] is not True:
        raise ValueError("Expected conforming v1 release")
    if set(manifest["artifacts"])!=FILES:
        raise ValueError("Unexpected artifact inventory")
    for name,digest in manifest["artifacts"].items():
        with (directory/name).open("rb") as src:
            if hashlib.file_digest(src,"sha256").hexdigest()!=digest:
                raise ValueError("Checksum mismatch: "+name)
    report=json.loads((directory/"validation-report.json").read_text())
    if report.get("conforms") is not True or report.get("findings")!=[]:
        raise ValueError("Validation report contains findings")
    ds=Dataset()
    ds.parse(directory/"formal-sciences.nq",format="nquads")
    tri=Dataset()
    tri.parse(directory/"formal-sciences.trig",format="trig")
    if set(ds.quads())!=set(tri.quads()):
        raise ValueError("Named datasets disagree")
    if set(ds.graph(URIRef(GRAPH+"asserted")))!=set(Graph().parse(directory/"formal-sciences.ttl")):
        raise ValueError("Asserted graph disagrees with Turtle")
    mappings=Dataset()
    mappings.parse(directory/"source-alignments.trig",format="trig")
    if set(mappings.quads())!=set(ds.quads((None,None,None,URIRef(GRAPH+"alignments")))):
        raise ValueError("Mappings disagree")
    if {str(ctx.identifier) for ctx in ds.contexts() if len(ctx)}!={GRAPH+k for k in manifest["counts"]}:
        raise ValueError("Graph roster mismatch")
    for key,count in manifest["counts"].items():
        if len(ds.graph(URIRef(GRAPH+key)))!=count:
            raise ValueError("Incorrect graph count: "+key)
    return manifest


def materialize(commit,directory,pin=None):
    if not re.fullmatch("[a-f0-9]{40}",commit):
        raise ValueError("Expected immutable upstream commit")
    directory.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent) as tmp:
        part=Path(tmp)
        for name in sorted(FILES|{"manifest.json"}):
            with urlopen(f"{ORIGIN}/{commit}/dist/{name}",timeout=90) as src, (part/name).open("wb") as out:
                shutil.copyfileobj(src,out)
        digest=hashlib.sha256((part/"manifest.json").read_bytes()).hexdigest()
        if pin and pin!=digest:
            raise ValueError("Manifest mismatch against receipt")
        manifest=verify(part)
        if directory.exists():
            if (directory/"manifest.json").read_bytes()!=(part/"manifest.json").read_bytes():
                raise ValueError("Destination contains another release")
            verify(directory)
        else:
            part.rename(directory)
        return dict(contract=manifest["contract"],repository="curricula-live/ontology-formal-sciences",
                    commit=commit,manifest_sha256=digest)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="cmd",required=True)
    check=sub.add_parser("verify")
    check.add_argument("directory",type=Path)
    pull=sub.add_parser("fetch")
    group=pull.add_mutually_exclusive_group(required=True)
    group.add_argument("--commit")
    group.add_argument("--receipt",type=Path)
    pull.add_argument("directory",type=Path)
    args=parser.parse_args()
    if args.cmd=="verify":
        print(json.dumps(verify(args.directory)["counts"]))
    else:
        receipt=json.loads(args.receipt.read_text()) if args.receipt else {}
        print(json.dumps(materialize(args.commit or receipt["commit"],args.directory,receipt.get("manifest_sha256")),indent=2))
