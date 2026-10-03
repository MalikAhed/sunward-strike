const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, value));
const finite = value => Number.isFinite(value) ? value : 0;
const ACTIONS = new Set(['forward', 'backward', 'left', 'right', 'sprint', 'jump', 'slide', 'crouch', 'ads', 'fire', 'reload']);
const EDGE_ACTIONS = new Set(['jump', 'slide', 'reload']);

export const INPUT_DEFAULTS = Object.freeze({sensitivity: 0.0023, adsSensitivityScale: 0.6, invertY: false, pitchLimit: 1.5});
export const KEY_ACTIONS = Object.freeze({
  KeyW: 'forward', KeyS: 'backward', KeyA: 'left', KeyD: 'right',
  ShiftLeft: 'sprint', ShiftRight: 'sprint', Space: 'jump', KeyC: 'slide',
  KeyX: 'crouch', ControlLeft: 'crouch', ControlRight: 'crouch', KeyR: 'reload',
});

/**
 * DOM-independent intent buffer. The UI owns pointer-lock/focus/menu policy and
 * calls setEnabled(false) / clear() on blur, escape, pause, death and mode exit.
 * No event listeners are installed implicitly, so it is also usable by touch
 * controls and deterministic input replay. Repeated keydown never repeats edges.
 */
export class GameInput {
  constructor(options = {}) {
    this.options = {...INPUT_DEFAULTS, ...options};
    const {sensitivity, adsSensitivityScale, pitchLimit} = this.options;
    if (!Number.isFinite(sensitivity) || sensitivity <= 0 ||
        !Number.isFinite(adsSensitivityScale) || adsSensitivityScale <= 0 ||
        !Number.isFinite(pitchLimit) || pitchLimit <= 0 || pitchLimit >= Math.PI / 2) {
      throw new RangeError('Input sensitivity/scaling/pitch limit must be finite and valid');
    }
    this.enabled = options.enabled !== false;
    this.yaw = 0;
    this.pitch = 0;
    this._held = new Set();
    this._edges = new Set();
    this._sources = new Map();
    this._analog = {x: 0, z: 0};
    this.setLook(options.yaw || 0, options.pitch || 0);
  }

  setLook(yaw, pitch) {
    this.yaw = finite(yaw);
    this.pitch = clamp(finite(pitch), -this.options.pitchLimit, this.options.pitchLimit);
    return this;
  }

  addLookDelta(dx, dy, adsFraction = 0) {
    if (!this.enabled) return this;
    const scale = this.options.sensitivity * (1 + clamp(finite(adsFraction), 0, 1) * (this.options.adsSensitivityScale - 1));
    return this.applyLookOffset(-finite(dx) * scale, -finite(dy) * scale * (this.options.invertY ? -1 : 1));
  }

  // A weapon may apply a recoil impulse to the same aim the mouse controls.
  // This deliberately does not spring the player's manual compensation away.
  applyLookOffset(deltaYaw, deltaPitch) {
    if (!this.enabled) return this;
    return this.setLook(this.yaw + finite(deltaYaw), this.pitch + finite(deltaPitch));
  }

  press(action, source = action) {
    if (!ACTIONS.has(action)) throw new RangeError(`Unknown input action: ${action}`);
    if (!this.enabled) return false;
    let sources = this._sources.get(action);
    if (!sources) { sources = new Set(); this._sources.set(action, sources); }
    if (sources.has(source)) return false;
    sources.add(source);
    const first = !this._held.has(action);
    this._held.add(action);
    if (first && EDGE_ACTIONS.has(action)) this._edges.add(action);
    return first;
  }

  release(action, source = action) {
    if (!ACTIONS.has(action)) throw new RangeError(`Unknown input action: ${action}`);
    const sources = this._sources.get(action);
    if (!sources) return false;
    sources.delete(source);
    if (!sources.size) { this._sources.delete(action); this._held.delete(action); }
    return true;
  }

  setMove(x, z) {
    if (!this.enabled) return this;
    this._analog.x = clamp(finite(x), -1, 1);
    this._analog.z = clamp(finite(z), -1, 1);
    return this;
  }

  clear() {
    this._held.clear();
    this._edges.clear();
    this._sources.clear();
    this._analog.x = this._analog.z = 0;
    return this;
  }

  setEnabled(enabled) {
    enabled = Boolean(enabled);
    if (enabled !== this.enabled) this.clear();
    this.enabled = enabled;
    return this;
  }

  consumeCommand() {
    const has = action => this.enabled && this._held.has(action);
    let x = this.enabled ? this._analog.x + Number(has('right')) - Number(has('left')) : 0;
    let z = this.enabled ? this._analog.z + Number(has('forward')) - Number(has('backward')) : 0;
    const length = Math.hypot(x, z);
    if (length > 1) { x /= length; z /= length; }
    const command = {x, z, yaw: this.yaw, pitch: this.pitch};
    for (const action of ['sprint', 'crouch', 'ads', 'fire']) command[action] = has(action);
    for (const action of EDGE_ACTIONS) command[action] = this.enabled && this._edges.has(action);
    this._edges.clear();
    return command;
  }
}
