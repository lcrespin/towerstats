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

// Initialisation du tableau de kills
function initRankingTable() {
    const toggleRankingTable = document.getElementById('toggle-ranking-table');
    if (toggleRankingTable) {
        toggleRankingTable.addEventListener('click', function() {
            const rankingTable = document.getElementById('ranking-table');
            if (rankingTable) {
                rankingTable.classList.toggle('hidden');
            }
            if (rankingTable.classList.contains('hidden')) {
                toggleRankingTable.textContent = '▼ Voir le détail des kills';
            } else {
                toggleRankingTable.textContent = '▲ Masquer le détail des kills';
            }
        });
    }
    initKillDetailTableSort();
}

function initKillDetailTableSort() {
    const table = document.getElementById('kill-detail-table');
    if (!table || !table.tBodies.length) return;
    const tbody = table.tBodies[0];
    const headers = table.querySelectorAll('thead th.sortable-th');
    headers.forEach(function(th) {
        th.addEventListener('click', function() {
            const col = parseInt(th.getAttribute('data-col'), 10);
            const type = th.getAttribute('data-sort-type') || 'number';
            const prevCol = parseInt(table.getAttribute('data-sort-col'), 10);
            const prevDir = table.getAttribute('data-sort-dir') || 'asc';
            const dir = (prevCol === col && prevDir === 'asc') ? 'desc' : 'asc';
            table.setAttribute('data-sort-col', col);
            table.setAttribute('data-sort-dir', dir);
            table.querySelectorAll('thead .sort-indicator').forEach(function(ind) { ind.textContent = ''; });
            th.querySelector('.sort-indicator').textContent = dir === 'asc' ? '▲' : '▼';
            var rows = Array.prototype.slice.call(tbody.rows);
            rows.sort(function(a, b) {
                var aCell = a.cells[col];
                var bCell = b.cells[col];
                if (!aCell || !bCell) return 0;
                var aVal = (type === 'number') ? parseFloat(aCell.textContent.replace(/\s/g, '').replace(',', '.')) : (aCell.textContent || '').trim();
                var bVal = (type === 'number') ? parseFloat(bCell.textContent.replace(/\s/g, '').replace(',', '.')) : (bCell.textContent || '').trim();
                if (type === 'number') {
                    if (isNaN(aVal)) aVal = -Infinity;
                    if (isNaN(bVal)) bVal = -Infinity;
                    return dir === 'asc' ? aVal - bVal : bVal - aVal;
                }
                var cmp = (aVal < bVal) ? -1 : (aVal > bVal) ? 1 : 0;
                return dir === 'asc' ? cmp : -cmp;
            });
            rows.forEach(function(row) { tbody.appendChild(row); });
        });
    });
}

