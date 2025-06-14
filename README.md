 USD Stage QC

This repo is an early prototype of a QC tool for USD scenes. It's part of a broader set of utilities I’m building to catch sneaky issues that can break things during rendering.

Primvars Check — our starting point and one of the core checks this tool performs

The Problem:

Let’s say you have a primvar (like Cd or st) on your geometry. — in our case, it’s called 'foo'.

![image](https://github.com/user-attachments/assets/08e0ae82-2d6a-48b9-aa3e-f73bdb4932c5)

Then you fracture it, or do some heavy geometry changes. Sometimes the attribute interpolation gets updated properly — but not always.

Now imagine you also run an attribute cleanup and remove that primvar entirely.

<img width="462" alt="image" src="https://github.com/user-attachments/assets/a981b38a-2f57-4812-85a7-53c67d29f4e7" />

All good? Not quite.

![image](https://github.com/user-attachments/assets/f7a3e792-e74e-4f14-875e-abd6799f85d3)

When you bring that geometry back into LOPs, that primvar might still be there — inherited or carried over from a previous layer — but now the number of values doesn’t match the new geometry’s topology. For example:

A vertex-interpolated primvar with 100 values… but your fractured geo has 500 vertices now.
A faceVarying primvar with stale data from before the fracture.
Mismatch like this can silently break things at render time — or worse, crash it altogether.

What this tool does

This little checker helps catch those mismatches by comparing the interpolation type of each primvar to the actual element count on the geometry (points, faces, vertices) — and lets you know if something’s off.
