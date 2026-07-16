# MangaMoins Scraper → PDF

Petit outil pour télécharger les pages d'un chapitre depuis
[mangamoins.com](https://mangamoins.com) et les assembler en un fichier
PDF, disponible en interface graphique ou en ligne de commande.

## Avertissement

MangaMoins héberge du contenu scantrad protégé par le droit d'auteur.
Cet outil est fourni à visée technique/éducative. Utilisez-le uniquement
sur du contenu que vous avez le droit de télécharger, pour un usage
personnel.

## ⚠️ À savoir avant d'installer

MangaMoins bloque volontairement l'accès direct aux images (voir
[Fonctionnement](#fonctionnement) plus bas). En pratique, **le
téléchargement échoue la plupart du temps sans le module Playwright**
(un navigateur headless) — ce n'est pas une option de confort, c'est ce
qui fait fonctionner l'outil aujourd'hui. La version graphique le
télécharge automatiquement toute seule au premier lancement ; en ligne
de commande, il faut l'installer explicitement (voir plus bas).

## Installation

### Option 1 — Application Windows (le plus simple)

1. Allez sur la page [Releases](../../releases) du projet et téléchargez
   `MangaMoins-to-PDF.exe` (dernière version).
2. Double-cliquez dessus. Aucune installation de Python n'est nécessaire.
3. Windows peut afficher un écran bleu **"Windows a protégé votre
   ordinateur"** au premier lancement (l'exécutable n'est pas signé
   numériquement — voir [Dépannage](#dépannage)). Cliquez sur
   **"Informations complémentaires"** puis **"Exécuter quand même"**.
4. Au tout premier téléchargement d'un chapitre, l'application récupère
   automatiquement le navigateur intégré nécessaire (~300 Mo, une seule
   fois : voir l'avertissement ci-dessus). Comptez 1-2 minutes selon
   votre connexion.

### Option 2 — Depuis les sources, sans ligne de commande (Windows)

1. Installez Python si nécessaire :
   [python.org/downloads](https://www.python.org/downloads/) — cochez
   **"Add python.exe to PATH"** pendant l'installation.
2. Téléchargez ce projet (bouton vert **Code → Download ZIP** sur
   GitHub, puis décompressez-le) ou clonez-le avec `git clone`.
3. Double-cliquez sur `install.bat`.
4. Quand le script demande `Installer le support navigateur
   maintenant ? (O/n)`, laissez la réponse par défaut (**Entrée**), voir
   l'avertissement ci-dessus.
5. Lancez l'interface graphique avec `venv\Scripts\python.exe gui_main.py`,
   ou la ligne de commande avec `venv\Scripts\python.exe main.py OP1188`.

### Option 3 — Installation manuelle (Windows/macOS/Linux)

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

### Interface graphique

```bash
python gui_main.py
```

1. Entrez un slug (`OP1188`) ou une URL complète de chapitre.
2. Le champ "Enregistrer le PDF sous" se remplit automatiquement ;
   changez-le avec **Parcourir...** si besoin.
3. Cliquez sur **Télécharger** (ou appuyez sur Entrée). La progression et
   le journal des pages s'affichent en direct.
4. Une fois terminé, une fenêtre propose d'ouvrir le dossier contenant le
   PDF.

### Ligne de commande

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

- **Écran bleu "Windows a protégé votre ordinateur" (SmartScreen)** —
  normal pour un exécutable non signé par un éditeur reconnu (signer un
  exécutable coûte un certificat payant). Cliquez sur "Informations
  complémentaires" puis "Exécuter quand même". Si vous préférez éviter
  cet écran, utilisez l'Option 2 ou 3 (installation depuis les sources).
- **`Erreur : Playwright n'est pas installé.`** (ligne de commande) —
  vous avez sauté la partie Playwright de l'installation. Suivez la
  commande affichée dans le message d'erreur.
- **`Erreur : Aucune page trouvée pour ce chapitre`** — vérifiez que le
  slug/l'URL est correct (ex : `OP1188` pour
  `https://mangamoins.com/scan/OP1188`). Si le slug est correct,
  MangaMoins a peut-être changé sa structure de page ; relancez en ligne
  de commande avec `--verbose` pour voir où ça bloque.
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

L'interface graphique (`gui.py`) et la ligne de commande (`main.py`)
partagent exactement cette même logique (`scraper.py` / `pdf_builder.py`) ;
seule la façon de la piloter change.

## Structure du projet

```
mangamoins-scraper/
├── mangamoins_scraper/
│   ├── __init__.py
│   ├── scraper.py      # logique de scraping (API, HTML, Playwright)
│   ├── pdf_builder.py  # assemblage des images en PDF
│   └── gui.py           # interface graphique (tkinter)
├── tests/                     # tests unitaires (pytest)
├── main.py                    # point d'entrée CLI
├── gui_main.py                 # point d'entrée GUI
├── install.bat                  # installation en un clic (Windows)
├── MangaMoins-to-PDF.spec         # config PyInstaller (build de l'exe GUI)
├── requirements.txt                  # dépendances de base
├── requirements-optional.txt         # fallback navigateur (Playwright)
├── requirements-dev.txt              # dépendances de développement (pytest)
├── requirements-build.txt            # dépendances pour builder l'exe (PyInstaller)
└── README.md
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent la logique pure (extraction de slug, détection
d'extension, sondage du nombre de pages, détection webp, aide de la GUI)
via des mocks ; aucun appel réseau réel n'est effectué.

Le code suit PEP 8 (vérifié avec `flake8`, config dans `setup.cfg`).

## Builder l'exécutable de la GUI

```bash
pip install -r requirements-build.txt
pyinstaller MangaMoins-to-PDF.spec
```

L'exécutable est généré dans `dist/MangaMoins-to-PDF.exe`. Il embarque
Playwright mais pas Chromium (téléchargé au premier lancement, voir
l'avertissement plus haut) pour rester raisonnablement léger.

## Limitations connues

- Un seul site supporté (MangaMoins).
- Un seul chapitre à la fois (pas de téléchargement en masse).
- Exécutable Windows non signé (déclenche l'avertissement SmartScreen,
  voir [Dépannage](#dépannage)).
- Dépend du DOM actuel de MangaMoins pour le fallback navigateur ; un
  changement de mise en page côté site peut casser le scraping jusqu'à
  mise à jour du code.
