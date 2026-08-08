# Contexte projet — ShaderTreeToUSD

Ce fichier résume les décisions prises lors d'une session de conception (hors
Claude Code, sur claude.ai) portant sur la refonte de la complexité du plugin,
puis le travail effectué dans Claude Code pour la mettre en œuvre. Il sert de
point de reprise : lis-le avant de proposer des changements pour rester
cohérent avec la direction déjà validée par l'auteur du projet.

**Dernière mise à jour : 2026-08-07. Les 3 étages du pipeline sont câblés de
bout en bout et validés dans Modo (voir plus bas).**

**PRIORITAIRE pour la prochaine session : finir le shader glPreview
(`UsdPreviewSurface`)** — les matériaux texturés apparaissent blancs dans le
viewport (Storm/Houdini). Cause identifiée et le chantier restant est
décrit en détail dans la section "Shader glPreview" plus bas (réseau de
lecture de texture dédié, `UsdUVTexture`/`UsdPrimvarReader_float2`/
`UsdTransform2d`). Lire cette section en premier avant de proposer autre
chose.

## Le projet

Kit Modo qui exporte un shader tree Modo vers USD/MaterialX, pour être
réimporté dans Houdini (Karma). Point d'entrée : `Scripts/lxserv/ExportShaderTree.py`
(commande Modo `exportShaderTree`), qui délègue à
`Scripts/python_modules/ShaderTree.py` (le cœur du système) et
`Scripts/python_modules/ShaderFilters.py` (tables de correspondance
Modo <-> USD).

`fnpxr` = nom donné par Foundry à sa copie interne des bindings Python de
Pixar USD (`pxr`). Fonctionnellement identique à `pxr` standard.

