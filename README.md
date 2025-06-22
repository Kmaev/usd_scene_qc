# USD Scene QC

This repo contains an early prototype of a QC tool for USD scenes, designed to help identify common issues before they cause problems at render time.

It’s part of a broader suite of **Houdini + USD utilities** I’m building to catch subtle scene issues.

## Presentation Demo:

https://vimeo.com/1093300593

## Currently Supports

- Missing reference validation  
- Attribute interpolation inconsistencies across time samples  
- Invalid or missing render settings  
- Unbound or missing cameras  
- Broken or inactive material bindings  

---

Ideal for **TDs and developers** working in **VFX or animation pipelines** who want lightweight, scriptable validation before handoff.


<img width="1047" alt="image" src="https://github.com/user-attachments/assets/41c12122-8a08-4648-bc37-55fcbfdb3e6d" />



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
Mismatch like this can silently break things at render time — or crash it altogether.


