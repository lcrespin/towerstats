const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const context = {
    document: { addEventListener() {} },
    window: { addEventListener() {} },
    console,
};
vm.createContext(context);
vm.runInContext(
    fs.readFileSync(path.join(__dirname, '../static/js/app.js'), 'utf8'),
    context
);

const sessionPlayers = [
    { name: 'ALICE', today: 3, total: 10, rank: 1 },
    { name: 'BOB', today: 1, total: 20, rank: 2 },
    { name: 'CARL', today: 0, total: 5, rank: 3 },
];

test('group podium title names the players and the season', () => {
    assert.equal(
        context.formatGroupPodiumTitle('DAVID-ERIC-LOUIS', 'saison 2'),
        'David Eric Louis saison 2'
    );
    assert.equal(
        context.formatGroupPodiumTitle('ERIC-LOUIS', 'all-time'),
        'Eric Louis all-time'
    );
});

test('a player with 0 wins still appears on the session podium', () => {
    const html = context.buildSessionPodium({
        players: sessionPlayers,
    });
    assert.match(html, /CARL/);
    assert.match(html, /pixel-podium-slot--3">[\s\S]*pixel-podium-value led-value">0<\/div><div class="pixel-podium-detail">victoires</);
    assert.doesNotMatch(html, /Saison/);
    assert.doesNotMatch(html, /Soirée/);
});

test('session header shows the exact end hour, not an approximate fin vers', () => {
    const html = context.buildSessionHeader({
        id: 'DAVID-ERIC-LOUIS',
        formatted_date: '08/10/2026',
        game_mode_label: 'Head Hunters',
        players: [{ name: 'DAVID' }, { name: 'ERIC' }, { name: 'LOUIS' }],
        details: { hour: 0, match_count: 33 },
    });
    assert.doesNotMatch(html, /fin vers/);
    assert.match(html, /08\/10\/2026 · fin à 0h · Head Hunters · 33 matchs · 3 joueurs/);
});

test('evening session table has no win percentage column', () => {
    const html = context.buildSessionTable({
        players: sessionPlayers,
        details: { combat: {} },
    });
    assert.doesNotMatch(html, /<th>%<\/th>/);
    assert.match(html, /<th>Victoires<\/th><th>Saison<\/th>/);
});

test('session and duel tables mark the player column for sticky scrolling', () => {
    const sessionHtml = context.buildSessionTable({
        players: sessionPlayers,
        details: { combat: {} },
    });
    assert.match(sessionHtml, /<th class="player-column">Joueur<\/th>/);
    assert.match(sessionHtml, /<td class="player-column rank-1"/);

    const duelHtml = context.buildDuelMatrix(sessionPlayers, {
        ALICE: { killBy: { BOB: 2 } },
        BOB: { killBy: { ALICE: 1 } },
    });
    assert.match(duelHtml, /<th class="player-column">Tueur → Victime<\/th>/);
    assert.match(duelHtml, /<td class="player-column">/);
});

test('archive session badge uses soiree number, date, mode and player count', () => {
    context.allSessions = [
        {
            session_select_id: '2026-10-08|DAVID-ERIC-LOUIS|HeadHunters',
            formatted_date: '08/10/2026',
            game_mode_label: 'Head Hunters',
            players: [{ name: 'DAVID' }, { name: 'ERIC' }, { name: 'LOUIS' }],
        },
        {
            session_select_id: '2026-10-01|ERIC-LOUIS|HeadHunters',
            formatted_date: '01/10/2026',
            game_mode_label: 'Head Hunters',
            players: [{ name: 'ERIC' }, { name: 'LOUIS' }],
        },
    ];
    assert.equal(
        context.buildSessionBadge(context.allSessions[0]),
        '<div class="session-badge">Soirée #2 - le 08/10/2026 · Head Hunters · 3 joueur(s)</div>'
    );
    assert.equal(
        context.buildSessionBadge(context.allSessions[1]),
        '<div class="session-badge">Soirée #1 - le 01/10/2026 · Head Hunters · 2 joueur(s)</div>'
    );
    assert.equal(context.buildSessionBadge({ live: true, ...context.allSessions[0] }), '');

    const sameDay = {
        session_select_id: '2026-10-08|DAVID-ERIC-LOUIS|HeadHunters',
        formatted_date: '08/10/2026',
        game_mode_label: 'Head Hunters',
        players: [{ name: 'DAVID' }, { name: 'ERIC' }],
    };
    context.allSessions.push(sameDay);
    assert.equal(
        context.buildSessionBadge(sameDay),
        '<div class="session-badge">Soirée #1 - le 08/10/2026 · Head Hunters · 2 joueur(s)</div>'
    );
});

test('replay session shows titled soirée and saison podiums side by side', () => {
    const html = context.buildSessionPodium({
        replay: true,
        players: sessionPlayers,
    });
    assert.match(html, /session-podiums/);
    assert.match(html, /Soirée/);
    assert.match(html, /Saison/);
});

test('live session shows titled soirée and saison podiums side by side', () => {
    const html = context.buildSessionPodium({
        live: true,
        players: sessionPlayers,
    });
    assert.match(html, /session-podiums/);
    assert.match(html, /Soirée/);
    assert.match(html, /Saison/);
    assert.match(html, /pixel-podium-name[^>]*>BOB<\/div><\/div><div class="pixel-podium-value led-value">20</);
    assert.match(html, /pixel-podium-name[^>]*>ALICE<\/div><\/div><div class="pixel-podium-value led-value">3</);
});
