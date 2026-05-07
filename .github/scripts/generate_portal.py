#!/usr/bin/env python3
"""
generate_portal.py
Consulta l'API de GitHub, busca tots els repos de l'organització,
llegeix els topics i regenera index.html amb les dades reals.

Topics reconeguts: {cicle}{curs}-{modul}  ex: asir1-par, daw2-dwec, smr1-rlo
"""

import os
import json
import urllib.request
import urllib.error
from datetime import date, timezone
import re

# ── CONFIG ───────────────────────────────────────────────────────────────────
ORG   = os.environ.get("ORG", "pedrosegarra")
TOKEN = os.environ.get("GH_TOKEN", "")

# Estructura del centre: cicle → curs → mòduls
# Format topic: {cicle_id}{num_curs}-{modul_id}  ex: asir1-par
ESTRUCTURA = {
    "asir": {
        "nom": "Administració de Sistemes Informàtics en Xarxa",
        "pill": "ASIR", "pillClass": "pill-asir",
        "cursos": {
            "1": {"label": "1r curs", "mods": {
                "par": {"codi": "0370", "nom": "Planificació i Administració de Xarxes"},
                "gbd": {"codi": "0369", "nom": "Gestió de Bases de Dades"},
                "fhw": {"codi": "0371", "nom": "Fonaments de Maquinari"},
                "lnd": {"codi": "0373", "nom": "Llenguatges de Marques"},
                "iso": {"codi": "0367", "nom": "Implantació de Sistemes Operatius"},
            }},
            "2": {"label": "2n curs", "mods": {
                "sad": {"codi": "0374", "nom": "Seguretat i Alta Disponibilitat"},
                "iaw": {"codi": "0378", "nom": "Implantació d'Aplicacions Web"},
                "sri": {"codi": "0376", "nom": "Serveis de Xarxa i Internet"},
                "aso": {"codi": "0377", "nom": "Administració de Sistemes Operatius"},
                "abd": {"codi": "0372", "nom": "Administració de Bases de Dades"},
            }},
        }
    },
    "daw": {
        "nom": "Desenvolupament d'Aplicacions Web",
        "pill": "DAW", "pillClass": "pill-daw",
        "cursos": {
            "1": {"label": "1r curs", "mods": {
                "dwec": {"codi": "0612", "nom": "Desenvolupament Web en Entorn Client"},
                "lnd":  {"codi": "0373", "nom": "Llenguatges de Marques"},
                "edes": {"codi": "0612", "nom": "Entorns de Desenvolupament"},
                "bbdd": {"codi": "0369", "nom": "Bases de Dades"},
            }},
            "2": {"label": "2n curs", "mods": {
                "dwes": {"codi": "0613", "nom": "Desenvolupament Web en Entorn Servidor"},
                "diw":  {"codi": "0614", "nom": "Disseny d'Interfícies Web"},
                "daw":  {"codi": "0615", "nom": "Desplegament d'Aplicacions Web"},
            }},
        }
    },
    "smr": {
        "nom": "Sistemes Microinformàtics i Xarxes",
        "pill": "SMR", "pillClass": "pill-smr",
        "cursos": {
            "1": {"label": "1r curs", "mods": {
                "soi": {"codi": "0221", "nom": "Sistemes Operatius en Xarxa"},
                "rlo": {"codi": "0222", "nom": "Xarxes Locals"},
            }},
            "2": {"label": "2n curs", "mods": {
                "ams": {"codi": "0223", "nom": "Aplicacions i Serveis en Xarxa"},
                "smc": {"codi": "0224", "nom": "Sistemes Microinformàtics"},
            }},
        }
    },
    "ce": {
        "nom": "Curs d'Especialització",
        "pill": "CE", "pillClass": "pill-ce",
        "cursos": {
            "1": {"label": "Mòduls", "mods": {
                "des": {"codi": "5167", "nom": "Desplegament de Programari"},
                "mon": {"codi": "5169", "nom": "Monitoratge i Seguretat"},
                "cib": {"codi": "5165", "nom": "Ciberseguretat en Entorns de les TI"},
            }},
        }
    },
}

# ── API HELPER ───────────────────────────────────────────────────────────────
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def gh_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} → {url}")
        return None

