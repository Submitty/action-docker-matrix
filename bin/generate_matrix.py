import json
import os
import subprocess
import sys
from pathlib import Path

if len(sys.argv) > 4:
    print("Too many arguments!", file=sys.stderr)
    exit(1)
elif len(sys.argv) < 2:
    print("Not enough arguments!", file=sys.argv)
    exit(1)

if not os.path.isdir("dockerfiles"):
    print("dockerfiles missing!", file=sys.stderr)
    exit(1)

username = sys.argv[1]

to_build = []

hash_before = sys.argv[2]
hash_after = sys.argv[3]

# Get list of all changed files between 2 commits
output = subprocess.check_output(["git", "--no-pager", "diff", "--name-only", "--diff-filter=d", hash_before, hash_after])
paths_updated = output.decode("utf-8").splitlines()

build_all = "UPDATE_ALL" in paths_updated

if not build_all:
    image_set = set()
    image_tag_set = set()

    for path in paths_updated:
        parts = Path(path).parts
        # Only rebuild if modified files were in dockerfiles
        if parts[0] != "dockerfiles":
            continue

        if len(parts) < 3:
            continue

        if not os.path.isdir(Path(parts[0], parts[1], parts[2])):
            continue

        if f"{parts[1]}:{parts[2]}" in image_tag_set:
            continue

        metadata = json.loads(open(Path(parts[0]) / parts[1] / "metadata.json").read())

        push_latest = False

        if metadata["pushLatest"]:
            if metadata["latestTag"] == parts[2]:
                push_latest = True

        tags = f"{username}/{parts[1]}:{parts[2]}"
        if push_latest:
            tags += f",{username}/{parts[1]}:latest"
        to_build.append(
            {
                "tags": tags,
                "context": str(os.path.dirname(path))
            }
        )
        image_set.add(parts[1])
        image_tag_set.add(f"{parts[1]}:{parts[2]}")
    
    # search for any metadata.json edits
    for path in paths_updated:
        parts = Path(path).parts
        if parts[0] != "dockerfiles":
            continue
        if len(parts) < 3:
            continue
        if parts[2] != "metadata.json":
            continue
        metadata = json.loads(open(Path(parts[0]) / parts[1] / "metadata.json").read())
        if not metadata["pushLatest"]:
            continue # there is no latest so nothing to rebuild
        tag = metadata["latestTag"]
        if parts[1] in image_set:
            continue # already being rebuilt
        tags = f"{username}/{parts[1]}:{tag},{username}/{parts[1]}:latest"
        to_build.append(
            {
                "tags": tags,
                "context": str(Path(parts[0]) / parts[1] / tag)
            }
        )
        
else:
    images = os.listdir("dockerfiles")
    for image in images:
        path = Path("dockerfiles") / image
        if not path.is_dir():
            continue

        metadata = json.loads(open(path / "metadata.json").read())
        
        tags = os.listdir(path)
        for tag in tags:
            newpath = path / tag
            if not newpath.is_dir():
                continue
            
            push_latest = False
            if metadata["pushLatest"]:
                if metadata["latestTag"] == tag:
                    push_latest = True

            tags = f"{username}/{image}:{tag}"
            if push_latest:
                tags += f",{username}/{image}:latest"
            to_build.append(
                {
                    "tags": tags,
                    "context": str(newpath)
                }
            )

finobj = {"include": to_build}

print(json.dumps(finobj))
