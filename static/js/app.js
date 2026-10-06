function getPlayerColor(playerName) {
    if (typeof playerColors === 'undefined') {
        return '#FFD700';
    }
    return playerColors[playerName.toUpperCase()] || '#FFD700';
}

function getMedal(rank) {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return '';
}

function getPlayerPortrait(playerName) {
    if (typeof playerPortraits === 'undefined') return null;
    return playerPortraits[playerName.toUpperCase()] || null;
}

function buildPlayerAvatarHtml(player) {
    var color = getPlayerColor(player);
    var portrait = getPlayerPortrait(player);
    if (portrait) {
        return '<div class="player-avatar player-avatar--portrait" style="--player-color: ' + color + ';">' +
            '<img src="' + portrait + '" alt="' + player + '"></div>';
    }
    return '<div class="player-avatar" style="--player-color: ' + color + ';">' + player.charAt(0) + '</div>';
}

function buildPodiumSlotHtml(position, step) {
    var cls = 'pixel-podium-slot pixel-podium-slot--' + position;
    if (!step) {
        return '<div class="' + cls + ' pixel-podium-slot--empty"></div>';
    }
    if (step.length > 1) cls += ' pixel-podium-slot--shared';
    var details = step.map(function(e) { return e.detail; }).filter(function(d, i, all) {
        return d && all.indexOf(d) === i;
    });
    var avatars = step.map(function(e) { return buildPlayerAvatarHtml(e.player); }).join('');
    var names = step.map(function(e) {
        return '<div class="pixel-podium-name" style="color: ' + getPlayerColor(e.player) + ';">' + e.player + '</div>';
    }).join('');
    return '<div class="' + cls + '">' +
        '<div class="pixel-podium-players" style="--count: ' + step.length + ';">' + avatars +
        '<div class="pixel-podium-medal">' + getMedal(position) + '</div>' + names + '</div>' +
        '<div class="pixel-podium-value led-value">' + step[0].value + '</div>' +
        '<div class="pixel-podium-detail">' + details.join(' · ') + '</div>' +
        '</div>';
}

// entries: [{ player, value, detail, rank }] sorted best first; equal ranks share a step
function groupPodiumSteps(entries) {
    var steps = [];
    entries.forEach(function(e) {
        var last = steps[steps.length - 1];
        if (last && last[0].rank === e.rank) {
            last.push(e);
        } else if (steps.length < 3) {
            steps.push([e]);
        }
    });
    return steps;
}

function buildPodiumSlotsHtml(entries) {
    var steps = groupPodiumSteps(entries);
    return [2, 1, 3].map(function(position) {
        return buildPodiumSlotHtml(position, steps[position - 1]);
    }).join('');
}

function renderGroupPodium(ranking) {
    var podium = document.getElementById('group-podium');
    if (!podium) return;
    podium.innerHTML = buildPodiumSlotsHtml(ranking.map(function(item) {
        return { player: item[1], value: item[2], detail: 'victoires', rank: item[0] };
    }));
}

function buildSessionPodium(session) {
    var entries = session.players
        .filter(function(p) { return p.today > 0; })
        .map(function(p) {
            return { player: p.name, value: p.today, detail: 'victoire' + (p.today > 1 ? 's' : ''), rank: p.rank };
        });
    if (!entries.length) return '';
    return '<div class="pixel-podium pixel-podium--session">' + buildPodiumSlotsHtml(entries) + '</div>';
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
        row.innerHTML =
            '<td class="player-column ' + rankClass + '" style="color: ' + playerColor + ';">' +
            medal + ' ' + playerName + '</td>' +
            '<td class="' + rankClass + '">' + playerData[2] + '</td>';
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

function initSortableTables() {
    document.querySelectorAll('table').forEach(function(table) {
        var ths = table.querySelectorAll('thead th');
        if (ths.length >= 3) makeTableSortable(table);
    });
}

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

function initGroupSelector() {
    const groupSelect = document.getElementById('group-select');
    if (groupSelect) {
        groupSelect.addEventListener('change', function() {
            updateRanking(this.value);
        });
    }
}

// allSessions / filteredSessions are declared in the inline script in index.html.
if (typeof filteredSessions === 'undefined') {
    filteredSessions = [];
}
let currentPlayerFilter = '';
let currentGroupFilter = '';
let highlightedSessionKey = null;

let playerFilterHandler = null;
let groupFilterHandler = null;
let filtersListenersAttached = false;

function filterSessions() {
    if (typeof allSessions === 'undefined') {
        return;
    }
    
    filteredSessions = allSessions.filter(function(session) {
        if (currentPlayerFilter) {
            const hasPlayer = session.players.some(function(p) {
                return p.name === currentPlayerFilter;
            });
            if (!hasPlayer) {
                return false;
            }
        }
        
        if (currentGroupFilter) {
            const sessionGroup = session.group || session.id;
            if (sessionGroup !== currentGroupFilter) {
                return false;
            }
        }
        
        return true;
    });
    
    currentPage = 1;
    updatePagination();
    updateSessionsCount();
    renderSessions();
}

function updatePagination() {
    totalPages = Math.ceil(filteredSessions.length / sessionsPerPage);
    if (totalPages === 0) {
        totalPages = 1;
    }
    if (currentPage > totalPages) {
        currentPage = totalPages;
    }
}

function updateSessionsCount() {
    const countElement = document.getElementById('sessions-count-value');
    if (countElement) {
        const total = filteredSessions ? filteredSessions.length : 0;
        countElement.textContent = total;
    }
}

function renderSessions() {
    if (typeof allSessions === 'undefined') {
        return;
    }
    
    const container = document.getElementById('all-sessions-list');
    if (!container) return;
    
    container.innerHTML = '';
    
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
    if (session.live) {
        parts.push('en cours');
    } else if (details.hour != null) {
        parts.push('fin vers ' + details.hour + 'h');
    }
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
    var careerTotals = typeof isCareerView !== 'undefined' && isCareerView && !session.live;
    var head = '<th>Joueur</th><th>Victoires</th><th>%</th><th>' + (careerTotals ? 'All-time' : 'Saison') + '</th>';
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
    return '<div class="ranking-scroll"><table class="ranking-table"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
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

function buildScoreboard(players, scoreboard, leadChanges) {
    if (!scoreboard || scoreboard.length < 2 || !players || players.length === 0) return '';
    var hint = leadChanges ? leadChanges + ' changement' + (leadChanges > 1 ? 's' : '') + ' de leader' : '';
    return '<div class="session-detail-block"><h4 class="session-detail-title">📈 Au fil de la soirée' +
        (hint ? ' <span class="session-detail-hint">(' + hint + ')</span>' : '') + '</h4>' +
        '<div class="session-scoreboard-chart"><canvas></canvas></div></div>';
}

function drawScoreboard(card, session) {
    var canvas = card.querySelector('.session-scoreboard-chart canvas');
    if (!canvas || canvas._chart || canvas.offsetParent === null || typeof Chart === 'undefined') return;
    var scoreboard = (session.details && session.details.scoreboard) || [];
    var names = session.players.map(function(p) { return p.name; }).sort();
    var datasets = names.map(function(name) {
        var dataset = buildPlayerLineDataset(name, scoreboard.map(function(row) {
            return (row.wins && row.wins[name]) || 0;
        }));
        dataset.cubicInterpolationMode = 'monotone';
        return dataset;
    });
    canvas._chart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: scoreboard.map(function(_row, i) { return String(i + 1); }),
            datasets: datasets
        },
        options: buildPlayerLineChartOptions({
            xTitle: 'Match',
            yTitle: 'Victoires',
            hoverChartRef: function() { return canvas._chart; },
            yScale: {
                min: 0,
                ticks: { color: CHART_TICK_COLOR, font: CHART_FONT_SMALL, precision: 0 }
            }
        })
    });
    canvas._chart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return canvas._chart; });
}