// Initialisation du toggle ELO legacy
function initEloLegacyToggle() {
    const toggleEloLegacy = document.getElementById('toggle-elo-legacy');
    if (toggleEloLegacy) {
        toggleEloLegacy.addEventListener('click', function() {
            const eloLegacyContainer = document.getElementById('elo-legacy-container');
            if (eloLegacyContainer) {
                eloLegacyContainer.classList.toggle('hidden');
            }
            if (eloLegacyContainer.classList.contains('hidden')) {
                toggleEloLegacy.textContent = '▼ ELO legacy';
            } else {
                toggleEloLegacy.textContent = '▲ Masquer ELO legacy';
            }
        });
    }
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

// Handlers pour les filtres (stockés pour pouvoir les supprimer)
let playerFilterHandler = null;
let groupFilterHandler = null;
let filtersListenersAttached = false;

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
    updateSessionsCount();
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

// Mettre à jour le compteur de sessions
function updateSessionsCount() {
    const countElement = document.getElementById('sessions-count-value');
    if (countElement) {
        const total = filteredSessions ? filteredSessions.length : 0;
        countElement.textContent = total;
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
        updateSessionsCount();
    }
    
    if (filteredSessions.length === 0) {
        container.innerHTML = '<div class="session-card p-2 sm:p-4 md:p-[15px] text-center" style="color: #ffd700;">Aucune session trouvée avec ces filtres.</div>';
        updatePaginationControls();
        updateSessionsCount();
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
        updateSessionsCount();
    }
    
    // Si les filtres sont déjà initialisés, synchroniser seulement les valeurs des selects
    // IMPORTANT: Ne pas réinitialiser les selects à vide, seulement synchroniser si la variable a une valeur
    if (filtersInitialized) {
        const playerSelect = document.getElementById('filter-player');
        if (playerSelect) {
            // Synchroniser la valeur du select avec la variable seulement si la variable a une valeur
            // Ne pas réinitialiser à vide pour préserver la sélection de l'utilisateur
            if (currentPlayerFilter && playerSelect.value !== currentPlayerFilter) {
                playerSelect.value = currentPlayerFilter;
            }
        }
        
        const groupSelect = document.getElementById('filter-group');
        if (groupSelect) {
            // Synchroniser la valeur du select avec la variable seulement si la variable a une valeur
            // Ne pas réinitialiser à vide pour préserver la sélection de l'utilisateur
            if (currentGroupFilter && groupSelect.value !== currentGroupFilter) {
                groupSelect.value = currentGroupFilter;
            }
        }
        
        updatePagination();
        updateSessionsCount();
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
    if (playerSelect) {
        // Remplir seulement si pas déjà rempli
        if (playerSelect.children.length === 1) {
            sortedPlayers.forEach(function(player) {
                const option = document.createElement('option');
                option.value = player;
                option.textContent = player;
                playerSelect.appendChild(option);
            });
        }
        
        // Synchroniser la valeur du select avec la variable (sans déclencher l'event)
        // IMPORTANT: Lire la valeur actuelle du select et la mettre dans la variable si elle n'est pas vide
        // Cela préserve la sélection de l'utilisateur même si la variable était vide
        if (playerSelect.value && !currentPlayerFilter) {
            currentPlayerFilter = playerSelect.value;
        }
        // Sinon, synchroniser le select avec la variable si la variable a une valeur
        else if (currentPlayerFilter && playerSelect.value !== currentPlayerFilter) {
            playerSelect.value = currentPlayerFilter;
        }
        
        // Attacher le listener seulement s'il n'est pas déjà attaché
        if (!filtersListenersAttached) {
            playerFilterHandler = function() {
                currentPlayerFilter = this.value;
                // Si un joueur est sélectionné, réinitialiser le filtre groupe
                if (currentPlayerFilter) {
                    currentGroupFilter = '';
                    const groupSelect = document.getElementById('filter-group');
                    if (groupSelect) {
                        groupSelect.value = '';
                    }
                }
                filterSessions();
            };
            playerSelect.addEventListener('change', playerFilterHandler);
        }
    }
    
    // Remplir la liste déroulante des groupes
    const groupSelect = document.getElementById('filter-group');
    if (groupSelect) {
        // Remplir seulement si pas déjà rempli
        if (groupSelect.children.length === 1) {
            sortedGroups.forEach(function(group) {
                const option = document.createElement('option');
                option.value = group;
                option.textContent = group;
                groupSelect.appendChild(option);
            });
        }
        
        // Synchroniser la valeur du select avec la variable (sans déclencher l'event)
        // IMPORTANT: Lire la valeur actuelle du select et la mettre dans la variable si elle n'est pas vide
        // Cela préserve la sélection de l'utilisateur même si la variable était vide
        if (groupSelect.value && !currentGroupFilter) {
            currentGroupFilter = groupSelect.value;
        }
        // Sinon, synchroniser le select avec la variable si la variable a une valeur
        else if (currentGroupFilter && groupSelect.value !== currentGroupFilter) {
            groupSelect.value = currentGroupFilter;
        }
        
        // Attacher le listener seulement s'il n'est pas déjà attaché
        if (!filtersListenersAttached) {
            groupFilterHandler = function() {
                currentGroupFilter = this.value;
                // Si un groupe est sélectionné, réinitialiser le filtre joueur
                if (currentGroupFilter) {
                    currentPlayerFilter = '';
                    const playerSelect = document.getElementById('filter-player');
                    if (playerSelect) {
                        playerSelect.value = '';
                    }
                }
                filterSessions();
            };
            groupSelect.addEventListener('change', groupFilterHandler);
            filtersListenersAttached = true;
        }
    }
    
    // Initialiser les sessions filtrées avec toutes les sessions si pas déjà fait
    if (filteredSessions.length === 0) {
        filteredSessions = allSessions.slice();
    }
    updatePagination();
    updateSessionsCount();
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
                    updateSessionsCount();
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

// Smooth scroll pour le menu (in-page anchors only)
function initSmoothScroll() {
    document.querySelectorAll('nav a').forEach(function(anchor) {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href') || '';
            if (href.indexOf('#') !== 0) {
                return;
            }
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// Graphique d'évolution des scores
let evolutionChart = null;

// Initialiser le graphique d'évolution
function initEvolutionChart() {
    if (typeof allSessions === 'undefined' || allSessions.length === 0) {
        return;
    }

    // Récupérer tous les groupes uniques
    const allGroups = new Set();
    allSessions.forEach(function(session) {
        const group = session.group || session.id;
        if (group) {
            allGroups.add(group);
        }
    });

    // Trier les groupes par le meilleur score du groupe (décroissant)
    const sortedGroups = Array.from(allGroups).sort(function(a, b) {
        const rankingA = rankingsByGroup[a] || [];
        const rankingB = rankingsByGroup[b] || [];
        const bestScoreA = rankingA.length > 0 ? rankingA[0][1] : 0;
        const bestScoreB = rankingB.length > 0 ? rankingB[0][1] : 0;
        return bestScoreB - bestScoreA; // Décroissant
    });

    // Remplir le sélecteur de groupe
    const groupSelect = document.getElementById('evolution-group-select');
    const cumulCheckbox = document.getElementById('evolution-cumul-checkbox');
    
    if (groupSelect) {
        sortedGroups.forEach(function(group) {
            const option = document.createElement('option');
            option.value = group;
            option.textContent = group;
            groupSelect.appendChild(option);
        });

        // Écouter les changements du sélecteur
        groupSelect.addEventListener('change', function() {
            const isCumul = cumulCheckbox ? cumulCheckbox.checked : true;
            updateEvolutionChart(this.value, isCumul);
        });
        
        // Écouter les changements de la case à cocher
        if (cumulCheckbox) {
            cumulCheckbox.addEventListener('change', function() {
                const groupId = groupSelect.value;
                if (groupId) {
                    updateEvolutionChart(groupId, this.checked);
                }
            });
        }

        // Initialiser avec le premier groupe si disponible
        if (sortedGroups.length > 0) {
            groupSelect.value = sortedGroups[0];
            const isCumul = cumulCheckbox ? cumulCheckbox.checked : true;
            updateEvolutionChart(sortedGroups[0], isCumul);
        }
    }
}

// Mettre à jour le graphique d'évolution
function updateEvolutionChart(groupId, isCumul) {
    if (typeof allSessions === 'undefined' || !groupId) {
        return;
    }
    
    // Par défaut, utiliser le mode cumul si non spécifié
    if (typeof isCumul === 'undefined') {
        const cumulCheckbox = document.getElementById('evolution-cumul-checkbox');
        isCumul = cumulCheckbox ? cumulCheckbox.checked : true;
    }

    // Filtrer les sessions du groupe sélectionné
    const groupSessions = allSessions.filter(function(session) {
        const sessionGroup = session.group || session.id;
        return sessionGroup === groupId;
    });

    if (groupSessions.length === 0) {
        return;
    }

    // Organiser les données par date
    const dataByDate = {};
    const dateMapping = {}; // Mapping date originale -> date formatée
    const allPlayers = new Set();

    groupSessions.forEach(function(session) {
        const originalDate = session.date; // Format YYYY-MM-DD pour le tri
        const formattedDate = session.formatted_date || session.date;
        
        // Utiliser la date originale comme clé pour le tri
        if (!dataByDate[originalDate]) {
            dataByDate[originalDate] = {};
            dateMapping[originalDate] = formattedDate;
        }
        
        if (session.players) {
            session.players.forEach(function(player) {
                allPlayers.add(player.name);
                // Utiliser total pour cumul, today pour session
                const value = isCumul ? (player.total || 0) : (player.today || 0);
                if (!dataByDate[originalDate][player.name]) {
                    dataByDate[originalDate][player.name] = 0;
                }
                dataByDate[originalDate][player.name] = value;
            });
        }
    });

    // Trier les dates par date originale (format YYYY-MM-DD)
    // pour avoir la plus ancienne à gauche, la plus récente à droite
    const sortedOriginalDates = Object.keys(dataByDate).sort();
    const sortedDates = sortedOriginalDates.map(function(originalDate) {
        return dateMapping[originalDate];
    });
    const sortedPlayers = Array.from(allPlayers).sort();

    // Préparer les données pour Chart.js
    const datasets = sortedPlayers.map(function(player) {
        const data = sortedOriginalDates.map(function(originalDate) {
            return dataByDate[originalDate][player] || 0;
        });
        return {
            label: player,
            data: data,
            backgroundColor: getPlayerColor(player),
            borderColor: getPlayerColor(player),
            borderWidth: 1
        };
    });

    // Obtenir le canvas
    const canvas = document.getElementById('evolution-chart');
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext('2d');

    // Détruire le graphique existant s'il existe
    if (evolutionChart) {
        evolutionChart.destroy();
    }

    // Créer le nouveau graphique
    evolutionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: isCumul ? 'Points totaux' : 'Points par session',
                        color: '#ffd700',
                        font: {
                            family: 'Press Start 2P',
                            size: 8
                        }
                    },
                    ticks: {
                        color: '#ffd700',
                        font: {
                            family: 'Press Start 2P',
                            size: 6
                        }
                    },
                    grid: {
                        color: 'rgba(139, 69, 19, 0.3)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Dates',
                        color: '#ffd700',
                        font: {
                            family: 'Press Start 2P',
                            size: 8
                        }
                    },
                    ticks: {
                        color: '#ffd700',
                        font: {
                            family: 'Press Start 2P',
                            size: 6
                        },
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        color: 'rgba(139, 69, 19, 0.3)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#ffd700',
                        font: {
                            family: 'Press Start 2P',
                            size: 6
                        },
                        usePointStyle: true,
                        padding: 10
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(45, 27, 61, 0.9)',
                    titleColor: '#ffd700',
                    bodyColor: '#ffd700',
                    borderColor: '#8b4513',
                    borderWidth: 2,
                    titleFont: {
                        family: 'Press Start 2P',
                        size: 8
                    },
                    bodyFont: {
                        family: 'Press Start 2P',
                        size: 7
                    },
                    padding: 10
                }
            }
        }
    });
}

// Initialisation des info-bulles
function initInfoBubbles() {
    const infoButtons = document.querySelectorAll('.info-button');
    
    infoButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const infoId = this.getAttribute('data-info');
            const infoBubble = document.getElementById(infoId);
            
            if (infoBubble) {
                // Fermer toutes les autres info-bulles
                document.querySelectorAll('.info-bubble').forEach(function(bubble) {
                    if (bubble.id !== infoId) {
                        bubble.classList.remove('active');
                    }
                });
                
                // Calculer la position de l'info-bulle par rapport au bouton
                const buttonRect = this.getBoundingClientRect();
                const bubbleWidth = Math.min(400, window.innerWidth - 40);
                const maxHeight = Math.min(window.innerHeight * 0.8, 600);
                
                // Toggle l'info-bulle actuelle d'abord pour calculer sa taille
                const isActive = infoBubble.classList.contains('active');
                infoBubble.classList.toggle('active');
                
                // Positionner l'info-bulle sous le bouton (vers le bas)
                setTimeout(function() {
                    const spaceBelow = window.innerHeight - buttonRect.bottom;
                    const spaceAbove = buttonRect.top;
                    const availableHeight = Math.min(maxHeight, Math.max(spaceBelow - 20, spaceAbove - 20));
                    
                    // Définir la hauteur maximale pour éviter de dépasser
                    infoBubble.style.maxHeight = availableHeight + 'px';
                    
                    // Si pas assez d'espace en bas, afficher au-dessus
                    if (spaceBelow < 200 && spaceAbove > spaceBelow) {
                        const topPosition = Math.max(10, buttonRect.top - availableHeight - 10);
                        infoBubble.style.top = topPosition + 'px';
                        infoBubble.style.bottom = 'auto';
                    } else {
                        // Afficher en bas par défaut
                        infoBubble.style.top = (buttonRect.bottom + 10) + 'px';
                        infoBubble.style.bottom = 'auto';
                    }
                    
                    // Position horizontale
                    infoBubble.style.right = (window.innerWidth - buttonRect.right) + 'px';
                    infoBubble.style.maxWidth = bubbleWidth + 'px';
                    
                    // Ajuster si l'info-bulle dépasse à droite
                    const finalRect = infoBubble.getBoundingClientRect();
                    if (finalRect.right > window.innerWidth - 10) {
                        infoBubble.style.right = '10px';
                    }
                    
                    // S'assurer que l'info-bulle ne dépasse pas en bas
                    if (finalRect.bottom > window.innerHeight - 10) {
                        const newTop = Math.max(10, window.innerHeight - availableHeight - 10);
                        infoBubble.style.top = newTop + 'px';
                    }
                }, 10);
            }
        });
    });
    
    // Fermer les info-bulles quand on clique ailleurs
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.info-button') && !e.target.closest('.info-bubble')) {
            document.querySelectorAll('.info-bubble').forEach(function(bubble) {
                bubble.classList.remove('active');
            });
        }
    });
    
    // Ajuster la position lors du scroll
    window.addEventListener('scroll', function() {
        document.querySelectorAll('.info-bubble.active').forEach(function(bubble) {
            const button = document.querySelector('[data-info="' + bubble.id + '"]');
            if (button) {
                const buttonRect = button.getBoundingClientRect();
                bubble.style.top = (buttonRect.bottom + 10) + 'px';
                bubble.style.right = (window.innerWidth - buttonRect.right) + 'px';
            }
        });
    });
}

