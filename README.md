# MangaMoins Scraper → PDF

Petit outil en ligne de commande pour télécharger les pages d'un chapitre
depuis [mangamoins.com](https://mangamoins.com) et les assembler en un
fichier PDF.

## Avertissement

MangaMoins héberge du contenu scantrad protégé par le droit d'auteur.
Cet outil est fourni à visée technique/éducative. Utilisez-le uniquement
sur du contenu que vous avez le droit de télécharger, pour un usage
personnel.

## Installation

### Windows, sans ligne de commande

Double-cliquez sur `install.bat`. Il installe Python (si nécessaire, à vous
de l'installer manuellement depuis [python.org](https://www.python.org/downloads/)
en cochant "Add python.exe to PATH"), crée un environnement virtuel et
installe les dépendances. Le support navigateur (Playwright) est proposé en
option pendant l'installation.

### Manuelle (toutes plateformes)

```bash
pip install -r requirements.txt
```

Cela installe uniquement les dépendances de base (`requests`, `pillow`,
`img2pdf`), suffisantes dans la grande majorité des cas.

Le fallback navigateur headless (Playwright) n'est nécessaire que si l'API
et le HTML de MangaMoins sont bloqués (voir plus bas). Pour l'installer :

```bash
pip install -r requirements-optional.txt
playwright install chromium
```

Si Playwright signale un exécutable manquant (`chrome-headless-shell`),
relancez simplement :

```bash
playwright install
```

## Utilisation

```bash
# À partir d'un slug de chapitre
python main.py OP1188

# À partir de l'URL complète, avec un nom de fichier personnalisé
python main.py https://mangamoins.com/scan/OP1188 -o one-piece-1188.pdf

# Forcer le fallback navigateur headless (si l'API/HTML sont bloqués,
# nécessite `pip install -r requirements-optional.txt` au préalable)
python main.py OP1188 --use-playwright

# Logs détaillés
python main.py OP1188 --verbose
```

Le PDF est écrit par défaut sous le nom `<slug>.pdf` dans le dossier
courant.

## Fonctionnement

1. **Session** : une requête est d'abord faite sur la page d'accueil pour
   obtenir les cookies de session.
2. **API interne** : `GET /api/v1/scan?slug=<slug>` renvoie une URL de
   base et un nombre de pages. **Attention** : MangaMoins retourne
   volontairement une `pagesBaseUrl` corrompue (préfixe/suffixe
   aléatoires ajoutés autour du vrai identifiant de dossier), comme
   mesure anti-scraping basique. Le nombre de pages (`pageNumbers`), lui,
   est fiable.
3. Le script **valide** l'URL de base renvoyée par l'API avec une requête
   réelle sur la page 1. Si elle est invalide :
   - **Fallback HTML** : parse la page du lecteur côté serveur (peu utile
     ici car le site est une SPA rendue côté client, mais gardé pour
     compatibilité).
   - **Fallback navigateur** : un navigateur Chromium headless
     (Playwright) charge la page et lit l'URL réelle de l'image dans le
     DOM rendu, qui elle n'est pas obfusquée.
4. Le nombre exact de pages est confirmé/ajusté en sondant les URLs autour
   du nombre indiqué par l'API (ou par balayage séquentiel si aucune
   information n'est disponible).
5. Les images sont téléchargées puis assemblées en PDF (les `.webp` sont
   converties en PNG au passage).

## Structure du projet

```
mangamoins-scraper/
├── mangamoins_scraper/
│   ├── __init__.py
│   ├── scraper.py      # logique de scraping (API, HTML, Playwright)
│   └── pdf_builder.py  # assemblage des images en PDF
├── tests/               # tests unitaires (pytest)
├── main.py              # point d'entrée CLI
├── install.bat           # installation en un clic (Windows)
├── requirements.txt          # dépendances de base
├── requirements-optional.txt # fallback navigateur (Playwright)
├── requirements-dev.txt      # dépendances de développement (pytest)
└── README.md
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent la logique pure (extraction de slug, détection
d'extension, sondage du nombre de pages, détection webp) via des mocks ;
aucun appel réseau réel n'est effectué.

## Limitations connues

- Un seul site supporté (MangaMoins).
- Un seul chapitre à la fois (pas de téléchargement en masse).
- Pas d'interface graphique.
