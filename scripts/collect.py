#!/usr/bin/env python3
"""Coleta métricas públicas de repositórios e constrói um histórico diário."""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TIMEZONE = ZoneInfo("America/Fortaleza")


def fetch_repositories(username: str, token: str | None = None) -> list[dict]:
    """GET /users/{user}/repos. Coleta todas as páginas (apenas dados públicos)."""
    result: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{quote(username, safe='')}/repos"
            f"?type=owner&per_page=100&page={page}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-pulse-daily-snapshot",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=25) as response:
                batch = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"GitHub API retornou HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Não foi possível consultar a API do GitHub: {exc.reason}") from exc
        if not isinstance(batch, list):
            raise RuntimeError("Resposta inesperada da API do GitHub")
        result.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return result


def build_snapshot(username: str, raw_repos: list[dict], ignored_full_name: str, now: datetime) -> dict:
    repos: list[dict] = []
    for repo in raw_repos:
        if repo.get("fork") or repo.get("private"):
            continue
        if str(repo.get("full_name", "")).casefold() == ignored_full_name.casefold():
            continue
        repos.append({
            "name": str(repo.get("name") or ""),
            "url": str(repo.get("html_url") or ""),
            "stars": int(repo.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or 0),
            "open_issues": int(repo.get("open_issues_count") or 0),
            "language": repo.get("language"),
            "last_push": repo.get("pushed_at"),
        })
    repos.sort(key=lambda item: (-item["stars"], -item["forks"], item["name"].casefold()))
    return {
        "date": now.date().isoformat(),
        "captured_at": now.isoformat(timespec="seconds"),
        "username": username,
        "repository_count": len(repos),
        "stars": sum(item["stars"] for item in repos),
        "forks": sum(item["forks"] for item in repos),
        "open_issues": sum(item["open_issues"] for item in repos),
        "repositories": repos,
    }


def read_snapshots(directory: Path) -> list[dict]:
    snapshots = [json.loads(file.read_text(encoding="utf-8")) for file in sorted(directory.glob("????-??-??.json"))]
    return sorted(snapshots, key=lambda item: item["date"])


def history_csv(snapshots: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["date", "repositories", "stars", "forks", "open_issues"])
    for snapshot in snapshots:
        writer.writerow([
            snapshot["date"], snapshot["repository_count"], snapshot["stars"],
            snapshot["forks"], snapshot["open_issues"],
        ])
    return output.getvalue()


def fmt_change(current: int, previous: int | None) -> str:
    if previous is None:
        return "primeira coleta"
    diff = current - previous
    return f"{diff:+d}" if diff else "0"


def render_status(snapshots: list[dict]) -> str:
    newest = snapshots[-1]
    previous = snapshots[-2] if len(snapshots) > 1 else None
    lines = [
        "# GitHub Pulse | Painel de métricas públicas", "",
        "> Este painel é atualizado automaticamente. Os commits de coleta não representam atividade manual de programação.", "",
        f"**Perfil monitorado:** [{newest['username']}](https://github.com/{newest['username']})  ",
        f"**Última coleta:** {newest['captured_at']} (America/Fortaleza)", "",
        "## Indicadores", "",
        "| Indicador | Atual | Diferença para a coleta anterior |", "| :-- | --: | --: |",
    ]
    for label, key in [
        ("Repositórios públicos próprios", "repository_count"),
        ("Estrelas recebidas", "stars"),
        ("Forks recebidos", "forks"),
        ("Issues abertas (aproximação da API)", "open_issues"),
    ]:
        before = previous[key] if previous is not None else None
        lines.append(f"| {label} | {newest[key]} | {fmt_change(newest[key], before)} |")
    lines.extend(["", "## Histórico visual", "", "![Histórico de estrelas](assets/stars.svg)", "", "## Repositórios em destaque", ""])
    if newest["repositories"]:
        lines.extend(["| Projeto | Linguagem | Estrelas | Forks | Último push |", "| :-- | :-- | --: | --: | :-- |"])
        for repo in newest["repositories"][:10]:
            name = repo["name"].replace("|", "\\|")
            language = str(repo["language"] or "—").replace("|", "\\|")
            last_push = str(repo["last_push"] or "—")[:10]
            lines.append(f"| [{name}]({repo['url']}) | {language} | {repo['stars']} | {repo['forks']} | {last_push} |")
    else:
        lines.append("Nenhum repositório público próprio encontrado (forks e este monitor são excluídos).")
    lines.extend(["", "## Últimas coletas", "", "| Data | Repositórios | Estrelas | Forks |", "| :-- | --: | --: | --: |"])
    for snap in reversed(snapshots[-14:]):
        lines.append(f"| {snap['date']} | {snap['repository_count']} | {snap['stars']} | {snap['forks']} |")
    lines.extend(["", "Dados completos: [`data/history.csv`](data/history.csv) e arquivos JSON diários em [`data/daily`](data/daily).", ""])
    return "\n".join(lines)


