# TowerStats

Stats TowerFall Ascension depuis une Google Sheet publique (CSV), déployé sur Cloud Run.

## Fonctionnalités

- Sessions corrigées (minuit, today/total, modes Head Hunters / Respawn 3)
- Saisons + vue carrière, filtres (dates, groupe, session, mode)
- Classements : % victoires, Elo session, Elo match, K/D, groupes
- Live session, archives détaillées, records, fiches de combat
- Courbes d'évolution (scores, win rate, Elo)

## Test en local

```bash
pip install -r requirements.txt
./run_local.sh          # Flask + reload ; ajoute --live pour démo live
```

Ou : `functions-framework --target=display_stats --port=8080`

→ http://localhost:8080

## Déploiement Cloud Run

```bash
gcloud run deploy towerstats-git \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated
```

Buildpacks Python + Gunicorn via `main:app`. `display_stats` reste l'entrée functions-framework.

## Structure

```
towerstats/
├── src/
│   ├── config.py           # Joueurs, couleurs, modes, URLs
│   ├── data_manager.py     # Fetch / filter / correct CSV
│   ├── stats_manager.py    # Classements et payload template
│   ├── elo.py              # Elo session et Elo match
│   ├── page.py             # Contexte homepage
│   ├── seasons.py          # Saisons et HUD
│   ├── combat_profiles.py  # Badges / courbe soirée
│   ├── session_*.py        # Faits, archives, records
│   ├── live_session.py     # Session en cours
│   ├── messages.py         # Messages win/lose
│   ├── taglines.py         # Sous-titres
│   └── main.py             # Flask
├── main.py                 # Entrée Gunicorn / Cloud Run
├── templates/
├── static/                 # css, js, images
├── tests/
└── scripts/
```

## Configuration

URLs CSV et joueurs dans `src/config.py` (`CSV_URL`, `MESSAGES_CSV_URL`, `PLAYER_TO_COLOR`).