def get_all_repos():
    """Retorna tots els repos públics de l'organització amb els seus topics."""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{ORG}/repos?type=public&per_page=100&page={page}"
        data = gh_get(url)
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    print(f"  Trobats {len(repos)} repos públics a {ORG}")
    return repos

def pages_url(owner, repo_name):
    """Construeix la URL de GitHub Pages d'un repo."""
    # Format estàndard: https://{owner}.github.io/{repo}
    return f"https://{owner}.github.io/{repo_name}"

def has_gh_pages(repo):
    """Comprova si el repo té GitHub Pages activat."""
    return repo.get("has_pages", False)

# ── PARSE TOPICS ─────────────────────────────────────────────────────────────
TOPIC_RE = re.compile(r'^([a-z]+)(\d+)-([a-z]+)$')

def parse_topic(topic):
    """Retorna (cicle, curs, modul) o None si el topic no es reconeix."""
    m = TOPIC_RE.match(topic)
    if not m:
        return None
    cicle, curs, modul = m.group(1), m.group(2), m.group(3)
    if cicle not in ESTRUCTURA:
        return None
    if curs not in ESTRUCTURA[cicle]["cursos"]:
        return None
    if modul not in ESTRUCTURA[cicle]["cursos"][curs]["mods"]:
        return None
    return (cicle, curs, modul)

# ── BUILD DATA ────────────────────────────────────────────────────────────────
def build_data(repos):
    """
    Retorna estructura de dades:
    { cicle: { curs: { modul: [ {user, url}, ... ] } } }
    """
    data = {}
    for cicle_id, cicle in ESTRUCTURA.items():
        data[cicle_id] = {}
        for curs_id in cicle["cursos"]:
            data[cicle_id][curs_id] = {}
            for mod_id in cicle["cursos"][curs_id]["mods"]:
                data[cicle_id][curs_id][mod_id] = []

    for repo in repos:
        if not has_gh_pages(repo):
            continue
        topics = repo.get("topics") or []
        owner  = repo["owner"]["login"]
        name   = repo["name"]
        url    = pages_url(owner, name)

        for topic in topics:
            parsed = parse_topic(topic)
            if parsed:
                cicle, curs, modul = parsed
                entry = {"user": owner, "url": url}
                if entry not in data[cicle][curs][modul]:
                    data[cicle][curs][modul].append(entry)

    return data

# ── GENERATE HTML ─────────────────────────────────────────────────────────────
def initials(user):
    parts = user.replace('.', ' ').replace('-', ' ').split()
    return ''.join(p[0].upper() for p in parts if p)[:2]

def render_chip(prof):
    ini = initials(prof["user"])
    return (
        f'<a class="chip" href="{prof["url"]}" target="_blank" rel="noopener">'
        f'<div class="chip-av">{ini}</div>{prof["user"]}</a>'
    )

def render_mod(cicle_id, curs_id, mod_id, data):
    mod_info = ESTRUCTURA[cicle_id]["cursos"][curs_id]["mods"][mod_id]
    profs    = data[cicle_id][curs_id][mod_id]
    has_mat  = len(profs) > 0

    badge = (
        '<span class="badge badge-si">● Material</span>' if has_mat
        else '<span class="badge badge-no">Sense material</span>'
    )
    chips = ''.join(render_chip(p) for p in profs)
    search_str = f"{mod_info['codi']} {mod_id} {mod_info['nom']} {' '.join(p['user'] for p in profs)}"

    return (
        f'<div class="mod" data-search="{search_str.lower()}">'
        f'<div class="mod-top">'
        f'<span class="mod-code">{mod_info["codi"]} · {mod_id.upper()}</span>{badge}'
        f'</div>'
        f'<div class="mod-name">{mod_info["nom"]}</div>'
        f'<div class="prof-chips">{chips}</div>'
        f'</div>'
    )