def render_svg(snapshots: list[dict]) -> str:
    """Gráfico SVG simples, sem bibliotecas de terceiros."""
    recent = snapshots[-60:]
    values = [int(s["stars"]) for s in recent]
    width, height = 820, 290
    left, top, chart_w, chart_h = 70, 42, 700, 188
    low = max(0, min(values) - 1)
    high = max(values) + 1
    if high <= low:
        high = low + 1
    pts = []
    for idx, value in enumerate(values):
        x = left + (idx * chart_w / max(1, len(values) - 1))
        y = top + chart_h - ((value - low) / (high - low) * chart_h)
        pts.append((x, y))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Evolução do total de estrelas nos últimos 60 registros">',
        f'<rect width="{width}" height="{height}" rx="16" fill="#0d1117"/>',
        '<text x="28" y="27" fill="#e6edf3" font-family="Arial,sans-serif" font-size="16" font-weight="bold">Estrelas dos repositórios públicos</text>',
    ]
    for idx in range(5):
        v = low + (high - low) * (idx / 4)
        y = top + chart_h - chart_h * idx / 4
        parts.extend([
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#30363d" stroke-width="1"/>',
            f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{v:.0f}</text>',
        ])
    if len(pts) == 1:
        x, y = pts[0]
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#3fb950"/>')
    else:
        parts.append(f'<polyline points="{polyline}" fill="none" stroke="#3fb950" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        x, y = pts[-1]
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#56d364"/>')
    parts.extend([
        f'<text x="{left}" y="{height-28}" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{recent[0]["date"]}</text>',
        f'<text x="{left+chart_w}" y="{height-28}" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{recent[-1]["date"]}</text>',
        '</svg>\n',
    ])
    return "\n".join(parts)


def main() -> int:
    username = os.environ.get("PULSE_USERNAME", "").strip()
    if not username:
        print("Defina PULSE_USERNAME com seu usuário do GitHub", file=sys.stderr)
        return 2
    now = datetime.now(TIMEZONE)
    daily_dir = DATA / "daily"
    destination = daily_dir / f"{now.date().isoformat()}.json"
    if destination.exists():
        print(f"Coleta de {now.date().isoformat()} já existe. Nenhum commit adicional necessário.")
        return 0

    try:
        repos = fetch_repositories(username, os.environ.get("GH_TOKEN"))
    except (RuntimeError, ValueError) as exc:
        print(f"Erro de coleta: {exc}", file=sys.stderr)
        return 1
    ignored = os.environ.get("PULSE_IGNORE_REPO", "")
    snapshot = build_snapshot(username, repos, ignored, now)
    daily_dir.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    snapshots = read_snapshots(daily_dir)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "history.csv").write_text(history_csv(snapshots), encoding="utf-8")
    (ROOT / "STATUS.md").write_text(render_status(snapshots), encoding="utf-8")
    assets = ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "stars.svg").write_text(render_svg(snapshots), encoding="utf-8")
    print(f"Coleta concluída: {snapshot['repository_count']} repositórios, {snapshot['stars']} estrelas, {snapshot['forks']} forks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
