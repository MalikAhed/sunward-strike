import {Vector3} from 'three';
import {Capsule} from 'three/addons/math/Capsule.js';
import {WalkController} from '../physics.js';
import {CapsuleContacts} from './capsule-contacts.js';

// Original SUNWARD tuning, inspired by a forward-sprint arena shooter. These
// are not measured Call of Duty values. The legacy explorer motor is untouched.
export const MOVEMENT_CONFIG = Object.freeze({
  version: 'sunward-arena-movement-1',
  fixedStep: 1 / 120,
  maxFrameTime: 0.1,
  collisionSubsteps: 5,
  radius: 0.35,
  standHeight: 1.8,
  crouchHeight: 1.1,
  slideHeight: 1.0,
  eyeFromTop: 0.16,
  walkSpeed: 4.6,
  sprintSpeed: 7.6,
  crouchSpeed: 2.5,
  groundAcceleration: 65,
  groundDeceleration: 80,
  airAcceleration: 6,
  gravity: 19,
  jumpSpeed: 5.5,
  jumpBuffer: 0.1,
  sprintForwardThreshold: 0.5,
  slideEntrySpeed: 6,
  slideStartSpeed: 10,
  slideEndSpeed: 4.6,
  slideDuration: 0.65,
  slideCommitment: 0.12,
  slideRecovery: 0.45,
  slideSteerRate: 0.8,
  adsSeconds: 0.18,
  adsMoveScale: 0.65,
  slideAdsTimeScale: 1.35,
  sprintToFire: 0.12,
});

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const finite = (x, fallback = 0) => Number.isFinite(x) ? x : fallback;
const approach = (x, target, distance) => x + clamp(target - x, -distance, distance);
const EPSILON = 1e-9;

function movementConfig(options) {
  const config = {...MOVEMENT_CONFIG, ...options};
  // The route-certified capsule dimensions and safe collision cadence are not
  // weapon/loadout settings. Invalid tuning must not silently break the map.
  for (const key of Object.keys(MOVEMENT_CONFIG)) {
    if (key === 'version') continue;
    if (!Number.isFinite(config[key]) || config[key] <= 0) {
      throw new RangeError(`Movement ${key} must be finite and positive`);
    }
  }
  if (config.radius !== 0.35 || config.standHeight !== 1.8) {
    throw new RangeError('The accepted map requires a 0.35 m radius / 1.8 m standing capsule');
  }
  if (config.fixedStep > 1 / 60 || config.maxFrameTime > 0.25 ||
      !Number.isInteger(config.collisionSubsteps) || config.collisionSubsteps < 5 ||
      config.crouchHeight < 2 * config.radius || config.slideHeight < 2 * config.radius ||
      config.slideHeight > config.crouchHeight || config.crouchHeight >= config.standHeight ||
      config.slideCommitment >= config.slideDuration || config.slideEndSpeed > config.slideStartSpeed ||
      config.sprintSpeed < config.walkSpeed || config.slideStartSpeed < config.sprintSpeed ||
      config.sprintForwardThreshold > 1 || config.adsMoveScale > 1 ||
      config.eyeFromTop >= config.slideHeight) {
    throw new RangeError('Invalid movement geometry, cadence, speed, or stance tuning');
  }
  return Object.freeze(config);
}

/**
 * Shared deterministic human/bot motor. x is local right and z is local forward;
 * yaw follows Three's YXZ camera convention. jump/slide are rising-edge actions.
 * update accepts render deltas, internally simulates 120 Hz, and discards time
 * above maxFrameTime rather than catching up after a background-tab pause.
 *
 * The collision body is the accepted WalkController capsule. _moveCapsule keeps
 * its five-substep ground reset, wall/floor support probe, signed slope drop,
 * recent support age and nonascending-only snap. The finite-triangle contact
 * narrow phase fixes side-edge penetration; no explorer source is changed.
 */