function bindScoreboard(card, session) {
    var details = card.querySelector('.session-details');
    if (!details || !card.querySelector('.session-scoreboard-chart')) return;
    details.addEventListener('toggle', function() {
        if (details.open) drawScoreboard(card, session);
    });
    requestAnimationFrame(function() {
        if (details.open) drawScoreboard(card, session);
    });
}

function destroySessionCharts(container) {
    container.querySelectorAll('.session-scoreboard-chart canvas').forEach(function(canvas) {
        if (canvas._chart) {
            canvas._chart.destroy();
            canvas._chart = null;
        }
    });
}

function readableTextColor(hex) {
    var h = String(hex || '').replace('#', '');
    if (h.length === 3) h = h.split('').map(function(c) { return c + c; }).join('');
    if (h.length !== 6) return '#fff';
    var r = parseInt(h.substr(0, 2), 16);
    var g = parseInt(h.substr(2, 2), 16);
    var b = parseInt(h.substr(4, 2), 16);
    return (0.299 * r + 0.587 * g + 0.114 * b) > 160 ? '#1a1a2e' : '#fff';
}

function buildMatchStrip(players, matches) {
    if (!matches || matches.length === 0) return '';
    var names = (players || []).map(function(p) { return p.name; });
    var cells = matches.map(function(match, i) {
        var color = match.winner ? getPlayerColor(match.winner) : '#666';
        var scores = names.map(function(name) {
            var score = match.scores && match.scores[name];
            return name + ' ' + (score != null ? score : '-');
        }).join(' · ');
        var title = '#' + (i + 1) + (match.winner ? ' · ' + match.winner : '') +
            (match.margin != null ? ' +' + match.margin : '') + ' · ' + scores;
        var textColor = readableTextColor(color);
        var light = textColor === '#fff' ? '' : ' is-light';
        return '<button type="button" class="session-match-chip' + light + '" data-match-index="' + i + '" style="background:' + color + '; color:' + textColor + ';" title="' + title + '">' + (i + 1) + '</button>';
    }).join('');
    return '<div class="session-detail-block"><h4 class="session-detail-title">🎬 Déroulé</h4>' +
        '<div class="session-match-strip">' + cells + '</div>' +
        '<div class="match-controls">' +
        '<button type="button" class="match-control" data-action="prev" aria-label="Match précédent">‹</button>' +
        '<button type="button" class="match-control match-control--play" data-action="play" aria-label="Rejouer la soirée">▶</button>' +
        '<button type="button" class="match-control" data-action="next" aria-label="Match suivant">›</button>' +
        '</div><div class="match-panel" hidden></div></div>';
}

function buildAheadMatrix(players, matrix) {
    if (!matrix || !players || players.length < 2) return '';
    var names = players.map(function(p) { return p.name; }).sort();
    if (!names.some(function(name) { return matrix[name]; })) return '';
    function ahead(a, b) { return (matrix[a] && matrix[a][b]) || 0; }
    var pairs = [];
    names.forEach(function(a, i) {
        names.slice(i + 1).forEach(function(b) {
            pairs.push(ahead(a, b) >= ahead(b, a) ? [a, b] : [b, a]);
        });
    });
    pairs.sort(function(p, q) {
        return (ahead(q[0], q[1]) - ahead(q[1], q[0])) - (ahead(p[0], p[1]) - ahead(p[1], p[0]));
    });
    var rows = pairs.map(function(pair) {
        var a = pair[0], b = pair[1];
        var x = ahead(a, b), y = ahead(b, a), total = x + y || 1;
        return '<div class="h2h-row">' +
            '<span class="h2h-name h2h-name--left">' + playerLabel(a) + '</span>' +
            '<span class="h2h-count' + (x > y ? ' is-ahead' : '') + '">' + x + '</span>' +
            '<div class="h2h-bar">' +
            '<span style="width: ' + (100 * x / total) + '%; background: ' + getPlayerColor(a) + ';"></span>' +
            '<span style="width: ' + (100 * y / total) + '%; background: ' + getPlayerColor(b) + ';"></span>' +
            '</div>' +
            '<span class="h2h-count' + (y > x ? ' is-ahead' : '') + '">' + y + '</span>' +
            '<span class="h2h-name">' + playerLabel(b) + '</span></div>';
    }).join('');
    return '<div class="session-detail-block"><h4 class="session-detail-title">🏆 Qui finit devant qui <span class="session-detail-hint">(matchs terminés devant l\'autre)</span></h4>' +
        rows + '</div>';
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
                return '<td class="session-duel-self" title="Auto-kills — se tuer soi-même">' + (count || '-') + '</td>';
            }
            var intensity = max > 0 ? count / max : 0;
            var hue = (1 - intensity) * 120;
            return '<td style="background-color: hsla(' + hue + ', 70%, 52%, 0.40);">' + (count || '-') + '</td>';
        }).join('');
        return '<tr><td>' + playerLabel(killer) + '</td>' + cells + '</tr>';
    }).join('');
    return '<div class="session-detail-block"><h4 class="session-detail-title">🎯 Duels</h4>' +
        '<div class="ranking-scroll"><table class="ranking-table session-duel-table"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
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

