// Fonction pour obtenir la couleur d'un joueur
function getPlayerColor(playerName) {
    if (typeof playerColors === 'undefined') {
        return '#FFD700'; // Or par défaut
    }
    return playerColors[playerName.toUpperCase()] || '#FFD700';
}

// Mise à jour du classement par groupe
function getMedal(rank) {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return '';
}

function buildPodiumSlotHtml(rank, player, value, detail) {
    if (!player) {
        return '<div class="pixel-podium-slot pixel-podium-slot--' + rank + ' pixel-podium-slot--empty"></div>';
    }
    var color = getPlayerColor(player);
    return '<div class="pixel-podium-slot pixel-podium-slot--' + rank + '">' +
        '<div class="pixel-podium-medal">' + getMedal(rank) + '</div>' +
        '<div class="player-avatar" style="--player-color: ' + color + ';">' + player.charAt(0) + '</div>' +
        '<div class="pixel-podium-name" style="color: ' + color + ';">' + player + '</div>' +
        '<div class="pixel-podium-value led-value">' + value + '</div>' +
        '<div class="pixel-podium-detail">' + detail + '</div>' +
        '</div>';
}

function renderGroupPodium(ranking) {
    var podium = document.getElementById('group-podium');
    if (!podium) return;
    var order = [2, 1, 3];
    var html = '';
    order.forEach(function(pRank) {
        var item = ranking[pRank - 1];
        if (item) {
            html += buildPodiumSlotHtml(item[0], item[1], item[2], 'victoires');
        } else {
            html += buildPodiumSlotHtml(pRank, null, '', '');
        }
    });
    podium.innerHTML = html;
}