// Graphiques pour les sources de kills
let killSourcesGlobalChart = null;
let killSourcesByPlayerChart = null;

// Initialiser les graphiques de sources de kills
function initKillSourcesCharts() {
    if (!hasDetailedStats || !killSourcesAggregated) {
        return;
    }
    
    // Graphique global (camembert)
    const globalCanvas = document.getElementById('kill-sources-global-chart');
    if (globalCanvas) {
        const globalSources = killSourcesAggregated.global || {};
        const labels = Object.keys(globalSources);
        const data = Object.values(globalSources);
        
        // Couleurs pour le graphique
        const colors = [
            'rgba(255, 99, 132, 0.8)',
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(153, 102, 255, 0.8)',
            'rgba(255, 159, 64, 0.8)',
            'rgba(199, 199, 199, 0.8)',
            'rgba(83, 102, 255, 0.8)',
            'rgba(255, 99, 255, 0.8)',
            'rgba(99, 255, 132, 0.8)'
        ];
        
        const ctx = globalCanvas.getContext('2d');
        
        if (killSourcesGlobalChart) {
            killSourcesGlobalChart.destroy();
        }
        
        killSourcesGlobalChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: '#8b4513',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        labels: {
                            color: '#ffd700',
                            font: {
                                family: 'Press Start 2P',
                                size: 8
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(45, 27, 61, 0.9)',
                        titleColor: '#ffd700',
                        bodyColor: '#ffd700',
                        borderColor: '#8b4513',
                        borderWidth: 2,
                        titleFont: {
                            family: 'Press Start 2P',
                            size: 8
                        },
                        bodyFont: {
                            family: 'Press Start 2P',
                            size: 7
                        },
                        padding: 10
                    }
                }
            }
        });
    }
    
    // Graphique par joueur (barres empilées)
    const byPlayerCanvas = document.getElementById('kill-sources-by-player-chart');
    if (byPlayerCanvas) {
        const byPlayer = killSourcesAggregated.by_player || {};
        const players = Object.keys(byPlayer);
        const allSources = new Set();
        
        // Collecter toutes les sources uniques
        players.forEach(function(player) {
            Object.keys(byPlayer[player]).forEach(function(source) {
                allSources.add(source);
            });
        });
        
        const sources = Array.from(allSources).sort();
        
        // Couleurs pour chaque source
        const sourceColors = {
            'Arrow': 'rgba(255, 99, 132, 0.8)',
            'JumpedOn': 'rgba(54, 162, 235, 0.8)',
            'Explosion': 'rgba(255, 206, 86, 0.8)',
            'Lava': 'rgba(255, 99, 99, 0.8)',
            'Brambles': 'rgba(75, 192, 192, 0.8)',
            'FallingObject': 'rgba(153, 102, 255, 0.8)',
            'Shock': 'rgba(255, 159, 64, 0.8)',
            'Squish': 'rgba(199, 199, 199, 0.8)',
            'SpikeBall': 'rgba(83, 102, 255, 0.8)',
            'Miasma': 'rgba(255, 99, 255, 0.8)'
        };
        
        // Créer les datasets pour chaque source
        const datasets = sources.map(function(source) {
            const data = players.map(function(player) {
                return byPlayer[player][source] || 0;
            });
            return {
                label: source,
                data: data,
                backgroundColor: sourceColors[source] || 'rgba(128, 128, 128, 0.8)',
                borderColor: '#8b4513',
                borderWidth: 1
            };
        });
        
        const ctx = byPlayerCanvas.getContext('2d');
        
        if (killSourcesByPlayerChart) {
            killSourcesByPlayerChart.destroy();
        }
        
        killSourcesByPlayerChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: players.map(function(p) {
                    return p;
                }),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Joueurs',
                            color: '#ffd700',
                            font: {
                                family: 'Press Start 2P',
                                size: 8
                            }
                        },
                        ticks: {
                            color: '#ffd700',
                            font: {
                                family: 'Press Start 2P',
                                size: 6
                            }
                        },
                        grid: {
                            color: 'rgba(139, 69, 19, 0.3)'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Kills (moy. par partie)',
                            color: '#ffd700',
                            font: {
                                family: 'Press Start 2P',
                                size: 8
                            }
                        },
                        ticks: {
                            color: '#ffd700',
                            font: {
                                family: 'Press Start 2P',
                                size: 6
                            }
                        },
                        grid: {
                            color: 'rgba(139, 69, 19, 0.3)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#ffd700',
                            font: {
                                family: 'Press Start 2P',
                                size: 6
                            },
                            usePointStyle: true,
                            padding: 10
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(45, 27, 61, 0.9)',
                        titleColor: '#ffd700',
                        bodyColor: '#ffd700',
                        borderColor: '#8b4513',
                        borderWidth: 2,
                        titleFont: {
                            family: 'Press Start 2P',
                            size: 8
                        },
                        bodyFont: {
                            family: 'Press Start 2P',
                            size: 7
                        },
                        padding: 10,
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                const v = context.raw;
                                if (v == null || v === 0) return null;
                                return context.dataset.label + ': ' + Number(v).toFixed(2) + ' (moy. part.)';
                            }
                        }
                    }
                }
            }
        });
    }
}

