# TowerStats - Google Sheets Statistics

Service Cloud Run qui affiche les statistiques depuis une Google Sheet publique en CSV.

## Fonctionnalités

- Récupération automatique des données depuis une Google Sheet publique (format CSV)
- Affichage en tableau HTML avec style moderne
- Gestion des erreurs avec messages explicites
- Support UTF-8 pour les caractères spéciaux

## Test en local

### Prérequis

1. **Installer les dépendances Python** :
```bash
pip install -r requirements.txt
```

### Lancer le serveur local

**Méthode simple (script automatique) :**
```bash
./run_local.sh
```

**Méthode manuelle :**
```bash
functions-framework --target=display_stats --port=8080
```

Le serveur sera accessible sur : http://localhost:8080

### Tester

Ouvrir dans votre navigateur : http://localhost:8080

Ou avec curl :
```bash
curl http://localhost:8080
```

## Déploiement sur Cloud Run

Le projet inclut un objet `app` WSGI compatible avec Gunicorn dans `main.py`, ce qui permet d'utiliser les buildpacks automatiques de Cloud Run :

```bash
gcloud run deploy towerstats-git \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated
```

Cloud Run détectera automatiquement Python, installera les dépendances depuis `requirements.txt`, et lancera Gunicorn avec `main:app`.

**Note :** L'objet `app` dans `main.py` est un wrapper WSGI qui permet la compatibilité avec Gunicorn tout en utilisant `functions-framework` en arrière-plan.

## Configuration

L'URL CSV est définie dans `main.py` :
```python
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/.../pub?output=csv'
```

Pour utiliser une autre Google Sheet, publiez-la en CSV et mettez à jour cette URL.
