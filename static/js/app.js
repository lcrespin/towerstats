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

// Variables globales pour le filtrage
// filteredSessions est initialisé dans le script inline du HTML
// Si elle n'existe pas encore, on l'initialise ici
if (typeof filteredSessions === 'undefined') {
    filteredSessions = [];
}
let currentPlayerFilter = '';
let currentGroupFilter = '';

// Filtrer les sessions selon les critères sélectionnés
function filterSessions() {
    if (typeof allSessions === 'undefined') {
        return;
    }
    
    filteredSessions = allSessions.filter(function(session) {
        // Filtre par joueur
        if (currentPlayerFilter) {
            const hasPlayer = session.players.some(function(p) {
                return p.name === currentPlayerFilter;
            });
            if (!hasPlayer) {
                return false;
            }
        }
        
        // Filtre par groupe
        if (currentGroupFilter) {
            const sessionGroup = session.group || session.id;
            if (sessionGroup !== currentGroupFilter) {
                return false;
            }
        }
        
        return true;
    });
    
    // Réinitialiser à la page 1 après filtrage
    currentPage = 1;
    updatePagination();
    renderSessions();
}

// Mettre à jour la pagination
function updatePagination() {
    totalPages = Math.ceil(filteredSessions.length / sessionsPerPage);
    if (totalPages === 0) {
        totalPages = 1;
    }
    if (currentPage > totalPages) {
        currentPage = totalPages;
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
    
    // S'assurer que filteredSessions est initialisé
    if (filteredSessions.length === 0 && allSessions.length > 0) {
        filteredSessions = allSessions.slice();
        updatePagination();
    }
    
    if (filteredSessions.length === 0) {
        container.innerHTML = '<div class="session-card p-2 sm:p-4 md:p-[15px] text-center" style="color: #ffd700;">Aucune session trouvée avec ces filtres.</div>';
        updatePaginationControls();
        return;
    }
    
    const start = (currentPage - 1) * sessionsPerPage;
    const end = start + sessionsPerPage;
    const pageSessions = filteredSessions.slice(start, end);
    
    pageSessions.forEach(function(session) {
        const sessionCard = document.createElement('div');
        sessionCard.className = 'session-card p-2 sm:p-4 md:p-[15px]';
        var tableRows = '';
        session.players.forEach(function(p, index) {
            var rank = index + 1;
            var rankClass = rank <= 3 ? 'rank-' + rank : '';
            var color = getPlayerColor(p.name);
            var medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
            tableRows += '<tr><td class="' + rankClass + '" style="color: ' + color + '; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">' + medal + ' ' + p.name + '</td><td class="' + rankClass + '">' + p.today + '</td><td class="' + rankClass + '">' + p.total + '</td></tr>';
        });
        sessionCard.innerHTML = '<div class="text-[7px] sm:text-[8px] md:text-[10px] mb-3 sm:mb-4" style="color: #ffd700;">Session: ' + session.id + ' - ' + (session.formatted_date || session.date) + '</div><div class="overflow-x-auto"><table class="ranking-table w-full text-[5px] sm:text-[6px] md:text-[9px]"><thead><tr><th>Joueur</th><th>Session</th><th>Total</th></tr></thead><tbody>' + tableRows + '</tbody></table></div>';
        container.appendChild(sessionCard);
    });
    
    updatePaginationControls();
}

// Mettre à jour les contrôles de pagination
function updatePaginationControls() {
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

// Variable pour suivre si les filtres ont été initialisés
let filtersInitialized = false;

// Initialiser les listes déroulantes de filtrage
function initFilters() {
    if (typeof allSessions === 'undefined' || allSessions.length === 0) {
        // Initialiser quand même filteredSessions pour éviter les erreurs
        filteredSessions = [];
        return;
    }
    
    // Toujours initialiser filteredSessions, même si les filtres sont déjà initialisés
    if (filteredSessions.length === 0 && !currentPlayerFilter && !currentGroupFilter) {
        filteredSessions = allSessions.slice();
    }
    
    // Ne pas réinitialiser les listes déroulantes si déjà fait
    if (filtersInitialized) {
        updatePagination();
        return;
    }
    
    // Extraire tous les joueurs uniques
    const allPlayers = new Set();
    const allGroups = new Set();
    
    allSessions.forEach(function(session) {
        // Le groupe peut être dans session.group ou session.id
        const group = session.group || session.id;
        if (group) {
            allGroups.add(group);
        }
        if (session.players && session.players.length > 0) {
            session.players.forEach(function(p) {
                allPlayers.add(p.name);
            });
        }
    });
    
    // Trier les joueurs et groupes
    const sortedPlayers = Array.from(allPlayers).sort();
    const sortedGroups = Array.from(allGroups).sort();
    
    // Remplir la liste déroulante des joueurs
    const playerSelect = document.getElementById('filter-player');
    if (playerSelect && playerSelect.children.length === 1) { // Seulement si pas déjà rempli
        sortedPlayers.forEach(function(player) {
            const option = document.createElement('option');
            option.value = player;
            option.textContent = player;
            playerSelect.appendChild(option);
        });
        
        playerSelect.addEventListener('change', function() {
            currentPlayerFilter = this.value;
            filterSessions();
        });
    }
    
    // Remplir la liste déroulante des groupes
    const groupSelect = document.getElementById('filter-group');
    if (groupSelect && groupSelect.children.length === 1) { // Seulement si pas déjà rempli
        sortedGroups.forEach(function(group) {
            const option = document.createElement('option');
            option.value = group;
            option.textContent = group;
            groupSelect.appendChild(option);
        });
        
        groupSelect.addEventListener('change', function() {
            currentGroupFilter = this.value;
            filterSessions();
        });
    }
    
    // Initialiser les sessions filtrées avec toutes les sessions si pas déjà fait
    if (filteredSessions.length === 0) {
        filteredSessions = allSessions.slice();
    }
    updatePagination();
    filtersInitialized = true;
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
            
            const isVisible = !container.classList.contains('hidden');
            if (isVisible) {
                container.classList.add('hidden');
                this.textContent = '▼ Voir toutes les sessions';
            } else {
                container.classList.remove('hidden');
                this.textContent = '▲ Masquer toutes les sessions';
                
                // Initialiser les filtres et filteredSessions
                initFilters();
                
                // S'assurer que filteredSessions est initialisé
                if (filteredSessions.length === 0 && typeof allSessions !== 'undefined' && allSessions.length > 0) {
                    filteredSessions = allSessions.slice();
                    updatePagination();
                }
                
                // Rendre les sessions
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

