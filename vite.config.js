import { defineConfig } from 'vite';
import {offlineBundlePlugin} from './scripts/offline/build-offline.mjs';
import {MAP_CONFIG} from './src/map-config.js';
import {ATMOSPHERE_CONFIG} from './src/atmosphere-config.js';
const runtimeNames=[...Object.values(MAP_CONFIG.assets),'map-poster.png',ATMOSPHERE_CONFIG.cloudTexture,ATMOSPHERE_CONFIG.mountainTexture];
if(MAP_CONFIG.assets.map.endsWith('.gz'))runtimeNames.push(MAP_CONFIG.assets.map.slice(0,-3));
export default defineConfig({base:'./',plugins:[offlineBundlePlugin(runtimeNames.map(name=>`assets/${name}`))],build:{target:'es2022',assetsInlineLimit:0},server:{host:'0.0.0.0',port:5173}});
