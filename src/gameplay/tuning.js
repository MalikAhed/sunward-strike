// Original SUNWARD gameplay values. These are tunable design choices, not
// measured/proprietary Call of Duty statistics. Movement has its own controller.
const freeze = object => {Object.values(object).forEach(value => {if(value && typeof value==='object')freeze(value);});return Object.freeze(object);};
export const GAMEPLAY_TUNING=freeze({
  version:'offline-core-kc-objective-r2',fixedStep:1/60,maxFrameDelta:.25,maxActors:16,
  actor:{health:100,radius:.35,height:1.8,eyeHeight:1.64,headHeight:1.43,regenDelay:4,regenPerSecond:35,respawnDelay:2,spawnProtection:.65,assistWindow:5},
  modes:{tdm:{scoreLimit:50,timeLimitSeconds:300},'kill-confirmed':{scoreLimit:35,timeLimitSeconds:300,tagLifetime:20,tagPickupRadius:1.25}},
  weapons:{
    carbine:{name:'SUNWARD Carbine',damageNear:34,damageFar:25,nearRange:22,farRange:40,maxRange:120,headMultiplier:1.5,rpm:660,magazine:30,reserveAmmo:120,infiniteReserve:true,reloadTactical:1.55,reloadEmpty:1.95,adsSeconds:.18,sprintToFire:.12,hipSpreadDegrees:1.6,adsSpreadDegrees:.16,movingSpread:1.4,airSpread:2,slideSpread:1.7,recoilPitchDegrees:.7,recoilYawDegrees:.22,recoilRecovery:8,maxRecoilDegrees:7},
    smg:{name:'SUNWARD Compact',damageNear:25,damageFar:18,nearRange:12,farRange:28,maxRange:90,headMultiplier:1.5,rpm:900,magazine:32,reserveAmmo:128,infiniteReserve:true,reloadTactical:1.35,reloadEmpty:1.75,adsSeconds:.14,sprintToFire:.10,hipSpreadDegrees:2.0,adsSpreadDegrees:.23,movingSpread:1.45,airSpread:2,slideSpread:1.7,recoilPitchDegrees:.5,recoilYawDegrees:.32,recoilRecovery:9,maxRecoilDegrees:8},
  },
  botObjectives:{commitRange:8.5,commitSeconds:2.5,retryDelay:2,minHealth:45,denialDistancePenalty:2},
  difficulty:{
    recruit:{reaction:[.45,.70],aimErrorDegrees:[3,5],turnDegrees:240,perceptionInterval:.15,decisionInterval:.30,sightRange:52,fovDegrees:110,burstShots:[2,4],burstPause:[.50,.95],memorySeconds:3,hearingRange:38,prediction:.05},
    regular:{reaction:[.28,.45],aimErrorDegrees:[1.5,2.8],turnDegrees:360,perceptionInterval:.10,decisionInterval:.20,sightRange:68,fovDegrees:120,burstShots:[3,6],burstPause:[.25,.55],memorySeconds:4,hearingRange:48,prediction:.10},
    veteran:{reaction:[.18,.30],aimErrorDegrees:[.7,1.6],turnDegrees:520,perceptionInterval:.08,decisionInterval:.16,sightRange:82,fovDegrees:130,burstShots:[4,8],burstPause:[.18,.38],memorySeconds:5,hearingRange:58,prediction:.16},
  },
});
export function matchSettings(input={}){
  const mode=input.mode??'tdm',difficulty=input.difficulty??'regular';
  if(!GAMEPLAY_TUNING.modes[mode])throw new RangeError('Unknown match mode: '+mode);
  if(!GAMEPLAY_TUNING.difficulty[difficulty])throw new RangeError('Unknown bot difficulty: '+difficulty);
  const friendlyBots=input.friendlyBots??2,enemyBots=input.enemyBots??3;
  for(const [name,value]of Object.entries({friendlyBots,enemyBots}))if(!Number.isInteger(value)||value<0)throw new RangeError(name+' must be a nonnegative integer');
  if(1+friendlyBots+enemyBots>GAMEPLAY_TUNING.maxActors)throw new RangeError('At most '+GAMEPLAY_TUNING.maxActors+' total actors');
  const defaults=GAMEPLAY_TUNING.modes[mode],scoreLimit=input.scoreLimit??defaults.scoreLimit,timeLimitSeconds=input.timeLimitSeconds??defaults.timeLimitSeconds;
  if(!Number.isInteger(scoreLimit)||scoreLimit<1||scoreLimit>1000)throw new RangeError('Score limit must be an integer from1 to1000');
  if(!Number.isFinite(timeLimitSeconds)||timeLimitSeconds<=0||timeLimitSeconds>3600)throw new RangeError('Time limit must be positive and at most3600 seconds');
  const weaponId=input.weaponId??'carbine';if(!GAMEPLAY_TUNING.weapons[weaponId])throw new RangeError('Unknown weapon');
  const seed=input.seed??7;if(!Number.isInteger(seed))throw new RangeError('Seed must be an integer');
  return Object.freeze({mode,difficulty,friendlyBots,enemyBots,scoreLimit,timeLimitSeconds,seed:seed>>>0,weaponId});
}
