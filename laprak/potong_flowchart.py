# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Naufal Habibi
import sys, numpy as np
from PIL import Image
im = Image.open(sys.argv[1]); a = np.array(im)
alpha = a[:,:,3] > 20
line = (abs(a[:,:,0].astype(int)-10) < 40) & (abs(a[:,:,1].astype(int)-25) < 40) & (abs(a[:,:,2].astype(int)-49) < 50)
safe = [y for y in range(a.shape[0]) if not (alpha[y] & ~line[y]).any()]
targets = [int(t) for t in sys.argv[2].split(",")]
cuts, y0 = [0], 0
for t in targets:
    c = max(s for s in safe if s <= y0 + t); cuts.append(c); y0 = c
cuts.append(a.shape[0]); print(cuts)
names = "abcdefgh"
for i in range(len(cuts)-1):
    p = im.crop((0, cuts[i], im.width, cuts[i+1])); bb = p.getbbox()
    p = p.crop((0, bb[1], im.width, bb[3]))
    p.save(f"output/03{names[i]}.png"); print(names[i], p.size)
