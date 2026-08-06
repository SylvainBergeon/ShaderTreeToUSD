# Contexte projet — ShaderTreeToUSD

Ce fichier résume les décisions prises lors d'une session de conception (hors
Claude Code, sur claude.ai) portant sur la refonte de la complexité du plugin,
puis le travail effectué dans Claude Code pour la mettre en œuvre. Il sert de
point de reprise : lis-le avant de proposer des changements pour rester
cohérent avec la direction déjà validée par l'auteur du projet.

**Dernière mise à jour : 2026-08-06, après les étapes 1 et 2 (voir plus bas).**

## Le projet

Kit Modo qui exporte un shader tree Modo vers USD/MaterialX, pour être
réimporté dans Houdini (Karma). Point d'entrée : `Scripts/lxserv/ExportShaderTree.py`
(commande Modo `exportShaderTree`), qui délègue à
`Scripts/python_modules/ShaderTree.py` (le cœur du système) et
`Scripts/python_modules/ShaderFilters.py` (tables de correspondance
Modo <-> USD).

`fnpxr` = nom donné par Foundry à sa copie interne des bindings Python de
Pixar USD (`pxr`). Fonctionnellement identique à `pxr` standard.

## Environnement de dev

- Le repo est un kit Modo chargeable directement depuis ce dossier (présence
  d'`index.cfg` à la racine) : pas besoin de packager en `.lpk` pour
  développer, `build_lpk.py` sert uniquement à la distribution.
- `ExportShaderTree.py` appelle `reload_modules()` à chaque exécution de la
  commande dans Modo -> `ShaderTree.py`, `ShaderFilters.py`, et maintenant
  **tout le package `Scripts/python_modules/normalize/`** sont rechargés à
  chaud depuis le disque (voir "Étage 2" plus bas — ce rechargement du
  package `normalize` a dû être ajouté explicitement, `reload()` ne
  descendant pas automatiquement dans les modules importés). Seul
  `ExportShaderTree.py` lui-même nécessite un restart de Modo si modifié.
- `.vscode/settings.json` configure l'analyse statique (stubs `lx`/`modo`,
  `extraPaths` vers le Python de Modo, résolution `pxr`). Ça ne permet pas
  d'exécuter le code Modo-dépendant, juste de l'éditer avec autocomplétion.
- **`.venv/` est maintenant un vrai environnement de dev/test** : `pytest`
  (pour `Scripts/python_modules/normalize/`, zéro dépendance Modo) et
  `MaterialX` (paquet PyPI officiel, utilisé uniquement par l'outil
  `Scripts/python_modules/normalize/tools/generate_node_registry.py` pour
  interroger la vraie librairie standard MaterialX) y sont installés. `lx`/
  `modo`/`fnpxr` restent absents — impossible d'exécuter le code Modo-
  dépendant (`ShaderTree.py`, `ShaderFilters.py`, `ExportShaderTree.py`) hors
  Modo.
