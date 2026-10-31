# cvregistry

Markdownban írt önéletrajzokból egységes, céges arculatú (Alvicom) PDF-eket generáló eszköz.

Minden CV egy mappa a `cvs/` alatt, nyelvenként egy Markdown fájllal. A generátor ezeket feldolgozza, egy HTML sablonba tölti, majd [WeasyPrint](https://weasyprint.org/) segítségével PDF-et készít belőlük.

## Követelmények

- Python 3.9+
- A WeasyPrint natív függőségei (Pango, Cairo)
  - macOS: `brew install pango`
  - Debian/Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`

## Telepítés

```sh
python3 -m venv .venv
.venv/bin/pip install -r src/requirements.txt
```

A `Makefile` automatikusan a `.venv` Pythonját használja, ha létezik.

## Használat

```sh
make cv                        # bekéri a CV nevét (cvs/<név>/)
make cv NAME=tar_gabor_zsolt   # egy adott ember összes nyelvi változata
make build                     # minden CV a cvs/ alatt
make clean                     # a generált PDF-ek törlése
```

A kimenet: `build/<név>/<nyelv>.pdf`, például `build/tar_gabor_zsolt/hu.pdf`.

Közvetlenül is futtatható:

```sh
.venv/bin/python src/generate.py cvs/tar_gabor_zsolt/hu.md
```

## Könyvtárszerkezet

```
cvs/<név>/
  hu.md          # magyar változat
  en.md          # angol változat
  selfie.jpeg    # opcionális fotó (.png / .jpg / .jpeg)
assets/
  alvicom-logo.png
src/
  generate.py                    # Markdown → HTML → PDF
  templates/modern-sidebar.html  # Jinja2 sablon
```

A fájl neve (`hu`, `en`) határozza meg a nyelvet és ezzel a szekciócímkéket a PDF-ben.
A fotót a generátor középről négyzetre vágja és kör alakúra maszkolja. Ha nincs fotó, a PDF anélkül készül el.

## Új CV hozzáadása

1. Hozz létre egy mappát: `cvs/<vezeteknev_keresztnev>/`
2. Másold be egy meglévő CV-t (pl. `cvs/tar_gabor_zsolt/hu.md`) kiindulásnak, és írd át.
3. Tegyél mellé egy `selfie.jpeg` fotót (opcionális).
4. `make cv NAME=<vezeteknev_keresztnev>`

## Markdown formátum

A feldolgozó a címsorok és a sorok formája alapján működik, ezért a formátumot pontosan kell követni.
Elválasztóként em dash (`—`) és középpont (`·`) szerepel.

```markdown
# Teljes Név

## Pozíció / titulus        ← az első ## mindig a titulus

## Rólam
Szabad szöveges bemutatkozás.

## Kompetencia
- **Kategória:** elem · elem · elem

## Készségek
- Python — 5                 ← szint 1–5

## Nyelvek
- Magyar — anyanyelv

## Hobbi
Hobbi1 · Hobbi2 · Hobbi3     ← egyetlen sor

## Eredmények
- **Típus** — Cím · kiadó/intézmény · év

## Szakmai tapasztalat

### Munkáltató

#### Pozíció vagy korszak · 2018 – 2024

*Alcím (pl. projekt típusa, csapatméret)*

- Feladat leírása — Technológia · Technológia
- Feladat technológiák nélkül
```

A szekciócímek magyarul és angolul is elfogadottak:

| Magyar               | Angol                     |
|----------------------|---------------------------|
| Rólam                | About                     |
| Kompetencia          | Competence                |
| Készségek            | Skills                    |
| Nyelvek              | Languages                 |
| Hobbi                | Hobbies                   |
| Eredmények           | Achievements              |
| Szakmai tapasztalat  | Professional Experience   |

Az ismeretlen című szekciókat a generátor figyelmen kívül hagyja.

## Licenc

MIT, lásd: [LICENSE](LICENSE).
