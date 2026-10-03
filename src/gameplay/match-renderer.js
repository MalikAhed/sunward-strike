import * as THREE from 'three';

const point = value => Array.isArray(value) ? value : [value?.x ?? 0, value?.y ?? 0, value?.z ?? 0];

// Original low-poly training silhouettes. Presentation never decides hits,
// visibility, damage, tag pickup, navigation, or scoring.
export class MatchRenderer {
  constructor(scene) {
    this.root = new THREE.Group(); this.root.name = 'OFFLINE_MATCH_ACTORS'; scene.add(this.root);
    this.actors = new Map(); this.tags = new Map(); this.effects = [];
    this.materials = {
      ally: new THREE.MeshStandardMaterial({color: 0x32bfc1, roughness: .82, flatShading: true}),
      enemy: new THREE.MeshStandardMaterial({color: 0xed7440, roughness: .82, flatShading: true}),
      dark: new THREE.MeshStandardMaterial({color: 0x263b4b, roughness: .85}),
      cream: new THREE.MeshStandardMaterial({color: 0xf8edd8, roughness: .9}),
      tagConfirm: new THREE.MeshStandardMaterial({color: 0xffce49, emissive: 0x9d5210, emissiveIntensity: .4, roughness: .5}),
      tagDeny: new THREE.MeshStandardMaterial({color: 0x5bddff, emissive: 0x147b8d, emissiveIntensity: .35, roughness: .5}),
    };
    this.geometries = {
      body: new THREE.CapsuleGeometry(.27, .55, 3, 7), head: new THREE.IcosahedronGeometry(.22, 1),
      limb: new THREE.CapsuleGeometry(.1, .35, 2, 5), gun: new THREE.BoxGeometry(.13, .17, .56),
      vest: new THREE.BoxGeometry(.42, .43, .13), tag: new THREE.BoxGeometry(.23, .34, .045),
      ring: new THREE.TorusGeometry(.31, .025, 4, 14),
    };
    this.time = 0; this.root.visible = false;
  }
  mesh(geometry, material) {
    const mesh = new THREE.Mesh(this.geometries[geometry], this.materials[material]);
    mesh.castShadow = true; mesh.receiveShadow = true;
    return mesh;
  }
  createActor(actor) {
    const group = new THREE.Group(), body = new THREE.Group(), team = actor.team === 0 ? 'ally' : 'enemy';
    const torso = this.mesh('body', team); torso.position.y = .99;
    const vest = this.mesh('vest', 'dark'); vest.position.set(0, 1.02, -.235);
    const head = this.mesh('head', 'cream'); head.position.y = 1.56;
    const helmet = this.mesh('head', team); helmet.scale.set(1.06, .6, 1.07); helmet.position.y = 1.69;
    const armL = this.mesh('limb', team), armR = this.mesh('limb', team);
    armL.position.set(-.3, 1.08, -.15); armR.position.set(.3, 1.08, -.15);
    armL.rotation.x = armR.rotation.x = -Math.PI / 2.9;
    const gun = this.mesh('gun', 'dark'); gun.position.set(.13, 1.02, -.47);
    body.add(torso, vest, head, helmet, armL, armR, gun);
    const legL = this.mesh('limb', 'dark'), legR = this.mesh('limb', 'dark');
    legL.position.set(-.14, .3, 0); legR.position.set(.14, .3, 0);
    group.add(body, legL, legR);
    if (actor.team === 0) {
      const ring = this.mesh('ring', 'ally'); ring.position.y = 2.02; ring.rotation.x = Math.PI / 2; group.add(ring);
    }
    group.name = `actor:${actor.id}`; this.root.add(group);
    const view = {group, body, legL, legR, lastPosition: new THREE.Vector3(...point(actor.position)), moving: 0};
    this.actors.set(actor.id, view); return view;
  }
  update(snapshot, dt) {
    this.time += dt;
    this.root.visible = Boolean(snapshot);
    if (!snapshot) return;
    const live = new Set();
    for (const actor of snapshot.actors ?? []) {
      if (actor.id === 'player') continue;
      live.add(actor.id);
      const view = this.actors.get(actor.id) ?? this.createActor(actor);
      view.group.visible = actor.alive !== false;
      const p = point(actor.position); view.group.position.fromArray(p);
      const distance = view.lastPosition.distanceTo(view.group.position);
      view.moving = Math.min(1, dt > 0 ? distance / dt / 3 : 0);
      view.group.rotation.y = actor.yaw ?? 0;
      // Scale only the silhouette when the shared motor changes capsule height.
      view.body.scale.y = Math.max(.48, (actor.height ?? 1.8) / 1.8);
      const stride = Math.sin(this.time * 11 + p[0]) * .45 * view.moving;
      view.legL.rotation.x = stride; view.legR.rotation.x = -stride;
      view.lastPosition.copy(view.group.position);
    }
    for (const [id, view] of this.actors) if (!live.has(id)) { this.root.remove(view.group); this.actors.delete(id); }
    const tagIds = new Set();
    for (const tag of snapshot.tags ?? []) {
      if (tag.resolved) continue;
      tagIds.add(tag.id);
      let view = this.tags.get(tag.id);
      if (!view) {
        view = new THREE.Group();
        const material = tag.victimTeam === 0 ? 'tagDeny' : 'tagConfirm';
        const front = this.mesh('tag', material), back = this.mesh('tag', material);
        front.rotation.z = .18; back.position.set(.12, -.055, .035); back.rotation.z = -.18;
        const ring = this.mesh('ring', material); ring.rotation.x = Math.PI / 2; ring.position.y = -.37;
        view.add(front, back, ring); this.tags.set(tag.id, view); this.root.add(view);
      }
      const p = point(tag.position); view.position.set(p[0], p[1] + .55 + Math.sin(this.time * 3) * .045, p[2]);
      view.rotation.y = this.time * 1.4;
    }
    for (const [id, view] of this.tags) if (!tagIds.has(id)) { this.root.remove(view); this.tags.delete(id); }
    for (let i = this.effects.length - 1; i >= 0; i--) {
      const effect = this.effects[i]; effect.life -= dt;
      if (effect.life <= 0) { this.root.remove(effect.mesh); effect.mesh.geometry.dispose(); effect.mesh.material.dispose(); this.effects.splice(i, 1); }
    }
  }
  shot(event) {
    if (this.effects.length >= 36 || !event.origin) return;
    const origin = new THREE.Vector3(...point(event.origin));
    const end = event.endPoint ? new THREE.Vector3(...point(event.endPoint))
      : origin.clone().addScaledVector(new THREE.Vector3(...point(event.direction)), 70);
    // Start a little in front of the shooter's eye so the line is never a full
    // screen slash from inside the near plane.
    const forward = end.clone().sub(origin).normalize(); origin.addScaledVector(forward, .45);
    const geometry = new THREE.BufferGeometry().setFromPoints([origin, end]);
    const material = new THREE.LineBasicMaterial({color: event.actorId === 'player' ? 0xffefba : 0xffbd78, transparent: true, opacity: .72});
    const mesh = new THREE.Line(geometry, material); mesh.frustumCulled = false;
    this.root.add(mesh); this.effects.push({mesh, life: .055});
  }
  clear() {
    for (const view of this.actors.values()) this.root.remove(view.group);
    for (const view of this.tags.values()) this.root.remove(view);
    for (const effect of this.effects) { this.root.remove(effect.mesh); effect.mesh.geometry.dispose(); effect.mesh.material.dispose(); }
    this.actors.clear(); this.tags.clear(); this.effects.length = 0; this.root.visible = false;
  }
  dispose() {
    this.clear(); this.root.removeFromParent();
    Object.values(this.geometries).forEach(geometry => geometry.dispose());
    Object.values(this.materials).forEach(material => material.dispose());
  }
}
