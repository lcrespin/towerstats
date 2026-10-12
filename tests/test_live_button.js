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

test('scroll-up button stays hidden until the page has moved down', () => {
    assert.equal(context.shouldShowScrollTop(0), false);
    assert.equal(context.shouldShowScrollTop(400), false);
    assert.equal(context.shouldShowScrollTop(401), true);
});

test('live chrome uses LIVE when active and REPLAY when idle', () => {
    assert.equal(context.liveChromeLabel(true), 'LIVE');
    assert.equal(context.liveChromeLabel(false), 'REPLAY');
});

test('live payload keeps the last session when the evening is not live', () => {
    const last = { id: 'ERIC-LOUIS', session_select_id: '2026-08-26|ERIC-LOUIS|HeadHunters' };
    const idle = context.liveStateFromPayload({ live: false, session: last });
    assert.equal(idle.live, false);
    assert.equal(idle.session, last);
    const active = context.liveStateFromPayload({ live: true, session: last });
    assert.equal(active.live, true);
    assert.equal(active.session, last);
});

test('replay popin card is an archive session, live popin is marked live', () => {
    const session = {
        id: 'ERIC-LOUIS',
        session_select_id: '2026-08-26|ERIC-LOUIS|HeadHunters',
        formatted_date: '26/08/2026',
        game_mode_label: 'Head Hunters',
        players: [
            { name: 'ERIC', today: 3, total: 10, rank: 1 },
            { name: 'LOUIS', today: 1, total: 20, rank: 2 },
        ],
    };
    context.allSessions = [session];

    const replay = context.sessionForLivePopin(session, false);
    assert.equal(replay.replay, true);
    assert.equal(replay.live, undefined);
    assert.match(context.buildSessionBadge(replay), /Soirée #1/);
    assert.match(context.buildSessionPodium(replay), /Soirée/);
    assert.match(context.buildSessionPodium(replay), /Saison/);

    const live = context.sessionForLivePopin(session, true);
    assert.equal(live.live, true);
    assert.equal(context.buildSessionBadge(live), '');
    assert.match(context.buildSessionPodium(live), /Saison/);
});

test('replay popin resolves the soiree badge from an API session copy', () => {
    const session = {
        session_select_id: '2026-10-08|DAVID-ERIC-LOUIS|HeadHunters',
        formatted_date: '08/10/2026',
        game_mode_label: 'Head Hunters',
        players: [{ name: 'DAVID' }, { name: 'ERIC' }, { name: 'LOUIS' }],
    };
    context.allSessions = [session];
    const replay = context.sessionForLivePopin(Object.assign({}, session), false);
    assert.match(context.buildSessionBadge(replay), /Soirée #1 - le 08\/10\/2026/);
});