function matchTarget(matches, target) {
    if (target) return target;
    return matches.reduce(function(max, match) {
        return match.winner ? Math.max(max, match.scores[match.winner] || 0) : max;
    }, 0);
}

function buildCoins(score, target, size) {
    var filled = Math.min(score, target);
    var html = '';
    for (var i = 0; i < target; i++) {
        html += '<span class="match-coin' + (i < filled ? ' is-filled' : '') + '"></span>';
    }
    for (var j = target; j < score; j++) {
        html += '<span class="match-coin is-bonus"></span>';
    }
    return '<span class="match-coins match-coins--' + size + '">' + html + '</span>';
}

var MATCH_KIND_BADGES = { close: 'Serré', blowout: 'Carton', tie: 'Égalité' };

function buildMatchRows(match, target, size) {
    var names = Object.keys(match.scores).sort(function(a, b) { return a.localeCompare(b); });
    return names.map(function(name) {
        var isWinner = name === match.winner;
        var score = match.scores[name];
        return '<div class="match-panel-row' + (isWinner ? ' is-winner' : '') + '">' +
            '<span class="match-crown" aria-hidden="true">' + (isWinner ? '👑' : '') + '</span>' +
            '<span class="match-panel-name" style="color: ' + getPlayerColor(name) + ';">' + name + '</span>' +
            buildCoins(score, target, size) +
            '<span class="match-panel-score">' + score + '</span></div>';
    }).join('');
}

function matchSubtitle(match) {
    return match.winner ? playerLabel(match.winner) + ' +' + match.margin : 'Égalité';
}

function buildMatchBadge(match) {
    var label = match.kind && match.kind !== 'tie' ? MATCH_KIND_BADGES[match.kind] : '';
    return label ? '<span class="match-badge match-badge--' + match.kind + '">' + label + '</span>' : '';
}

function buildMatchTimeline(players, matches, target) {
    if (!matches || matches.length === 0) return '';
    var goal = matchTarget(matches, target);
    var cards = matches.map(function(match, i) {
        var color = match.winner ? getPlayerColor(match.winner) : 'var(--border)';
        return '<div class="match-card" role="button" tabindex="0" data-match-index="' + i + '" style="border-top-color: ' + color + ';">' +
            '<div class="match-card-head"><span class="match-card-number">Match ' + (i + 1) + '</span>' +
            '<span class="match-card-result">' + matchSubtitle(match) + '</span>' + buildMatchBadge(match) + '</div>' +
            buildMatchRows(match, goal, 'md') + '</div>';
    }).join('');
    return '<div class="session-detail-block"><h4 class="session-detail-title">📜 Match par match</h4>' +
        '<div class="match-card-grid">' + cards + '</div></div>';
}

function buildMatchPanel(match, index, target) {
    return '<div class="match-panel-title">Match ' + (index + 1) + ' · ' + matchSubtitle(match) + buildMatchBadge(match) + '</div>' +
        buildMatchRows(match, target, 'lg');
}

var MATCH_REPLAY_MS = 1200;

