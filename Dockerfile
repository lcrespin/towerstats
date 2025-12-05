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

# Copier le script d'entrée
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Exposer le port 8080 (port par défaut de Cloud Run)
EXPOSE 8080

# Utiliser le script d'entrée
CMD ["./entrypoint.sh"]

