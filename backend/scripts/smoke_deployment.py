import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class SmokeTarget:
    name: str
    url: str
    expect_json: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run read-only deployment smoke checks for CivicPulse AI.",
    )
    parser.add_argument(
        "--api-base-url",
        required=True,
        help="Public backend base URL, for example https://api.example.com",
    )
    parser.add_argument(
        "--frontend-url",
        required=True,
        help="Public frontend URL, for example https://app.example.com",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def normalize_base_url(value: str) -> str:
    stripped = value.strip()
    return stripped if stripped.endswith("/") else f"{stripped}/"


def get(target: SmokeTarget, *, timeout: float) -> dict[str, Any] | str:
    request = Request(target.url, headers={"Accept": "application/json,text/html,*/*"})
    with urlopen(request, timeout=timeout) as response:
        status = response.status
        payload = response.read()
        if status < 200 or status >= 300:
            raise RuntimeError(f"{target.name} returned HTTP {status}")
        if target.expect_json:
            decoded = json.loads(payload.decode("utf-8"))
            if not isinstance(decoded, dict):
                raise RuntimeError(f"{target.name} returned non-object JSON")
            return decoded
        return payload[:120].decode("utf-8", errors="replace")


def smoke_targets(api_base_url: str, frontend_url: str) -> list[SmokeTarget]:
    api = normalize_base_url(api_base_url)
    frontend = normalize_base_url(frontend_url)
    return [
        SmokeTarget("frontend", frontend, expect_json=False),
        SmokeTarget("frontend health", urljoin(frontend, "health"), expect_json=False),
        SmokeTarget("backend live", urljoin(api, "health/live"), expect_json=True),
        SmokeTarget("backend ready", urljoin(api, "health/ready"), expect_json=True),
        SmokeTarget("public issues API", urljoin(api, "api/v1/issues?page=1&page_size=1"), True),
        SmokeTarget("public areas API", urljoin(api, "api/v1/areas"), True),
    ]


def main() -> None:
    args = parse_args()
    failures: list[str] = []
    for target in smoke_targets(args.api_base_url, args.frontend_url):
        try:
            payload = get(target, timeout=args.timeout)
            if isinstance(payload, dict):
                summary = ",".join(sorted(payload.keys())[:6])
            else:
                summary = payload.replace("\n", " ")[:80]
            print(json.dumps({"target": target.name, "ok": True, "summary": summary}))
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            failures.append(target.name)
            print(
                json.dumps(
                    {
                        "target": target.name,
                        "ok": False,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:300],
                    },
                ),
            )
    if failures:
        raise SystemExit(f"Smoke checks failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