function updateRanking(groupId) {
    if (typeof rankingsByGroup === 'undefined') {
        return;
    }
    const ranking = rankingsByGroup[groupId] || [];
    const tbody = document.getElementById('ranking-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    ranking.forEach((playerData) => {
        const rank = playerData[0];
        const rankClass = rank <= 3 ? `rank-${rank}` : '';
        const playerName = playerData[1];
        const playerColor = getPlayerColor(playerName);
        const medal = getMedal(rank);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="player-column ${rankClass}" style="color: ${playerColor}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">${medal} ${playerName}</td>
            <td class="${rankClass}">${playerData[2]}</td>
        `;
        tbody.appendChild(row);
    });
    renderGroupPodium(ranking);
}

// Make a single table sortable by column (for tables with 3+ columns)
function makeTableSortable(table) {
    const thead = table.querySelector('thead');
    if (!thead) return;
    const ths = thead.querySelectorAll('th');
    if (ths.length < 3) return;
    if (table.getAttribute('data-sortable-inited') === '1') return;

    table.setAttribute('data-sortable-inited', '1');
    const tbody = table.tBodies[0];
    if (!tbody) return;

    ths.forEach(function(th, i) {
        th.classList.add('sortable-th');
        th.setAttribute('data-col', String(i));
        if (!th.hasAttribute('data-sort-type')) {
            th.setAttribute('data-sort-type', i === 0 ? 'text' : 'number');
        }
        if (!th.querySelector('.sort-indicator')) {
            const span = document.createElement('span');
            span.className = 'sort-indicator';
            th.appendChild(span);
        }
    });

    const headers = table.querySelectorAll('thead th.sortable-th');
    headers.forEach(function(th) {
        th.addEventListener('click', function() {
            const col = parseInt(th.getAttribute('data-col'), 10);
            const type = th.getAttribute('data-sort-type') || 'number';
            const prevCol = parseInt(table.getAttribute('data-sort-col'), 10);
            const prevDir = table.getAttribute('data-sort-dir') || 'desc';
            const dir = (prevCol === col && prevDir === 'desc') ? 'asc' : 'desc';
            table.setAttribute('data-sort-col', col);
            table.setAttribute('data-sort-dir', dir);
            table.querySelectorAll('thead .sort-indicator').forEach(function(ind) { ind.textContent = ''; });
            var ind = th.querySelector('.sort-indicator');
            if (ind) ind.textContent = dir === 'asc' ? '▲' : '▼';
            var rows = Array.prototype.slice.call(tbody.rows);
            rows.sort(function(a, b) {
                var aCell = a.cells[col];
                var bCell = b.cells[col];
                if (!aCell || !bCell) return 0;
                var aVal = (type === 'number') ? parseFloat(String(aCell.textContent).replace(/\s/g, '').replace(',', '.')) : (aCell.textContent || '').trim();
                var bVal = (type === 'number') ? parseFloat(String(bCell.textContent).replace(/\s/g, '').replace(',', '.')) : (bCell.textContent || '').trim();
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

// Init sortable for all tables with 3+ columns
function initSortableTables() {
    document.querySelectorAll('table').forEach(function(table) {
        var ths = table.querySelectorAll('thead th');
        if (ths.length >= 3) makeTableSortable(table);
    });
}

// Initialisation du tableau de kills
function initRankingTable() {
    const toggleRankingTable = document.getElementById('toggle-ranking-table');
    if (toggleRankingTable) {
        toggleRankingTable.addEventListener('click', function() {
            var wrapper = document.getElementById('kill-detail-wrapper');
            if (wrapper) {
                wrapper.classList.toggle('hidden');
            }
            if (wrapper && wrapper.classList.contains('hidden')) {
                toggleRankingTable.textContent = '▼ Voir le détail des kills';
            } else {
                toggleRankingTable.textContent = '▲ Masquer le détail des kills';
            }
        });
    }
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
let highlightedSessionKey = null;

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
        container.innerHTML = '<div class="session-card p-2 sm:p-4 md:p-[15px] text-center" style="color: var(--text);">Aucune session trouvée avec ces filtres.</div>';
        updatePaginationControls();
        updateSessionsCount();
        return;
    }
    
    const start = (currentPage - 1) * sessionsPerPage;
    const end = start + sessionsPerPage;
    const pageSessions = filteredSessions.slice(start, end);
    
    pageSessions.forEach(function(session) {
        var highlight = !!highlightedSessionKey && session.session_select_id === highlightedSessionKey;
        container.appendChild(buildSessionCard(session, highlight));
    });
    
    updatePaginationControls();
}

function renderLatestSessions() {
    var container = document.getElementById('latest-sessions-list');
    if (!container || typeof latestSessions === 'undefined') return;
    container.innerHTML = '';
    latestSessions.forEach(function(session) {
        container.appendChild(buildSessionCard(session, false));
    });
}

var KILL_SOURCE_LABELS = {
    'Arrow': 'Flèche',
    'JumpedOn': 'Écrasé',
    'Explosion': 'Explosion',
    'Brambles': 'Ronces',
    'Squish': 'Aplati',
    'Lava': 'Lave',
    'Miasma': 'Miasme',
    'FallingObject': 'Chute d\'objet',
    'SpikeBall': 'Boule à pics',
    'Shock': 'Électrocuté'
};

function playerLabel(name) {
    return '<span style="color: ' + getPlayerColor(name) + ';">' + name + '</span>';
}

function formatRatio(value) {
    return value.toFixed(2).replace('.', ',');
}

function buildSessionHeader(session) {
    var details = session.details || {};
    var parts = [session.formatted_date || session.date];
    if (details.hour != null) parts.push('fin vers ' + details.hour + 'h');
    parts.push(session.game_mode_label || session.game_mode);
    if (details.match_count) parts.push(details.match_count + ' match' + (details.match_count > 1 ? 's' : ''));
    parts.push(session.players.length + ' joueur' + (session.players.length > 1 ? 's' : ''));
    return '<div class="session-card-title">' + session.id + '</div>' +
        '<div class="session-card-meta">' + parts.join(' · ') + '</div>';
}

function buildSessionTable(session) {
    var combat = (session.details && session.details.combat) || {};
    var hasCombat = Object.keys(combat).length > 0;
    var sessionWins = session.players.reduce(function(sum, p) { return sum + p.today; }, 0);
    var head = '<th>Joueur</th><th>Session</th><th>%</th><th>Total</th>';
    if (hasCombat) head += '<th>Kills</th><th>Morts</th><th>Auto</th><th>K/D</th>';
    var rows = '';
    session.players.forEach(function(p) {
        var rank = p.rank != null ? p.rank : 0;
        var rankClass = rank <= 3 ? 'rank-' + rank : '';
        var cell = '<td class="' + rankClass + '">';
        var pct = sessionWins > 0 ? Math.round(100 * p.today / sessionWins) + '%' : '-';
        rows += '<tr><td class="' + rankClass + '" style="color: ' + getPlayerColor(p.name) + '; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">' + getMedal(rank) + ' ' + p.name + '</td>' +
            cell + p.today + '</td>' + cell + pct + '</td>' + cell + p.total + '</td>';
        if (hasCombat) {
            var c = combat[p.name];
            if (c) {
                var kd = c.death > 0 ? formatRatio(c.kill / c.death) : (c.kill > 0 ? '∞' : '-');
                rows += cell + c.kill + '</td>' + cell + c.death + '</td>' + cell + c.self + '</td>' + cell + kd + '</td>';
            } else {
                rows += cell + '-</td>' + cell + '-</td>' + cell + '-</td>' + cell + '-</td>';
            }
        }
        rows += '</tr>';
    });
    return '<div class="overflow-x-auto"><table class="ranking-table w-full text-[5px] sm:text-[6px] md:text-[9px]"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

function buildSessionAwards(awards) {
    if (!awards || awards.length === 0) return '';
    var items = awards.map(function(award) {
        var holders = award.holders.map(function(chain) {
            return chain.map(playerLabel).join(' → ');
        }).join(', ');
        return '<div class="session-award"><span class="session-award-emoji" aria-hidden="true">' + award.emoji + '</span>' +
            '<div><div class="session-award-title">' + award.title + '</div>' +
            '<div class="session-award-holders">' + holders + '</div>' +
            '<div class="session-award-value">' + award.value + ' ' + award.unit + '</div></div></div>';
    }).join('');
    return '<div class="session-awards">' + items + '</div>';
}

function buildDuelMatrix(players, combat) {
    var names = players.map(function(p) { return p.name; }).filter(function(n) { return combat[n]; });
    if (names.length < 2) return '';
    var max = 0;
    names.forEach(function(victim) {
        names.forEach(function(killer) {
            if (killer !== victim) max = Math.max(max, combat[victim].killBy[killer] || 0);
        });
    });
    var head = '<th>Tueur → Victime</th>' + names.map(function(n) { return '<th>' + playerLabel(n) + '</th>'; }).join('');
    var rows = names.map(function(killer) {
        var cells = names.map(function(victim) {
            var count = combat[victim].killBy[killer] || 0;
            if (killer === victim) {
                return '<td class="session-duel-self" title="Auto-kills">' + (count || '-') + '</td>';
            }
            var intensity = max > 0 ? count / max : 0;
            var hue = (1 - intensity) * 120;
            return '<td style="background-color: hsla(' + hue + ', 70%, 52%, 0.40);">' + (count || '-') + '</td>';
        }).join('');
        return '<tr><td>' + playerLabel(killer) + '</td>' + cells + '</tr>';
    }).join('');
    return '<div class="session-detail-block"><h4 class="session-detail-title">🎯 Duels</h4>' +
        '<div class="overflow-x-auto"><table class="ranking-table session-duel-table w-full text-[5px] sm:text-[6px] md:text-[9px]"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
}

function buildDeathCauses(players, combat) {
    var rows = players.filter(function(p) { return combat[p.name]; }).map(function(p) {
        var causes = combat[p.name].killFrom || {};
        var total = Object.keys(causes).reduce(function(sum, k) { return sum + causes[k]; }, 0);
        if (total === 0) return '';
        var sorted = Object.keys(causes).sort(function(a, b) { return causes[b] - causes[a]; });
        var segments = sorted.map(function(source, i) {
            var label = KILL_SOURCE_LABELS[source] || source;
            return '<span class="session-cause-segment session-cause-segment--' + Math.min(i, 4) + '" style="width: ' + (100 * causes[source] / total) + '%;" title="' + label + ' : ' + causes[source] + '"></span>';
        }).join('');
        var legend = sorted.slice(0, 3).map(function(source, i) {
            return '<span class="session-cause-dot session-cause-segment--' + i + '"></span>' +
                (KILL_SOURCE_LABELS[source] || source) + ' ' + Math.round(100 * causes[source] / total) + '%';
        }).join(' · ');
        return '<div class="session-cause-row"><div class="session-cause-name">' + playerLabel(p.name) + '</div>' +
            '<div class="session-cause-bar">' + segments + '</div>' +
            '<div class="session-cause-legend">' + legend + '</div></div>';
    }).join('');
    if (!rows) return '';
    return '<div class="session-detail-block"><h4 class="session-detail-title">☠️ Causes de mort</h4>' + rows + '</div>';
}

function buildMatchTimeline(players, matches) {
    if (!matches || matches.length === 0) return '';
    var names = players.map(function(p) { return p.name; });
    var head = '<th>#</th>' + names.map(function(n) { return '<th>' + playerLabel(n) + '</th>'; }).join('');
    var rows = matches.map(function(match, i) {
        var cells = names.map(function(n) {
            var score = match.scores[n];
            var cls = n === match.winner ? ' class="session-match-winner"' : '';
            return '<td' + cls + '>' + (score != null ? score : '-') + '</td>';
        }).join('');
        return '<tr><td>' + (i + 1) + '</td>' + cells + '</tr>';
    }).join('');
    return '<div class="session-detail-block"><h4 class="session-detail-title">📜 Match par match <span class="session-detail-hint">(kills, vainqueur surligné)</span></h4>' +
        '<div class="overflow-x-auto session-match-scroll"><table class="ranking-table session-match-table w-full text-[5px] sm:text-[6px] md:text-[9px]"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
}

function buildSessionDetails(session) {
    var details = session.details || {};
    var combat = details.combat || {};
    var body = buildSessionAwards(details.awards) +
        buildDuelMatrix(session.players, combat) +
        buildDeathCauses(session.players, combat) +
        buildMatchTimeline(session.players, details.matches);
    if (!body) return '';
    return '<details class="session-details"><summary class="session-details-summary">Détails de la soirée</summary>' +
        '<div class="session-details-body">' + body + '</div></details>';
}

function buildSessionCard(session, highlight) {
    var card = document.createElement('div');
    card.className = 'session-card p-2 sm:p-4 md:p-[15px]';
    card.dataset.sessionKey = session.session_select_id;
    if (highlight) card.classList.add('session-card--highlight');
    card.innerHTML = buildSessionHeader(session) + buildSessionTable(session) + buildSessionDetails(session);
    var tbl = card.querySelector('table');
    if (tbl) makeTableSortable(tbl);
    return card;
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

function openSessionInArchives(sessionKey) {
    if (typeof allSessions === 'undefined' || !sessionKey) {
        return;
    }
    var container = document.getElementById('all-sessions-container');
    if (!container) {
        return;
    }
    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        var toggleBtn = document.getElementById('toggle-all-sessions');
        if (toggleBtn) {
            toggleBtn.textContent = '▲ Masquer toutes les sessions';
        }
        initFilters();
    }

    currentPlayerFilter = '';
    currentGroupFilter = '';
    ['filter-player', 'filter-group'].forEach(function(id) {
        var select = document.getElementById(id);
        if (select) { select.value = ''; }
    });
    filteredSessions = allSessions.slice();
    var index = filteredSessions.findIndex(function(s) {
        return s.session_select_id === sessionKey;
    });
    if (index < 0) {
        return;
    }
    updatePagination();
    updateSessionsCount();
    currentPage = Math.floor(index / sessionsPerPage) + 1;
    highlightedSessionKey = sessionKey;
    renderSessions();

    var card = Array.prototype.find.call(
        container.querySelectorAll('.session-card'),
        function(el) { return el.dataset.sessionKey === sessionKey; }
    );
    if (card) {
        var top = card.getBoundingClientRect().top + window.scrollY - getScrollOffsetTop();
        window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
}

function initRecordLinks() {
    document.querySelectorAll('#records .record-card').forEach(function(card) {
        card.addEventListener('click', function(e) {
            var target = e.target.closest('[data-session-key]');
            if (target) {
                openSessionInArchives(target.getAttribute('data-session-key'));
            }
        });
    });
}

// Short hash names -> section ids (for clean URLs like /#sessions or /#evolution)
var ANCHOR_HASH_MAP = {
    'records': 'records',
    'cette-semaine': 'records',
    'podium': 'podium',
    'archives': 'derniere-soiree',
    'combat': 'combat',
    'fleches': 'combat',
    'parcours': 'parcours',
    'saison': 'parcours',
    'leaderboards': 'records',
    'classements': 'podium',
    'sessions': 'derniere-soiree',
    'kills': 'combat',
    'evolution': 'parcours'
};

var SECTION_NAV_MAP = {
    'records': 'records',
    'podium': 'podium',
    'derniere-soiree': 'archives',
    'combat': 'combat',
    'parcours': 'parcours'
};

var LINE_CHART_TOP_N = 5;
var showAllLineChartPlayers = false;

var CHART_TEXT_COLOR = '#ece6d8';
var CHART_TICK_COLOR = '#a89c88';

var CHART_FONT = {
    family: "'Inter', system-ui, sans-serif",
    size: 11
};

var CHART_FONT_SMALL = {
    family: "'Inter', system-ui, sans-serif",
    size: 10
};

function getScrollOffsetTop() {
    var nav = document.querySelector('nav');
    return nav ? nav.offsetHeight + 8 : 80;
}

function scrollToAnchor() {
    var hash = (window.location.hash || '').replace(/^#/, '').toLowerCase();
    if (!hash) { return; }
    var sectionId = ANCHOR_HASH_MAP[hash] || hash;
    var el = document.getElementById(sectionId);
    if (el) {
        var offset = getScrollOffsetTop();
        var top = el.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
}

function initAnchorOnLoad() {
    if (!window.location.hash) { return; }
    setTimeout(scrollToAnchor, 150);
}

// Smooth scroll pour le menu (resolve short hashes via ANCHOR_HASH_MAP, then scroll)
function initSmoothScroll() {
    document.querySelectorAll('nav a').forEach(function(anchor) {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href') || '';
            if (href.indexOf('#') !== 0) {
                return;
            }
            e.preventDefault();
            const hash = href.replace(/^#/, '').toLowerCase();
            const sectionId = ANCHOR_HASH_MAP[hash] || hash;
            const target = document.getElementById(sectionId);
            if (target) {
                const offset = getScrollOffsetTop();
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
                if (ANCHOR_HASH_MAP[hash]) {
                    window.location.hash = hash;
                }
            }
        });
    });
}

function initScrollSpy() {
    var sectionIds = Object.keys(SECTION_NAV_MAP);
    var sections = sectionIds.map(function(id) {
        return document.getElementById(id);
    }).filter(Boolean);
    if (!sections.length) {
        return;
    }

    var navLinks = document.querySelectorAll('nav ul a[href^="#"], .mobile-menu-link[href^="#"]');
    var currentNavHash = '';

    function setActiveNav(navHash) {
        if (!navHash || navHash === currentNavHash) {
            return;
        }
        currentNavHash = navHash;
        navLinks.forEach(function(link) {
            var href = (link.getAttribute('href') || '').replace(/^#/, '').toLowerCase();
            link.classList.toggle('nav-active', href === navHash);
        });
    }

    var offset = getScrollOffsetTop();
    var observer = new IntersectionObserver(function(entries) {
        var visible = entries.filter(function(entry) {
            return entry.isIntersecting;
        }).sort(function(a, b) {
            return b.intersectionRatio - a.intersectionRatio;
        });
        if (!visible.length) {
            return;
        }
        var navHash = SECTION_NAV_MAP[visible[0].target.id];
        if (navHash) {
            setActiveNav(navHash);
        }
    }, {
        rootMargin: '-' + offset + 'px 0px -55% 0px',
        threshold: [0, 0.05, 0.15, 0.3]
    });

    sections.forEach(function(section) {
        observer.observe(section);
    });
}

function initLeaderTabs() {
    var tabs = document.querySelectorAll('#podium .leader-card, #podium .leader-group-tab');
    var panels = document.querySelectorAll('#podium .leader-panel');
    if (!tabs.length) {
        return;
    }
    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            var target = tab.getAttribute('data-tab');
            tabs.forEach(function(t) {
                var isActive = t === tab;
                t.classList.toggle('active', isActive);
                t.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });
            var activePanel = null;
            panels.forEach(function(panel) {
                var isActive = panel.getAttribute('data-panel') === target;
                panel.classList.toggle('hidden', !isActive);
                if (isActive) { activePanel = panel; }
            });
            if (activePanel && window.matchMedia('(max-width: 639px)').matches) {
                var top = activePanel.getBoundingClientRect().top + window.scrollY - getScrollOffsetTop();
                window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
            }
        });
    });
}

function initToggleKillMatrix() {
    var btn = document.getElementById('toggle-kill-matrix');
    var container = document.getElementById('kill-matrix-container');
    if (!btn || !container) {
        return;
    }
    btn.addEventListener('click', function() {
        container.classList.toggle('hidden');
        btn.textContent = container.classList.contains('hidden')
            ? '▼ Voir la matrice détaillée'
            : '▲ Masquer la matrice';
    });
}

function initEvolutionTabs() {
    var tabs = document.querySelectorAll('.evolution-tab');
    var panels = document.querySelectorAll('.evolution-tab-panel');
    if (!tabs.length) {
        return;
    }

    var chartResizers = {
        scores: function() {
            if (evolutionChart) { evolutionChart.resize(); }
        },
        winrate: function() {
            if (winRateEvolutionChart) { winRateEvolutionChart.resize(); }
        },
        'elo-session': function() {
            if (eloEvolutionChart) { eloEvolutionChart.resize(); }
        },
        'elo-match': function() {
            if (eloMatchEvolutionChart) { eloMatchEvolutionChart.resize(); }
        },
        soiree: function() {
            if (eveningCurveChart) { eveningCurveChart.resize(); }
        }
    };

    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            var target = tab.getAttribute('data-tab');
            tabs.forEach(function(t) {
                var isActive = t === tab;
                t.classList.toggle('active', isActive);
                t.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });
            panels.forEach(function(panel) {
                panel.classList.toggle('hidden', panel.getAttribute('data-panel') !== target);
            });
            setTimeout(function() {
                var resizeFn = chartResizers[target];
                if (resizeFn) {
                    resizeFn();
                }
            }, 80);
        });
    });
}

function initShowAllPlayersToggle() {
    var mainToggle = document.getElementById('evolution-show-all-players');
    var syncToggles = document.querySelectorAll('.evolution-show-all-players-sync');
    if (!mainToggle) {
        return;
    }

    function applyShowAll(checked) {
        showAllLineChartPlayers = checked;
        mainToggle.checked = checked;
        syncToggles.forEach(function(el) {
            el.checked = checked;
        });
        refreshLineEvolutionCharts();
    }

    mainToggle.addEventListener('change', function() {
        applyShowAll(mainToggle.checked);
    });
    syncToggles.forEach(function(el) {
        el.addEventListener('change', function() {
            applyShowAll(el.checked);
        });
    });
}

function refreshLineEvolutionCharts() {
    initWinRateEvolutionChart();
    initEloEvolutionChart();
    renderEloMatchEvolutionChart();
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

    const datasets = sortedPlayers.map(function(player) {
        const color = getPlayerColor(player);
        return {
            label: player,
            data: sortedOriginalDates.map(function(originalDate) {
                return dataByDate[originalDate][player] || 0;
            }),
            _baseColor: color,
            _baseBackgroundColor: color,
            _baseBorderColor: color,
            _baseBorderWidth: 1,
            backgroundColor: color,
            borderColor: color,
            borderWidth: 1,
            borderRadius: 2,
            maxBarThickness: 22
        };
    });

    const canvas = document.getElementById('evolution-chart');
    if (!canvas) {
        return;
    }

    if (evolutionChart) {
        evolutionChart.destroy();
    }

    evolutionChart = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: sortedDates,
            datasets: datasets
        },
        options: buildPlayerLineChartOptions({
            xTitle: 'Dates',
            yTitle: isCumul ? 'Points totaux' : 'Points par session',
            hoverChartRef: function() { return evolutionChart; },
            yScale: {
                beginAtZero: true,
                grid: { color: 'rgba(168, 156, 136, 0.22)' }
            },
            xScale: {
                ticks: {
                    color: CHART_TICK_COLOR,
                    font: CHART_FONT_SMALL,
                    maxRotation: 45,
                    minRotation: 45,
                    autoSkip: true
                },
                grid: { color: 'rgba(168, 156, 136, 0.12)' }
            }
        })
    });
    evolutionChart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return evolutionChart; });
}

// Graphique d'évolution moyenne de victoires par session
let winRateEvolutionChart = null;

function initWinRateEvolutionChart() {
    if (typeof winRateEvolutionData === 'undefined' || winRateEvolutionData.length === 0) {
        return;
    }
    const labels = winRateEvolutionData.map(function(point) { return point.formatted_date; });
    const datasets = buildPlayerLineDatasets(winRateEvolutionData, 'win_rate_by_player', {
        topN: LINE_CHART_TOP_N,
        showAll: showAllLineChartPlayers
    });
    let dataMax = 0;
    winRateEvolutionData.forEach(function(point) {
        const rates = point.win_rate_by_player || {};
        Object.keys(rates).forEach(function(p) {
            const v = rates[p];
            if (v != null && v > dataMax) { dataMax = v; }
        });
    });
    const yMax = dataMax > 0 ? Math.min(1, dataMax * 1.10) : 0.1;

    const canvas = document.getElementById('win-rate-evolution-chart-canvas');
    if (!canvas) { return; }
    if (winRateEvolutionChart) { winRateEvolutionChart.destroy(); }
    winRateEvolutionChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: buildPlayerLineChartOptions({
            xTitle: 'Session',
            yTitle: 'Taux de victoires',
            hoverChartRef: function() { return winRateEvolutionChart; },
            yScale: {
                min: 0,
                max: yMax,
                ticks: {
                    color: CHART_TICK_COLOR,
                    callback: function(value) { return (value * 100).toFixed(0) + '%'; }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const v = context.parsed.y;
                            return v != null ? (v * 100).toFixed(1) + '%' : '';
                        }
                    }
                }
            }
        })
    });
    winRateEvolutionChart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return winRateEvolutionChart; });
}

let eveningCurveChart = null;

function initEveningCurveChart() {
    if (typeof eveningCurveData === 'undefined' || !eveningCurveData) {
        return;
    }
    const canvas = document.getElementById('evening-curve-chart-canvas');
    const byPlayer = eveningCurveData.players || {};
    const players = Object.keys(byPlayer).sort();
    if (!canvas || !players.length) {
        return;
    }
    let dataMax = 0;
    const datasets = players.map(function(player) {
        const buckets = byPlayer[player];
        const dataset = buildPlayerLineDataset(player, buckets.map(function(b) {
            if (b.rate != null && b.rate > dataMax) { dataMax = b.rate; }
            return b.rate;
        }));
        dataset.pointRadius = 4;
        dataset._buckets = buckets;
        return dataset;
    });
    const yMax = dataMax > 0 ? Math.min(1, dataMax * 1.10) : 0.1;

    if (eveningCurveChart) { eveningCurveChart.destroy(); }
    eveningCurveChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: eveningCurveData.labels, datasets: datasets },
        options: buildPlayerLineChartOptions({
            xTitle: 'Rang du match dans la session',
            yTitle: 'Taux de victoires',
            hoverChartRef: function() { return eveningCurveChart; },
            yScale: {
                min: 0,
                max: yMax,
                ticks: {
                    color: CHART_TICK_COLOR,
                    callback: function(value) { return (value * 100).toFixed(0) + '%'; }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: function(items) {
                            return items.length ? 'Matchs ' + items[0].label : '';
                        },
                        label: function(context) {
                            const bucket = context.dataset._buckets[context.dataIndex];
                            if (!bucket || bucket.rate == null) { return ''; }
                            return context.dataset.label + ' : ' + (bucket.rate * 100).toFixed(0) + '% (' + bucket.wins + '/' + bucket.played + ')';
                        }
                    }
                }
            }
        })
    });
    eveningCurveChart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return eveningCurveChart; });
}

// --- Utilitaires communs (survol + lignes sans points) ---

function sortTooltipItemsByValueDesc(a, b) {
    const ya = a.parsed.y != null ? a.parsed.y : a.raw;
    const yb = b.parsed.y != null ? b.parsed.y : b.raw;
    if (ya == null && yb == null) {
        return 0;
    }
    if (ya == null) {
        return 1;
    }
    if (yb == null) {
        return -1;
    }
    return yb - ya;
}

function dimChartColor(color, alpha) {
    if (typeof color !== 'string') {
        return color;
    }
    const rgba = color.match(/^rgba?\(([^)]+)\)$/);
    if (rgba) {
        const parts = rgba[1].split(',').map(function(part) { return part.trim(); });
        if (parts.length >= 3) {
            return 'rgba(' + parts[0] + ', ' + parts[1] + ', ' + parts[2] + ', ' + alpha + ')';
        }
    }
    if (color.charAt(0) === '#' && color.length >= 7) {
        const hexAlpha = Math.round(alpha * 255).toString(16).padStart(2, '0');
        return color.slice(0, 7) + hexAlpha;
    }
    return color;
}

function applyMultiSeriesChartHighlight(chart, activeDatasetIndex) {
    if (!chart || !chart.data || !chart.data.datasets) {
        return;
    }
    chart.data.datasets.forEach(function(ds, i) {
        const base = ds._baseColor || ds.borderColor;
        const bg = ds._baseBackgroundColor != null ? ds._baseBackgroundColor : base;
        const border = ds._baseBorderColor != null ? ds._baseBorderColor : base;
        const bw = ds._baseBorderWidth != null ? ds._baseBorderWidth : 2;
        if (activeDatasetIndex == null) {
            ds.borderColor = border;
            ds.backgroundColor = bg;
            ds.borderWidth = bw;
        } else if (i === activeDatasetIndex) {
            ds.borderColor = border;
            ds.backgroundColor = bg;
            ds.borderWidth = 3;
        } else {
            ds.borderColor = typeof border === 'string' && border.indexOf('rgba') === 0
                ? dimChartColor(border, 0.45) : border + '55';
            ds.backgroundColor = typeof bg === 'string' && bg.indexOf('rgba') === 0
                ? dimChartColor(bg, 0.2)
                : (typeof base === 'string' && base.charAt(0) === '#' ? base + '55' : bg);
            ds.borderWidth = 1;
        }
    });
    chart.update('none');
}

function getMultiSeriesHoveredDatasetIndex(chart, event) {
    const native = event && (event.native || event);
    if (!chart || !native || !chart.canvas || !chart.scales.x) {
        return null;
    }
    const rect = chart.canvas.getBoundingClientRect();
    const mouseX = native.clientX - rect.left;
    const mouseY = native.clientY - rect.top;
    const area = chart.chartArea;
    if (
        mouseX < area.left || mouseX > area.right ||
        mouseY < area.top || mouseY > area.bottom
    ) {
        return null;
    }
    const rawIndex = chart.scales.x.getValueForPixel(mouseX);
    if (rawIndex == null || Number.isNaN(rawIndex)) {
        return null;
    }
    const dataIndex = Math.max(0, Math.min(
        chart.data.labels.length - 1,
        Math.round(rawIndex)
    ));
    let bestIdx = null;
    let bestDist = Infinity;
    chart.data.datasets.forEach(function(ds, datasetIndex) {
        const value = ds.data[dataIndex];
        if (value == null) {
            return;
        }
        const meta = chart.getDatasetMeta(datasetIndex);
        const point = meta.data[dataIndex];
        if (!point || point.skip) {
            return;
        }
        const dist = Math.abs(point.y - mouseY);
        if (dist < bestDist) {
            bestDist = dist;
            bestIdx = datasetIndex;
        }
    });
    return bestIdx;
}

function createDatasetHoverHandler(getChart) {
    return function(event) {
        const chart = getChart();
        if (!chart) {
            return;
        }
        const idx = getMultiSeriesHoveredDatasetIndex(chart, event);
        if (chart._hoverDatasetIndex === idx) {
            return;
        }
        chart._hoverDatasetIndex = idx;
        applyMultiSeriesChartHighlight(chart, idx);
    };
}

function bindChartHoverReset(canvas, getChart, resetFn) {
    if (!canvas || canvas.dataset.hoverResetBound) {
        return;
    }
    canvas.dataset.hoverResetBound = '1';
    canvas.addEventListener('mouseleave', function() {
        const chart = getChart();
        if (!chart) {
            return;
        }
        resetFn(chart);
    });
}

function bindMultiSeriesChartHoverReset(canvas, getChart) {
    bindChartHoverReset(canvas, getChart, function(chart) {
        chart._hoverDatasetIndex = null;
        applyMultiSeriesChartHighlight(chart, null);
    });
}

function buildPlayerLineDataset(player, data) {
    const color = getPlayerColor(player);
    return {
        label: player,
        data: data,
        _baseColor: color,
        _baseBackgroundColor: color + '33',
        _baseBorderWidth: 2,
        borderColor: color,
        backgroundColor: color + '33',
        borderWidth: 2,
        fill: false,
        spanGaps: false,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHitRadius: 8
    };
}

function getTopPlayersByLastValue(points, playerValuesKey, topN) {
    var allPlayers = new Set();
    points.forEach(function(point) {
        Object.keys(point[playerValuesKey] || {}).forEach(function(p) { allPlayers.add(p); });
    });
    var ranked = Array.from(allPlayers).map(function(player) {
        var lastVal = null;
        for (var i = points.length - 1; i >= 0; i--) {
            var values = points[i][playerValuesKey] || {};
            if (values[player] != null) {
                lastVal = values[player];
                break;
            }
        }
        return { player: player, lastVal: lastVal != null ? lastVal : -Infinity };
    }).sort(function(a, b) {
        return b.lastVal - a.lastVal;
    });
    return ranked.slice(0, topN).map(function(item) { return item.player; });
}

function buildPlayerLineDatasets(points, playerValuesKey, options) {
    options = options || {};
    var allPlayers = new Set();
    points.forEach(function(point) {
        Object.keys(point[playerValuesKey] || {}).forEach(function(p) { allPlayers.add(p); });
    });
    var players;
    if (options.showAll) {
        players = Array.from(allPlayers).sort();
    } else if (options.topN) {
        players = getTopPlayersByLastValue(points, playerValuesKey, options.topN);
    } else {
        players = Array.from(allPlayers).sort();
    }
    return players.map(function(player) {
        const data = points.map(function(point) {
            const value = point[playerValuesKey] && point[playerValuesKey][player];
            return value != null ? value : null;
        });
        return buildPlayerLineDataset(player, data);
    });
}

function buildPlayerLineChartOptions(opts) {
    opts = opts || {};
    const xTicks = {
        color: CHART_TICK_COLOR,
        font: CHART_FONT_SMALL,
        maxRotation: 45,
        autoSkip: true
    };
    if (opts.xTickLimit) {
        xTicks.maxTicksLimit = opts.xTickLimit;
        xTicks.minRotation = 45;
        xTicks.maxRotation = 60;
    }
    const hoverChartRef = opts.hoverChartRef;
    const yScale = Object.assign({
        title: { display: true, text: opts.yTitle || 'ELO', color: CHART_TEXT_COLOR, font: CHART_FONT },
        ticks: { color: CHART_TICK_COLOR, font: CHART_FONT_SMALL }
    }, opts.yScale || {});
    const xScale = Object.assign({
        title: { display: true, text: opts.xTitle || 'Session', color: CHART_TEXT_COLOR, font: CHART_FONT },
        ticks: xTicks
    }, opts.xScale || {});
    const plugins = Object.assign({
        legend: {
            labels: {
                color: CHART_TEXT_COLOR,
                font: CHART_FONT,
                usePointStyle: true,
                padding: 10
            }
        }
    }, opts.plugins || {});
    plugins.tooltip = Object.assign(
        { itemSort: sortTooltipItemsByValueDesc },
        plugins.tooltip || {}
    );
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: hoverChartRef ? { mode: 'index', axis: 'x', intersect: false } : undefined,
        onHover: hoverChartRef ? createDatasetHoverHandler(hoverChartRef) : undefined,
        scales: { x: xScale, y: yScale },
        plugins: plugins
    };
}

function buildEloEvolutionDatasets(points) {
    return buildPlayerLineDatasets(points, 'elo_by_player');
}

function applyEloChartHighlight(chart, activeDatasetIndex) {
    applyMultiSeriesChartHighlight(chart, activeDatasetIndex);
}

function getEloChartHoveredDatasetIndex(chart, event) {
    return getMultiSeriesHoveredDatasetIndex(chart, event);
}

function buildEloLineChartOptions(xTitle, xTickLimit, hoverChartRef) {
    return buildPlayerLineChartOptions({
        xTitle: xTitle,
        yTitle: 'ELO',
        xTickLimit: xTickLimit,
        hoverChartRef: hoverChartRef
    });
}

// Graphique d'évolution ELO par session
let eloEvolutionChart = null;

function initEloEvolutionChart() {
    if (typeof eloEvolutionData === 'undefined' || eloEvolutionData.length === 0) {
        return;
    }
    const labels = eloEvolutionData.map(function(point) { return point.formatted_date; });
    const datasets = buildPlayerLineDatasets(eloEvolutionData, 'elo_by_player', {
        topN: LINE_CHART_TOP_N,
        showAll: showAllLineChartPlayers
    });
    const canvas = document.getElementById('elo-evolution-chart-canvas');
    if (!canvas) { return; }
    if (eloEvolutionChart) { eloEvolutionChart.destroy(); }
    eloEvolutionChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: buildPlayerLineChartOptions({
            xTitle: 'Session',
            yTitle: 'ELO',
            hoverChartRef: function() { return eloEvolutionChart; }
        })
    });
    eloEvolutionChart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return eloEvolutionChart; });
}

// Graphique d'évolution ELO match (un point par match)
let eloMatchEvolutionChart = null;

function getEloMatchGranularity() {
    const checked = document.querySelector('input[name="elo-match-granularity"]:checked');
    return checked ? checked.value : 'session';
}

function isEloMatchChartBaseline(point) {
    return point.is_chart_baseline || point.formatted_date === 'Départ';
}

function eloMatchEvolutionSessionView(matchPoints) {
    if (!matchPoints || !matchPoints.length) {
        return [];
    }
    const depart = matchPoints.find(isEloMatchChartBaseline);
    const sessionLast = new Map();
    const sessionOrder = [];
    matchPoints.forEach(function(point) {
        if (isEloMatchChartBaseline(point)) {
            return;
        }
        const key = (point.session_date || point.date || '') + '|' + (point.session_id || '');
        if (!sessionLast.has(key)) {
            sessionOrder.push(key);
        }
        sessionLast.set(key, point);
    });
    const out = [];
    if (depart) {
        out.push(depart);
    }
    sessionOrder.forEach(function(key) {
        const point = sessionLast.get(key);
        out.push(Object.assign({}, point, {
            formatted_date: point.session_label || point.formatted_date
        }));
    });
    return out;
}

function getEloMatchEvolutionDisplayPoints() {
    if (typeof eloMatchEvolutionData === 'undefined' || !eloMatchEvolutionData.length) {
        return [];
    }
    if (getEloMatchGranularity() === 'match') {
        return eloMatchEvolutionData;
    }
    return eloMatchEvolutionSessionView(eloMatchEvolutionData);
}

function renderEloMatchEvolutionChart() {
    const points = getEloMatchEvolutionDisplayPoints();
    if (!points.length) {
        return;
    }
    const labels = points.map(function(point) { return point.formatted_date; });
    const datasets = buildPlayerLineDatasets(points, 'elo_by_player', {
        topN: LINE_CHART_TOP_N,
        showAll: showAllLineChartPlayers
    });
    const canvas = document.getElementById('elo-match-evolution-chart-canvas');
    if (!canvas) {
        return;
    }
    const isMatchView = getEloMatchGranularity() === 'match';
    if (eloMatchEvolutionChart) {
        eloMatchEvolutionChart.destroy();
    }
    eloMatchEvolutionChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: buildEloLineChartOptions('Match', isMatchView ? 24 : undefined, function() {
            return eloMatchEvolutionChart;
        })
    });
    eloMatchEvolutionChart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return eloMatchEvolutionChart; });
}

function initEloMatchEvolutionChart() {
    if (typeof eloMatchEvolutionData === 'undefined' || eloMatchEvolutionData.length === 0) {
        return;
    }
    renderEloMatchEvolutionChart();
    document.querySelectorAll('input[name="elo-match-granularity"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            renderEloMatchEvolutionChart();
        });
    });
}

// Portail overlays (filtres + infobulles au-dessus du thème arcade)
function initOverlayPortal() {
    var portal = document.getElementById('app-overlays');
    if (!portal) {
        return;
    }
    document.querySelectorAll('section .info-bubble, .container .info-bubble').forEach(function(bubble) {
        if (bubble.parentElement !== portal) {
            portal.appendChild(bubble);
        }
    });
    var backdrop = document.getElementById('overlay-backdrop');
    if (backdrop && !backdrop.dataset.bound) {
        backdrop.dataset.bound = '1';
        backdrop.addEventListener('click', function() {
            closeAllOverlays();
        });
    }
}

function updateOverlayBackdrop() {
    var backdrop = document.getElementById('overlay-backdrop');
    if (!backdrop) {
        return;
    }
    var popoverOpen = document.getElementById('date-picker-popover') &&
        document.getElementById('date-picker-popover').classList.contains('active');
    var infoOpen = document.querySelector('.info-bubble.active');
    var open = popoverOpen || infoOpen;
    backdrop.classList.toggle('active', !!open);
    backdrop.setAttribute('aria-hidden', open ? 'false' : 'true');
}

function setFilterToggleOpen(isOpen) {
    var toggleBtn = document.getElementById('toggle-date-picker');
    if (!toggleBtn) {
        return;
    }
    toggleBtn.classList.toggle('is-open', !!isOpen);
    toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

function closeAllOverlays() {
    var popover = document.getElementById('date-picker-popover');
    if (popover) {
        popover.classList.remove('active');
        popover.setAttribute('aria-hidden', 'true');
    }
    setFilterToggleOpen(false);
    document.querySelectorAll('.info-bubble.active').forEach(function(bubble) {
        bubble.classList.remove('active');
        bubble.style.transform = '';
    });
    updateOverlayBackdrop();
}

function positionInfoBubbleCentered(infoBubble) {
    infoBubble.style.top = '50%';
    infoBubble.style.left = '50%';
    infoBubble.style.right = 'auto';
    infoBubble.style.bottom = 'auto';
    infoBubble.style.transform = 'translate(-50%, -50%)';
    infoBubble.style.maxWidth = Math.min(520, window.innerWidth - 32) + 'px';
    infoBubble.style.maxHeight = Math.min(window.innerHeight * 0.8, 600) + 'px';
}

// Initialisation des info-bulles
function initInfoBubbles() {
    const infoButtons = document.querySelectorAll('.info-button[data-info]');
    
    infoButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const infoId = this.getAttribute('data-info');
            const infoBubble = document.getElementById(infoId);
            
            if (infoBubble) {
                var popover = document.getElementById('date-picker-popover');
                if (popover) {
                    popover.classList.remove('active');
                    popover.setAttribute('aria-hidden', 'true');
                    setFilterToggleOpen(false);
                }

                document.querySelectorAll('.info-bubble').forEach(function(bubble) {
                    if (bubble.id !== infoId) {
                        bubble.classList.remove('active');
                        bubble.style.transform = '';
                    }
                });
                
                const isActive = infoBubble.classList.contains('active');
                infoBubble.classList.toggle('active');
                
                if (infoBubble.classList.contains('active')) {
                    positionInfoBubbleCentered(infoBubble);
                } else {
                    infoBubble.style.transform = '';
                }
                updateOverlayBackdrop();
            }
        });
    });
    
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.info-button') && !e.target.closest('.info-bubble') &&
            !e.target.closest('#date-picker-popover') && !e.target.closest('#toggle-date-picker')) {
            document.querySelectorAll('.info-bubble.active').forEach(function(bubble) {
                bubble.classList.remove('active');
                bubble.style.transform = '';
            });
            updateOverlayBackdrop();
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllOverlays();
        }
    });
}

function updateKillRelationshipsTable(useTotals) {
    const subtitle = document.getElementById('kill-relationships-subtitle');
    if (subtitle) {
        subtitle.textContent = useTotals ? 'Nombre total de kills' : 'Moyenne de kills par partie';
    }
    const cells = document.querySelectorAll('#kill-relationships-table .kill-cell');
    cells.forEach(function(cell) {
        const avg = parseFloat(cell.getAttribute('data-avg')) || 0;
        const total = parseInt(cell.getAttribute('data-total'), 10) || 0;
        const maxAvg = parseFloat(cell.getAttribute('data-max-avg')) || 1;
        const maxTotal = parseInt(cell.getAttribute('data-max-total'), 10) || 1;
        const value = useTotals ? total : avg;
        const maxVal = useTotals ? maxTotal : maxAvg;
        cell.textContent = value > 0 ? (useTotals ? String(value) : value.toFixed(2)) : '-';
        const intensity = maxVal > 0 ? Math.min(value / maxVal, 1) : 0;
        const hue = (1 - intensity) * 120;
        cell.style.backgroundColor = 'hsla(' + hue + ', 70%, 52%, 0.40)';
    });
}

function initKillRelationshipsTotalsToggle() {
    const toggle = document.getElementById('kill-relationships-totals-toggle');
    if (!toggle) return;
    toggle.addEventListener('change', function() {
        updateKillRelationshipsTable(toggle.checked);
        renderRivalryMap(toggle.checked);
    });
}

function renderRivalryMap(useTotals) {
    if (typeof hasDetailedStats !== 'undefined' && !hasDetailedStats) {
        return;
    }
    var svg = document.getElementById('rivalry-map');
    var mapContainer = document.getElementById('rivalry-map-container');
    if (!svg || !mapContainer || typeof allPlayersForMatrix === 'undefined') {
        return;
    }
    var players = allPlayersForMatrix || [];
    if (!players.length) {
        return;
    }

    var avgData = typeof killRelationshipsData !== 'undefined' ? killRelationshipsData : {};
    var totalData = typeof killRelationshipsTotalsData !== 'undefined' ? killRelationshipsTotalsData : {};
    var data = useTotals ? totalData : avgData;
    var valueLabel = useTotals ? ' kills total' : '/partie';

    var w = Math.max(mapContainer.clientWidth || 600, 320);
    var h = Math.max(360, players.length * 55);
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.innerHTML = '';

    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    var marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', 'arrowhead');
    marker.setAttribute('markerWidth', '8');
    marker.setAttribute('markerHeight', '6');
    marker.setAttribute('refX', '7');
    marker.setAttribute('refY', '3');
    marker.setAttribute('orient', 'auto');
    var arrowPoly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    arrowPoly.setAttribute('points', '0 0, 8 3, 0 6');
    arrowPoly.setAttribute('fill', 'context-stroke');
    marker.appendChild(arrowPoly);
    defs.appendChild(marker);
    svg.appendChild(defs);

    var cx = w / 2;
    var cy = h / 2;
    var radius = Math.min(w, h) * 0.34;
    var positions = {};
    var n = players.length;

    players.forEach(function(player, i) {
        var angle = (i / n) * Math.PI * 2 - Math.PI / 2;
        positions[player] = {
            x: cx + radius * Math.cos(angle),
            y: cy + radius * Math.sin(angle)
        };
    });

    var maxVal = 0;
    players.forEach(function(killer) {
        players.forEach(function(victim) {
            if (killer === victim) { return; }
            var val = (data[killer] && data[killer][victim]) || 0;
            if (val > maxVal) { maxVal = val; }
        });
    });
    if (maxVal <= 0) { maxVal = 1; }

    var tooltip = document.getElementById('rivalry-map-tooltip');

    players.forEach(function(killer) {
        players.forEach(function(victim) {
            if (killer === victim) { return; }
            var val = (data[killer] && data[killer][victim]) || 0;
            if (val <= 0) { return; }

            var from = positions[killer];
            var to = positions[victim];
            var intensity = val / maxVal;
            var dx = to.x - from.x;
            var dy = to.y - from.y;
            var len = Math.sqrt(dx * dx + dy * dy) || 1;
            var nodeR = 28;
            var x1 = from.x + (dx / len) * nodeR;
            var y1 = from.y + (dy / len) * nodeR;
            var x2 = to.x - (dx / len) * (nodeR + 4);
            var y2 = to.y - (dy / len) * (nodeR + 4);
            var hue = (1 - intensity) * 120;

            var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
            line.setAttribute('stroke', 'hsla(' + hue + ', 80%, 50%, ' + (0.35 + intensity * 0.55) + ')');
            line.setAttribute('stroke-width', (1 + intensity * 5).toFixed(1));
            line.setAttribute('marker-end', 'url(#arrowhead)');
            line.classList.add('rivalry-edge');
            line.addEventListener('mouseenter', function(e) {
                if (tooltip) {
                    tooltip.classList.remove('hidden');
                    tooltip.textContent = killer + ' → ' + victim + ': ' + (useTotals ? val : val.toFixed(2)) + valueLabel;
                    tooltip.style.left = (e.offsetX + 12) + 'px';
                    tooltip.style.top = (e.offsetY + 12) + 'px';
                }
            });
            line.addEventListener('mouseleave', function() {
                if (tooltip) { tooltip.classList.add('hidden'); }
            });
            svg.appendChild(line);
        });
    });

    players.forEach(function(player) {
        var pos = positions[player];
        var color = getPlayerColor(player);
        var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');

        var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', pos.x);
        circle.setAttribute('cy', pos.y);
        circle.setAttribute('r', '26');
        circle.setAttribute('fill', color);
        circle.setAttribute('stroke', '#f2c94c');
        circle.setAttribute('stroke-width', '3');
        circle.classList.add('rivalry-node-circle');

        var text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', pos.x);
        text.setAttribute('y', pos.y + 5);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', '#1a1a2e');
        text.setAttribute('font-family', 'Press Start 2P, cursive');
        text.setAttribute('font-size', '14');
        text.textContent = player.charAt(0);

        var name = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        name.setAttribute('x', pos.x);
        name.setAttribute('y', pos.y + 42);
        name.setAttribute('text-anchor', 'middle');
        name.setAttribute('fill', color);
        name.setAttribute('font-family', 'Inter, sans-serif');
        name.setAttribute('font-size', '11');
        name.setAttribute('font-weight', 'bold');
        name.textContent = player.length > 8 ? player.substring(0, 7) + '…' : player;

        g.appendChild(circle);
        g.appendChild(text);
        g.appendChild(name);
        svg.appendChild(g);
    });
}

function initRivalryMap() {
    if (typeof hasDetailedStats !== 'undefined' && !hasDetailedStats) {
        return;
    }
    var toggle = document.getElementById('kill-relationships-totals-toggle');
    renderRivalryMap(toggle ? toggle.checked : false);
    window.addEventListener('resize', function() {
        renderRivalryMap(toggle ? toggle.checked : false);
    });
}

function syncDateInputsWithSessionSelect() {
    const sessionSelect = document.getElementById('session-select');
    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    if (!sessionSelect || !dateStart || !dateEnd) return;
    var hasSession = sessionSelect.value !== '';
    dateStart.disabled = hasSession;
    dateEnd.disabled = hasSession;
}

function initDatePickerToggle() {
    const toggleBtn = document.getElementById('toggle-date-picker');
    const popover = document.getElementById('date-picker-popover');
    const closeBtn = popover && popover.querySelector('.date-picker-close');
    const sessionSelect = document.getElementById('session-select');
    if (!toggleBtn || !popover) return;

    syncDateInputsWithSessionSelect();
    if (sessionSelect) {
        sessionSelect.addEventListener('change', syncDateInputsWithSessionSelect);
    }

    popover.querySelectorAll('input[type="date"]').forEach(function(input) {
        input.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (input.disabled || typeof input.showPicker !== 'function') {
                return;
            }
            try {
                input.showPicker();
            } catch (err) {}
        });
    });

    function openPopover() {
        document.querySelectorAll('.info-bubble.active').forEach(function(bubble) {
            bubble.classList.remove('active');
            bubble.style.transform = '';
        });
        popover.classList.add('active');
        popover.setAttribute('aria-hidden', 'false');
        setFilterToggleOpen(true);
        updateOverlayBackdrop();
    }

    function closePopover() {
        popover.classList.remove('active');
        popover.setAttribute('aria-hidden', 'true');
        setFilterToggleOpen(false);
        updateOverlayBackdrop();
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
        if (!popover.classList.contains('active')) {
            return;
        }
        if (popover.contains(e.target) || toggleBtn.contains(e.target)) {
            return;
        }
        var active = document.activeElement;
        if (active && popover.contains(active) && active.matches('input[type="date"]')) {
            return;
        }
        closePopover();
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

function initBackgroundParallax() {
    const bg = document.querySelector('.arcade-bg');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!bg || !finePointer || reducedMotion) {
        return;
    }
    let mouseX = 0;
    let mouseY = 0;
    let frame = null;

    function applyPosition() {
        frame = null;
        bg.style.setProperty('--parallax-x', (0.5 - mouseX / window.innerWidth).toFixed(3));
        bg.style.setProperty('--parallax-y', (0.5 - mouseY / window.innerHeight).toFixed(3));
    }

    document.addEventListener('mousemove', function(e) {
        mouseX = e.clientX;
        mouseY = e.clientY;
        if (!frame) {
            frame = requestAnimationFrame(applyPosition);
        }
    }, { passive: true });
}

document.addEventListener('DOMContentLoaded', function() {
    initBackgroundParallax();
    initOverlayPortal();
    initRankingTable();
    initEloLegacyToggle();
    initDatePickerToggle();
    initMobileMenu();
    initGroupSelector();
    renderLatestSessions();
    initSessionsPagination();
    initSortableTables();
    initSmoothScroll();
    initScrollSpy();
    initLeaderTabs();
    initRecordLinks();
    initEvolutionTabs();
    initShowAllPlayersToggle();
    initToggleKillMatrix();
    initEvolutionChart();
    initWinRateEvolutionChart();
    initEloEvolutionChart();
    initEloMatchEvolutionChart();
    initEveningCurveChart();
    initInfoBubbles();
    if (hasDetailedStats) {
        initKillRelationshipsTotalsToggle();
        initRivalryMap();
    }
    initAnchorOnLoad();
});

window.addEventListener('hashchange', scrollToAnchor);

