#!/usr/bin/env python3
"""
WM 2026 – Ergebnis-Updater.

Holt die aktuellen Spiele der FIFA WM 2026 von football-data.org (kostenloser
Tarif, der Key kommt aus der Umgebungsvariable FOOTBALL_DATA_API_KEY) und trägt
in data.json die Ergebnisse ein. Bei K.o.-Spielen werden zusätzlich die echten
Mannschaften gesetzt, sobald sie feststehen.

Nur Standardbibliothek – keine pip-Installation nötig.

Der Spielplan (wer/wann/wo + Sender) bleibt unverändert; es werden ausschliesslich
Tore (sa/sb) und – im K.o. – die Teamnamen (a/b) überschrieben.
"""

import json
import os
import sys
import unicodedata
import urllib.request
import urllib.error
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:
    BERLIN = None  # Fallback weiter unten

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
API_URL = "https://api.football-data.org/v4/competitions/WC/matches"

# ---------------------------------------------------------------------------
# Mannschaftsnamen: viele mögliche API-Schreibweisen -> unser deutscher Name.
# Wird normalisiert verglichen (klein, ohne Akzente, ohne Sonderzeichen),
# daher reicht je eine repräsentative Variante.
# ---------------------------------------------------------------------------
NAME_VARIANTS = {
    "Mexiko": ["Mexico"],
    "Südafrika": ["South Africa"],
    "Südkorea": ["South Korea", "Korea Republic", "Republic of Korea", "Korea"],
    "Tschechien": ["Czechia", "Czech Republic"],
    "Kanada": ["Canada"],
    "Schweiz": ["Switzerland"],
    "Bosnien-Herzegowina": ["Bosnia and Herzegovina", "Bosnia-Herzegovina",
                            "Bosnia & Herzegovina", "Bosnia Herzegovina"],
    "Katar": ["Qatar"],
    "Brasilien": ["Brazil"],
    "Marokko": ["Morocco"],
    "Schottland": ["Scotland"],
    "Haiti": ["Haiti"],
    "USA": ["United States", "United States of America", "USA"],
    "Türkei": ["Türkiye", "Turkiye", "Turkey"],
    "Paraguay": ["Paraguay"],
    "Australien": ["Australia"],
    "Deutschland": ["Germany"],
    "Ecuador": ["Ecuador"],
    "Elfenbeinküste": ["Ivory Coast", "Cote d'Ivoire", "Côte d'Ivoire"],
    "Curaçao": ["Curacao", "Curaçao"],
    "Niederlande": ["Netherlands", "Holland"],
    "Japan": ["Japan"],
    "Schweden": ["Sweden"],
    "Tunesien": ["Tunisia"],
    "Belgien": ["Belgium"],
    "Ägypten": ["Egypt"],
    "Iran": ["Iran", "IR Iran", "Islamic Republic of Iran"],
    "Neuseeland": ["New Zealand"],
    "Spanien": ["Spain"],
    "Uruguay": ["Uruguay"],
    "Saudi-Arabien": ["Saudi Arabia"],
    "Kap Verde": ["Cape Verde", "Cabo Verde", "Cape Verde Islands"],
    "Frankreich": ["France"],
    "Senegal": ["Senegal"],
    "Norwegen": ["Norway"],
    "Irak": ["Iraq"],
    "Argentinien": ["Argentina"],
    "Österreich": ["Austria"],
    "Algerien": ["Algeria"],
    "Jordanien": ["Jordan"],
    "Portugal": ["Portugal"],
    "Kolumbien": ["Colombia"],
    "Usbekistan": ["Uzbekistan"],
    "DR Kongo": ["DR Congo", "Congo DR", "Democratic Republic of Congo",
                "Democratic Republic of the Congo", "Congo Democratic Republic"],
    "England": ["England"],
    "Kroatien": ["Croatia"],
    "Ghana": ["Ghana"],
    "Panama": ["Panama"],
}


