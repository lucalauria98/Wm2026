# WM 2026 Spielplan – online stellen & automatisch aktualisieren

Diese Anleitung bringt die Seite auf GitHub Pages und richtet den „Roboter" ein,
der die Ergebnisse alle 30 Minuten von selbst nachträgt. Danach musst du nie
wieder etwas anfassen.

Diese Dateien gehören ins Repo:

```
index.html                              ← die Webseite
data.json                               ← Spielplan + Ergebnisse (wird automatisch aktualisiert)
update.py                               ← holt die Ergebnisse von der API
.github/workflows/update-results.yml    ← startet update.py alle 30 Min
```

---

## 1. Kostenlosen API-Key holen (1 Minute)

1. Auf **https://www.football-data.org/client/register** mit E-Mail registrieren.
2. Du bekommst einen **API-Token** (eine lange Zeichenkette) per Mail / im Konto.
   Den brauchst du gleich. Der kostenlose Tarif enthält die WM, reicht völlig.

---

## 2. Repo anlegen und Dateien hochladen

1. Auf **github.com** → **+** → **New repository**.
2. Name z.B. `wm2026`, auf **Public** lassen, **Create repository**.
3. **„uploading an existing file"** → alle Dateien reinziehen.
   Wichtig: die Datei `update-results.yml` muss im Ordner `.github/workflows/`
   landen. Beim Upload im Browser einfach den Pfad mit eintippen:
   schreib vor den Dateinamen `.github/workflows/` – GitHub legt die Ordner an.
   (Einfacher geht's, wenn du das Repo lokal klonst und die Ordnerstruktur 1:1
   so hochpushst.)
4. **Commit changes**.

---

## 3. Den API-Key als Secret hinterlegen

Damit der Key **geheim** bleibt (er steht NICHT im Quelltext der Seite):

1. Im Repo: **Settings** → links **Secrets and variables** → **Actions**.
2. **New repository secret**.
3. Name exakt: `FOOTBALL_DATA_API_KEY`
4. Secret: dein Token aus Schritt 1. → **Add secret**.

---

## 4. Dem Roboter Schreibrechte geben (wird gern übersehen!)

Damit die Action `data.json` zurückschreiben darf:

1. **Settings** → **Actions** → **General**.
2. Runterscrollen zu **Workflow permissions**.
3. **Read and write permissions** auswählen → **Save**.

---

## 5. GitHub Pages einschalten

1. **Settings** → **Pages**.
2. *Source*: **Deploy from a branch**, Branch **main** / Ordner **/ (root)** → **Save**.
3. Nach 1–2 Minuten erscheint dein Link, z.B.
   **https://DEIN-USERNAME.github.io/wm2026/**

Diesen Link kannst du mit allen teilen. HTTPS ist automatisch dabei.

---

## 6. Einmal testen

1. Reiter **Actions** oben im Repo.
2. Links **„WM-Ergebnisse aktualisieren"** → rechts **Run workflow** → **Run workflow**.
3. Nach ein paar Sekunden sollte der Lauf grün sein. Klick rein – im Log steht,
   wie viele Spiele zugeordnet und wie viele mit Ergebnis eingetragen wurden.
   Wenn sich etwas geändert hat, wird `data.json` automatisch committet.

Ab jetzt läuft das **alle 30 Minuten von allein**.

---

## Gut zu wissen

- **Verzögerung:** Im kostenlosen API-Tarif sind die Ergebnisse leicht verzögert,
  nicht in Echtzeit. Für „kurz nach Abpfiff steht's da" reicht das locker – ein
  Live-Ticker ist es bewusst nicht.
- **K.o.-Runde:** Sobald die Gruppen durch sind, trägt der Roboter die echten
  Mannschaften ein; die Platzhalter („1. Gruppe A") verschwinden automatisch.
- **Sender (ARD/ZDF/MagentaTV):** Liefert keine API – das ist die feste Zuordnung
  in `data.json`. Der Roboter fasst nur Tore und (im K.o.) die Teamnamen an, sonst
  nichts.
- **Cron-Zeiten:** GitHub startet geplante Läufe manchmal ein paar Minuten später
  als angegeben – normal, kein Fehler. Die Frequenz kannst du in
  `update-results.yml` bei `cron:` ändern (z.B. `*/15 * * * *` für alle 15 Min).
- **Sollte mal ein Ergebnis nicht auftauchen:** Höchstwahrscheinlich schreibt die
  API einen Teamnamen anders, als hinterlegt ist. In `update.py` unter
  `NAME_VARIANTS` die Schreibweise ergänzen – fertig.