// Initialisation globale quand le DOM est prêt
function initDatePickerToggle() {
    const toggleBtn = document.getElementById('toggle-date-picker');
    const popover = document.getElementById('date-picker-popover');
    const closeBtn = popover && popover.querySelector('.date-picker-close');
    if (!toggleBtn || !popover) return;

    function openPopover() {
        popover.classList.add('active');
        popover.setAttribute('aria-hidden', 'false');
    }

    function closePopover() {
        popover.classList.remove('active');
        popover.setAttribute('aria-hidden', 'true');
    }

    toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (popover.classList.contains('active')) {
            closePopover();
        } else {
            openPopover();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', closePopover);
    }

    document.addEventListener('click', function(e) {
        if (popover.classList.contains('active') && !popover.contains(e.target) && e.target !== toggleBtn) {
            closePopover();
        }
    });
}

function initMobileMenu() {
    const toggle = document.getElementById('mobile-menu-toggle');
    const menu = document.getElementById('mobile-menu');
    const links = menu && menu.querySelectorAll('.mobile-menu-link');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', function() {
        const isOpen = menu.classList.toggle('mobile-menu-open');
        toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        menu.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
    });

    if (links) {
        links.forEach(function(link) {
            link.addEventListener('click', function() {
                menu.classList.remove('mobile-menu-open');
                toggle.setAttribute('aria-expanded', 'false');
                menu.setAttribute('aria-hidden', 'true');
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initRankingTable();
    initEloLegacyToggle();
    initDatePickerToggle();
    initMobileMenu();
    initGroupSelector();
    initSessionsPagination();
    initSmoothScroll();
    initEvolutionChart();
    initInfoBubbles();
    if (hasDetailedStats) {
        initKillSourcesCharts();
    }
});

