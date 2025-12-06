#!/bin/bash

# Script pour lancer le serveur en local

PORT=8080

echo "🚀 Démarrage du serveur local..."
echo ""
echo "📋 Vérification des dépendances..."

# Vérifier si les dépendances sont installées
if ! python3 -c "import functions_framework" 2>/dev/null; then
    echo "⚠️  Installation des dépendances..."
    pip install -r requirements.txt
fi

echo ""
echo "🔌 Vérification du port $PORT..."

# Vérifier si le port est déjà utilisé
if lsof -ti:$PORT &>/dev/null; then
    PID=$(lsof -ti:$PORT)
    echo "⚠️  Le port $PORT est déjà utilisé par le processus $PID"
    read -p "Voulez-vous arrêter ce processus et utiliser le port $PORT ? (o/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[OoYy]$ ]]; then
        kill $PID
        sleep 1
        echo "✅ Processus arrêté"
    else
        # Essayer un autre port
        PORT=8081
        while lsof -ti:$PORT &>/dev/null; do
            PORT=$((PORT + 1))
        done
        echo "✅ Utilisation du port $PORT à la place"
    fi
fi

echo ""
echo "✅ Démarrage du serveur sur http://localhost:$PORT"
echo "   Mode développement avec rechargement automatique activé"
echo "   Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer Flask directement en mode développement avec rechargement automatique
export FLASK_APP=main:app
export FLASK_ENV=development
export FLASK_DEBUG=1
PYTHONUNBUFFERED=1 flask run --host=0.0.0.0 --port=$PORT --reload
