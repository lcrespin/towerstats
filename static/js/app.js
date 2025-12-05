// Fonction pour obtenir la couleur d'un joueur
function getPlayerColor(playerName) {
    if (typeof playerColors === 'undefined') {
        return '#FFD700'; // Or par défaut
    }
    return playerColors[playerName.toUpperCase()] || '#FFD700';
}

// Mise à jour du classement par groupe
function updateRanking(groupId) {
    if (typeof rankingsByGroup === 'undefined') {
        return;
    }
    const ranking = rankingsByGroup[groupId] || [];
    const tbody = document.getElementById('ranking-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    ranking.forEach((playerData, index) => {
        const rank = index + 1;
        const rankClass = rank <= 3 ? `rank-${rank}` : '';
        const playerName = playerData[0];
        const playerColor = getPlayerColor(playerName);
        const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="${rankClass}" style="color: ${playerColor}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">${medal} ${playerName}</td>
            <td class="${rankClass}">${playerData[1]}</td>
        `;
        tbody.appendChild(row);
    });
}

// Initialisation du sélecteur de groupe
function initGroupSelector() {
    const groupSelect = document.getElementById('group-select');
    if (groupSelect) {
        groupSelect.addEventListener('change', function() {
            updateRanking(this.value);
        });
    }
}

// Rendu des sessions avec pagination
function renderSessions() {
    if (typeof allSessions === 'undefined') {
        return;
    }
    
    const container = document.getElementById('all-sessions-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    const start = (currentPage - 1) * sessionsPerPage;
    const end = start + sessionsPerPage;
    const pageSessions = allSessions.slice(start, end);
    
    pageSessions.forEach(function(session) {
        const sessionCard = document.createElement('div');
        sessionCard.className = 'session-card';
        var tableRows = '';
        session.players.forEach(function(p, index) {
            var rank = index + 1;
            var rankClass = rank <= 3 ? 'rank-' + rank : '';
            var color = getPlayerColor(p.name);
            var medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
            tableRows += '<tr><td class="' + rankClass + '" style="color: ' + color + '; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">' + medal + ' ' + p.name + '</td><td class="' + rankClass + '">' + p.today + '</td><td class="' + rankClass + '">' + p.total + '</td></tr>';
        });
        sessionCard.innerHTML = '<div style="color: #ffd700; margin-bottom: 15px; font-size: 10px;">Session: ' + session.id + ' - ' + session.date + '</div><table class="ranking-table"><thead><tr><th>Joueur</th><th>Session</th><th>Total</th></tr></thead><tbody>' + tableRows + '</tbody></table>';
        container.appendChild(sessionCard);
    });
    
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (pageInfo) {
        pageInfo.textContent = `${currentPage} / ${totalPages}`;
    }
    if (prevBtn) {
        prevBtn.disabled = currentPage === 1;
    }
    if (nextBtn) {
        nextBtn.disabled = currentPage === totalPages;
    }
}

// Initialisation de la pagination des sessions
function initSessionsPagination() {
    if (typeof allSessions === 'undefined') {
        return;
    }
    
    const toggleBtn = document.getElementById('toggle-all-sessions');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const container = document.getElementById('all-sessions-container');
            if (!container) return;
            
            const isVisible = container.style.display !== 'none';
            container.style.display = isVisible ? 'none' : 'block';
            this.textContent = isVisible ? '▼ Voir toutes les sessions' : '▲ Masquer toutes les sessions';
            
            if (!isVisible && currentPage === 1) {
                renderSessions();
            }
        });
    }
    
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                renderSessions();
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            if (currentPage < totalPages) {
                currentPage++;
                renderSessions();
            }
        });
    }
}

// Smooth scroll pour le menu
function initSmoothScroll() {
    document.querySelectorAll('nav a').forEach(function(anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// Initialisation globale quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    initGroupSelector();
    initSessionsPagination();
    initSmoothScroll();
});

