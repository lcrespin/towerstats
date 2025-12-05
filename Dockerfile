# Utiliser une image Python officielle légère
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY main.py .

# Exposer le port 8080 (port par défaut de Cloud Run)
EXPOSE 8080

# Définir la variable d'environnement pour le port
ENV PORT=8080

# Lancer la fonction avec functions-framework
CMD exec functions-framework --target=display_stats --port=$PORT --host=0.0.0.0

