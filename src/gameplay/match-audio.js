// Original procedural effects. No downloads, licensed samples or autoplay.
// The graph has at most 16 live sources; every ended voice disconnects itself.
export class MatchAudio {
  constructor({contextFactory = null, maxVoices = 16} = {}) {
    if(!Number.isInteger(maxVoices)||maxVoices<1||maxVoices>64)throw new RangeError('Voice limit must be an integer from 1 to 64');
    this.context = null; this.contextFactory = contextFactory; this.enabled = true;
    this.maxVoices = maxVoices; this.voices = new Set(); this.lastShot = -Infinity; this.noiseBuffer = null;
  }
  activate() {
    // Called only by explicit Play, Resume or Unmute gestures in main.js.
    if (!this.enabled) return;
    try {
      const Context = typeof window === 'undefined' ? null : window.AudioContext || window.webkitAudioContext;
      if (!this.context && !this.contextFactory && !Context) return;
      this.context ??= this.contextFactory ? this.contextFactory() : new Context();
      this.context.resume()?.catch(() => {});
    } catch { /* muted or unsupported browser */ }
  }
  setEnabled(enabled) {
    this.enabled = Boolean(enabled);
    if (!this.enabled) this.stopAll();
  }
  get available() { return Boolean(this.enabled && this.context && this.context.state === 'running'); }
  addVoice(source, nodes = []) {
    while (this.voices.size >= this.maxVoices) this.releaseVoice(this.voices.values().next().value, true);
    const voice = {source, nodes}; this.voices.add(voice);
    source.onended = () => this.releaseVoice(voice);
    return voice;
  }
  releaseVoice(voice, stop = false) {
    if (!this.voices.delete(voice)) return;
    voice.source.onended = null;
    if (stop) try { voice.source.stop(); } catch { /* already stopped */ }
    try { voice.source.disconnect(); } catch { /* already disconnected */ }
    for (const node of voice.nodes) try { node.disconnect(); } catch { /* disposed */ }
  }
  stopAll() { for (const voice of [...this.voices]) this.releaseVoice(voice, true); }
  tone(frequency, duration, volume = .05, type = 'sine', endFrequency = frequency) {
    if (!this.available) return;
    const c = this.context, oscillator = c.createOscillator(), gain = c.createGain(), now = c.currentTime;
    oscillator.type = type; oscillator.frequency.setValueAtTime(frequency, now);
    oscillator.frequency.exponentialRampToValueAtTime(Math.max(1, endFrequency), now + duration);
    gain.gain.setValueAtTime(volume, now); gain.gain.exponentialRampToValueAtTime(.001, now + duration);
    oscillator.connect(gain).connect(c.destination); this.addVoice(oscillator, [gain]);
    oscillator.start(now); oscillator.stop(now + duration);
  }
  shot(isPlayer = true) {
    if (!this.available) return;
    const c = this.context;
    if (!isPlayer && c.currentTime - this.lastShot < .075) return;
    this.lastShot = c.currentTime;
    if (!this.noiseBuffer) {
      const length = Math.floor(c.sampleRate * .085), buffer = c.createBuffer(1, length, c.sampleRate), data = buffer.getChannelData(0);
      // Fixed deterministic noise, separate from simulation RNG.
      let seed = 2463534242;
      for (let i = 0; i < length; i++) { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; data[i] = ((seed >>> 0) / 2147483648 - 1) * (1 - i / length) ** 3; }
      this.noiseBuffer = buffer;
    }
    const source = c.createBufferSource(), gain = c.createGain(), filter = c.createBiquadFilter();
    source.buffer = this.noiseBuffer; filter.type = 'lowpass'; filter.frequency.value = isPlayer ? 2500 : 950;
    gain.gain.value = isPlayer ? .115 : .026;
    source.connect(filter).connect(gain).connect(c.destination); this.addVoice(source, [filter, gain]); source.start();
    if (isPlayer) this.tone(85, .07, .055, 'triangle', 50);
  }
  hit() { this.tone(1150, .045, .025, 'sine', 1550); }
  reload(completed = false) { this.tone(completed ? 330 : 160, completed ? .11 : .06, .026, 'triangle', completed ? 540 : 110); }
  death() { this.stopAll(); this.tone(180, .4, .04, 'triangle', 45); }
  tag(confirmed = true) { this.tone(confirmed ? 880 : 560, .16, .035, 'sine', confirmed ? 1320 : 700); }
  dispose() { this.stopAll(); this.context?.close()?.catch(() => {}); this.context = null; this.noiseBuffer = null; }
}
