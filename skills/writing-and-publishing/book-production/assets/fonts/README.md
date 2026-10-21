# Bundled fonts

EB Garamond, Cormorant Garamond, Lora, Source Serif 4 and Inter, all SIL Open Font License 1.1 (`OFL-*.txt`). Source: google/fonts variable fonts. Source Serif 4 is pinned at the 12pt optical size, Inter at 14.

The files here are **static** instances (Regular, Medium, SemiBold, Bold, each with Italic), cut from the variable fonts with fontTools. Chrome writes non-default instances of a variable font into a PDF as Type 3 fonts, which IngramSpark rejects and some print shops' RIPs render poorly. Static files avoid that.

To add another family (example: Lora):

```python
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
# download Lora[wght].ttf and Lora-Italic[wght].ttf from github.com/google/fonts/tree/main/ofl/lora first
for src, ital in (("Lora[wght].ttf", False), ("Lora-Italic[wght].ttf", True)):
    for w, name in ((400, "Regular"), (500, "Medium"), (600, "SemiBold"), (700, "Bold")):
        f = instancer.instantiateVariableFont(TTFont(src), {"wght": w}, updateFontNames=True)
        style = ("" if name == "Regular" else name) + ("Italic" if ital else "")
        f.save(f"Lora-{style or 'Regular'}.ttf")
```

Then add it to `BUNDLED_FAMILIES` in `scripts/build_book.py` (family name -> file stem) and keep its licence file here. Fonts already installed on the machine (Lufga, Libre Baskerville, Cormorant Garamond) work by name without bundling, if they are static files.
