# MangaMoins Scraper → PDF

Petit outil en ligne de commande pour télécharger les pages d'un chapitre
depuis [mangamoins.com](https://mangamoins.com) et les assembler en un
fichier PDF.

## Avertissement

MangaMoins héberge du contenu scantrad protégé par le droit d'auteur.
Cet outil est fourni à visée technique/éducative. Utilisez-le uniquement
sur du contenu que vous avez le droit de télécharger, pour un usage
personnel.

## ⚠️ À savoir avant d'installer

MangaMoins bloque volontairement l'accès direct aux images (voir
[Fonctionnement](#fonctionnement) plus bas). En pratique, **le
téléchargement échoue la plupart du temps sans le module Playwright** —
ce n'est pas une option de confort, c'est ce qui fait fonctionner l'outil
aujourd'hui. Les instructions ci-dessous l'installent par défaut ; ne le
sautez que si vous savez ce que vous faites.

## Installation

### Windows, sans ligne de commande (recommandé)

1. Installez Python si ce n'est pas déjà fait :
   [python.org/downloads](https://www.python.org/downloads/) — cochez
   bien **"Add python.exe to PATH"** pendant l'installation.
2. Téléchargez ce projet (bouton vert **Code → Download ZIP** sur
   GitHub, puis décompressez-le) ou clonez-le avec `git clone`.
3. Double-cliquez sur `install.bat`.
4. Quand le script demande `Installer le support navigateur
   maintenant ? (o/N)`, répondez **`o`** (voir l'avertissement
   ci-dessus). Cette étape télécharge Chromium (~300 Mo), c'est normal
   que ça prenne quelques minutes.
5. Une fois terminé, utilisez l'outil avec :
   ```bat
   venv\Scripts\python.exe main.py OP1188
   ```

Si l'étape 4 est ignorée par erreur, vous pouvez l'installer après coup :
```bat
venv\Scripts\pip.exe install -r requirements-optional.txt
venv\Scripts\python.exe -m playwright install chromium
```

### Manuelle (Windows/macOS/Linux)

```bash
pip install -r requirements.txt
pip install -r requirements-optional.txt
playwright install chromium
```

La première ligne installe les dépendances de base (`requests`,
`pillow`, `img2pdf`) ; les deux suivantes installent le fallback
navigateur (Playwright), nécessaire dans la pratique pour la majorité
des chapitres (voir l'avertissement ci-dessus).

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

# Forcer directement le fallback navigateur (évite les tentatives
# API/HTML vouées à l'échec, donc un peu plus rapide)
python main.py OP1188 --use-playwright

# Logs détaillés (utile en cas de problème)
python main.py OP1188 --verbose
```

Le PDF est écrit par défaut sous le nom `<slug>.pdf` dans le dossier
courant.

## Dépannage

- **`Erreur : Playwright n'est pas installé.`** — vous avez sauté la
  partie Playwright de l'installation. Suivez la commande affichée dans
  le message d'erreur (ou revoyez la section [Installation](#installation)).
- **`Erreur : Aucune page trouvée pour ce chapitre`** — vérifiez que le
  slug/l'URL est correct (ex : `OP1188` pour
  `https://mangamoins.com/scan/OP1188`). Si le slug est correct,
  MangaMoins a peut-être changé sa structure de page ; relancez avec
  `--verbose` pour voir où ça bloque.
- **`'install.bat' n'est pas reconnu...` ou rien ne se passe au
  double-clic** — assurez-vous d'avoir décompressé le ZIP avant de
  lancer le script (ne pas l'exécuter depuis l'intérieur de l'archive).
- **Erreur liée à `pip` pendant `install.bat`** — vérifiez que Python a
  bien été installé avec l'option "Add python.exe to PATH" cochée, puis
  relancez `install.bat`.

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
   réelle sur la page 1. Si elle est invalide (c'est le cas actuellement
   pour la quasi-totalité des chapitres testés) :
   - **Fallback HTML** : parse la page du lecteur côté serveur. Échoue
     systématiquement aujourd'hui car le site est une SPA rendue côté
     client (gardé pour compatibilité si MangaMoins change son
     implémentation).
   - **Fallback navigateur** : un navigateur Chromium headless
     (Playwright) charge la page et lit l'URL réelle de l'image dans le
     DOM rendu, qui elle n'est pas obfusquée. **C'est la méthode qui
     fonctionne réellement en pratique aujourd'hui.**
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
- Dépend du DOM actuel de MangaMoins pour le fallback navigateur ; un
  changement de mise en page côté site peut casser le scraping jusqu'à
  mise à jour du code.
