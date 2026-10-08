# MORGENBRIEFING.

Kostenlose Android-optimierte Hörseite mit Link zum offiziellen ARD-Tagesschau-Podcast und eigenem KI-Podcastplayer.

## Einrichtung

GitHub Pages unter Settings > Pages > Source **GitHub Actions** aktivieren. Workflow unter Actions prüfen.

Die tägliche ChatGPT-E-Mail-Automation überträgt Inhalte aktuell **noch nicht** in `data/edition.json`. Das bleibt als Integrationsschritt offen.

Setze `date`, `articles` (category, title, summary, optional source) und ein geprüftes `podcast_script` in `data/edition.json`. Der Workflow erzeugt dann kostenlos offline per Piper deutsche Sprache als MP3 und veröffentlicht sie. Bei leerem Skript wird kein erfundener Player angezeigt.

Die Tagesschau wird nur auf ihrer offiziellen Seite verlinkt. Öffentliche GitHub Pages sind für alle erreichbar; keine privaten Informationen eintragen. Kostenloses GitHub-Actions-Kontingent und Infrastrukturverfügbarkeit sind nicht garantiert.