- `__pycache__/` et `.pytest_cache/` sont dans `.gitignore` — ne plus les
  committer (des `.pyc` trainaient dans l'historique, ils ont été untrack).
- **Convention de commit** : les commits faits par Claude Code dans ce repo
  sont préfixés `CLAUDE_` dans leur titre, pour les distinguer des commits
  faits directement par l'auteur.

## Le problème identifié

Le point de douleur signalé par l'auteur : **le traitement des cas
particuliers est trop complexe**, en particulier dans `ShaderTree.py`.
`USD_export_shadertree()` (fonction principale, parcours récursif de l'arbre)
mélangeait trois responsabilités dans la même passe :

1. parcours de l'arbre (dispatch par tag XML)
2. interprétation métier (quel BRDF, quel type de blend, conversions
   physiques specular/IOR, résolution des noms d'effet...)
3. appels effectifs à l'API USD (`UsdShade`, `Sdf`)

Direction validée : pipeline en 3 étages.

```
Modo (item tree)  -->  XML brut          -->  XML canonique       -->  Stage USD
  XML_export_item()      (existe)              (FAIT)                  (PAS ENCORE branché)
```

## Étage 1 — FAIT : refactor local de deux fonctions

`_USD_apply_overrides` (conversions specular/IOR selon le BRDF gtr/principled)
et `_USD_connect_operator` (connexion des opérateurs de blend) sont
refactorisées dans `Scripts/python_modules/ShaderTree.py`, comportement
identique + deux corrections :
- `_USD_apply_overrides` : suppression d'une ligne morte (`specCol` assigné
  puis toujours écrasé juste après), et protection division par zéro sur
  diffuse noir pur (dans `_USD_tinted_spec_color` — retourne blanc au lieu de
  planter).
- `_USD_connect_operator` : le pattern "connecter si `UsdShade.Output`, sinon
  `eval()` + `Set()`" (dupliqué 3 fois) est extrait dans `_USD_set_or_connect`.
  Les deux chemins (Multiply/Divide vs autres blends) partagent la création
  du premier nœud.

**Convention de nommage étendue à tout le module** : `export_basic_execute()`
est le **seul** point d'entrée appelé depuis l'extérieur du module (par
`ExportShaderTree.py`). Toutes les autres fonctions du module ont été
préfixées `_` + domaine : `_USD_*`, `_XML_*`, `_JSON_*`, `_UTIL_*` (ou juste
`_` pour les fonctions transverses aux domaines : `_diag`,
`_initialize_preferences`).

## Étage 2 — FAIT : module de normalisation

`Scripts/python_modules/normalize/` contient 4 passes pures, `Element ->
Element`, zéro dépendance `lx`/`modo`/`fnpxr`, testées avec pytest
(`tests/normalize/`, 69 tests) :

- **`normalize_specular_ior`** — migration de `_USD_apply_overrides`.
- **`normalize_blend_operators`** — migration de `_USD_connect_operator` :
  résout `channels/blend` en `usdOperator` (nom de nœud USD/MaterialX). Les
  15 valeurs de blend Modo (`lx.symbol.sICVAL_TEXTURELAYER_BLEND_*`) sont
  dupliquées en littéraux (obtenues en interrogeant une instance Modo réelle,
  puisque `ShaderFilters.usdInputMap["blend"]` a ses clés indexées par ces
  symboles `lx` et ne peut pas être importé hors Modo).
- **`normalize_projection_defaults`** — résout `txtrLocator/channels/projType`
  en `usdProjType`, avec fallback vers `"uv"` pour tout type non supporté
  (miroir du fallback silencieux qui existait dans
  `_USD_create_texture_output`).
- **`normalize_effect_channel_names`** — résout `channels/effect` en
  `usdInputName` (table dupliquée depuis `ShaderFilters.usdInputMap['effect']`
  — celle-ci a des clés en chaînes brutes, pas de dépendance `lx`, donc pas
  besoin de requête Modo pour la copier).

Toutes les passes sont **non-destructives** (retournent une copie) : c'est
volontaire, car `_USD_create_mtlx_standard_surface_shader` construit le
shader glPreview et le shader mtlx à partir du **même** XML source, et le
preview a besoin des valeurs brutes (pas des overrides gtr/principled).

**`Scripts/python_modules/normalize/node_registry.py`** : catalogue statique
des ~60 nœuds USD/MaterialX réellement utilisés dans `ShaderTree.py` (inputs
nommés + types + type de sortie), généré depuis la vraie librairie standard
MaterialX via `Scripts/python_modules/normalize/tools/generate_node_registry.py`
(à relancer si un nouveau `CreateIdAttr(...)` apparaît dans `ShaderTree.py`).
Ça a permis de **confirmer** que le découpage `multiply`/`divide` (2 nœuds,
`in1`/`in2`) vs les 8 autres blends (1 nœud, `fg`/`bg`/`mix`) était correct
— d'où la suppression de l'attribut `usdMixPattern` qui le codait à la main
dans `normalize_blend_operators` : c'est maintenant dérivable à la volée
depuis `node_registry.py` (présence d'un input `'mix'`) plutôt que dupliqué.

**Deux bugs trouvés et corrigés pendant ce travail** (pas des régressions
introduites, des bugs pré-existants révélés par le cross-check) :
1. `ShaderTree.py:867` créait un nœud `"ND_normalmap"` — id invalide,
   n'existe pas dans MaterialX (seuls `ND_normalmap_float`/`_vector2`
   existent). Corrigé en `ND_normalmap_float` (`scale` y est réglé comme un
   float simple).
2. `reload_modules()` dans `ExportShaderTree.py` ne rechargeait que `ST`
   (ShaderTree) et `SF` (ShaderFilters) — les modifs sous `normalize/`
   étaient ignorées jusqu'à un restart de Modo. Corrigé : le package
   `normalize` et ses 5 sous-modules sont rechargés explicitement (sous-
   modules d'abord, `__init__.py` du package ensuite) avant `ST`.

**Rien de tout ça n'est encore branché dans la construction USD réelle** —
`_USD_export_shadertree`, `_USD_apply_overrides`, `_USD_connect_operator`
etc. sont inchangés et continuent à faire le travail "à la volée" comme
avant. Seul ajout côté export : `export_basic_execute()` calcule
`xml_shadertree_normalized` (XML passé dans les 4 passes) et le sauvegarde à
part (`<nom>_normalized.xml`) quand l'export XML est actif, pour comparaison
manuelle avec le XML brut — pas encore utilisé pour la construction USD
elle-même.

### Décisions encore ouvertes

1. **Vocabulaire canonique** : toujours pas tranché formellement. Les passes
   actuelles suivent la direction recommandée (garder les noms de balises/
   canaux Modo, normaliser seulement les valeurs, ajouter des attributs
   `usd*` en plus plutôt que renommer).
2. **Où vivent les tables de `ShaderFilters.py`** : toujours ouvert
   structurellement. Contournement actuel : les tables sans dépendance `lx`
   (effect) ou nécessitant une requête Modo ponctuelle (blend) sont
   **dupliquées** dans `normalize/`, avec commentaire pointant vers la
   source — accepté comme compromis temporaire, pas une solution définitive
   (risque de drift entre les deux copies si `ShaderFilters.py` change).
3. **Migration progressive** : c'est le modèle suivi jusqu'ici — chaque passe
   construite et testée indépendamment, `_USD_export_shadertree` non touché
   tant que le câblage réel n'est pas décidé.

## Exécution/tests hors Modo — FAIT pour l'étage 2

- `pytest` installé dans `.venv`, lancer avec `.venv/bin/python3 -m pytest`
  (config dans `pytest.ini` à la racine, `pythonpath = Scripts`).
  `tests/normalize/` : 69 tests couvrant les 4 passes + le registre de
  nœuds.
- **Étage 3 (construction USD)** : toujours pas testé hors Modo. Reste
  possible en installant `usd-core` (déjà fait dans `.venv` pour d'autres
  besoins, mais **n'inclut pas `UsdMtlx`** — l'introspection MaterialX est
  passée par le paquet PyPI `MaterialX` séparé, pas par `fnpxr`/`pxr`).
- **Étage 1 (extraction Modo)** reste dépendant de l'interpréteur embarqué de
  Modo. Pour du debug interactif dessus : `debugpy.listen()` côté Modo +
  "Python Debugger: Remote Attach" côté VS Code.

## Prochaines étapes suggérées (à valider avec l'auteur avant de foncer)

1. **Brancher les passes de normalisation dans la construction réelle** :
   remplacer les appels à `_USD_apply_overrides`/`_USD_connect_operator`/etc.
   dans `_USD_create_mtlx_standard_surface_shader`/`_USD_export_shadertree`
   par une lecture du XML déjà normalisé. Commencer par une seule passe
   (specular_ior, la plus isolée) plutôt que les 4 d'un coup. Cette
   vérification-là ne peut plus se faire avec pytest seul : il faut tester
   dans Modo et comparer un export avant/après sur un vrai shader tree pour
   confirmer que le `.usda` produit est identique.
2. **Concevoir le mécanisme générique de reconnexion des inputs** évoqué par
   l'auteur : au lieu de coder à la main la forme de chaque opérateur USD
   (comme le faisait `usdMixPattern`), utiliser `node_registry.py` pour
   déterminer dynamiquement quels inputs connecter selon le nœud USD ciblé.
   Pas commencé — juste l'infrastructure de données (`node_registry.py`)
   est en place.
3. **Trancher la décision n°2** (emplacement des tables `ShaderFilters.py`)
   si la duplication actuelle devient un problème (une table modifiée dans
   un seul des deux endroits).
4. Seulement après : `normalize_projection_defaults`/
   `normalize_effect_channel_names` sont déjà faits — simplifier
   `USD_export_shadertree` pour qu'il devienne un simple walker générique
   (étage 3) une fois que tout ce qui précède est branché.

Ne pas réintroduire de logique de cas particulier dans l'étage 3 — c'est
précisément ce que cette refonte cherche à éviter.
