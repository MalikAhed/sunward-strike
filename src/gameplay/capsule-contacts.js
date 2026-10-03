import {Plane, Vector3} from 'three';
import {Capsule} from 'three/addons/math/Capsule.js';

const EPSILON = 1e-12;
const clamp01 = x => Math.max(0, Math.min(1, x));

/**
 * Finite-triangle narrow phase for the shared game motor. Three's stock
 * plane-first capsule test can choose a deep face correction when a tall
 * capsule only grazes the side edge of a sloped triangle. Against a ramp
 * underside this can push it through the floor, then back onto the ramp.
 *
 * Use the actual closest points of the capsule axis and finite triangle:
 * both endpoint/triangle pairs, all three segment/edge pairs, and an actual
 * segment/face intersection. This prevents the invalid correction at contact;
 * it does not clamp displacement, teleport a body back, or alter map geometry.
 * Broadphase, one-sided surface convention and capsule dimensions are retained.
 */
export class CapsuleContacts {
  constructor() {
    this.capsule = new Capsule();
    this.triangles = [];
    this.plane = new Plane();
    this.axis = new Vector3();
    this.edge = new Vector3();
    this.offset = new Vector3();
    this.axisPoint = new Vector3();
    this.trianglePoint = new Vector3();
    this.bestAxis = new Vector3();
    this.bestTriangle = new Vector3();
    this.correction = new Vector3();
    this.contact = {normal: new Vector3(), depth: 0};
    this.result = {normal: new Vector3(), depth: 0};
  }

  _consider(axisPoint, trianglePoint) {
    const squared = axisPoint.distanceToSquared(trianglePoint);
    if (squared < this.bestSquared) {
      this.bestSquared = squared;
      this.bestAxis.copy(axisPoint);
      this.bestTriangle.copy(trianglePoint);
    }
  }

  _segmentEdge(start, end, a, b) {
    this.axis.subVectors(end, start);
    this.edge.subVectors(b, a);
    this.offset.subVectors(start, a);
    const axisLength = this.axis.lengthSq(), edgeLength = this.edge.lengthSq();
    const edgeOffset = this.edge.dot(this.offset);
    let s = 0, t = 0;
    if (axisLength <= EPSILON) {
      t = edgeLength > EPSILON ? clamp01(edgeOffset / edgeLength) : 0;
    } else {
      const axisOffset = this.axis.dot(this.offset);
      if (edgeLength <= EPSILON) s = clamp01(-axisOffset / axisLength);
      else {
        const dot = this.axis.dot(this.edge), denominator = axisLength * edgeLength - dot * dot;
        s = denominator > EPSILON ? clamp01((dot * edgeOffset - axisOffset * edgeLength) / denominator) : 0;
        t = (dot * s + edgeOffset) / edgeLength;
        if (t < 0) { t = 0; s = clamp01(-axisOffset / axisLength); }
        else if (t > 1) { t = 1; s = clamp01((dot - axisOffset) / axisLength); }
      }
    }
    this.axisPoint.copy(start).addScaledVector(this.axis, s);
    this.trianglePoint.copy(a).addScaledVector(this.edge, t);
    this._consider(this.axisPoint, this.trianglePoint);
  }

  triangleContact(capsule, triangle) {
    triangle.getPlane(this.plane);
    const startDistance = this.plane.distanceToPoint(capsule.start);
    const endDistance = this.plane.distanceToPoint(capsule.end);
    const radius = capsule.radius;
    if ((startDistance > radius && endDistance > radius) ||
        (startDistance < 0 && endDistance < 0)) return false;

    this.bestSquared = Infinity;
    triangle.closestPointToPoint(capsule.start, this.trianglePoint);
    this._consider(capsule.start, this.trianglePoint);
    triangle.closestPointToPoint(capsule.end, this.trianglePoint);
    this._consider(capsule.end, this.trianglePoint);
    this._segmentEdge(capsule.start, capsule.end, triangle.a, triangle.b);
    this._segmentEdge(capsule.start, capsule.end, triangle.b, triangle.c);
    this._segmentEdge(capsule.start, capsule.end, triangle.c, triangle.a);

    // Test a real point on the plane, not a projected arbitrary interpolation
    // of endpoint distances with radius already subtracted.
    const denominator = startDistance - endDistance;
    if (Math.abs(denominator) > EPSILON) {
      const t = startDistance / denominator;
      if (t >= 0 && t <= 1) {
        this.axisPoint.copy(capsule.start).lerp(capsule.end, t);
        if (triangle.containsPoint(this.axisPoint)) {
          this.bestSquared = 0;
          this.bestAxis.copy(this.axisPoint);
          this.bestTriangle.copy(this.axisPoint);
        }
      }
    }
    if (this.bestSquared >= radius * radius) return false;
    const distance = Math.sqrt(this.bestSquared);
    if (distance > 1e-8) {
      this.contact.normal.subVectors(this.bestAxis, this.bestTriangle).multiplyScalar(1 / distance);
      this.contact.depth = radius - distance;
    } else {
      // A body already straddling the finite face needs actual depenetration.
      // Continuous edge contacts prevent this branch in valid side approaches.
      this.contact.normal.copy(this.plane.normal);
      this.contact.depth = radius - Math.min(startDistance, endDistance);
    }
    return this.contact;
  }

  intersect(tree, capsule) {
    if (typeof tree.getCapsuleTriangles !== 'function') return tree.capsuleIntersect(capsule);
    this.capsule.copy(capsule);
    this.triangles.length = 0;
    tree.getCapsuleTriangles(this.capsule, this.triangles);
    let collided = false;
    for (const triangle of this.triangles) {
      const contact = this.triangleContact(this.capsule, triangle);
      if (contact && contact.depth > EPSILON) {
        collided = true;
        this.capsule.translate(this.correction.copy(contact.normal).multiplyScalar(contact.depth));
      }
    }
    if (!collided) return false;
    this.result.normal.subVectors(this.capsule.start, capsule.start);
    this.result.depth = this.result.normal.length();
    if (this.result.depth <= EPSILON) return false;
    this.result.normal.multiplyScalar(1 / this.result.depth);
    return this.result;
  }
}