export class PlayerController extends WalkController {
  constructor(tree = null, options = {}) {
    super(tree);
    this.config = movementConfig(options);
    this.time = 0;
    this.alive = true;
    this.bodyHeight = this.config.standHeight;
    this.yaw = 0;
    this.sprinting = false;
    this.sliding = false;
    this.crouched = false;
    this.adsFraction = 0;
    this.sprintEndedAt = -Infinity;
    this.weaponReadyAt = 0;
    this.slideReadyAt = 0;
    this.slideStartedAt = -Infinity;
    this.lastSlideEnd = null;
    this.droppedTime = 0;
    this._accumulator = 0;
    this._jumpQueuedUntil = -Infinity;
    this._slideQueued = false;
    this._previousJump = false;
    this._previousSlide = false;
    this._airSpeedLimit = this.config.walkSpeed;
    this._slideDirection = new Vector3(0, 0, -1);
    this._groundIntent = new Vector3();
    this._wish = new Vector3();
    this._clearance = new Capsule(new Vector3(), new Vector3(), this.config.radius);
    this._contacts = new CapsuleContacts();
    this._jumpedThisTick = false;
    this._blockedByWall = false;
    this._lipContact = false;
    this._airborneJump = false;
  }

  spawn(cameraPosition, {yaw = 0} = {}) {
    // super.spawn is deliberately unchanged: input is standing camera position,
    // feet = eye - 1.64, bottom centre = feet + .35, top centre = feet + 1.45.
    super.spawn(cameraPosition);
    this.alive = true;
    this.yaw = finite(yaw);
    this.bodyHeight = this.config.standHeight;
    this.sprinting = false;
    this.sliding = false;
    this.crouched = false;
    this.adsFraction = 0;
    this.sprintEndedAt = -Infinity;
    this.weaponReadyAt = this.time;
    this.slideReadyAt = this.time;
    this.slideStartedAt = -Infinity;
    this.lastSlideEnd = null;
    this._airSpeedLimit = this.config.walkSpeed;
    this._groundIntent.set(0, 0, 0);
    this._lipContact = false;
    this._airborneJump = false;
    this.resetInput();
    return this;
  }

  resetInput() {
    this._accumulator = 0;
    this._jumpQueuedUntil = -Infinity;
    this._slideQueued = false;
    this._previousJump = false;
    this._previousSlide = false;
    return this;
  }

  setAlive(alive) {
    alive = Boolean(alive);
    if (alive === this.alive) return this;
    this.alive = alive;
    this.resetInput();
    this.velocity.set(0, 0, 0);
    this._groundIntent.set(0, 0, 0);
    this.sprinting = false;
    this.sliding = false;
    this.adsFraction = 0;
    this.slideReadyAt = this.time + this.config.slideRecovery;
    return this;
  }

  get horizontalSpeed() { return Math.hypot(this.velocity.x, this.velocity.z); }
  get eyeHeight() { return this.bodyHeight - this.config.eyeFromTop; }
  get canFire() { return this.alive && !this.sprinting && this.time + EPSILON >= this.weaponReadyAt; }
  get movementMode() {
    if (!this.alive) return 'dead';
    if (this.sliding) return 'slide';
    if (!this.onFloor) return this.velocity.y > 0 ? 'jump' : 'fall';
    if (this.crouched) return 'crouch';
    if (this.sprinting) return 'sprint';
    return this.horizontalSpeed > 0.05 ? 'walk' : 'idle';
  }

  feetPosition(target = new Vector3()) {
    return target.copy(this.collider.start).addScaledVector(this.floorRay.direction, this.collider.radius);
  }

  cameraPosition(target = new Vector3()) {
    return target.copy(this.collider.start).add(new Vector3(0, this.eyeHeight - this.collider.radius, 0));
  }

  canStand() { return this._canSetHeight(this.config.standHeight); }