function bindMatchStrip(card, session) {
    var details = session.details || {};
    var matches = details.matches || [];
    var strip = card.querySelector('.session-match-strip');
    var panel = card.querySelector('.match-panel');
    if (!strip || !panel || matches.length === 0) return;
    var goal = matchTarget(matches, details.target);
    var grid = card.querySelector('.match-card-grid');
    var controls = card.querySelector('.match-controls');
    var playBtn = controls && controls.querySelector('[data-action="play"]');
    var prevBtn = controls && controls.querySelector('[data-action="prev"]');
    var current = -1;
    var playTimer = null;

    function selectMatch(index) {
        var chip = strip.querySelector('.session-match-chip[data-match-index="' + index + '"]');
        if (!chip) return false;
        card.querySelectorAll('.session-match-chip.is-active, .match-card.is-active').forEach(function(el) {
            el.classList.remove('is-active');
        });
        chip.classList.add('is-active');
        var matchCard = grid && grid.querySelector('.match-card[data-match-index="' + index + '"]');
        if (matchCard) matchCard.classList.add('is-active');
        panel.innerHTML = buildMatchPanel(matches[index], index, goal);
        panel.hidden = false;
        current = index;
        if (prevBtn) prevBtn.disabled = index === 0;
        return true;
    }

    function stopPlayback() {
        clearInterval(playTimer);
        playTimer = null;
        if (playBtn) {
            playBtn.textContent = '▶';
            playBtn.setAttribute('aria-label', 'Rejouer la soirée');
        }
    }

    function startPlayback() {
        selectMatch(0);
        playBtn.textContent = '⏸';
        playBtn.setAttribute('aria-label', 'Pause');
        playTimer = setInterval(function() {
            if (!card.isConnected || current >= matches.length - 1) {
                stopPlayback();
                return;
            }
            selectMatch(current + 1);
        }, MATCH_REPLAY_MS);
    }

    if (controls) {
        controls.addEventListener('click', function(e) {
            var btn = e.target.closest('.match-control');
            if (!btn) return;
            var action = btn.dataset.action;
            if (action === 'play') {
                if (playTimer) stopPlayback(); else startPlayback();
                return;
            }
            stopPlayback();
            if (action === 'prev' && current > 0) selectMatch(current - 1);
            if (action === 'next') selectMatch((current + 1) % matches.length);
        });
    }

    strip.addEventListener('click', function(e) {
        var chip = e.target.closest('.session-match-chip');
        if (!chip) return;
        stopPlayback();
        selectMatch(parseInt(chip.dataset.matchIndex, 10));
    });
    selectMatch(matches.length - 1);
    if (!grid) return;
    function onCard(e) {
        var matchCard = e.target.closest('.match-card');
        if (!matchCard) return;
        if (e.type === 'keydown') {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            e.preventDefault();
        }
        stopPlayback();
        if (selectMatch(parseInt(matchCard.dataset.matchIndex, 10))) {
            strip.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    grid.addEventListener('click', onCard);
    grid.addEventListener('keydown', onCard);
}

function buildSessionDetails(session, open) {
    var details = session.details || {};
    var combat = details.combat || {};
    var body = buildScoreboard(session.players, details.scoreboard, details.lead_changes) +
        buildMatchStrip(session.players, details.matches) +
        buildAheadMatrix(session.players, details.ahead_matrix) +
        buildDuelMatrix(session.players, combat) +
        buildDeathCauses(session.players, combat) +
        buildMatchTimeline(session.players, details.matches, details.target);
    if (!body) return '';
    return '<details class="session-details"' + (open ? ' open' : '') + '><summary class="session-details-summary">Détails de la soirée</summary>' +
        '<div class="session-details-body">' + body + '</div></details>';
}

function buildSessionCard(session, highlight, openDetails) {
    var card = document.createElement('div');
    card.className = 'session-card p-2 sm:p-4 md:p-[15px]';
    card.dataset.sessionKey = session.session_select_id;
    if (highlight) card.classList.add('session-card--highlight');
    card.innerHTML = buildSessionHeader(session) + buildSessionPodium(session) +
        buildSessionAwards((session.details || {}).awards) + buildSessionTable(session) + buildSessionDetails(session, openDetails);
    var tbl = card.querySelector('table');
    if (tbl) makeTableSortable(tbl);
    bindMatchStrip(card, session);
    bindScoreboard(card, session);
    return card;
}

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

let filtersInitialized = false;

function initFilters() {
    if (typeof allSessions === 'undefined' || allSessions.length === 0) {
        filteredSessions = [];
        return;
    }

    if (filteredSessions.length === 0 && !currentPlayerFilter && !currentGroupFilter) {
        filteredSessions = allSessions.slice();
        updateSessionsCount();
    }

    // Do not wipe the user's select: only copy JS state onto the select when that state is non-empty.
    if (filtersInitialized) {
        const playerSelect = document.getElementById('filter-player');
        if (playerSelect) {
            if (currentPlayerFilter && playerSelect.value !== currentPlayerFilter) {
                playerSelect.value = currentPlayerFilter;
            }
        }

        const groupSelect = document.getElementById('filter-group');
        if (groupSelect) {
            if (currentGroupFilter && groupSelect.value !== currentGroupFilter) {
                groupSelect.value = currentGroupFilter;
            }
        }

        updatePagination();
        updateSessionsCount();
        return;
    }

    const allPlayers = new Set();
    const allGroups = new Set();

    allSessions.forEach(function(session) {
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

    const sortedPlayers = Array.from(allPlayers).sort();
    const sortedGroups = Array.from(allGroups).sort();

    const playerSelect = document.getElementById('filter-player');
    if (playerSelect) {
        if (playerSelect.children.length === 1) {
            sortedPlayers.forEach(function(player) {
                const option = document.createElement('option');
                option.value = player;
                option.textContent = player;
                playerSelect.appendChild(option);
            });
        }

        if (playerSelect.value && !currentPlayerFilter) {
            currentPlayerFilter = playerSelect.value;
        }
        else if (currentPlayerFilter && playerSelect.value !== currentPlayerFilter) {
            playerSelect.value = currentPlayerFilter;
        }

        if (!filtersListenersAttached) {
            playerFilterHandler = function() {
                currentPlayerFilter = this.value;
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

    const groupSelect = document.getElementById('filter-group');
    if (groupSelect) {
        if (groupSelect.children.length === 1) {
            sortedGroups.forEach(function(group) {
                const option = document.createElement('option');
                option.value = group;
                option.textContent = group;
                groupSelect.appendChild(option);
            });
        }

        if (groupSelect.value && !currentGroupFilter) {
            currentGroupFilter = groupSelect.value;
        }
        else if (currentGroupFilter && groupSelect.value !== currentGroupFilter) {
            groupSelect.value = currentGroupFilter;
        }

        if (!filtersListenersAttached) {
            groupFilterHandler = function() {
                currentGroupFilter = this.value;
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

    if (filteredSessions.length === 0) {
        filteredSessions = allSessions.slice();
    }
    updatePagination();
    updateSessionsCount();
    filtersInitialized = true;
}

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

                initFilters();

                if (filteredSessions.length === 0 && typeof allSessions !== 'undefined' && allSessions.length > 0) {
                    filteredSessions = allSessions.slice();
                    updatePagination();
                    updateSessionsCount();
                }

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
    'fiches': 'fiches',
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
    'fiches': 'fiches',
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
    var visibleHeights = {};
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            visibleHeights[entry.target.id] = entry.isIntersecting ? entry.intersectionRect.height : 0;
        });
        var bestId = null;
        Object.keys(visibleHeights).forEach(function(id) {
            if (visibleHeights[id] > 0 && (!bestId || visibleHeights[id] > visibleHeights[bestId])) {
                bestId = id;
            }
        });
        if (bestId && SECTION_NAV_MAP[bestId]) {
            setActiveNav(SECTION_NAV_MAP[bestId]);
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
    var tabs = document.querySelectorAll('.evolution-tab[data-tab]');
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

let evolutionChart = null;

function initEvolutionChart() {
    if (typeof allSessions === 'undefined' || allSessions.length === 0) {
        return;
    }

    const allGroups = new Set();
    allSessions.forEach(function(session) {
        const group = session.group || session.id;
        if (group) {
            allGroups.add(group);
        }
    });

    const sortedGroups = Array.from(allGroups).sort(function(a, b) {
        const rankingA = rankingsByGroup[a] || [];
        const rankingB = rankingsByGroup[b] || [];
        const bestScoreA = rankingA.length > 0 ? rankingA[0][1] : 0;
        const bestScoreB = rankingB.length > 0 ? rankingB[0][1] : 0;
        return bestScoreB - bestScoreA;
    });

    const groupSelect = document.getElementById('evolution-group-select');
    const cumulCheckbox = document.getElementById('evolution-cumul-checkbox');
    
    if (groupSelect) {
        sortedGroups.forEach(function(group) {
            const option = document.createElement('option');
            option.value = group;
            option.textContent = group;
            groupSelect.appendChild(option);
        });

        groupSelect.addEventListener('change', function() {
            const isCumul = cumulCheckbox ? cumulCheckbox.checked : true;
            updateEvolutionChart(this.value, isCumul);
        });
        
        if (cumulCheckbox) {
            cumulCheckbox.addEventListener('change', function() {
                const groupId = groupSelect.value;
                if (groupId) {
                    updateEvolutionChart(groupId, this.checked);
                }
            });
        }

        if (sortedGroups.length > 0) {
            groupSelect.value = sortedGroups[0];
            const isCumul = cumulCheckbox ? cumulCheckbox.checked : true;
            updateEvolutionChart(sortedGroups[0], isCumul);
        }
    }
}

function updateEvolutionChart(groupId, isCumul) {
    if (typeof allSessions === 'undefined' || !groupId) {
        return;
    }
    
    if (typeof isCumul === 'undefined') {
        const cumulCheckbox = document.getElementById('evolution-cumul-checkbox');
        isCumul = cumulCheckbox ? cumulCheckbox.checked : true;
    }

    const groupSessions = allSessions.filter(function(session) {
        const sessionGroup = session.group || session.id;
        return sessionGroup === groupId;
    });

    if (groupSessions.length === 0) {
        return;
    }

    const dataByDate = {};
    const dateMapping = {};
    const allPlayers = new Set();

    groupSessions.forEach(function(session) {
        const originalDate = session.date;
        const formattedDate = session.formatted_date || session.date;
        
        if (!dataByDate[originalDate]) {
            dataByDate[originalDate] = {};
            dateMapping[originalDate] = formattedDate;
        }
        
        if (session.players) {
            session.players.forEach(function(player) {
                allPlayers.add(player.name);
                const value = isCumul ? (player.total || 0) : (player.today || 0);
                if (!dataByDate[originalDate][player.name]) {
                    dataByDate[originalDate][player.name] = 0;
                }
                dataByDate[originalDate][player.name] = value;
            });
        }
    });

    // Sort by source YYYY-MM-DD so the chart reads oldest to newest (formatted dates would not).
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

    evolutionChart = mountPlayerLineChart(evolutionChart, 'evolution-chart', {
        type: 'bar',
        labels: sortedDates,
        datasets: datasets,
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
}

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
    winRateEvolutionChart = mountPlayerLineChart(winRateEvolutionChart, 'win-rate-evolution-chart-canvas', {
        labels: labels,
        datasets: datasets,
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

    eveningCurveChart = mountPlayerLineChart(eveningCurveChart, 'evening-curve-chart-canvas', {
        labels: eveningCurveData.labels,
        datasets: datasets,
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
}

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

function mountPlayerLineChart(existingChart, canvasId, spec) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) {
        return existingChart;
    }
    if (existingChart) {
        existingChart.destroy();
    }
    var chart = new Chart(canvas.getContext('2d'), {
        type: spec.type || 'line',
        data: { labels: spec.labels, datasets: spec.datasets },
        options: spec.options
    });
    chart._hoverDatasetIndex = null;
    bindMultiSeriesChartHoverReset(canvas, function() { return chart; });
    return chart;
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

function buildEloLineChartOptions(xTitle, xTickLimit, hoverChartRef) {
    return buildPlayerLineChartOptions({
        xTitle: xTitle,
        yTitle: 'ELO',
        xTickLimit: xTickLimit,
        hoverChartRef: hoverChartRef
    });
}

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
    eloEvolutionChart = mountPlayerLineChart(eloEvolutionChart, 'elo-evolution-chart-canvas', {
        labels: labels,
        datasets: datasets,
        options: buildPlayerLineChartOptions({
            xTitle: 'Session',
            yTitle: 'ELO',
            hoverChartRef: function() { return eloEvolutionChart; }
        })
    });
}

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
    const isMatchView = getEloMatchGranularity() === 'match';
    eloMatchEvolutionChart = mountPlayerLineChart(eloMatchEvolutionChart, 'elo-match-evolution-chart-canvas', {
        labels: labels,
        datasets: datasets,
        options: buildEloLineChartOptions('Match', isMatchView ? 24 : undefined, function() {
            return eloMatchEvolutionChart;
        })
    });
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

// Move bubbles into #app-overlays so they paint above the arcade theme.
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
        backdrop.addEventListener('wheel', function(e) {
            if (document.documentElement.classList.contains('live-popin-open')) {
                e.preventDefault();
            }
        }, { passive: false });
        backdrop.addEventListener('touchmove', function(e) {
            if (document.documentElement.classList.contains('live-popin-open')) {
                e.preventDefault();
            }
        }, { passive: false });
    }
}

var liveScrollLockY = null;

function setLivePageScrollLocked(locked) {
    if (locked) {
        if (liveScrollLockY == null) {
            liveScrollLockY = window.scrollY;
        }
        document.documentElement.classList.add('live-popin-open');
        document.body.style.top = '-' + liveScrollLockY + 'px';
        return;
    }
    document.documentElement.classList.remove('live-popin-open');
    if (liveScrollLockY == null) {
        return;
    }
    var y = liveScrollLockY;
    liveScrollLockY = null;
    document.body.style.top = '';
    window.scrollTo(0, y);
}

function updateOverlayBackdrop() {
    var backdrop = document.getElementById('overlay-backdrop');
    if (!backdrop) {
        return;
    }
    var popoverOpen = document.getElementById('date-picker-popover') &&
        document.getElementById('date-picker-popover').classList.contains('active');
    var liveOpen = document.getElementById('live-popin') &&
        document.getElementById('live-popin').classList.contains('active');
    var infoOpen = document.querySelector('.info-bubble.active');
    var open = popoverOpen || liveOpen || infoOpen;
    setLivePageScrollLocked(!!liveOpen);
    var liveBtn = document.getElementById('live-button');
    if (liveBtn) {
        var liveVisible = !!liveState.session && !liveOpen;
        liveBtn.classList.toggle('is-hidden', !liveVisible);
        liveBtn.setAttribute('aria-hidden', liveVisible ? 'false' : 'true');
    }
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
    var livePopin = document.getElementById('live-popin');
    if (livePopin) {
        livePopin.classList.remove('active');
        livePopin.setAttribute('aria-hidden', 'true');
    }
    var liveBtn = document.getElementById('live-button');
    if (liveBtn) {
        liveBtn.setAttribute('aria-expanded', 'false');
    }
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

var KILL_MODE_SUBTITLES = {
    avg: 'Moyenne de kills par partie',
    totals: 'Nombre total de kills'
};
var killMode = 'avg';

function formatKillValue(mode, value) {
    if (mode === 'totals') { return String(value); }
    return value.toFixed(2);
}

function updateKillRelationshipsTable(mode) {
    const subtitle = document.getElementById('kill-relationships-subtitle');
    if (subtitle) {
        subtitle.textContent = KILL_MODE_SUBTITLES[mode] + ' — survolez un joueur pour voir ses flèches';
    }
    const cells = document.querySelectorAll('#kill-relationships-table .kill-cell');
    cells.forEach(function(cell) {
        const useTotals = mode === 'totals';
        const value = useTotals
            ? parseInt(cell.getAttribute('data-total'), 10) || 0
            : parseFloat(cell.getAttribute('data-avg')) || 0;
        const maxVal = useTotals
            ? parseInt(cell.getAttribute('data-max-total'), 10) || 1
            : parseFloat(cell.getAttribute('data-max-avg')) || 1;
        const intensity = maxVal > 0 ? Math.min(value / maxVal, 1) : 0;
        cell.textContent = value > 0 ? formatKillValue(mode, value) : '-';
        const hue = (1 - intensity) * 120;
        cell.style.backgroundColor = 'hsla(' + hue + ', 70%, 52%, 0.40)';
    });
}

function initKillModeTabs() {
    var tabs = document.querySelectorAll('.evolution-tab[data-kill-mode]');
    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            killMode = tab.getAttribute('data-kill-mode');
            tabs.forEach(function(t) {
                var active = t === tab;
                t.classList.toggle('active', active);
                t.setAttribute('aria-selected', active ? 'true' : 'false');
            });
            updateKillRelationshipsTable(killMode);
            renderRivalryMap(killMode);
        });
    });
}

var rivalryLockedPlayer = null;
var rivalryLayout = null;
var rivalryPull = {};
var rivalryAnim = null;
var RIVALRY_NS = 'http://www.w3.org/2000/svg';
var RIVALRY_NODE_R = 28;
var RIVALRY_FOCUS_BUMP = 58;
var RIVALRY_ANIM_MS = 320;

function rivalryEase(t) {
    return 1 - Math.pow(1 - t, 3);
}

function rivalryNodePos(player, amounts) {
    var p = rivalryLayout && rivalryLayout.positions[player];
    if (!p) { return { x: 0, y: 0, r: RIVALRY_NODE_R, scale: 1 }; }
    var t = (amounts && amounts[player]) || 0;
    var dx = p.x - rivalryLayout.cx;
    var dy = p.y - rivalryLayout.cy;
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    return {
        x: p.x + dx / len * RIVALRY_FOCUS_BUMP * t,
        y: p.y + dy / len * RIVALRY_FOCUS_BUMP * t,
        r: RIVALRY_NODE_R * (1 + 0.15 * t),
        scale: 1 + 0.12 * t
    };
}

function setRivalryEdgeGeometry(edge, amounts) {
    var killer = edge.getAttribute('data-killer');
    var victim = edge.getAttribute('data-victim');
    var width = parseFloat(edge.getAttribute('data-width')) || 2;
    var from = rivalryNodePos(killer, amounts);
    var to = rivalryNodePos(victim, amounts);
    var dx = to.x - from.x;
    var dy = to.y - from.y;
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    var shift = width / 2 + 1.5;
    var px = -(dy / len) * shift;
    var py = (dx / len) * shift;
    var x1 = from.x + (dx / len) * from.r + px;
    var y1 = from.y + (dy / len) * from.r + py;
    var x2 = to.x - (dx / len) * (to.r + 4) + px;
    var y2 = to.y - (dy / len) * (to.r + 4) + py;
    var line = edge.querySelector('line');
    var label = edge.querySelector('.rivalry-edge-label');
    if (line) {
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
    }
    if (label) {
        label.setAttribute('x', x1 + (x2 - x1) * 0.6 - (dy / len) * (width / 2 + 8));
        label.setAttribute('y', y1 + (y2 - y1) * 0.6 + (dx / len) * (width / 2 + 8) + 4);
    }
}

function paintRivalryLayout(svg, amounts) {
    if (!rivalryLayout || !svg) { return; }
    svg.querySelectorAll('.rivalry-node').forEach(function(node) {
        var name = node.getAttribute('data-player');
        var pos = rivalryNodePos(name, amounts);
        node.setAttribute('transform', 'translate(' + pos.x + ',' + pos.y + ') scale(' + pos.scale + ')');
    });
    svg.querySelectorAll('.rivalry-edge-group').forEach(function(edge) {
        setRivalryEdgeGeometry(edge, amounts);
    });
}

function applyRivalryLayout(svg, pulled, instant) {
    if (!rivalryLayout || !svg) { return; }
    var from = {};
    var to = {};
    Object.keys(rivalryLayout.positions).forEach(function(name) {
        from[name] = rivalryPull[name] || 0;
        to[name] = name === pulled ? 1 : 0;
    });
    var unchanged = Object.keys(to).every(function(name) {
        return Math.abs(from[name] - to[name]) < 0.001;
    });
    if (rivalryAnim) {
        cancelAnimationFrame(rivalryAnim);
        rivalryAnim = null;
    }
    if (instant || unchanged) {
        rivalryPull = to;
        paintRivalryLayout(svg, rivalryPull);
        return;
    }
    var start = performance.now();
    function frame(now) {
        var t = Math.min(1, (now - start) / RIVALRY_ANIM_MS);
        var e = rivalryEase(t);
        var amounts = {};
        Object.keys(to).forEach(function(name) {
            amounts[name] = from[name] + (to[name] - from[name]) * e;
        });
        rivalryPull = amounts;
        paintRivalryLayout(svg, amounts);
        if (t < 1) {
            rivalryAnim = requestAnimationFrame(frame);
        } else {
            rivalryAnim = null;
            rivalryPull = to;
        }
    }
    rivalryAnim = requestAnimationFrame(frame);
}

function renderRivalryMap(mode) {
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

    var dataByMode = {
        avg: typeof killRelationshipsData !== 'undefined' ? killRelationshipsData : {},
        totals: typeof killRelationshipsTotalsData !== 'undefined' ? killRelationshipsTotalsData : {}
    };
    var data = dataByMode[mode] || dataByMode.avg;
    var valueLabel = { avg: '/partie', totals: ' kills total' }[mode] || '';

    var w = Math.max(mapContainer.clientWidth || 600, 320);
    var h = Math.max(400, players.length * 58);
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.innerHTML = '';
    if (rivalryAnim) {
        cancelAnimationFrame(rivalryAnim);
        rivalryAnim = null;
    }

    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    var marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', 'arrowhead');
    marker.setAttribute('markerUnits', 'userSpaceOnUse');
    marker.setAttribute('markerWidth', '14');
    marker.setAttribute('markerHeight', '12');
    marker.setAttribute('refX', '12');
    marker.setAttribute('refY', '6');
    marker.setAttribute('orient', 'auto');
    var arrowPoly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    arrowPoly.setAttribute('points', '0 0, 14 6, 0 12');
    arrowPoly.setAttribute('fill', 'context-stroke');
    marker.appendChild(arrowPoly);
    defs.appendChild(marker);
    svg.appendChild(defs);

    var cx = w / 2;
    var cy = h / 2;
    var radius = Math.min(w, h) * 0.30;
    var positions = {};
    var n = players.length;

    players.forEach(function(player, i) {
        var angle = (i / n) * Math.PI * 2 - Math.PI / 2;
        positions[player] = {
            x: cx + radius * Math.cos(angle),
            y: cy + radius * Math.sin(angle)
        };
    });
    rivalryLayout = { cx: cx, cy: cy, positions: positions };

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

            var intensity = Math.min(val / maxVal, 1);
            var hue = (1 - intensity) * 120;
            var alpha = 0.35 + intensity * 0.55;
            var width = 1 + intensity * 5;

            var line = document.createElementNS(RIVALRY_NS, 'line');
            line.setAttribute('stroke', 'hsla(' + hue + ', 85%, 52%, ' + alpha + ')');
            line.setAttribute('stroke-width', width.toFixed(1));
            line.setAttribute('marker-end', 'url(#arrowhead)');
            line.classList.add('rivalry-edge');
            line.addEventListener('mouseenter', function(e) {
                if (tooltip) {
                    tooltip.classList.remove('hidden');
                    tooltip.textContent = killer + ' → ' + victim + ': ' + formatKillValue(mode, val) + valueLabel;
                    tooltip.style.left = (e.offsetX + 12) + 'px';
                    tooltip.style.top = (e.offsetY + 12) + 'px';
                }
            });
            line.addEventListener('mouseleave', function() {
                if (tooltip) { tooltip.classList.add('hidden'); }
            });

            var label = document.createElementNS(RIVALRY_NS, 'text');
            label.setAttribute('text-anchor', 'middle');
            label.classList.add('rivalry-edge-label');
            label.textContent = formatKillValue(mode, val);

            var edge = document.createElementNS(RIVALRY_NS, 'g');
            edge.classList.add('rivalry-edge-group');
            edge.setAttribute('data-killer', killer);
            edge.setAttribute('data-victim', victim);
            edge.setAttribute('data-width', width.toFixed(1));
            edge.appendChild(line);
            edge.appendChild(label);
            svg.appendChild(edge);
            setRivalryEdgeGeometry(edge, rivalryPull);
        });
    });

    players.forEach(function(player) {
        var color = getPlayerColor(player);
        var g = document.createElementNS(RIVALRY_NS, 'g');
        g.classList.add('rivalry-node');
        g.setAttribute('data-player', player);
        g.addEventListener('mouseenter', function() { applyRivalryFocus(svg, player); });
        g.addEventListener('mouseleave', function() { applyRivalryFocus(svg, rivalryLockedPlayer); });
        g.addEventListener('click', function(e) {
            e.stopPropagation();
            rivalryLockedPlayer = rivalryLockedPlayer === player ? null : player;
            applyRivalryFocus(svg, rivalryLockedPlayer || player);
        });

        var hit = document.createElementNS(RIVALRY_NS, 'circle');
        hit.setAttribute('r', '34');
        hit.setAttribute('fill', 'transparent');
        g.appendChild(hit);

        var circle = document.createElementNS(RIVALRY_NS, 'circle');
        circle.setAttribute('r', '26');
        circle.setAttribute('fill', color);
        circle.setAttribute('stroke', '#f2c94c');
        circle.setAttribute('stroke-width', '3');
        circle.classList.add('rivalry-node-circle');
        g.appendChild(circle);

        var letter = document.createElementNS(RIVALRY_NS, 'text');
        letter.setAttribute('y', '5');
        letter.setAttribute('text-anchor', 'middle');
        letter.setAttribute('fill', '#1a1a2e');
        letter.setAttribute('font-family', 'Press Start 2P, cursive');
        letter.setAttribute('font-size', '14');
        letter.textContent = player.charAt(0);
        g.appendChild(letter);

        var name = document.createElementNS(RIVALRY_NS, 'text');
        name.setAttribute('y', '42');
        name.setAttribute('text-anchor', 'middle');
        name.setAttribute('fill', color);
        name.setAttribute('font-family', 'Inter, sans-serif');
        name.setAttribute('font-size', '11');
        name.setAttribute('font-weight', 'bold');
        name.classList.add('rivalry-node-name');
        name.textContent = player.length > 8 ? player.substring(0, 7) + '…' : player;
        g.appendChild(name);
        svg.appendChild(g);
    });

    applyRivalryFocus(svg, rivalryLockedPlayer, true);
}

function applyRivalryFocus(svg, player, instant) {
    svg.classList.toggle('rivalry-map--focused', !!player);
    svg.querySelectorAll('.rivalry-edge-group').forEach(function(edge) {
        var involved = edge.getAttribute('data-killer') === player
            || edge.getAttribute('data-victim') === player;
        edge.classList.toggle('is-focused', involved);
        edge.classList.toggle('is-outgoing', edge.getAttribute('data-killer') === player);
        edge.classList.toggle('is-incoming', edge.getAttribute('data-victim') === player);
    });
    svg.querySelectorAll('.rivalry-node').forEach(function(node) {
        node.classList.toggle('is-selected', node.getAttribute('data-player') === player);
    });
    applyRivalryLayout(svg, rivalryLockedPlayer, instant);
}

function initRivalryMap() {
    if (typeof hasDetailedStats !== 'undefined' && !hasDetailedStats) {
        return;
    }
    var svg = document.getElementById('rivalry-map');
    if (svg) {
        svg.addEventListener('click', function() {
            rivalryLockedPlayer = null;
            applyRivalryFocus(svg, null);
        });
    }
    renderRivalryMap(killMode);
    window.addEventListener('resize', function() {
        renderRivalryMap(killMode);
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

var LIVE_POLL_MS = 60000;
var LIVE_IDLE_POLL_MS = 300000;
var liveState = {
    session: (typeof liveSession !== 'undefined') ? liveSession : null,
    fetchedAt: Date.now(),
    renderedKey: null,
    timer: null
};

function setLiveButtonVisible(session) {
    document.querySelectorAll('#live-button .live-button-group, #live-popin-title .live-button-group').forEach(function(group) {
        group.textContent = session ? (session.id || '') : '';
    });
    var btn = document.getElementById('live-button');
    if (!btn) {
        return;
    }
    var popin = document.getElementById('live-popin');
    var popinOpen = popin && popin.classList.contains('active');
    var visible = !!session && !popinOpen;
    btn.classList.toggle('is-hidden', !visible);
    btn.setAttribute('aria-hidden', visible ? 'false' : 'true');
}

function formatLiveUpdated(session, from) {
    var details = session.details || {};
    var parts = [];
    if (details.match_count) {
        parts.push(details.match_count + ' match' + (details.match_count > 1 ? 's' : '') + ' joué' + (details.match_count > 1 ? 's' : ''));
    }
    if (details.hour != null) parts.push('dernier envoi vers ' + details.hour + 'h');
    var seconds = Math.max(0, Math.round((Date.now() - from) / 1000));
    parts.push('vérifié il y a ' + seconds + 's');
    return parts.join(' · ');
}

function updateLiveUpdatedLabel() {
    var el = document.getElementById('live-popin-updated');
    if (!el) {
        return;
    }
    el.textContent = liveState.session ? formatLiveUpdated(liveState.session, liveState.fetchedAt) : '';
}

function renderLivePopin(session) {
    var body = document.getElementById('live-popin-body');
    if (!body) {
        return;
    }
    var key = session ? JSON.stringify(session) : 'ended';
    if (key === liveState.renderedKey) {
        return;
    }
    liveState.renderedKey = key;
    destroySessionCharts(body);
    body.innerHTML = '';
    if (!session) {
        body.innerHTML = '<p class="live-popin-ended">Session terminée</p>';
        return;
    }
    body.appendChild(buildSessionCard(Object.assign({}, session, { live: true }), false, true));
}

function applyLivePayload(payload) {
    var session = payload && payload.live ? payload.session : null;
    liveState.session = session;
    liveState.fetchedAt = Date.now();
    setLiveButtonVisible(session);
    var popin = document.getElementById('live-popin');
    if (popin && popin.classList.contains('active')) {
        renderLivePopin(session);
        updateLiveUpdatedLabel();
    }
}

function scheduleLivePoll() {
    clearTimeout(liveState.timer);
    liveState.timer = setTimeout(fetchLiveSession, liveState.session ? LIVE_POLL_MS : LIVE_IDLE_POLL_MS);
}

function fetchLiveSession() {
    if (document.hidden) {
        scheduleLivePoll();
        return;
    }
    fetch('/api/live').then(function(res) {
        return res.ok ? res.json() : null;
    }).then(function(data) {
        if (data) {
            applyLivePayload(data);
        }
    }).catch(function() {}).then(scheduleLivePoll);
}

function openLivePopin() {
    var popin = document.getElementById('live-popin');
    if (!popin) {
        return;
    }
    var datePopover = document.getElementById('date-picker-popover');
    if (datePopover) {
        datePopover.classList.remove('active');
        datePopover.setAttribute('aria-hidden', 'true');
        setFilterToggleOpen(false);
    }
    document.querySelectorAll('.info-bubble.active').forEach(function(bubble) {
        bubble.classList.remove('active');
        bubble.style.transform = '';
    });
    renderLivePopin(liveState.session);
    updateLiveUpdatedLabel();
    popin.classList.add('active');
    popin.setAttribute('aria-hidden', 'false');
    var liveBtn = document.getElementById('live-button');
    if (liveBtn) {
        liveBtn.setAttribute('aria-expanded', 'true');
    }
    updateOverlayBackdrop();
}

function closeLivePopin() {
    var popin = document.getElementById('live-popin');
    if (!popin) {
        return;
    }
    popin.classList.remove('active');
    popin.setAttribute('aria-hidden', 'true');
    var liveBtn = document.getElementById('live-button');
    if (liveBtn) {
        liveBtn.setAttribute('aria-expanded', 'false');
    }
    updateOverlayBackdrop();
}

function initLiveSession() {
    var btn = document.getElementById('live-button');
    var popin = document.getElementById('live-popin');
    if (!btn || !popin) {
        return;
    }
    setLiveButtonVisible(liveState.session);
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (popin.classList.contains('active')) {
            closeLivePopin();
        } else {
            openLivePopin();
        }
    });
    var closeBtn = popin.querySelector('.live-popin-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeLivePopin);
    }
    scheduleLivePoll();
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            fetchLiveSession();
        }
    });
    setInterval(function() {
        if (popin.classList.contains('active')) {
            updateLiveUpdatedLabel();
        }
    }, 1000);
}

document.addEventListener('DOMContentLoaded', function() {
    initBackgroundParallax();
    initOverlayPortal();
    initRankingTable();
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
    initLiveSession();
    if (hasDetailedStats) {
        initKillModeTabs();
        initRivalryMap();
    }
    initAnchorOnLoad();
});

window.addEventListener('hashchange', scrollToAnchor);

