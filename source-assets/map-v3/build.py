#!/usr/bin/env python3
"""Rebuild into a new build/ directory; source scenes are never overwritten."""
from pathlib import Path
import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--blender',default='blender');p.add_argument('--export',action='store_true');a=p.parse_args()
here=Path(__file__).resolve().parent;base=here.parent/'map/Sunward_TestSite.blend';out=here/'build/Sunward_ClassicLayout_v3_rebuilt.blend'
if out.exists():raise SystemExit('build output exists; move it aside before rebuilding')
out.parent.mkdir(parents=True,exist_ok=True)
flags=['--coral','--grass']
if (here/'source/layout/interior-dressing/interior_dressing_patch.py').exists():flags.append('--dressing')
if (here/'source/houses/native-style/native_atmosphere.py').exists():flags.append('--native-style')
subprocess.run([a.blender,'-b',str(base),'-t','2','-P',str(here/'source/integration/integrate_candidate.py'),'--','--inputs',str(here/'source'),'--output',str(out),'--version','3.0']+flags,check=True)
if a.export:subprocess.run([a.blender,'-b',str(out),'-t','2','-P',str(here/'source/integration/export_optimized.py')],check=True)
print('New editable source:',out)
