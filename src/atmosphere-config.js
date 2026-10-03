// Original n5 distant sky. Angles are degrees; Three axes are Y-up.
// All positions are relative to camera translation only (never its rotation).
// Authoritative classic map geometry is outside this module.
export const ATMOSPHERE_CONFIG = Object.freeze({
  version: 'distant-painted-banks-n5',
  radius: 360,
  skyRadius: 400,
  cloudTexture: 'cream-cloud-atlas-n5.png',
  mountainTexture: 'peach-mountain-atlas-n5.png',
  textureSize: [1536,1024],
  colors: {zenith:'#3287e2', middle:'#4d9eef', horizon:'#95c6f2', nadir:'#ead0b4'},
  // Pixel-space rectangles with original alpha preserved. Coordinates use top-left origin.
  cloudRects:[[11,101,763,440],[768,105,1528,451],[15,552,768,921],[775,562,1525,914]],
  mountainRects:[[5,170,1531,463],[5,592,1531,879]],
  clouds: [
    {azimuth:0,elevation:24,width:21,sprite:0},
    {azimuth:35,elevation:17,width:24,sprite:1},
    {azimuth:76,elevation:27,width:19,sprite:2},
    {azimuth:113,elevation:20,width:23,sprite:3},
    {azimuth:151,elevation:31,width:17,sprite:0},
    {azimuth:190,elevation:20,width:26,sprite:2},
    {azimuth:232,elevation:24,width:21,sprite:1},
    {azimuth:268,elevation:19,width:24,sprite:3},
    {azimuth:309,elevation:25,width:21,sprite:0},
    {azimuth:343,elevation:39,width:14,sprite:2},
    {azimuth:94,elevation:44,width:11,sprite:1},
    {azimuth:213,elevation:43,width:13,sprite:3},
  ],
  mountains: [
    {azimuth:0,width:88,height:13,base:-2,sprite:0},
    {azimuth:60,width:87,height:11,base:-2.5,sprite:1},
    {azimuth:120,width:90,height:12,base:-2,sprite:0},
    {azimuth:180,width:86,height:11,base:-2,sprite:1},
    {azimuth:240,width:92,height:13,base:-2,sprite:0},
    {azimuth:300,width:88,height:12,base:-2,sprite:1},
  ],
  // Exact client far projection avoids sky being clipped by a map-sized far plane.
  backgroundDepth: 0.99999,
});
