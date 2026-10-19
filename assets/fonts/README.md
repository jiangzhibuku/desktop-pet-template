# Fonts

No font is bundled with this repository.

The app automatically uses a CJK-capable system font (`Microsoft YaHei` on
Windows).  If you want a custom font:

1. Make sure its license allows redistribution **and** commercial use.
2. Copy the `.ttf` / `.ttc` / `.otf` file into this folder.
3. Restart the app.  The first font found here is registered automatically.

Alternatively set an absolute path in `config.json`:

```json
{ "font": "C:/Windows/Fonts/msyh.ttc" }
```

Fonts are covered by their own licenses; they are **not** covered by this
project's MIT license.