  snapshot() {
    return {
      time: this.time,
      alive: this.alive,
      movementMode: this.movementMode,
      sprinting: this.sprinting,
      sliding: this.sliding,
      crouched: this.crouched,
      onFloor: this.onFloor,
      adsFraction: this.adsFraction,
      horizontalSpeed: this.horizontalSpeed,
      bodyHeight: this.bodyHeight,
      height: this.bodyHeight,
      eyeHeight: this.eyeHeight,
      sprintEndedAt: this.sprintEndedAt,
      sprintBlockRemaining: Math.max(0, this.weaponReadyAt - this.time),
      slideRecoveryRemaining: Math.max(0, this.slideReadyAt - this.time),
      slideElapsed: this.sliding ? this.time - this.slideStartedAt : 0,
      lastSlideEnd: this.lastSlideEnd,
      canFire: this.canFire,
      spreadMultiplier: this.sliding ? 1.7 : !this.onFloor ? 1.9 : this.crouched ? 0.85 : this.horizontalSpeed > 0.2 ? 1.25 : 1,
      feet: this.feetPosition().toArray(),
      velocity: this.velocity.toArray(),
      yaw: this.yaw,
    };
  }

  update(dt, command = {}) {
    if (!Number.isFinite(dt) || dt < 0) throw new RangeError('Movement dt must be finite and nonnegative');
    if (command.alive !== undefined) this.setAlive(command.alive);
    if (!this.alive || !this.tree) {
      this.velocity.set(0, 0, 0);
      this.resetInput();
      return this;
    }
    this.yaw = finite(command.yaw, this.yaw);
    const jump = Boolean(command.jump);
    const slide = Boolean(command.slide);
    if (jump && !this._previousJump) {
      this._jumpQueuedUntil = Math.max(this.time + this.config.jumpBuffer,
        this.sliding ? this.slideStartedAt + this.config.slideCommitment + this.config.fixedStep : -Infinity);
    }
    if (slide && !this._previousSlide) this._slideQueued = true;
    this._previousJump = jump;
    this._previousSlide = slide;
    const acceptedTime = Math.min(dt, this.config.maxFrameTime);
    this.droppedTime += dt - acceptedTime;
    this._accumulator += acceptedTime;
    const step = this.config.fixedStep;
    while (this._accumulator + EPSILON >= step) {
      this._step(step, command);
      this._accumulator = Math.max(0, this._accumulator - step);
      this.time += step;
    }
    return this;
  }

  _canSetHeight(height) {
    if (height <= this.bodyHeight + EPSILON || !this.tree) return true;
    // Check the entire added capsule volume, not one ceiling ray. The extension
    // begins at the current head sphere, so ordinary floor contact cannot hide
    // a ceiling in the octree's combined resolution normal.
    this._clearance.start.copy(this.collider.end);
    this._clearance.end.copy(this.collider.start);
    this._clearance.end.y += height - 2 * this.collider.radius;
    const hit = this._contacts.intersect(this.tree, this._clearance);
    return !hit || hit.depth <= 0.001;
  }

  _setHeight(height) {
    if (!this._canSetHeight(height)) return false;
    this.collider.end.copy(this.collider.start);
    this.collider.end.y += height - 2 * this.collider.radius;
    this.bodyHeight = height;
    this.crouched = height < this.config.standHeight - EPSILON;
    return true;
  }

  _setSprint(next) {
    if (this.sprinting && !next) {
      this.sprintEndedAt = this.time;
      this.weaponReadyAt = this.time + this.config.sprintToFire;
    }
    this.sprinting = next;
  }

  _endSlide(reason) {
    if (!this.sliding) return;
    this.sliding = false;
    this.slideReadyAt = this.time + this.config.slideRecovery;
    this.lastSlideEnd = reason;
    this._limitHorizontal(this.config.sprintSpeed);
    this._groundIntent.set(this.velocity.x, 0, this.velocity.z);
  }

  _limitHorizontal(speed) {
    const actual = this.horizontalSpeed;
    if (actual > speed) {
      this.velocity.x *= speed / actual;
      this.velocity.z *= speed / actual;
    }
  }

