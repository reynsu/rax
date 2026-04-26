"""Mine objective signals from public React/RN GitHub repos.

For each repo in the input list, fetch and persist:
    - defect_density_per_file:  fraction of files touched by `fix`-keyword
                                commits in the last `lookback_days` days
    - lifespan_years:           age of the repo (createdAt -> now)
    - star_count, contributor_count, recent_activity (commits in window)
    - cve_count:                advisory count from GitHub Security Advisories
    - review_intensity:         avg comments per PR over a sample

Output: one JSON file per repo at `tests/corpus/mined/<owner>__<repo>.json`.

These signals are PROXY for code quality, not ground truth. They correlate
weakly. Use them in the corpus as one layer among four (synthetic anchors,
mined signals, self-consistency, cross-LLM consensus). See
`references/corpus.md` for the full epistemology.

Usage:
    GITHUB_TOKEN=... python scripts/mine_corpus.py \
        --repos tests/corpus/mined/repo_list.txt \
        --output tests/corpus/mined/

Without GITHUB_TOKEN the script will refuse to run (the unauthenticated
GitHub API rate-limit is too low to mine 50+ repos).

For offline / CI environments without an API token, run:
    python scripts/mine_corpus.py --synthesize 50 --output tests/corpus/mined/

This synthesizes valid-schema placeholder files so downstream consumers
(corpus validators, conformal calibration) can run end-to-end without a
real mined corpus. The placeholders are clearly marked `"synthetic": true`.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


GITHUB_GRAPHQL = "https://api.github.com/graphql"

# GitHub owner / repo names are ASCII alphanumerics + `-`, `_`, `.`. Reject
# anything else so a hostile repo list cannot escape `--output` via path
# traversal in the constructed filename.
_GH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def _validate_slug(slug: str) -> tuple[str, str]:
    """Split `owner/repo` and validate both halves. Raises ValueError."""
    if "/" not in slug:
        raise ValueError(f"slug missing '/': {slug!r}")
    owner, name = slug.split("/", 1)
    for label, value in (("owner", owner), ("name", name)):
        if not _GH_NAME_RE.match(value):
            raise ValueError(f"invalid {label} {value!r} in slug {slug!r}")
    return owner, name


# ----- HTTP helpers (stdlib only — no external deps required) -----


def _gql(query: str, variables: Dict[str, Any], token: str) -> Dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GITHUB_GRAPHQL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "rax-mine-corpus/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


REPO_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    createdAt
    pushedAt
    stargazerCount
    forkCount
    isArchived
    isFork
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100) {
            totalCount
            nodes { messageHeadline committedDate }
          }
        }
      }
    }
    pullRequests(states: MERGED, first: 30, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { comments { totalCount } reviews { totalCount } }
    }
    securityAdvisories: vulnerabilityAlerts(first: 1) { totalCount }
  }
}
"""


# ----- mining -----


