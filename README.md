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

```bash
pip install -r requirements.txt
playwright install chromium
```

Si Playwright signale un exécutable manquant (`chrome-headless-shell`),
relancez simplement :

```bash
playwright install
```

L'installation de Chromium (Playwright) n'est nécessaire que si le
fallback navigateur est utilisé (voir plus bas).

## Utilisation

```bash
# À partir d'un slug de chapitre
python main.py OP1188

# À partir de l'URL complète, avec un nom de fichier personnalisé
python main.py https://mangamoins.com/scan/OP1188 -o one-piece-1188.pdf

# Forcer le fallback navigateur headless (si l'API/HTML sont bloqués)
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
├── main.py             # point d'entrée CLI
├── requirements.txt
└── README.md
```

## Limitations connues

- Un seul site supporté (MangaMoins).
- Un seul chapitre à la fois (pas de téléchargement en masse).
- Pas d'interface graphique.
