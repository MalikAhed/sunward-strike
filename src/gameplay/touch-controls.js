// DOM bindings only. All authoritative held/edge state remains in GameInput.
// A second finger can never release an action held by the first finger.
export function bindTouchActions(root, input, {enabled = () => true, onAction = () => {}} = {}) {
  const holders = new Map(), keyboardHolders = new Set(), cleanups = [];
  const buttons = [...root.querySelectorAll('[data-action]')];
  const release = (button, pointerId) => {
    const action = button.dataset.action, ids = holders.get(action);
    if (!ids?.delete(pointerId)) return;
    if (!ids.size) { input.release(action); holders.delete(action); }
    button.classList.remove('held');
  };
  for (const button of buttons) {
    const down = event => {
      if (!enabled()) return;
      event.preventDefault();
      const action = button.dataset.action;
      let ids = holders.get(action);
      if (!ids) { ids = new Set(); holders.set(action, ids); }
      if (ids.has(event.pointerId)) return;
      if (!ids.size) input.press(action);
      ids.add(event.pointerId); button.classList.add('held');
      try { button.setPointerCapture?.(event.pointerId); } catch { /* detached pointer */ }
      onAction(action);
    };
    const up = event => release(button, event.pointerId);
    const keyDown = event => {
      if (!enabled() || !['Enter', ' '].includes(event.key)) return;
      event.preventDefault(); keyboardHolders.add(button.dataset.action);
      input.press(button.dataset.action, `button:${button.dataset.action}`); button.classList.add('held');
    };
    const keyUp = event => {
      if (!['Enter', ' '].includes(event.key)) return;
      event.preventDefault(); keyboardHolders.delete(button.dataset.action);
      input.release(button.dataset.action, `button:${button.dataset.action}`); button.classList.remove('held');
    };
    const blur = () => {keyboardHolders.delete(button.dataset.action);input.release(button.dataset.action, `button:${button.dataset.action}`);};
    button.addEventListener('keydown', keyDown);button.addEventListener('keyup', keyUp);button.addEventListener('blur', blur);
    button.addEventListener('pointerdown', down);
    for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) button.addEventListener(type, up);
    cleanups.push(() => {
      button.removeEventListener('keydown', keyDown);button.removeEventListener('keyup', keyUp);button.removeEventListener('blur', blur);
      button.removeEventListener('pointerdown', down);
      for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) button.removeEventListener(type, up);
    });
  }
  function clear() {
    for (const action of holders.keys()) input.release(action);
    for (const action of keyboardHolders) input.release(action, `button:${action}`);
    keyboardHolders.clear(); holders.clear(); buttons.forEach(button => button.classList.remove('held'));
  }
  return {clear, dispose() { clear(); cleanups.forEach(cleanup => cleanup()); }};
}