Vocabulaire XML du shader tree (confirmé par l'auteur) :
- `<advancedMaterial/>` = le nœud shader (BRDF) lui-même, ex. MtlX Standard
  Surface.
- `<mask/>` = le vrai "matériau" au sens USD : un groupe de couches
  d'opérateurs, assigné à un groupe de polygones du même nom (via `ptag`).
  Plusieurs couches (`imageMap`/`noise`/`constant`) visant le même `effect`
  s'empilent et s'évaluent en cascade selon leur `blend`, dans l'ordre où
  elles apparaissent sous le `<mask>`.
- `<channels>` = conteneur générique des paramètres de l'élément parent, quel
  que soit son tag. Tous les canaux Modo d'un item y sont exportés, mais
  seul un sous-ensemble a un équivalent USD (le reste est silencieusement
  ignoré par `_UTIL_get_mapped_channel`, qui retourne `None` — c'est voulu,
  ne pas essayer de "tout traduire mécaniquement").

## Environnement de dev

- Le repo est un kit Modo chargeable directement depuis ce dossier (présence
  d'`index.cfg` à la racine) : pas besoin de packager en `.lpk` pour
  développer, `build_lpk.py` sert uniquement à la distribution.
- `ExportShaderTree.py` appelle `reload_modules()` à chaque exécution de la
  commande dans Modo -> `ShaderTree.py`, `ShaderFilters.py`, et **tout le
  package `Scripts/python_modules/normalize/`** (5 sous-modules + le package
  lui-même) sont rechargés à chaud depuis le disque. Seul
  `ExportShaderTree.py` lui-même nécessite un restart de Modo si modifié
  (piège vécu en session : un fix dans ce fichier n'était pas actif tant que
  Modo n'avait pas redémarré, alors que tout le reste rechargeait bien).
- `.vscode/settings.json` configure l'analyse statique (stubs `lx`/`modo`,
  `extraPaths` vers le Python de Modo, résolution `pxr`). Ça ne permet pas
  d'exécuter le code Modo-dépendant, juste de l'éditer avec autocomplétion.
- **`.venv/` est un vrai environnement de dev/test** : `pytest` (pour
  `Scripts/python_modules/normalize/`, zéro dépendance Modo) et `MaterialX`
  (paquet PyPI officiel, utilisé uniquement par
  `Scripts/python_modules/normalize/tools/generate_node_registry.py` pour
  interroger la vraie librairie standard MaterialX) y sont installés. `lx`/
  `modo`/`fnpxr` restent absents — impossible d'exécuter le code Modo-
  dépendant (`ShaderTree.py`, `ShaderFilters.py`, `ExportShaderTree.py`) hors
  Modo ; `usd-core` est aussi installé mais **n'inclut pas `UsdMtlx`**.
- `__pycache__/` et `.pytest_cache/` sont dans `.gitignore`.
- **Convention de commit** : les commits faits par Claude Code dans ce repo
  sont préfixés `CLAUDE_` dans leur titre, pour les distinguer des commits
  faits directement par l'auteur.

## Le problème identifié

Le point de douleur signalé par l'auteur : **le traitement des cas
particuliers est trop complexe**, en particulier dans `ShaderTree.py`.
`USD_export_shadertree()` (fonction principale, parcours récursif de l'arbre)
mélangeait trois responsabilités dans la même passe : parcours de l'arbre,
interprétation métier (BRDF, blend, conversions specular/IOR, résolution des
noms d'effet...), et appels effectifs à l'API USD.

Direction validée, maintenant en place :

```
Modo (item tree)  -->  XML brut          -->  XML canonique       -->  Stage USD
  XML_export_item()      (existe)          normalize.normalize()      construction lit
                                            (Scripts/python_modules/    le XML normalisé
                                             normalize/, FAIT)          (FAIT, câblé)
```

## Étage 1 — FAIT : refactor local + convention de nommage

`_USD_apply_overrides` (conversions specular/IOR) et `_USD_connect_operator`
(connexion des opérateurs de blend) ont été refactorisées avec un
comportement identique, corrections mineures (ligne morte, division par
zéro). **`_USD_apply_overrides` et ses helpers ont depuis été supprimés** —
voir étage 2/3, remplacés par `normalize_specular_ior`.

**Convention de nommage étendue à tout le module** : `export_basic_execute()`
est le **seul** point d'entrée appelé depuis l'extérieur du module (par
`ExportShaderTree.py`). Toutes les autres fonctions sont préfixées `_` +
domaine : `_USD_*`, `_XML_*`, `_JSON_*`, `_UTIL_*`, `_DEBUG_diag` (voir
"Logging" plus bas), ou juste `_` pour `_initialize_preferences`.

## Étage 2 — FAIT : module de normalisation

`Scripts/python_modules/normalize/` contient 4 passes pures, `Element ->
Element`, zéro dépendance `lx`/`modo`/`fnpxr`, testées avec pytest
(`tests/normalize/`, 72 tests) :

- **`normalize_specular_ior`** — ajoute un attribut `usdValue` sur **tous**
  les canaux de chaque `advancedMaterial` : valeur corrigée gtr/principled
  quand une règle s'applique (specAmt/refIndex/disperse/tranRough/specCol/
  sheenTint), copie brute de `value` sinon. `value` (brut) n'est jamais
  modifié. **Important** : le shader glPreview (UsdPreviewSurface) lit aussi
  `usdValue`, pas `value` — il modélise specular/IOR de la même façon que les
  BRDF mtlx, donc il a besoin de la même valeur corrigée, pas de la valeur
  Modo brute (décision validée par l'auteur, contre-intuitive au premier
  abord).
- **`normalize_blend_operators`** — résout `channels/blend` en `usdOperator`
  (nom de nœud USD/MaterialX). Les 15 valeurs de blend Modo
  (`lx.symbol.sICVAL_TEXTURELAYER_BLEND_*`) sont dupliquées en littéraux
  (obtenues en interrogeant une instance Modo réelle, puisque
  `ShaderFilters.usdInputMap["blend"]` a ses clés indexées par ces symboles
  `lx`). `usdMixPattern` (dual/single) a été ajouté puis **retiré** : c'est
  dérivable à la volée depuis `node_registry.py` (présence d'un input
  `'mix'`), pas besoin de le dupliquer.
- **`normalize_projection_defaults`** — résout `txtrLocator/channels/projType`
  en `usdProjType` (toujours `"uv"` ou `"triplanar"`, fallback vers `"uv"`
  pour tout le reste).
- **`normalize_effect_channel_names`** — résout `channels/effect` en
  `usdInputName` (table dupliquée depuis `ShaderFilters.usdInputMap['effect']`
  — clés en chaînes brutes, pas de dépendance `lx`).

Toutes les passes sont **non-destructives** (retournent une copie) et
n'écrivent que des attributs en plus (`usd*`), jamais en place sur `value`
(sauf `normalize_specular_ior` qui écrit `usdValue`, un attribut séparé —
`value` reste toujours intact).

**`Scripts/python_modules/normalize/node_registry.py`** : catalogue statique
des ~60 nœuds USD/MaterialX réellement utilisés dans `ShaderTree.py` (inputs
nommés + types + type de sortie), généré depuis la vraie librairie standard
MaterialX via `tools/generate_node_registry.py` (à relancer si un nouveau
`CreateIdAttr(...)` apparaît). A servi à **confirmer** que le découpage
multiply/divide (in1/in2) vs les 8 autres blends (fg/bg/mix) était correct.
**Pas branché à un mécanisme générique de reconnexion** — décision prise en
session : le rester tant qu'aucun nouveau nœud ne casse le découpage actuel
codé en dur dans `_USD_connect_operator`. Pas la peine de généraliser dans
l'abstrait sans cas concret.

## Étage 3 — FAIT : câblage dans la construction USD réelle

Les 4 passes sont branchées. `export_basic_execute()` calcule
`xml_shadertree_normalized = normalize_shadertree(xml_shadertree)`
(inconditionnellement, plus seulement pour la comparaison XML), et
`_USD_write_file`/`_USD_export_shadertree` ne travaillent plus qu'avec **ce
seul arbre normalisé** — pas de double arbre threadé en parallèle : les
passes écrivent des attributs en plus, jamais de suppression, donc un seul
arbre suffit pour servir mtlx (lit `usdValue`/`usdOperator`/etc.) et
glPreview (lit `value` brut, sauf pour specular/IOR — voir plus haut) à la
fois.

`_USD_apply_overrides` et ses 3 helpers (`_ior_from_spec_amt`,
`_saturating_curve`, `_tinted_spec_color`) ont été **supprimés** de
`ShaderTree.py` — code mort une fois `normalize_specular_ior` branché.
`usdInputMap["blend"]`/`usdInputMap['effect']` ne sont plus consultés à la
construction (seul `usdInputMap['uvTile']` reste utilisé, non couvert par une
passe).

Pour porter `usdInputName` jusqu'à `_USD_connect_effect_stack`/
`_USD_connect_texture_output_to_shader_input` (qui ne voient que la clé
`effectName`, pas l'élément XML), un nouveau `ShadingContext.effectUsdInputNames`
(dict `effectName -> usdInputName`) a été ajouté, rempli dans
`_USD_add_shader_connector_to_context`.

`shaderConnector.blend` a été renommé `modoBlendOperator` (pendant Modo de
`usdOperator`) — encore utilisé pour le diagnostic "non supporté" (où
`usdOperator` est justement vide) et pour la comparaison `lx.symbol` qui
choisit le câblage dual/single dans `_USD_connect_operator`.

**Validé dans Modo sur le fichier d'exemple "PF_ShaderBall_base"** : topologie
du nodegraph et valeurs des paramètres confirmées correctes, après les
corrections ci-dessous.

### Bugs trouvés et corrigés pendant les tests Modo

Tous pré-existants ou introduits par le câblage lui-même, pas des régressions
sur du code qui marchait avant — révélés par le test réel, impossible à
détecter par pytest seul :

1. **`ND_normalmap` → `ND_normalmap_float`** : id de nœud MaterialX invalide
   (trouvé en croisant tous les `CreateIdAttr(...)` avec `node_registry.py`).
2. **`reload_modules()` ne rechargeait pas `normalize/`** : corrigé (voir
   "Environnement de dev").
3. **Fuite de contexte entre masks** (le plus significatif) : dans
   `_USD_export_shadertree`, `context.material`/`shader`/`previewShader`
   n'étaient jamais restaurés après le traitement d'un `<mask>`. Un
   `advancedMaterial` "nu" (sans mask, ex. un matériau de fallback) traité
   juste après un mask frère héritait du `context.material` du mask
   précédent au lieu d'être ignoré (`if context.material is None: return
   context` ne couvrait que le tout premier passage) — il écrasait alors la
   connexion `mtlx:surface` du mask. Corrigé par sauvegarde/restauration de
   ces 3 champs autour du traitement d'un mask (pas juste un reset à `None`,
   pour rester correct avec des masks imbriqués sans `ptag`). Comportement
   validé par l'auteur : un `advancedMaterial` hors mask doit être **ignoré**
   (pas de matériau de fallback implémenté — ce serait une nouvelle
   fonctionnalité, pas ce bug-ci).
4. **`_USD_apply_overrides` n'appliquait aucun override si `brdfType` était
   absent** d'un `advancedMaterial` (retour anticipé qui sautait aussi le
   fallback "copie la valeur brute"), laissant `usdValue` à `None` et
   plantant `_USD_create_shader_input` (`float(None)`). Corrigé : le calcul
   des overrides est isolé dans `_compute_overrides()`, et la boucle qui pose
   `usdValue` sur chaque canal s'exécute toujours, indépendamment de ce que
   `_compute_overrides` a pu résoudre.
5. **`export_usdz` retiré** : préférence jamais reliée à une vraie
   génération de `.usdz` (zip), sans UI, et référencée dans
   `export_basic_execute()` sans jamais être assignée dans
   `_initialize_preferences()` (`NameError` latent si `.usd`/`.usda` étaient
   tous deux désactivés). Si un vrai export `.usdz` est voulu un jour :
   partir de `_UTIL_copy_and_clean_files()` qui gère déjà la consolidation
   des textures.
6. **Bug de variable dans `_UTIL_copy_and_clean_files()`** : le message
   diagnostic "moved to unused" référençait `newPath` (fuite d'une boucle
   précédente) au lieu de `old_file`.

## Shader glPreview (`UsdPreviewSurface`) — FAIT partiellement (2026-08-07)

`exportGlPreviewMaterial` ne fonctionnait pas du tout avant cette session.
Quatre bugs réels trouvés et corrigés (indépendants du câblage étage 2/3
ci-dessus) :

1. `stdMatChannelMap[...]['glPreview']['stencil']` mappait vers
   `"opacityThreshold"`, absent de `usdTypeMap` → crash quasi garanti
   (`stencil` existe sur tout `advancedMaterial`). Entrée ajoutée.
2. `_USD_connect_texture_output_to_shader_input` ne connectait
   `previewShader` que pour les effets `bump`/`normal` (deux blocs codés en
   dur) — tous les autres canaux texturés (couleur diffuse, roughness,
   spéculaire, métallique, émission) n'atteignaient jamais le preview.
   `normalize_effect_channel_names` résout maintenant aussi
   `usdPreviewInputName` par effet (table reprise de
   `usdInputMap['effect_gl']`, qui était du code mort), portée par
   `context.effectPreviewInputNames` jusqu'au point de connexion générique.
3. `specAmt`/`luminousAmt` étaient mappés vers `"specular"`/`"emissive"` —
   des inputs qui **n'existent pas** sur `UsdPreviewSurface` (vérifié via
   `Sdr.Registry().GetShaderNodeByName('UsdPreviewSurface').GetShaderInputNames()`).
   `normalize_specular_ior` pondère maintenant `specCol`/`luminousCol` par
   ces intensités dans un nouvel attribut `usdPreviewValue` (glPreview
   uniquement ; le shader mtlx continue à lire `usdValue`).
4. Structure du fichier (connexion `outputs:surface` universel → shader
   `UsdPreviewSurface`) **vérifiée correcte via l'API USD réelle**
   (`UsdShade.Material.ComputeSurfaceSource()`, testé avec `usd-core` dans
   `.venv` sur un vrai bloc `Material` exporté) — donc pas juste une
   relecture de texte.

**Décision prise en session** : l'`info:id` reste `"UsdPreviewSurface"`
(schéma canonique, output `surface`) plutôt que le nœud MaterialX-wrappé
`ND_UsdPreviewSurface_surfaceshader`/`out` que Houdini authore lui-même —
essayé puis abandonné, motivé uniquement par l'espoir (non confirmé) que ça
le ferait apparaître dans l'éditeur de graphe de matériaux de Houdini,
objectif finalement jugé hors scope.

### Limite connue, acceptée pour l'instant

Les matériaux **texturés** apparaissent blancs dans le viewport (Houdini/
Storm/OpenGL) : `UsdPreviewSurface` et les moteurs de preview temps réel ne
savent lire les textures qu'à travers une famille de nœuds USD natifs
spécifique — `UsdUVTexture`, `UsdPrimvarReader_float2`, `UsdTransform2d`
(vérifiés présents dans `Sdr.Registry()`) — **pas** les nœuds MaterialX
(`ND_image_color3`, `ND_mix`...) utilisés par le graphe mtlx existant. Les
matériaux à valeurs constantes (sans texture) sont corrects, puisqu'aucune
lecture de nœud n'est nécessaire pour eux.

Corriger ça proprement demanderait de construire un **second réseau de
lecture de texture, en parallèle du graphe mtlx**, dédié au preview
(`UsdPrimvarReader_float2` → `UsdTransform2d` → `UsdUVTexture`) — un
chantier de la taille d'une nouvelle étape de construction, pas un simple
ajustement de mapping. Décision explicite de l'auteur : accepter la limite
pour l'instant plutôt que de s'y attaquer maintenant.

## Logging — FAIT : consolidé dans `_DEBUG_diag()`

`_diag` a été renommé `_DEBUG_diag` et généralisé : chaque appel imprime
maintenant lui-même sur la console (si `verbose and verbose_modify_tree`)
**et** enregistre dans le XML diagnostic (si `export_diagnostic`) — un seul
appel par site au lieu d'un `if verbose: print(...)` + un appel `_DEBUG_diag`
séparés partout.

Les 5 sous-flags devenus inutiles une fois ce gate unique en place
(`verboseSetValue`, `verboseCreateShader`, `verboseOverrideValue`,
`verboseConsolidate`, `verboseUnsupported`) ont été **retirés entièrement** :
globals Python, `_initialize_preferences()`, défauts dans
`ExportShaderTree.py`, cases à cocher dans `Configs/preferences.CFG`. Ne
restent que `verbose` et `verboseModifyTree`.

Tous les `print()` redondants avec `_DEBUG_diag` ont été supprimés (~30
sites), y compris des traces de debug brutes sans aucun pendant diag
(`shaderConnector.dump()`, les traces dans `_USD_connect_effect_stack`/
`_USD_connect_texture_output_to_shader_input`) — l'auteur a choisi de tout
nettoyer plutôt que de garder du code mort, quitte à réintroduire des prints
ciblés si un futur bug l'exige.

### Décisions encore ouvertes

1. **Vocabulaire canonique** : de facto tranché par la pratique — les 4
   passes gardent les noms Modo et ajoutent des attributs `usd*` en plus,
   jamais de renommage. Pas de validation formelle écrite ailleurs que ce
   fichier, mais c'est le pattern suivi partout maintenant.
2. **Où vivent les tables de `ShaderFilters.py`** : toujours ouvert
   structurellement. Les tables `blend`/`effect` restent dupliquées dans
   `normalize/` (risque de drift si `ShaderFilters.py` change) — à trancher
   si ça devient un problème réel, pas avant.
3. **Mécanisme générique de reconnexion (`node_registry.py`)** : volontairement
   pas construit — voir étage 2. Revisiter seulement si un nouveau nœud ne
   rentre plus dans le découpage dual/single actuel.
4. **Lookup inverse dans `_USD_connect_effect_stack`** (fallback "pas de
   texture connectée" → lit la valeur par défaut du matériau via
   `stdMatChannelMap[...]['principled']`) : lit encore `value` (brut), pas
   `usdValue`. Incohérence potentielle si ce fallback s'applique un jour à un
   canal concerné par les overrides specular/IOR (specAmt, refIndex...) —
   identifiée mais **pas corrigée**, laissée pour plus tard.

## Exécution/tests hors Modo

- `pytest` installé dans `.venv`, lancer avec `.venv/bin/python3 -m pytest`
  (config dans `pytest.ini` à la racine, `pythonpath = Scripts`).
  `tests/normalize/` : 72 tests couvrant les 4 passes + le registre de
  nœuds. Zéro dépendance Modo.
- **Étage 3 (construction USD)** : toujours pas testable hors Modo (pas de
  shim `fnpxr`/`UsdMtlx` mis en place) — validation faite manuellement dans
  Modo à chaque étape de câblage.
- **Étage 1 (extraction Modo)** reste dépendant de l'interpréteur embarqué de
  Modo. Debug interactif : `debugpy.listen()` côté Modo + "Python Debugger:
  Remote Attach" côté VS Code.

## Export MaterialX natif (`.mtlx`) — exploré, abandonné (2026-08-07)

Idée envisagée : ajouter une sortie `.mtlx` natif (XML, lisible par d'autres
DCC comme Blender, indépendamment de l'USD). Investigation faite directement
dans la console Python de Modo :

- **`UsdMtlx` (via `fnpxr`) inutilisable pour ça** : le `plugInfo.json` du
  plugin `UsdMtlxFileFormat` déclare explicitement `"supportsWriting": false`
  — ce n'est pas une limite Foundry, c'est une limite générale du format côté
  USD (support à l'écriture resté incomplet en amont). Le binding Python
  (`_usdMtlx.so`) confirmé n'exposer que `_TestFile`/`_TestString` (des
  utilitaires internes pour la découverte de fichiers par Sdr/Ndr), aucune
  API de lecture/écriture de document MaterialX.
- **Le paquet `MaterialX` autonome** (celui utilisé en dev pour générer
  `node_registry.py`) **n'est pas installé** dans le Python embarqué de Modo
  (`ModuleNotFoundError`). L'installer soi-même dans le Python de Modo serait
  possible pour un usage personnel, mais ce kit est **destiné à être
  distribué** à d'autres utilisateurs Modo — leur imposer d'installer un
  paquet Python tiers (avec du code compilé, donc pas vendorable simplement
  pour toutes les plateformes) dans leur Modo n'est pas réaliste.
- Seule voie restante identifiée : écrire le XML `.mtlx` à la main avec
  `ElementTree` (zéro dépendance), en réutilisant le XML déjà normalisé
  (`usdValue`/`usdOperator`/etc.) et `node_registry.py`. Jugé disproportionné
  par rapport au besoin actuel — **abandonné**, pas de code touché.

Si l'idée revient un jour : ne pas re-tester `UsdMtlx`/`MaterialX` dans Modo,
c'est déjà tranché ci-dessus. La question à se reposer est plutôt "est-ce que
l'effort d'un sérialiseur `.mtlx` maison vaut le besoin réel à ce moment-là".

## Prochaines étapes possibles

0. **PRIORITAIRE** : réseau de lecture de texture dédié au preview
   (`UsdUVTexture`/`UsdPrimvarReader_float2`/`UsdTransform2d`), pour que les
   matériaux texturés ne soient plus blancs dans le viewport — voir "Shader
   glPreview" ci-dessus. Limite acceptée temporairement le 2026-08-07,
   l'auteur veut y revenir en priorité à la prochaine session.

Le reste, aucune urgence, à discuter avec l'auteur :

1. Trancher la décision n°2 (emplacement des tables `ShaderFilters.py`) si la
   duplication devient gênante.
2. Corriger le lookup inverse (décision n°4 ci-dessus) si un cas réel le
   révèle nécessaire.
3. Simplifier `_USD_export_shadertree` en vraie table de dispatch
   (`tag -> builder`) maintenant que toute la logique métier en est sortie —
   refactor mécanique à faible risque, pas encore fait faute de nécessité
   immédiate.
4. Mécanisme générique de reconnexion via `node_registry.py`, si un nouveau
   nœud USD l'exige un jour.
5. ~~Mettre à jour `build_lpk.py`~~ — **FAIT le 2026-08-08** :
   `ignorepath`/`ignorefiles` excluent maintenant `.venv`, `__pycache__`,
   `.pytest_cache`, `tests`, `.claude`, `normalize/tools` (outil de dev
   dépendant de `MaterialX`), `pytest.ini`, `CLAUDE.md`, `.code-workspace`.
   Vérifié en dry-run (3085 → 18 fichiers) puis en conditions réelles
   (`.lpk` de 54 Ko généré, `index.xml` régénéré correctement). Corrigé au
   passage : `index.xml` était dupliqué dans l'archive.

Ne pas réintroduire de logique de cas particulier dans la construction USD —
c'est précisément ce que cette refonte cherchait à éviter.
