import {formatClock, resultTitle} from './match-flow.js';
import {GAMEPLAY_TUNING} from './tuning.js';

const modeLabel = mode => mode === 'kc' || mode === 'kill-confirmed' ? 'KILL CONFIRMED' : 'TEAM DEATHMATCH';

export class MatchUI {
  constructor(document, handlers = {}) {
    this.document = document;
    this.handlers = handlers;
    this.previousPhase = null;
    this.disposers = [];
    this.$ = id => document.getElementById(id);
    const modes=GAMEPLAY_TUNING.modes;this.text('match-limit-summary',`TDM: ${modes.tdm.scoreLimit} eliminations / ${formatClock(modes.tdm.timeLimitSeconds)} · Kill Confirmed: ${modes['kill-confirmed'].scoreLimit} tags / ${formatClock(modes['kill-confirmed'].timeLimitSeconds)}`);
    const on = (id, action) => {
      const element = this.$(id), callback = () => handlers[action]?.();
      element?.addEventListener('click', callback);
      this.disposers.push(() => element?.removeEventListener('click', callback));
    };
    for (const [id, action] of Object.entries({
      'play-offline': 'setup', 'intro-play': 'setup', 'start-match': 'start',
      'setup-close': 'leave', 'retry-match-assets': 'retry', 'pause-match': 'pause',
      'toggle-match-sound': 'toggleSound', 'resume-match': 'resume', 'restart-match': 'restart', 'leave-match': 'leave',
      'play-again': 'restart', 'change-match': 'setup', 'return-explorer': 'leave',
    })) on(id, action);
    const trap = event => {
      if (event.key !== 'Tab' || this.$('match-menu').classList.contains('hidden')) return;
      const focusable = [...this.$('match-menu').querySelectorAll('button, select, [tabindex="0"]')]
        .filter(element => !element.disabled && !element.closest('.hidden'));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !focusable.includes(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !focusable.includes(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    };
    this.$('match-menu').addEventListener('keydown', trap);
    this.disposers.push(() => this.$('match-menu').removeEventListener('keydown', trap));
  }
  settings() {
    return {mode: this.$('match-mode').value, difficulty: this.$('match-difficulty').value,
      teamSize: Number(this.$('match-size').value), duration: GAMEPLAY_TUNING.modes[this.$('match-mode').value].timeLimitSeconds};
  }
  text(id, text) { const element = this.$(id); if (element && element.textContent !== String(text)) element.textContent = String(text); }
  visible(id, visible) { this.$(id)?.classList.toggle('hidden', !visible); }
  renderFlow(flow) {
    const isMatch = flow.active || flow.phase === 'ended';
    this.$('app').dataset.match = isMatch ? flow.phase : 'off';
    this.visible('match-menu', flow.modal);
    this.visible('match-setup', flow.phase === 'setup');
    this.visible('match-pause', flow.phase === 'paused');
    this.visible('match-result', flow.phase === 'ended');
    this.visible('match-hud', isMatch);
    this.visible('match-death', flow.phase === 'dead');
    this.visible('match-touch', flow.acceptsInput);
    this.visible('pause-match', flow.simulating);
    this.visible('play-offline', !isMatch);
    const failed = Object.values(flow.assets).some(value => value === 'error');
    this.$('start-match').disabled = !flow.ready;
    this.visible('retry-match-assets', failed);
    this.text('match-readiness', failed ? 'An arena asset failed to load. Retry below; exploration remains available.'
      : flow.ready ? 'Arena ready. Matches run locally after loading.' : 'Preparing the map and collision before you can play…');
    this.text('pause-reason', flow.reason || 'The match clock is paused');
    if (flow.phase !== this.previousPhase) {
      const focusId = {setup: flow.ready ? 'start-match' : 'match-mode', paused: 'resume-match', ended: 'play-again'}[flow.phase];
      if (focusId) this.$(focusId)?.focus({preventScroll: true});
      if (this.previousPhase && flow.phase === 'explore') this.$('play-offline')?.focus({preventScroll: true});
      this.previousPhase = flow.phase;
    }
  }
  render(snapshot = {}) {
    const {player = {}, score = [0, 0], mode = 'tdm', remaining = 300, scoreLimit = 40,
      movement = {}, weapon = {}, respawn = 0, killFeed = []} = snapshot;
    this.text('match-mode-label', modeLabel(mode));
    this.text('score-sun', score[0] ?? 0); this.text('score-ember', score[1] ?? 0);
    this.text('match-timer', formatClock(remaining)); this.text('score-target', `FIRST TO ${scoreLimit}`);
    const health = Math.max(0, Math.ceil(player.health ?? 100));
    this.text('player-health', health); this.$('health-fill').style.width = `${Math.min(100, health)}%`;
    this.$('health-track').setAttribute('aria-valuenow', String(health));
    this.text('match-ammo', weapon.reloading ? '··' : weapon.ammo ?? 30);
    this.text('match-reserve', `/ ${weapon.reserve === Infinity ? '∞' : weapon.reserve ?? '∞'}`);
    this.text('weapon-status', weapon.reloading ? 'RELOADING' : movement.sliding ? 'SLIDING' : movement.sprinting ? 'SPRINTING' : movement.crouched ? 'CROUCHED' : 'CARBINE');
    this.text('match-kd', `${player.kills ?? 0} K / ${player.deaths ?? 0} D`);
    this.text('match-objective', mode === 'kc' || mode === 'kill-confirmed' ? 'Gold tags confirm · blue tags deny' : 'Eliminate the orange team');
    this.text('respawn-countdown', `Returning in ${Math.max(0, respawn).toFixed(1)}s`);
    this.text('kill-feed', killFeed.slice(-3).join('\n'));
    this.$('match-crosshair').style.setProperty('--spread', `${Math.min(14, Math.max(0, (movement.spreadMultiplier ?? 1) - 1) * 3)}px`);
    this.$('match-crosshair').classList.toggle('ads', (movement.adsFraction ?? 0) > .8);
    this.visible('match-crosshair', player.alive !== false);
    this.$('app').classList.toggle('low-health', health > 0 && health < 35);
  }
  showResult(snapshot, winner) {
    this.text('result-title', resultTitle(winner, snapshot.player?.team ?? 'sun'));
    this.text('result-mode', modeLabel(snapshot.mode));
    this.text('result-score', `${snapshot.score?.[0] ?? 0} : ${snapshot.score?.[1] ?? 0}`);
    this.text('result-stats', `${snapshot.player?.kills ?? 0} eliminations · ${snapshot.player?.deaths ?? 0} deaths · ${snapshot.player?.confirms ?? 0} confirmations`);
  }
  announce(message) { this.text('match-announcement', message); }
  dispose() { this.disposers.forEach(dispose => dispose()); }
}
