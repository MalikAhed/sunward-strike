// Presentation lifecycle, independent of the simulation clock. No transition
// starts a match implicitly when an asset finishes loading.
export class MatchFlow {
  constructor() {
    this.phase = 'explore';
    this.resumePhase = 'playing';
    this.assets = {map: 'loading', collision: 'loading'};
    this.assetErrors = {};
    this.reason = '';
    this.settings = null;
    this.result = null;
    this.runId = 0;
  }
  get ready() { return Object.values(this.assets).every(value => value === 'ready'); }
  get active() { return ['playing', 'dead', 'paused'].includes(this.phase); }
  get simulating() { return this.phase === 'playing' || this.phase === 'dead'; }
  get acceptsInput() { return this.phase === 'playing'; }
  get modal() { return ['setup', 'paused', 'ended'].includes(this.phase); }
  setAsset(name, status, error = '') {
    if (!(name in this.assets) || !['loading', 'ready', 'error'].includes(status)) return false;
    this.assets[name] = status;
    if (error) this.assetErrors[name] = String(error); else delete this.assetErrors[name];
    if (status !== 'ready' && this.simulating) this.pause('An arena asset became unavailable');
    return true;
  }
  openSetup() {
    if (this.active) return this.pause('Match menu');
    this.phase = 'setup'; this.reason = ''; this.result = null;
    return true;
  }
  start(settings = {}) {
    if (!this.ready || !['setup', 'ended', 'paused'].includes(this.phase)) return false;
    this.settings = Object.freeze({...settings});
    this.phase = 'playing'; this.resumePhase = 'playing'; this.reason = ''; this.result = null; this.runId++;
    return true;
  }
  pause(reason = 'Match paused') {
    if (!this.simulating) return false;
    this.resumePhase = this.phase; this.phase = 'paused'; this.reason = reason;
    return true;
  }
  resume() {
    if (this.phase !== 'paused' || !this.ready) return false;
    this.phase = this.resumePhase; this.reason = '';
    return true;
  }
  died(runId = this.runId) {
    if (runId !== this.runId || !this.active) return false;
    if (this.phase === 'paused') this.resumePhase = 'dead'; else this.phase = 'dead';
    return true;
  }
  respawned(runId = this.runId) {
    if (runId !== this.runId || !this.active) return false;
    if (this.phase === 'paused') this.resumePhase = 'playing'; else this.phase = 'playing';
    return true;
  }
  finish(result, runId = this.runId) {
    if (runId !== this.runId || !this.active) return false;
    this.result = result; this.phase = 'ended'; this.reason = '';
    return true;
  }
  leave() {
    if (this.phase === 'explore') return false;
    this.phase = 'explore'; this.result = null; this.reason = ''; this.runId++;
    return true;
  }
}

export function formatClock(seconds) {
  const whole = Math.max(0, Math.ceil(Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
}

export function resultTitle(winner, playerTeam = 'sun') {
  return winner == null || winner === 'draw' ? 'DRAW' : winner === playerTeam ? 'VICTORY' : 'DEFEAT';
}
