# Portal de Materials — IES El Caminas

Portal web que mostra automàticament els materials didàctics publicats pels professors de l'institut, organitzats per cicle, curs i mòdul.

## Com funciona

1. Un professor crea un repo a l'organització GitHub
2. Activa **GitHub Pages** (branca `gh-pages`)
3. Afig un **topic** al repo amb el format `cicle+curs-modul`:
   - `asir1-par` → ASIR 1r curs · Planificació i Administració de Xarxes
   - `asir2-sad` → ASIR 2n curs · Seguretat i Alta Disponibilitat
   - `daw1-dwec` → DAW 1r curs · Desenvolupament Web en Entorn Client
   - `smr1-rlo`  → SMR 1r curs · Xarxes Locals
   - `ce1-des`   → CE · Desplegament de Programari

4. La nit següent, la GitHub Action detecta el repo i actualitza el portal automàticament.

## Actualització manual

Des de GitHub → Actions → "Actualitzar portal" → Run workflow

## Migrar a la organització oficial

Canviar una línia al fitxer `.github/workflows/update-portal.yml`:

```yaml
ORG: pedrosegarra   # ← canviar per: ieselcaminas
```

## Estructura

```
.
├── index.html                         # Portal (generat automàticament)
├── .github/
│   ├── workflows/
│   │   └── update-portal.yml          # GitHub Action (cron nocturn)
│   └── scripts/
│       └── generate_portal.py         # Script de generació
└── README.md
```