def norm(s):
    """Klein, ohne Akzente, nur a-z0-9."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


# normalisierte Variante -> deutscher Name
SYN = {}
for de, variants in NAME_VARIANTS.items():
    SYN[norm(de)] = de
    for v in variants:
        SYN[norm(v)] = de


def to_de(api_name):
    """API-Teamname -> unser deutscher Name (oder Original, wenn unbekannt)."""
    if not api_name:
        return None
    return SYN.get(norm(api_name), api_name)


def berlin_dt(utc_iso):
    """ISO-UTC-String -> (datum 'YYYY-MM-DD', zeit 'HH:MM') in Berliner Zeit."""
    s = utc_iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if BERLIN is not None:
        dt = dt.astimezone(BERLIN)
    else:
        # grober Fallback: feste Sommerzeit-Verschiebung +2h
        from datetime import timedelta
        dt = dt.astimezone(timezone.utc) + timedelta(hours=2)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def fetch_matches(token):
    req = urllib.request.Request(API_URL, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("matches", [])


SCORERS_URL = "https://api.football-data.org/v4/competitions/WC/scorers?limit=25"


def fetch_scorers(token):
    req = urllib.request.Request(SCORERS_URL, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("scorers", [])


def main():
    token = os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()
    if not token:
        print("FEHLER: FOOTBALL_DATA_API_KEY ist nicht gesetzt.", file=sys.stderr)
        sys.exit(1)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    base = data["matches"]

    # ----- Indizes über den festen Spielplan aufbauen -----
    # Gruppenspiele: nach Team-Paar (deutsch, als frozenset)
    group_idx = {}
    # alle Spiele: nach (datum, zeit) -> für K.o.-Zuordnung
    time_idx = {}
    for i, m in enumerate(base):
        if m.get("p") == "group":
            key = frozenset((m["a"], m["b"]))
            group_idx[key] = i
        time_idx.setdefault((m["d"], m["t"]), []).append(i)

    # ----- API abrufen -----
    try:
        api = fetch_matches(token)
    except urllib.error.HTTPError as e:
        print(f"FEHLER beim Abruf: HTTP {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa
        print(f"FEHLER beim Abruf: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"{len(api)} Spiele von der API erhalten.")

    # frische Kopie zum Reinschreiben
    new = json.loads(json.dumps(base))
    matched = 0
    scored = 0
    unmatched = []

    for am in api:
        stage = (am.get("stage") or "").upper()
        utc = am.get("utcDate")
        if not utc:
            continue
        d, t = berlin_dt(utc)

        home = (am.get("homeTeam") or {}).get("name")
        away = (am.get("awayTeam") or {}).get("name")
        score = am.get("score") or {}
        ft = score.get("fullTime") or {}
        htsc = score.get("halfTime") or {}
        sh, sa_ = ft.get("home"), ft.get("away")
        hh, ha = htsc.get("home"), htsc.get("away")
        status = am.get("status")

        ref_name = None
        for r in (am.get("referees") or []):
            ref_name = r.get("name")
            if (r.get("type") or "").upper() in ("REFEREE", "MAIN_REFEREE"):
                break

        home_de = to_de(home)
        away_de = to_de(away)

        is_group = (stage == "GROUP_STAGE") or (
            home_de in NAME_VARIANTS and away_de in NAME_VARIANTS
            and frozenset((home_de, away_de)) in group_idx
        )

        idx = None
        if is_group and home_de and away_de:
            idx = group_idx.get(frozenset((home_de, away_de)))
        else:
            # K.o.: über Datum + Anstosszeit zuordnen (eindeutig, wenn nur 1 Spiel)
            cands = time_idx.get((d, t), [])
            if len(cands) == 1:
                idx = cands[0]
            elif len(cands) > 1 and home_de and away_de:
                # bei gleichzeitigem Anstoss per Team eingrenzen
                for c in cands:
                    if base[c]["a"] in (home_de, away_de) or base[c]["b"] in (home_de, away_de):
                        idx = c
                        break

        if idx is None:
            unmatched.append(f"{d} {t} {home}–{away} [{stage}]")
            continue

        matched += 1

        # K.o.: echte Teams eintragen, sobald bekannt
        if not is_group:
            if home_de:
                new[idx]["a"] = home_de
            if away_de:
                new[idx]["b"] = away_de

        # Orientierung: Gruppenspiele werden per (ungeordnetem) Team-Paar
        # zugeordnet – die Plan-Reihenfolge a/b muss NICHT der Heim/Auswärts-
        # Reihenfolge der API entsprechen. Tore daher passend zu a/b drehen,
        # statt sie stur als Heim/Auswärts zu übernehmen (sonst vertauscht).
        # (Bei K.o. wurde "a" gerade auf das Heimteam gesetzt -> swap=False.)
        swap = (new[idx]["a"] == away_de) or (new[idx]["b"] == home_de)

        # Ergebnis eintragen (sobald vorhanden / Spiel beendet)
        if sh is not None and sa_ is not None and status in (
            "IN_PLAY", "PAUSED", "FINISHED", "AWARDED"
        ):
            g_home, g_away = int(sh), int(sa_)
            new[idx]["sa"], new[idx]["sb"] = (
                (g_away, g_home) if swap else (g_home, g_away)
            )
            if hh is not None and ha is not None:
                new[idx]["ht"] = [int(ha), int(hh)] if swap else [int(hh), int(ha)]
            scored += 1

        # Schiedsrichter eintragen, sobald bekannt (sofern die API ihn liefert)
        if ref_name:
            new[idx]["ref"] = ref_name

    if unmatched:
        print(f"Nicht zugeordnet ({len(unmatched)}):")
        for u in unmatched:
            print("   -", u)

    print(f"Zugeordnet: {matched} · mit Ergebnis: {scored}")

    # ----- Torschützenliste (eigene Free-Tier-Ressource) -----
    old_scorers = data.get("scorers")
    new_scorers = old_scorers
    try:
        raw_scorers = fetch_scorers(token)
        new_scorers = []
        for s in raw_scorers:
            goals = s.get("goals")
            if goals is None:
                continue
            player = s.get("player") or {}
            team = s.get("team") or {}
            new_scorers.append({
                "name": player.get("name") or "?",
                "team": to_de(team.get("name")) if team.get("name") else "",
                "goals": int(goals),
            })
        print(f"Torschützen: {len(new_scorers)}")
    except urllib.error.HTTPError as e:
        print(f"Torschützen-Abruf: HTTP {e.code} {e.reason} (übersprungen)")
    except Exception as e:  # noqa
        print(f"Torschützen-Abruf fehlgeschlagen: {e} (übersprungen)")

    matches_changed = (new != base)
    scorers_changed = (new_scorers != old_scorers)
    if not matches_changed and not scorers_changed:
        print("Keine Änderung – data.json bleibt unverändert.")
        return

    data["matches"] = new
    if new_scorers is not None:
        data["scorers"] = new_scorers
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("data.json aktualisiert.")


if __name__ == "__main__":
    main()
