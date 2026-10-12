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

function coinCount(html) {
    return (html.match(/class="match-coin(?:\s|")/g) || []).length;
}

test('a 4-point match shows 4 coins even when the evening target is 8', () => {
    const match = { winner: 'ERIC', scores: { ERIC: 4, LOUIS: 2 }, target: 4 };
    assert.equal(context.matchGoal(match, 8), 4);
    const html = context.buildCoins(4, context.matchGoal(match, 8), 'md');
    assert.equal(coinCount(html), 4);
    assert.equal((html.match(/is-filled/g) || []).length, 4);
});

test('an 8-point match keeps 8 coins', () => {
    const match = { winner: 'ERIC', scores: { ERIC: 8, LOUIS: 3 }, target: 8 };
    assert.equal(context.matchGoal(match, 8), 8);
    assert.equal(coinCount(context.buildCoins(8, context.matchGoal(match), 'md')), 8);
});

test('an odd winning score uses the even goal and a bonus coin', () => {
    const match = { winner: 'ERIC', scores: { ERIC: 11, LOUIS: 9 } };
    assert.equal(context.matchGoal(match), 10);
    const html = context.buildCoins(11, context.matchGoal(match), 'md');
    assert.equal(coinCount(html), 11);
    assert.equal((html.match(/is-filled/g) || []).length, 10);
    assert.equal((html.match(/is-bonus/g) || []).length, 1);
});

test('timeline cards use each match goal instead of one evening target', () => {
    const matches = [
        { winner: 'ERIC', scores: { ERIC: 4, LOUIS: 2 }, target: 4 },
        { winner: 'LOUIS', scores: { ERIC: 3, LOUIS: 8 }, target: 8 },
    ];
    const html = context.buildMatchTimeline([], matches, 8);
    assert.equal(coinCount(html), 24);
});