def render_curs(cicle_id, curs_id, data, is_first):
    curs_info = ESTRUCTURA[cicle_id]["cursos"][curs_id]
    mods_html = ''.join(
        render_mod(cicle_id, curs_id, mod_id, data)
        for mod_id in curs_info["mods"]
    )
    n_mods = len(curs_info["mods"])
    n_mat  = sum(1 for m in curs_info["mods"] if data[cicle_id][curs_id][m])
    open_cls = " open" if is_first else ""
    chev = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>'

    return (
        f'<div class="curs{open_cls}" id="{cicle_id}{curs_id}">'
        f'<div class="curs-hdr" onclick="toggleCurs(this)">'
        f'<span class="curs-label">{curs_info["label"]}</span>'
        f'<div class="curs-meta"><span>{n_mods} mòduls · {n_mat} amb material</span>{chev}</div>'
        f'</div>'
        f'<div class="mods-grid">{mods_html}</div>'
        f'</div>'
    )

def render_cicle(cicle_id, data, is_first):
    cicle_info = ESTRUCTURA[cicle_id]
    total_mods = sum(len(c["mods"]) for c in cicle_info["cursos"].values())
    total_mat  = sum(
        sum(1 for m in c["mods"] if data[cicle_id][curs_id][m])
        for curs_id, c in cicle_info["cursos"].items()
    )
    cursos_html = ''.join(
        render_curs(cicle_id, curs_id, data, i == 0)
        for i, curs_id in enumerate(cicle_info["cursos"])
    )
    open_cls = " open" if is_first else ""
    chev = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>'

    return (
        f'<div class="ciclo{open_cls}" id="ciclo-{cicle_id}">'
        f'<div class="ciclo-hdr" onclick="toggleCiclo(this)">'
        f'<div class="ciclo-left">'
        f'<span class="ciclo-pill {cicle_info["pillClass"]}">{cicle_info["pill"]}</span>'
        f'<span class="ciclo-name">{cicle_info["nom"]}</span>'
        f'</div>'
        f'<div class="ciclo-right">'
        f'<span class="ciclo-meta">{total_mods} mòduls · {total_mat} amb material</span>'
        f'{chev}</div></div>'
        f'<div class="ciclo-body">{cursos_html}</div>'
        f'</div>'
    )

# ── INJECT INTO HTML ──────────────────────────────────────────────────────────

def inject(html, data):
    today = date.today().isoformat()
    print("  ESTRUCTURA keys:", list(ESTRUCTURA.keys()))
    for cicle_id, cicle in ESTRUCTURA.items():
        for curs_id, c in cicle["cursos"].items():
            print(f"  cicle={cicle_id} curs={curs_id} mods={list(c['mods'].keys())}")
    html = re.sub(r'const SYNC_DATE = "[^"]*"', f'const SYNC_DATE = "{today}"', html)
    for cicle_id, cicle in ESTRUCTURA.items():
        for curs_id, c in cicle["cursos"].items():
            for mod_id in c["mods"]:
                profs = data[cicle_id][curs_id][mod_id]
                if mod_id == 'asir1-par':
                    test = re.search(rf"id:'{re.escape(mod_id)}'", html)
                    if test:
                        print(f"  ENCONTRADO en pos {test.start()}")
                        print(f"  >>>{html[test.start():test.start()+100]}<<<")
                    else:
                        print(f"  NO ENCONTRADO: {mod_id}")
                if profs:
                    parts = []
                    for p in profs:
                        parts.append("{user:'" + p['user'] + "',url:'" + p['url'] + "'}")
                    profs_js = ','.join(parts)
                else:
                    profs_js = ''
                html = re.sub(
                    rf"(\{{id:'{re.escape(mod_id)}',[^}}]*profs:)\[[^\]]*\]",
                    rf"\g<1>[{profs_js}]",
                    html
                )
    return html
# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"=== Generant portal per a org: {ORG} ===")

    repos = get_all_repos()
    data  = build_data(repos)

    # Compta resum
    total_mat = sum(
        1
        for cicle_id, cicle in ESTRUCTURA.items()
        for curs_id, c in cicle["cursos"].items()
        for mod_id in c["mods"]
        if data[cicle_id][curs_id][mod_id]
    )
    print(f"  Mòduls amb material: {total_mat}")

    # Llig el template
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir   = os.path.join(script_dir, '..', '..')
    html_path  = os.path.join(root_dir, 'index.html')

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    html = inject(html, data)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  index.html actualitzat ({date.today()})")

if __name__ == '__main__':
    main()