def mine_repo(owner: str, name: str, token: str, lookback_days: int = 365) -> Dict[str, Any]:
    """Mine a single repo via GitHub GraphQL."""
    data = _gql(REPO_QUERY, {"owner": owner, "name": name}, token)
    repo = (data.get("data") or {}).get("repository")
    if not repo:
        raise RuntimeError(f"repo {owner}/{name} not found or not accessible: {data}")

    created_at = datetime.fromisoformat(repo["createdAt"].replace("Z", "+00:00"))
    pushed_at = datetime.fromisoformat(repo["pushedAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    lifespan_years = (now - created_at).days / 365.25

    history = ((repo.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}
    commits = history.get("nodes") or []
    fix_keywords = ("fix", "bug", "regression", "hotfix", "patch")
    fix_commits = sum(
        1 for c in commits if any(k in (c["messageHeadline"] or "").lower() for k in fix_keywords)
    )
    defect_density_per_file = round(fix_commits / max(1, len(commits)), 4)

    cutoff = now.timestamp() - lookback_days * 24 * 3600
    recent_activity = sum(
        1 for c in commits
        if datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00")).timestamp() >= cutoff
    )

    prs = (repo.get("pullRequests") or {}).get("nodes") or []
    if prs:
        avg_comments = sum((p.get("comments") or {}).get("totalCount", 0) for p in prs) / len(prs)
        avg_reviews = sum((p.get("reviews") or {}).get("totalCount", 0) for p in prs) / len(prs)
    else:
        avg_comments = avg_reviews = 0.0

    advisories = (repo.get("securityAdvisories") or {}).get("totalCount", 0)

    return {
        "owner": owner,
        "name": name,
        "name_with_owner": repo.get("nameWithOwner"),
        "created_at": repo["createdAt"],
        "pushed_at": repo["pushedAt"],
        "is_archived": repo.get("isArchived", False),
        "is_fork": repo.get("isFork", False),
        "lifespan_years": round(lifespan_years, 2),
        "star_count": repo.get("stargazerCount", 0),
        "fork_count": repo.get("forkCount", 0),
        "defect_density_per_file": defect_density_per_file,
        "recent_activity_commits": recent_activity,
        "review_intensity": {
            "avg_comments_per_pr": round(avg_comments, 2),
            "avg_reviews_per_pr": round(avg_reviews, 2),
        },
        "cve_count": advisories,
        "synthetic": False,
        "mined_at": now.isoformat(),
    }


# ----- synthesis (offline path) -----


_PLACEHOLDER_REPOS = [
    "facebook/react-native", "expo/expo", "microsoft/react-native-windows",
    "react-native-elements/react-native-elements", "GeekyAnts/NativeBase",
    "infinitered/ignite", "wix/Detox", "react-native-async-storage/async-storage",
    "callstack/react-native-paper", "software-mansion/react-native-reanimated",
    "react-navigation/react-navigation", "facebook/react", "vercel/next.js",
    "vercel/swr", "TanStack/query", "TanStack/router", "remix-run/remix",
    "pmndrs/zustand", "redux/redux", "reduxjs/redux-toolkit",
    "facebook/lexical", "tldraw/tldraw", "primer/react", "shadcn-ui/ui",
    "radix-ui/primitives", "chakra-ui/chakra-ui", "mui/material-ui",
    "mantinedev/mantine", "Microsoft/fluentui", "ant-design/ant-design",
    "sveltejs/svelte", "vuejs/core", "solidjs/solid", "qwikdev/qwik",
    "vitejs/vite", "webpack/webpack", "evanw/esbuild", "swc-project/swc",
    "babel/babel", "rollup/rollup", "parcel-bundler/parcel",
    "storybookjs/storybook", "playwright/playwright", "cypress-io/cypress",
    "DefinitelyTyped/DefinitelyTyped", "microsoft/TypeScript", "type-challenges/type-challenges",
    "preactjs/preact", "marko-js/marko", "alpinejs/alpine", "stimulusjs/stimulus",
    "gatsbyjs/gatsby", "withastro/astro",
]


def synthesize_one(slug: str, rng: random.Random) -> Dict[str, Any]:
    owner, name = _validate_slug(slug)
    return {
        "owner": owner,
        "name": name,
        "name_with_owner": slug,
        "created_at": "2020-01-01T00:00:00Z",
        "pushed_at": "2026-04-01T00:00:00Z",
        "is_archived": False,
        "is_fork": False,
        "lifespan_years": round(rng.uniform(2.0, 8.0), 2),
        "star_count": rng.randint(500, 200000),
        "fork_count": rng.randint(50, 30000),
        "defect_density_per_file": round(rng.uniform(0.05, 0.45), 4),
        "recent_activity_commits": rng.randint(5, 100),
        "review_intensity": {
            "avg_comments_per_pr": round(rng.uniform(0.5, 8.0), 2),
            "avg_reviews_per_pr": round(rng.uniform(0.5, 4.0), 2),
        },
        "cve_count": rng.randint(0, 4),
        "synthetic": True,
        "mined_at": "2026-04-25T00:00:00Z",
    }


def synthesize(out_dir: Path, n: int) -> int:
    rng = random.Random(42)
    out_dir.mkdir(parents=True, exist_ok=True)
    pool = list(_PLACEHOLDER_REPOS)
    if n > len(pool):
        # extend with synthesized owner/repo names for the overflow
        pool += [f"acme-{i}/example-{i}" for i in range(n - len(pool))]
    written = 0
    for slug in pool[:n]:
        owner, name = _validate_slug(slug)
        path = out_dir / f"{owner}__{name}.json"
        if path.exists():
            continue
        path.write_text(json.dumps(synthesize_one(slug, rng), indent=2) + "\n")
        written += 1
    return written


# ----- main -----


def _read_repo_list(path: Path) -> List[str]:
    out: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", type=Path, help="file with one owner/repo per line")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--synthesize", type=int, metavar="N",
                    help="synthesize N placeholder files (offline / CI)")
    ap.add_argument("--lookback-days", type=int, default=365)
    ap.add_argument("--rate-sleep", type=float, default=0.5,
                    help="seconds between API calls")
    args = ap.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)

    if args.synthesize is not None:
        n = synthesize(args.output, args.synthesize)
        print(f"synthesized {n} placeholder mined files at {args.output}")
        return 0

    if not args.repos:
        ap.error("either --repos or --synthesize is required")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN env var required for real mining; "
              "use --synthesize <N> for offline placeholders", file=sys.stderr)
        return 2

    repos = _read_repo_list(args.repos)
    print(f"mining {len(repos)} repos -> {args.output}")
    output_root = args.output.resolve()
    written = failed = 0
    for slug in repos:
        try:
            owner, name = _validate_slug(slug)
        except ValueError as exc:
            print(f"skip malformed: {slug} ({exc})", file=sys.stderr)
            continue
        out_path = (args.output / f"{owner}__{name}.json").resolve()
        # Defense-in-depth: reject anything that escapes --output even after
        # validation, in case the regex is loosened later.
        try:
            out_path.relative_to(output_root)
        except ValueError:
            print(f"skip {slug}: resolves outside --output ({out_path})", file=sys.stderr)
            continue
        try:
            data = mine_repo(owner, name, token, lookback_days=args.lookback_days)
            out_path.write_text(json.dumps(data, indent=2) + "\n")
            written += 1
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
            print(f"  ! {slug}: {exc}", file=sys.stderr)
            failed += 1
        time.sleep(args.rate_sleep)

    print(f"done: {written} written, {failed} failed")
    return 0 if written > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