  _step(dt, command) {
    const c = this.config;
    let x = clamp(finite(command.x), -1, 1), z = clamp(finite(command.z), -1, 1);
    const magnitude = Math.hypot(x, z);
    if (magnitude > 1) { x /= magnitude; z /= magnitude; }
    const inputLength = Math.min(1, magnitude);
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    this._wish.set(cos * x - sin * z, 0, -sin * x - cos * z);
    const forward = inputLength > 0 && z / inputLength >= c.sprintForwardThreshold;
    const ads = Boolean(command.ads) && !command.reloading;
    const wasOnFloor = this.onFloor;
    const priorGroundAge = this.groundAge;
    // A rounded capsule may briefly bear on a raised step lip whose contact
    // normal is too steep to be a floor. Preserve desired ground drive while
    // that actual upward lip contact persists, without inventing ground support
    // in open air or carrying it into an explicit jump.
    const supportedDrive = this.onFloor || (this._lipContact && !this._airborneJump);
    const jumpQueued = this._jumpQueuedUntil + EPSILON >= this.time;
    this._jumpedThisTick = false;
    this._blockedByWall = false;
    this._lipContact = false;

    if (this.sliding) {
      const age = this.time - this.slideStartedAt;
      if (!this.onFloor) this._endSlide('airborne');
      else if (age + EPSILON >= c.slideDuration) this._endSlide('duration');
      else if (age + EPSILON >= c.slideCommitment && (jumpQueued || this._slideQueued || command.crouch)) this._endSlide(jumpQueued ? 'jump' : 'cancel');
    } else if (this._slideQueued && !jumpQueued && this.onFloor && this.sprinting &&
               this.horizontalSpeed >= c.slideEntrySpeed && this.time + EPSILON >= this.slideReadyAt) {
      this.sliding = true;
      this.slideStartedAt = this.time;
      this.lastSlideEnd = null;
      this._slideDirection.set(this.velocity.x, 0, this.velocity.z).normalize();
      this._setHeight(c.slideHeight);
      this._setSprint(false);
    }
    this._slideQueued = false;

    if (!this.sliding) this._setHeight(command.crouch ? c.crouchHeight : c.standHeight);
    const wantsSprint = Boolean(command.sprint) && forward && inputLength > 0.1 &&
      !ads && !command.fire && !command.reload && !command.reloading &&
      !this.sliding && !this.crouched && supportedDrive;
    this._setSprint(wantsSprint);
    const adsSeconds = c.adsSeconds * (this.sliding ? c.slideAdsTimeScale : 1);
    this.adsFraction = approach(this.adsFraction, ads ? 1 : 0, dt / adsSeconds);

    let jump = jumpQueued && this.onFloor && !this.sliding;
    if (jump && this.crouched) jump = this._setHeight(c.standHeight);
    if (jump) {
      this._jumpQueuedUntil = -Infinity;
      this._airborneJump = true;
      this._airSpeedLimit = Math.min(c.sprintSpeed, Math.max(c.walkSpeed, this.horizontalSpeed));
      this._limitHorizontal(this._airSpeedLimit);
      this._setSprint(false);
    }

    if (this.sliding) {
      if (inputLength > 0.1) {
        const current = Math.atan2(this._slideDirection.x, this._slideDirection.z);
        const desired = Math.atan2(this._wish.x, this._wish.z);
        const difference = Math.atan2(Math.sin(desired - current), Math.cos(desired - current));
        const angle = current + clamp(difference, -c.slideSteerRate * dt, c.slideSteerRate * dt);
        this._slideDirection.set(Math.sin(angle), 0, Math.cos(angle));
      }
      const progress = clamp((this.time - this.slideStartedAt) / c.slideDuration, 0, 1);
      const speed = c.slideStartSpeed + (c.slideEndSpeed - c.slideStartSpeed) * progress;
      this.velocity.x = this._slideDirection.x * speed;
      this.velocity.z = this._slideDirection.z * speed;
    } else {
      const grounded = supportedDrive && !jump;
      // The explorer solver reapplies desired planar speed at each collision
      // substep. Keep a separate accelerated ground intent for the same reason:
      // feeding its collision-projected X/Z back into acceleration can strand a
      // capsule on the already-certified raised stair lips. Actual velocity
      // still governs slide entry, air momentum and weapon movement feedback.
      if (grounded) {
        this.velocity.x = this._groundIntent.x;
        this.velocity.z = this._groundIntent.z;
      }
      const speed = grounded
        ? (this.sprinting ? c.sprintSpeed : this.crouched ? c.crouchSpeed : c.walkSpeed) * (1 - this.adsFraction * (1 - c.adsMoveScale))
        : this._airSpeedLimit;
      const targetX = this._wish.x * speed, targetZ = this._wish.z * speed;
      const dx = targetX - this.velocity.x, dz = targetZ - this.velocity.z;
      const distance = Math.hypot(dx, dz);
      const acceleration = grounded ? (inputLength < 0.01 ? c.groundDeceleration : c.groundAcceleration) : c.airAcceleration;
      const fraction = distance > 0 ? Math.min(1, acceleration * dt / distance) : 0;
      this.velocity.x += dx * fraction;
      this.velocity.z += dz * fraction;
      if (!grounded) this._limitHorizontal(this._airSpeedLimit);
      else this._groundIntent.set(this.velocity.x, 0, this.velocity.z);
    }

    this._moveCapsule(dt, jump);
    // Collision projection on a steep landing can convert vertical fall speed
    // into lateral speed. It must not create an extra launch or bunny-hop boost.
    this._limitHorizontal(this.sliding ? c.slideStartSpeed : this.onFloor ? c.sprintSpeed : this._airSpeedLimit);
    if (!wasOnFloor && this.onFloor && priorGroundAge > 0.03 && !supportedDrive) this._groundIntent.set(this.velocity.x, 0, this.velocity.z);
    if (this.onFloor) this._airborneJump = false;
    if (wasOnFloor && !this.onFloor) {
      this._airSpeedLimit = Math.min(c.sprintSpeed, Math.max(c.walkSpeed, this.horizontalSpeed));
      this._limitHorizontal(this._airSpeedLimit);
      this._setSprint(false);
      if (this.sliding) this._endSlide('airborne');
    }
    if (this.sliding && this._blockedByWall) this._endSlide('blocked');
  }

  _moveCapsule(dt, jump) {
    const c = this.config;
    const horizontalX = this.velocity.x, horizontalZ = this.velocity.z;
    // Retain the accepted explorer integration/support rules, with horizontal
    // desired velocity / stance supplied above, bounded fixed-rate dt, and the
    // corrected finite-triangle narrow phase for contact geometry.
    for (let i = 0; i < c.collisionSubsteps; i++) {
      const step = dt / c.collisionSubsteps, wasOnFloor = this.onFloor;
      this.velocity.x = horizontalX;
      this.velocity.z = horizontalZ;
      if (this.onFloor) {
        this.velocity.y = 0;
        if (jump) { this.velocity.y = c.jumpSpeed; jump = false; this._jumpedThisTick = true; }
      } else this.velocity.y -= c.gravity * step;
      this.collider.translate(this.delta.copy(this.velocity).multiplyScalar(step));
      const hit = this._contacts.intersect(this.tree, this.collider);
      this.onFloor = false;
      if (hit) {
        this.onFloor = hit.normal.y > 0.45;
        const inward = hit.normal.dot(this.velocity);
        if (inward < 0) {
          if (hit.normal.y > 0.001 && hit.normal.y <= 0.45 && !this._airborneJump) this._lipContact = true;
          if (Math.abs(hit.normal.y) < 0.45 && -inward > 1) this._blockedByWall = true;
          this.velocity.addScaledVector(hit.normal, -inward);
        }
        this.collider.translate(hit.normal.multiplyScalar(hit.depth));
      }
      if (!this.onFloor && this.velocity.y <= 0.001) {
        this.floorRay.origin.copy(this.collider.start);
        const floor = this.tree.rayIntersect(this.floorRay);
        if (floor) {
          floor.triangle.getNormal(this.floorNormal);
          if (this.floorNormal.y > 0.45) {
            const drop = floor.distance - this.collider.radius / this.floorNormal.y;
            if ((wasOnFloor || this.groundAge <= 0.03) && drop >= -0.05 && drop <= 0.08) {
              this.collider.translate(this.delta.set(0, -Math.max(0, drop), 0));
              this.onFloor = true;
              this.velocity.y = 0;
            } else if (floor.distance <= this.collider.radius + 0.025) {
              this.onFloor = true;
              this.velocity.y = Math.max(0, this.velocity.y);
            }
          }
        }
      }
      this.groundAge = this.onFloor ? 0 : this.groundAge + step;
    }
  }
}
