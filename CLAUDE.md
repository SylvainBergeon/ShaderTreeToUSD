# Contexte projet — ShaderTreeToUSD

Ce fichier résume les décisions prises lors d'une session de conception (hors
Claude Code, sur claude.ai) portant sur la refonte de la complexité du plugin,
puis le travail effectué dans Claude Code pour la mettre en œuvre. Il sert de
point de reprise : lis-le avant de proposer des changements pour rester
cohérent avec la direction déjà validée par l'auteur du projet.

**Dernière mise à jour : 2026-08-09. Les 3 étages du pipeline sont câblés de
bout en bout et validés dans Modo (voir plus bas).**

**Contexte important (2026-08-08, fin de session)** : dans le setup de
l'auteur, **le viewport GL de Houdini/Karma résout le graphe mtlx
directement** ("Material_5"/`outputs:mtlx:surface`, le shader de rendu
réel) au moins quand le réseau `UsdPreviewSurface` séparé
("Material_5_preview"/`outputs:surface`) n'apporte rien de plus — voir
"Shader glPreview" plus bas.

Round 4 (graphe mtlx, **CONFIRMÉ VISUELLEMENT dans Houdini/Karma**) : plus
de chaîne `UsdPrimvarReader_float2`→`UsdTransform2d` pour lire les UV —
l'input `"texcoord"` du nœud image est laissé non connecté, Karma résolvant
ça lui-même vers le UV set par défaut. `_USD_create_UV_texture_transform`
supprimée. Texture affichée, tuilage et offset corrects (branche
`ND_tiledimage`, wrap repeat). **Compromis toujours en place, pas testé** :
`uvRotation` n'est plus porté par rien côté mtlx, et pour la branche
`ND_image` (wrap edge/mirror/reset) `wrapU`/`wrapV`/`m02`/`m12` sont aussi
ignorés.

Round 5 (réseau glPreview, **CONFIRMÉ DANS HOUDINI**) : même simplification
appliquée à `_USD_create_preview_*` (`UsdUVTexture.inputs:st` laissé non
connecté). Rendu et preview connectés tous les deux, graphe propre dans
l'éditeur de matériau de Houdini — le risque signalé (défaut littéral
`(0,0)` de `UsdUVTexture.inputs:st`) ne s'est pas matérialisé en pratique.

Round 6 (tentative de fix `ND_minus`/blend modes façon Photoshop, **ESSAYÉE
PUIS RÉ-INVERSÉE, EXPLICATION TROUVÉE**) : différence de rendu Modo/Karma
sur "Subtract" ayant motivé un échange fg/bg dans `_USD_connect_operator`
pour `ND_minus` et 6 autres opérateurs — l'auteur est revenu dessus le
2026-08-09 ("probablement faux"), `_USD_connect_operator` est repassé à la
convention d'origine (non échangée) partout, **et c'était la bonne
décision** : la vraie cause de la différence de rendu était le bug de
pivot de tuilage du Round 8 (texture damier utilisée pour le test — un
mauvais pivot de tuilage combiné à "Subtract" produit un résultat très
différent d'un pivot correct). Rien à faire ici, l'inversion fg/bg reste
non pertinente.

Round 7 (colorspace des textures, **CONFIRMÉ CORRECT DANS HOUDINI, GARDER
TEL QUEL**) : `"(default)"` Modo **ne signifie PAS** "aucune
transformation" (hypothèse initiale, infirmée) — il résout vers l'une de 4
préférences Modo (`Preferences > Color Management`, une par catégorie de
profondeur de bits) interrogées en live et confirmées par l'auteur :
8bit/16bit/numeric → `sRGB`, float → `linear`, sur son installation.
Résolution (heuristique format→profondeur de bits + lookup) entièrement
dans `normalize/colorspace.py`, préférences passées en paramètre depuis
Stage 1 (`_initialize_colormanagement_defaults`, dans Modo — seule partie
qui ne peut pas bouger, c'est un appel `lx.eval()`). Toute valeur
`!= "(default)"` reste passée telle quelle (colorspace Modo piloté par
OCIO, pas un petit enum comme les wrap/blend modes). Câblé en métadonnée
`colorSpace` libre **et** sur l'enum restreint `sourceColorSpace`
(`raw`/`sRGB`/`auto`), à la fois côté mtlx et côté glPreview (ceinture et
bretelles). **Confirmé par l'auteur (2026-08-09)** : la différence de
rendu perçue comme "colorspace" a disparu une fois le pivot de tuilage du
Round 8 corrigé — c'était le même symptôme que le Round 6, pas un bug de
colorspace. **Décision de l'auteur : ne plus toucher à ce système, il
fonctionne correctement et pourra servir dans d'autres cas.**

Round 8 (bug réel, pivot de tuilage `ND_tiledimage`, **CONFIRMÉ CORRIGÉ
DANS HOUDINI**, 2026-08-09) : l'UV map n'était pas alignée pareil entre
Modo et Houdini dès que `wrapU`/`wrapV` ≠ 1. Vérifié dans le vrai source
MaterialX (`NG_tiledimage_*`, pas juste le nodedef) : `ND_tiledimage` tuile
depuis l'origine `(0,0)`, pas depuis le centre `(0.5,0.5)` comme Modo.
Corrigé en injectant un terme compensatoire `0.5*(uvtiling-1)` dans
`uvoffset` — se réduit exactement à l'ancien comportement quand
`uvtiling=(1,1)`, donc pas de régression pour ce cas. **Confirmé par
l'auteur : les UV maps sont maintenant correctement alignées entre Modo
et Houdini**, et ce même bug explique aussi la différence de "couleur"
signalée en même temps (voir Round 6/7 ci-dessus) — un seul bug, pas deux.

Round 9 (sélection de l'UV map par couche, **SOLUTION VALIDÉE À LA MAIN
DANS HOUDINI, PAS ENCORE RECONFIRMÉE VIA UN EXPORT**, 2026-08-09) : un mesh
peut avoir plusieurs UV maps dans Modo, nommées par chaîne (`"Texture"`,
`"texture2"`, ...) et choisies par couche de texture via
`txtrLocator/channels/uvMap` — déjà extrait en XML mais jamais lu par la
construction USD (le Round 4 laissait `"texcoord"` systématiquement non
connecté). Confirmé par l'auteur : la géométrie arrive dans Houdini via
Alembic, où les UV maps Modo deviennent des primvars nommés à l'identique
— **pas d'indirection par index**, contrairement à l'hypothèse initiale de
l'auteur (`ND_texcoord_vector2`/`"index"`, déjà écarté au Round 3 pour
cette même raison). Premier essai avec `UsdPrimvarReader_float2` (nœud
natif USD/Hydra, pas un vrai nœud MaterialX) — ne se résolvait pas comme
source d'UV dans le graphe mtlx compilé, corrigé par l'auteur (testé à la
main dans Houdini) vers `ND_geompropvalue_vector2`, le mécanisme MaterialX
natif pour ça (`"geomprop"`/`"out"`, vérifié contre la vraie librairie
standard). Nouvelle fonction `_USD_create_UV_texcoord_reader`
(`ShaderTree.py`) : construit ce nœud et connecte son `outputs:out` sur
`"texcoord"` quand `uvMap` est renseigné ; retourne `None` (donc
`"texcoord"` reste non connecté, comportement du Round 4 inchangé) quand
`uvMap` est vide — le cas le plus courant, une couche qui utilise
simplement l'UV set par défaut du mesh. Vérifié structurellement contre
`usd-core`. Portée volontairement limitée au graphe mtlx (le sujet du
jour) — le réseau glPreview n'a pas été retouché.

**PRIORITAIRE pour la prochaine session** : re-exporter depuis Modo et
confirmer dans Houdini que `rainbowh_Image_2` (`Shaderball_Material`, la
seule couche du fichier de test utilisant une UV map non-défaut,
`"texture2"`) lit maintenant la bonne UV map via le code (la solution
elle-même est déjà validée à la main, reste à confirmer que le code généré
correspond). Décider si le compromis
rotation/scale/offset du Round 4 (`ND_image`, wrap edge/mirror/reset, et
`uvRotation` dans tous les cas — toujours non porté par rien côté mtlx)
est acceptable tel quel, ou s'il faut lui appliquer le même genre de
correction que le Round 8. Rester vigilant sur bump/normal/`<constant>`,
toujours non exercés par le fichier de test "PF_ShaderBall_base".

## Le projet

Kit Modo qui exporte un shader tree Modo vers USD/MaterialX, pour être
réimporté dans Houdini (Karma). Point d'entrée : `Scripts/lxserv/ExportShaderTree.py`
(commande Modo `exportShaderTree`), qui délègue à
`Scripts/python_modules/ShaderTree.py` (le cœur du système) et le package
`Scripts/python_modules/ShaderFilters/` (tables de correspondance
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
  commande dans Modo -> `ShaderTree.py`, et **les packages
  `Scripts/python_modules/normalize/` et `Scripts/python_modules/ShaderFilters/`**
  (sous-modules explicitement listés + le package lui-même, pour chacun)
  sont rechargés à chaud depuis le disque. Seul `ExportShaderTree.py`
  lui-même nécessite un restart de Modo si modifié (piège vécu en session :
  un fix dans ce fichier n'était pas actif tant que Modo n'avait pas
  redémarré, alors que tout le reste rechargeait bien — et le même piège se
  reproduit à chaque fois qu'un module simple devient un package : `reload()`
  ne redescend pas automatiquement dans ses sous-modules, il faut les lister
  à la main dans `NORMALIZE_MODULES`/`SHADERFILTERS_MODULES`). **Autre variante
  du même piège, trouvée le 2026-08-08 en testant le réseau de lecture de
  texture glPreview dans Modo** : `python_modules.normalize.uv_wrap_modes`
  n'a jamais été ajouté à `NORMALIZE_MODULES` depuis sa création (oubli, pas
  une histoire de module devenu package) — Modo tournait donc avec une copie
  figée de ce fichier depuis son lancement, plantant sur
  `Sdf.ValueTypeNames.Token.Set(None)` (`usdNativeWrapMode` absent de la
  copie chargée) dès que le nouveau code glPreview essayait de le lire.
  Corrigé (ajouté à la liste) — **nécessite, comme toujours pour
  `ExportShaderTree.py`, un restart de Modo pour prendre effet**. À garder en
  tête : si un futur ajout de submodule `normalize/`/`ShaderFilters/` casse
  encore une fois de cette façon, vérifier `NORMALIZE_MODULES`/
  `SHADERFILTERS_MODULES` en premier.
- `.vscode/settings.json` configure l'analyse statique (stubs `lx`/`modo`,
  `extraPaths` vers le Python de Modo, résolution `pxr`). Ça ne permet pas
  d'exécuter le code Modo-dépendant, juste de l'éditer avec autocomplétion.
- **`.venv/` est un vrai environnement de dev/test** : `pytest` (pour
  `Scripts/python_modules/normalize/`, zéro dépendance Modo) et `MaterialX`
  (paquet PyPI officiel, utilisé uniquement par
  `Scripts/python_modules/normalize/tools/generate_node_registry.py` pour
  interroger la vraie librairie standard MaterialX) y sont installés. `lx`/
  `modo`/`fnpxr` restent absents — impossible d'exécuter le code Modo-
  dépendant (`ShaderTree.py`, `ShaderFilters/`, `ExportShaderTree.py`) hors
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

**Décision prise en session (2026-08-07)** : l'`info:id` reste
`"UsdPreviewSurface"` (schéma canonique, output `surface`) plutôt que le
nœud MaterialX-wrappé `ND_UsdPreviewSurface_surfaceshader`/`out` que
Houdini authore lui-même — essayé puis abandonné, motivé uniquement par
l'espoir (non confirmé) que ça le ferait apparaître dans l'éditeur de
graphe de matériaux de Houdini, objectif finalement jugé hors scope.

### Réseau de lecture de texture natif — IMPLÉMENTÉ le 2026-08-08, GRAPHE USD VÉRIFIÉ, RENDU VISUEL PAS ENCORE CONFIRMÉ

**État de la validation (2026-08-08, sur l'export réel "PF_ShaderBall_base")** :
export sans erreur après ajout de `uv_wrap_modes` à `NORMALIZE_MODULES` (voir
"Environnement de dev" — c'était le seul bug, pas dans le code glPreview
lui-même) et restart de Modo. Le `.usda` produit a été relu intégralement et
correspond exactement à ce qui est décrit ci-dessous : `UsdPrimvarReader_
float2`→`UsdTransform2d`→`UsdUVTexture` connecté directement à `diffuseColor`/
`emissiveColor` (pas le graphe mtlx), `ND_tiledimage`+`uvtiling` pour les
textures en mode "repeat" (y compris une avec `wrapU`/`wrapV`=(2,2), tuilage
confirmé correct), `ND_image`+`uaddressmode`/`vaddressmode="clamp"` pour une
texture en mode "edge", "dernière couche gagne" confirmé sur un effet à deux
couches empilées (`Shaderball_Material`), `tranAmount` (sans équivalent
preview) correctement sans aucune connexion preview. **Reste à faire** :
confirmer visuellement dans Storm/Houdini que ça rend correctement (relire un
graphe n'est pas pareil que le voir rendu), et tester un fichier avec
bump/normal et/ou `<constant>` — absents de "PF_ShaderBall_base", donc ces
deux chemins de code n'ont encore jamais tourné.

Cause du problème (diagnostiquée le 2026-08-07, corrigée le 2026-08-08) :
`UsdPreviewSurface` et les moteurs de preview temps réel (Storm/Houdini) ne
savent lire les textures qu'à travers une famille de nœuds USD natifs figée
— `UsdUVTexture`, `UsdPrimvarReader_float2`, `UsdTransform2d` — **pas** les
nœuds MaterialX (`ND_image_color3`, `ND_mix`, `ND_constant_*`...) du graphe
mtlx existant. Avant cette session, `previewShader` était connecté
directement à la sortie du graphe mtlx (`output`) pour quasiment tous les
effets (bump/normal exceptés, câblés à part) — d'où le blanc.

Un second réseau, natif et parallèle au graphe mtlx, a été ajouté dans
`ShaderTree.py` :

- `_USD_create_preview_UV_texture_transform` — `UsdPrimvarReader_float2`
  (`varname="st"`) → `UsdTransform2d`, mêmes scale/translation/rotation que
  la version mtlx (`_USD_create_UV_texture_transform`).
- `_USD_create_preview_UV_texture` — `UsdUVTexture` lisant le même fichier
  que la version mtlx. Approxime `invert`/`brightness` via les inputs
  natifs `scale`/`bias` de `UsdUVTexture` (`valeur*scale+bias`, vérifié
  contre `usd-core`/`shaderDefs.usda` réel). Pour un effet `bump`/`normal`,
  combine ça avec le déballage normal-map standard
  (`scale=(2,2,2,1)`/`bias=(-1,-1,-1,0)`, `sourceColorSpace="raw"` —
  convention documentée dans le doc `inputs:normal` d'`UsdPreviewSurface`
  lui-même). Sélectionne le bon port de sortie (`r`/`g`/`b`/`a`/`rgb`)
  selon `channels/alpha`/`channels/swizzling`/`channels/rgba` — c'est ce
  qui rend la connexion type-correcte, pas juste une amélioration
  cosmétique. `contrast` et le remap min/max n'ont pas d'équivalent natif
  et ne sont pas appliqués côté preview (le mtlx garde sa pleine fidélité).
- `_USD_create_preview_texture_output` — orchestre les deux ci-dessus.
  Retourne `None` (aucune connexion preview créée) pour une projection
  triplanaire (pas d'équivalent natif) ou l'absence de fichier texture.
- `ShadingContext.previewOutputs` (nouveau champ, `effectName -> 
  UsdShade.Output | valeur littérale`) — rempli depuis les branches
  `imageMap` et `constant` de `_USD_export_shadertree`, reset à chaque
  mask. "Dernière couche gagne" pour un effet empilé sur plusieurs
  couches : Storm ne sait pas non plus évaluer le graphe de blend mtlx, une
  vraie fusion multi-couches côté preview n'est donc pas représentable.
  `_USD_connect_texture_output_to_shader_input` lit ce dict (au lieu de
  connecter aveuglément `output`, le graphe mtlx) pour câbler
  `previewShader` ; s'il n'y a pas d'entrée pour l'effet, l'input du
  preview garde sa valeur littérale déjà posée par
  `_USD_create_mtlx_standard_surface_shader` — au pire inchangé, jamais
  pire qu'avant.
- `effect_channel_names.py` : `"bump"` ajouté à
  `USD_PREVIEW_INPUT_NAME_BY_EFFECT` (pointe vers le même input `normal`
  qu'`"normal"`) — bump et normal passent maintenant tous les deux par le
  même mécanisme générique, plus de câblage spécifique par effet dans
  `_USD_connect_texture_output_to_shader_input`.
- `uv_wrap_modes.py` : nouvel attribut `usdNativeWrapMode` (table
  `USD_NATIVE_WRAP_MODE_BY_TILE`), distinct de `usdWrapMode` (mtlx) car le
  wrap "repeat" Modo se traduit par `"periodic"` côté MaterialX mais
  `"repeat"` côté schéma natif `UsdUVTexture.wrapS/wrapT` — vérifié contre
  `shaderDefs.usda` réel, pas une supposition.

**Deux bugs (préexistants, pas des régressions de cette session) trouvés en
vérifiant les types/inputs contre le vrai schéma USD
(`.venv/lib/.../pxr/pluginfo/usdShaders/resources/shaders/shaderDefs.usda`,
livré avec `usd-core`) et corrigés au passage :**

1. **`lumiAmount` pointait vers un input `"emissive"` qui n'existe pas sur
   `UsdPreviewSurface`** (seul `emissiveColor`, `color3f`, existe — pas
   d'input scalaire d'intensité émissive séparé). Retiré de
   `USD_PREVIEW_INPUT_NAME_BY_EFFECT` (aucun équivalent natif sans un nœud
   de multiplication, indisponible dans le catalogue figé de Storm — même
   famille de limite que `contrast`/remap min-max).
2. **`_USD_create_constant` ne posait jamais la valeur du nœud
   `ND_constant_*`** (input `"value"` jamais créé) — une couche `<constant>`
   (couleur plate, sans image) était donc déjà cassée côté mtlx, pas
   seulement côté preview. Corrigé en lisant `channels/value` (supposé,
   **non vérifié en Modo** — voir ci-dessous) et en le posant sur le nœud ;
   la même valeur est aussi utilisée directement (sans nœud) pour le
   preview.

### Point à vérifier en priorité dans Modo

Le nom exact du canal XML portant la couleur d'une couche `<constant>` est
une supposition (`channels/value`, par analogie avec `channels/value1`/
`value2` de `<noise>`) — il n'y a pas de fichier XML d'exemple dans le repo
pour le confirmer, et Modo n'est pas accessible depuis cet environnement. Si
le nom réel diffère, `_USD_create_constant` lèvera une erreur
(`xml.find(...)` retournera `None`) à l'export d'une couche `<constant>` —
facile à repérer et corriger une fois testé dans Modo.

### `ND_tiledimage` côté mtlx — IMPLÉMENTÉ le 2026-08-08, GRAPHE USD VÉRIFIÉ, RENDU VISUEL PAS ENCORE CONFIRMÉ

Observation de l'auteur en cours de session, faite dans Houdini : quand le
graphe mtlx utilise `ND_tiledimage` plutôt que `ND_image` pour lire une
texture, Houdini génère lui-même un shader de preview correct **sans**
avoir besoin du réseau natif documenté ci-dessus. Décision de l'auteur :
garder le réseau natif quand même (utile pour d'autres moteurs/cas d'usage
qui ne bénéficient pas de cette résolution automatique de Houdini), mais
basculer aussi le graphe mtlx sur `ND_tiledimage` pour en profiter.

En creusant les vrais inputs de `ND_tiledimage` (requête directe contre le
paquet `MaterialX` standalone dans `.venv`, comme pour `node_registry.py` —
`uvtiling`/`uvoffset`/`realworldimagesize`/`realworldtilesize`/`texcoord`/
`file`, **pas** de `wrapS`/`wrapT` ni `uaddressmode`/`vaddressmode`), deux
choses ont été trouvées et corrigées dans `_USD_create_UV_texture`/
`_USD_create_UV_texture_transform` (`ShaderTree.py`) :

1. **Bug préexistant, indépendant de `ND_tiledimage`** : le vrai nom
   d'input MaterialX pour le wrap mode de `ND_image` est
   `uaddressmode`/`vaddressmode` (enum `constant`/`clamp`/`periodic`/
   `mirror`) — le code posait `wrapS`/`wrapT` (les noms natifs
   `UsdUVTexture`, utilisés à raison dans le réseau glPreview, mais jamais
   validés par MaterialX pour `ND_image`). USD n'empêche pas de créer un
   attribut sous un nom qui ne correspond à aucun input réel du nodedef —
   ça ne plante pas, ça ne fait juste rien. Autrement dit, le wrap mode
   configuré dans Modo (edge/mirror/reset) n'a probablement **jamais**
   atteint le rendu mtlx, toujours retombé silencieusement sur le défaut
   `ND_image` (`periodic`, répétition). `USD_WRAP_MODE_BY_TILE`
   (`normalize/uv_wrap_modes.py`) avait aussi la mauvaise valeur pour
   `"reset"` (`"black"`, un token natif qui n'existe pas dans l'enum
   MaterialX — corrigé en `"constant"`).
2. **`ND_tiledimage` n'a aucun input de wrap mode par axe** (c'est
   intrinsèquement un nœud de tuilage) — impossible d'y représenter
   edge/mirror/reset. `_USD_uses_mtlx_tiledimage(xml)` bascule donc entre
   les deux : `ND_tiledimage` (+ `uvtiling` = `wrapU`/`wrapV`) uniquement
   quand `tileU` **et** `tileV` valent `"repeat"` ; `ND_image` (+
   `uaddressmode`/`vaddressmode`, maintenant corrects) sinon.
   `_USD_create_UV_texture_transform` consulte la même fonction pour poser
   `scale=(1,1)` (tuilage géré par `uvtiling`) ou `scale=(wrapU,wrapV)`
   (comme avant, `ND_image` n'a pas de tuilage propre).

`tools/generate_node_registry.py`/`node_registry.py` mis à jour avec les 3
variantes `ND_tiledimage_{float,color3,color4}`.

#### Round 2, suite à un test réel dans Houdini/Karma (2026-08-08)

Découverte importante en testant "PF_ShaderBall_base" dans Houdini : **le
viewport GL/Karma de l'auteur résout en fait le graphe mtlx directement**
(probablement via la traduction MaterialX-vers-Hydra de Karma, qui sait
interpréter un graphe mtlx complet, pas seulement le catalogue figé
`UsdUVTexture`/`UsdPrimvarReader_float2`/`UsdTransform2d`) — pas
nécessairement le réseau natif glPreview séparé documenté plus haut. Deux
symptômes remontés en éditant le graphe mtlx à la main dans Houdini :

1. En déconnectant `..._streader` (`ND_texcoord_vector2`) et en forçant une
   valeur littérale sur `..._transform` (`UsdTransform2d`), la texture
   s'affichait — suggérant que la chaîne streader→transform ne se résolvait
   pas correctement dans la traduction MaterialX de Karma.
2. Une fois affichée, `wrapU`/`wrapV` étaient ignorés car `ND_image` n'a pas
   d'input de tuilage.

Le point 2 est exactement le chantier `ND_tiledimage` déjà en cours ci-dessus
— l'auteur a recommandé, et ça a été implémenté :
- `uvoffset` de `ND_tiledimage` posé depuis `m02`/`m12` (au lieu de les
  laisser sur `UsdTransform2d.translation`) — `_USD_create_UV_texture`
  (branche `ND_tiledimage`) et `_USD_create_UV_texture_transform` (qui pose
  `translation=(0,0)` dans ce cas). `ND_tiledimage` n'a pas d'input de
  rotation en revanche, donc `UsdTransform2d` continue de porter la
  rotation (`uvRotation`) dans tous les cas — ça répond au passage au
  "point à vérifier" noté dans une version précédente de cette section
  (l'ordre tuilage/translation/rotation n'est plus ambigu : rotation par
  `UsdTransform2d`, tuilage+offset par `ND_tiledimage`, dans cet ordre).

Pour le point 1, première hypothèse (partielle) : `ND_texcoord_vector2` a un
type de sortie MaterialX réel `vector2` (vérifié contre `node_registry.py`/la
vraie librairie standard), mais le code posait `TexCoord2f` (un type-rôle
USD/Hydra, pas un type MaterialX) sur toute la chaîne streader→transform.
Remplacé par `Float2` de bout en bout dans `_USD_create_UV_texture_transform`.
**Corrigé mais pas suffisant** — voir Round 3.

#### Round 3, cause racine du point 1 trouvée par l'auteur (2026-08-08)

En relisant le `.usda` régénéré après le Round 2, l'auteur a repéré que
`rainbowh_Image_streader` (`ND_texcoord_vector2`) **n'avait aucune sortie
exploitable** — le vrai problème n'était pas (seulement) le type `TexCoord2f`,
c'est le nœud lui-même : `ND_texcoord_vector2` prend un `index` (entier,
"le Nième UV set"), une convention purement MaterialX sans lien direct avec
un nom de primvar USD. La traduction MaterialX-vers-Hydra de Karma n'avait
rien pour résoudre "index 0" vers un primvar réel de la mesh, et ne
produisait donc rien.

Corrigé en remplaçant `ND_texcoord_vector2`("index"=0) par
`UsdPrimvarReader_float2`("varname"="st") dans `_USD_create_UV_texture_transform`
— exactement le nœud déjà utilisé (et qui fonctionnait) côté réseau natif
glPreview (`_USD_create_preview_UV_texture_transform`). Les délégués
MaterialX-vers-Hydra d'USD reconnaissent `UsdPrimvarReader_*` comme pont
explicite entre la géométrie et un graphe mtlx, ce qui contourne
l'ambiguïté de "index" entièrement. `ND_texcoord_vector2` n'est donc plus
utilisé nulle part dans `ShaderTree.py` — retiré de
`tools/generate_node_registry.py`/`node_registry.py` (qui catalogue les ids
réellement utilisés).

#### Round 4, décision de l'auteur : abandonner le chaînage texcoord côté mtlx — CONFIRMÉ DANS HOUDINI (2026-08-08)

Recentrage explicite de l'auteur en fin de session : **le réseau
`UsdPreviewSurface` (`Material_5_preview`) n'est plus ce qu'on teste** — dans
son setup, le viewport GL de Houdini/Karma résout le graphe mtlx directement
(`Material_5`/`outputs:mtlx:surface`), pas ce réseau séparé. `_USD_create_preview_*`
reste dans le code mais n'a plus été touché ce round.

Sur le graphe mtlx (le vrai sujet), demande explicite : ne plus construire
de chaîne `UsdPrimvarReader_float2`→`UsdTransform2d` du tout pour
`ND_standard_surface_surfaceshader` — laisser l'input `"texcoord"` du nœud
image (`ND_image`/`ND_tiledimage`) simplement non connecté. Karma résout ça
tout seul vers le UV set par défaut de la mesh, ce qui contourne le
problème (quel qu'il soit exactement) qui empêchait la chaîne explicite de
fonctionner même après le fix `UsdPrimvarReader_float2` du Round 3.

Implémenté : `_USD_create_texture_output` n'appelle plus de fonction de
transform pour la branche `uv` et passe `None` à `_USD_create_UV_texture`,
qui ne crée l'input `"texcoord"` que si une source est fournie.
`_USD_create_UV_texture_transform` est devenue morte et a été supprimée.
`_USD_create_preview_UV_texture_transform` (réseau glPreview, hors périmètre
ce round) n'a pas changé.

**Résultat confirmé par l'auteur dans Houdini/Karma, sur "PF_ShaderBall_base"
re-exporté** : la texture s'affiche, le tuilage est correct, l'offset est
correct, et Houdini/Karma infère le preview GL directement depuis ce même
graphe mtlx (pas besoin du réseau `UsdPreviewSurface` séparé) — cohérent
avec la clarification de périmètre en tête de fichier.

**Compromis, accepté implicitement par la demande, à garder en tête (pas
encore testé visuellement)** : plus aucun mécanisme ne porte `uvRotation`
côté mtlx (ni `UsdTransform2d` ni `ND_tiledimage`, qui n'a pas d'input
rotation) — une texture tournée dans Modo ne le sera probablement plus dans
le rendu Karma. Pour la branche `ND_image` (wrap edge/mirror/reset, pas de
tuilage `ND_tiledimage`), `wrapU`/`wrapV`/`m02`/`m12` sont aussi désormais
entièrement ignorés (`ND_image` n'a ni tuilage ni offset propres). Seule la
branche `ND_tiledimage` garde un positionnement correct (tuilage + offset
via ses inputs propres, indépendants de `"texcoord"`) — **et c'est
exactement cette branche qui a été validée ci-dessus** (wrap repeat, cas
`rainbowh_Image`). Le cas `ND_image`/rotation reste à tester.

#### Round 5, même simplification appliquée au réseau glPreview — CONFIRMÉ DANS HOUDINI (2026-08-08)

L'auteur réactive `exportGlPreviewMaterial` et demande d'appliquer la même
simplification que le Round 4 au réseau `UsdPreviewSurface` séparé (jusque
là non touché) : `_USD_create_preview_texture_output` ne construit plus de
chaîne `UsdPrimvarReader_float2`→`UsdTransform2d`, passe `None` à
`_USD_create_preview_UV_texture`, qui ne connecte l'input `"st"` de
`UsdUVTexture` que si une source est fournie. `_USD_create_preview_UV_texture_transform`
est devenue morte et a été supprimée (même sort que `_USD_create_UV_texture_transform`
au Round 4).

**Point d'attention signalé avant d'implémenter** : contrairement à
`ND_image`/`ND_tiledimage`, `UsdUVTexture.inputs:st` a une valeur par
défaut *littérale* `(0,0)` dans son schéma USD natif, sans garantie de
résolution implicite vers le UV set par défaut comme pour le graphe mtlx.
**Confirmé sans problème par l'auteur** : rendu et preview connectés tous
les deux, graphe propre dans l'éditeur de matériau de Houdini. Le risque
signalé ne s'est pas matérialisé (ou le viewport GL lit de toute façon le
graphe mtlx en pratique, comme aux rounds précédents, rendant la question
sans objet pour ce cas de test).

**Faux problème, résolu (2026-08-08)** : le blend à deux couches sur
`Shaderball_Material` (`rainbowh_Image`/`rainbowh_Image_2`, `blend=subtract`)
avait été noté comme suspect plus tôt dans cette session (Karma ne semblait
lire que la première couche) — confirmé correct par l'auteur une fois le
graphe mtlx retesté après le fix Round 4. Vraisemblablement un symptôme du
même problème de résolution `"texcoord"` que le reste, pas un bug séparé
dans `_USD_connect_operator`/`_USD_connect_effect_stack`. Rien à investiguer
ici.

#### Round 6, tentative de fix `ND_minus` (Subtract) — RÉ-INVERSÉE (2026-08-09, voir fin de section)

Différence visuelle repérée par l'auteur entre le rendu Modo et Houdini/
Karma sur un blend "Subtract". Investigation en trois temps :

1. Formule réelle de `ND_minus` vérifiée dans le source GLSL/OSL de
   MaterialX (`stdlib_genglsl_impl.mtlx`, pas juste le nodedef) :
   `mix*(bg-fg) + (1-mix)*bg`, soit `bg - mix*fg`. Formule bien formée en
   soi, rien d'évidemment cassé.
2. Test de contrôle de l'auteur, dans Modo : deux couches empilées avec
   exactement la même texture, blend Subtract à mix=100% → noir pur
   (`fg-bg=0` si `bg=fg`). Reproduit algébriquement avec la formule
   vérifiée ci-dessus en chaînant `ND_mix` (blend "Normal", = `fg` pur à
   mix=1) puis `ND_minus` : cohérent, mais ce test ne distingue pas le sens
   fg/bg puisque le résultat est nul dans les deux sens quand fg=bg.
3. Test décisif de l'auteur, directement dans Houdini, avec deux textures
   **différentes** : la correspondance visuelle avec Modo n'est obtenue
   que si `"fg"` reçoit la pile accumulée (les couches en dessous, ce que
   `_USD_connect_operator` appelle `input`) et `"bg"` reçoit cette
   nouvelle couche (ce que `_USD_connect_operator` appelle `output` /
   `connector.output`) — **l'inverse de la convention fg=nouvelle-couche/
   bg=pile-accumulée utilisée pour tous les autres opérateurs** (vérifiée
   correcte pour `ND_mix`/"Normal" : à mix=1, elle doit donner la nouvelle
   couche pure, ce qui exige fg=nouvelle-couche).

Corrigé dans `_USD_connect_operator` (`ShaderTree.py`) : la branche
générique (tout sauf multiply/divide) inverse fg/bg pour
`ND_minus`/`ND_plus`/`ND_burn`/`ND_dodge`/`ND_difference`/`ND_overlay`/
`ND_screen` — sur instruction explicite de l'auteur, étendant à toute la
famille des blend modes façon Photoshop le fix validé pour `ND_minus`
seul. Seul `ND_mix` (blend "Normal") garde la convention d'origine
(fg=nouvelle-couche/bg=pile-accumulée), vérifiée correcte séparément (à
mix=1 elle doit donner la nouvelle couche pure).

**Seul `ND_minus` a été testé par l'auteur contre un rendu Modo réel** —
les 6 autres opérateurs suivent le même fix par extrapolation/instruction,
pas par vérification individuelle.

**Tension repérée en re-dérivant la formule, signalée à l'auteur avant
d'étendre le fix, pas résolue** : la formule `bg - mix*fg` (`ND_minus`,
et la même structure `mix*op(fg,bg)+(1-mix)*bg` pour les 6 autres) donne
`out = bg` exactement à `mix=0`, quel que soit `fg` — l'opérateur "fond"
donc vers **`bg`** à opacité nulle. Avec la convention standard de la
plupart des piles de calques (0% opacité = aucun effet visible = la pile
accumulée, PAS la nouvelle couche), il faudrait `bg = pile accumulée` —
soit la convention *non échangée*, qui est justement celle utilisée pour
`ND_mix` et qui existait déjà pour ces 7 opérateurs avant ce fix. Le fix
appliqué ici (`bg = nouvelle couche`) n'a été confirmé correct par
l'auteur qu'à **mix=100%** — son comportement à opacité partielle
(fondu vers la nouvelle couche plutôt que vers la pile accumulée) n'a
jamais été testé et pourrait être un vrai problème, ou pas, selon ce que
fait réellement Modo à opacité partielle pour ces blend modes. À vérifier
un jour avec un calque à opacité non-100% si ça devient pertinent.

**RÉ-INVERSÉ (2026-08-09)** : l'auteur est revenu sur ce fix ("probablement
faux") — `_USD_connect_operator` est repassé à la convention d'origine,
non échangée, pour tous les opérateurs (`fg` = nouvelle couche, `bg` =
pile accumulée), y compris `ND_minus`. Historique ci-dessus conservé tel
quel pour la trace, mais **ne reflète plus le code actuel**. La tension
signalée au paragraphe précédent (fondu vers `bg` à `mix=0`) est ce qui a
probablement motivé le retour en arrière — avec la convention d'origine,
`bg=pile accumulée` fond bien vers "aucun effet" à opacité nulle, cohérent
avec toutes les autres piles de calques.

**EXPLICATION TROUVÉE (2026-08-09)** : la différence de rendu Modo/Karma
sur "Subtract" qui avait motivé ce fix n'était pas un bug fg/bg du tout —
c'était le bug de pivot de tuilage `ND_tiledimage` du Round 8. L'auteur
testait avec une texture damier (grille de couleurs), donc un mauvais
pivot de tuilage décale visiblement les couleurs échantillonnées à chaque
UV, ce qui *ressemblait* à un problème de blend/colorspace mais n'en était
pas un. Confirmé par l'auteur : une fois le Round 8 corrigé, le rendu
correspond à Modo, avec la convention fg/bg d'origine (non échangée). Rien
à reconsidérer ici.

#### Round 7, colorspace des textures — CONFIRMÉ CORRECT DANS HOUDINI, NE PLUS Y TOUCHER (2026-08-08/09)

L'auteur repère que `imageMap/videoStill/channels/colorspace` (déjà extrait
en XML brut, jamais lu par la construction USD) devrait être câblé sur les
nœuds de lecture de texture. Investigation avant d'écrire quoi que ce soit,
comme pour les autres tables cette session — **en plusieurs passes, la
première hypothèse s'étant révélée fausse** :

1. Recherche dans les stubs SDK (`lx.symbol`, `lx.service.ColorMapping`,
   requête live dans Modo par l'auteur) : le colorspace de Modo **n'est pas
   un petit enum fixe** comme les wrap modes ou les blend modes — c'est
   piloté par un système OCIO complet, avec plusieurs configs enregistrées
   simultanément sur la scène (`aces`, `foundry-v1`, `Foundry-WideGamut`,
   `nuke-default`, `spi-anim`, `spi-vfx` observés). Une table de
   correspondance 1:1 comme pour les wrap modes n'aurait pas de sens ici.
2. Première hypothèse de l'auteur : `"(default)"` signifierait "aucune
   transformation de colorspace" → mappé sur `"raw"`. **Corrigée par la
   suite** (voir point 4) — cette hypothèse ne tenait pas.
3. L'auteur suggère de regarder du côté de `modo.scene.current()` pour
   trouver la vraie source de `"(default)"`. Aucune méthode colorspace
   trouvée ni sur le wrapper `modo.Scene` ni sur l'objet `lx.object.Scene`
   sous-jacent (liste complète vérifiée en live, pas juste les stubs,
   forcément incomplets) — pas une propriété de scène/item.
4. Trouvé en cherchant dans les `.cfg` de Modo (`prefs.cfg`, la source de
   vérité pour les définitions de préférences, hors stubs) : `"(default)"`
   résout en fait vers l'une de **4 préférences distinctes**
   (`Preferences > Color Management`), une par catégorie de profondeur de
   bits — `colormanagement.8bit_default_colorspace`,
   `..16bit_default_colorspace`, `..float_default_colorspace`,
   `..numeric_default_colorspace` — confirmées et interrogées en live par
   l'auteur (`pref.value colormanagement.<catégorie>_default_colorspace ?`,
   retourne `"<configOCIO>:<colorspace>"`, ex. `"nuke-default:sRGB"`).
   Résultat réel sur l'installation de l'auteur : 8bit/16bit/numeric →
   `sRGB` (une vraie transformation, pas "raw" !), float → `linear`. Ça
   confirme aussi la config OCIO active (`nuke-default`).

**`"(default)"` ne signifie donc PAS "aucune transformation"** — c'est
juste ce que l'auteur avait initialement supposé, contredit par la
préférence réelle (`sRGB` pour la catégorie la plus courante, 8-bit).

Implémentation finale, en trois morceaux — **consolidée une seconde fois**
(2026-08-08, plus tard dans la session) sur demande de l'auteur, pour
regrouper le maximum de logique dans `normalize/colorspace.py` plutôt que
de la répartir entre ce fichier et `ShaderTree.py` :

- **Stage 1** (`ShaderTree.py`, dans Modo) : `_initialize_colormanagement_defaults()`
  lit les 4 préférences une fois par export (même convention que
  `_initialize_preferences()`), préfixe de config retiré (`"nuke-
  default:sRGB"` → `"sRGB"`) — **la seule partie qui ne peut pas bouger**,
  puisque c'est un appel `lx.eval()` et que `normalize/` doit rester à zéro
  dépendance `lx`/`modo`/`fnpxr`, comme les 5 autres passes du package.
  Passé directement en paramètre à `normalize_shadertree(xml, colorspaceDefaultByCategory)`
  dans `export_basic_execute` — plus d'étape de résolution séparée sur
  l'arbre brut.
- **Stage 2** (`normalize/colorspace.py`) : `normalize_colorspace(xml,
  colorspaceDefaultByCategory=None)` fait maintenant tout le travail —
  table d'heuristique format→profondeur de bits (`MODO_FORMAT_COLORSPACE_CATEGORY`,
  PNG/JPG/TGA → 8bit, EXR/HDR → float, etc. — **pas fiable à 100%**, ex. un
  PNG peut être en 16-bit, mais Modo n'expose pas la profondeur de bits
  réelle dans les canaux déjà extraits ; retombe sur 8bit, le cas le plus
  courant, si le format n'est pas reconnu) **et** résolution
  (`colorspaceDefaultByCategory.get(category)`, retombant sur `"raw"` si le
  dict est vide/incomplet), en un seul passage sur chaque `videoStill`. Le
  seul paramètre qui casse l'uniformité des 5 autres passes (toutes
  `xml -> xml` sans argument) — appelée séparément dans `normalize()`
  plutôt que via `NORMALIZATION_PASSES`, pour cette raison précise. Toute
  valeur `!= "(default)"` reste passée telle quelle, sans traduction (cf
  point 1 ci-dessus).
- **Stage 3** (câblage `ShaderTree.py`) : métadonnée `colorSpace` libre sur
  l'input `"file"` du nœud mtlx (`UsdAttribute.SetColorSpace()`, vérifié
  contre `usd-core`). Sur demande de l'auteur (2026-08-08), **la même
  métadonnée est maintenant aussi posée sur `"file"` côté glPreview**
  (`_USD_create_preview_UV_texture`), en plus de l'enum restreint
  `sourceColorSpace` (`raw`/`sRGB`/`auto`) de `UsdUVTexture` déjà en place —
  ceinture et bretelles, au cas où l'un des deux mécanismes ne serait pas
  lu par tel ou tel outil. Le forçage `"raw"` pour les normal maps reste
  prioritaire sur les deux (métadonnée et input). Vérifié en construisant
  le nœud directement contre `usd-core` (`inputs:file` porte bien
  `colorSpace = "sRGB"` en plus de `inputs:sourceColorSpace = "sRGB"`).

**Confirmation indépendante (lecture directe des 6 configs OCIO livrées
avec Modo, `.../Modo*.app/Contents/Resources/ocio_configs/*/config.ocio`)** :
`foundry-v1`/`nuke-default`/`aces` ont bien un colorspace littéralement
nommé `raw` (et `aces` mappe même son rôle `default` sur `raw`), mais
`spi-anim`/`spi-vfx` utilisent une nomenclature totalement différente
(`lnf`, `vd16`, `cpf`, `ncf`..., leur rôle `default` pointant sur `ncf`) —
aucun `raw`/`sRGB` nulle part. Ça illustre concrètement la limite déjà
documentée pour les valeurs de colorspace *explicites* (le passage tel
quel ne fonctionnera que si la config active dans Modo et celle de Karma
partagent la même nomenclature) — mais ne remet pas en cause la résolution
via préférences ci-dessus, qui ne dépend pas de cette nomenclature.

La logique de résolution (heuristique format→profondeur de bits + lookup)
vit entièrement dans `normalize/colorspace.py` et est vérifiée par pytest
(`tests/normalize/test_colorspace.py`, table passée en paramètre de test,
pas besoin de Modo). Seul `_initialize_colormanagement_defaults()`
(`ShaderTree.py`, Stage 1, l'appel `lx.eval()` lui-même) n'a aucun test
automatisé possible, comme tout Stage 1. Point resté incertain : la table
`MODO_FORMAT_COLORSPACE_CATEGORY`, jamais vérifiée précisément contre le
vrai comportement de Modo (un PNG 16-bit ou un format non listé tomberait
sur la mauvaise catégorie) — mais sans conséquence visible constatée par
l'auteur jusqu'ici.

**CONFIRMÉ CORRECT PAR L'AUTEUR (2026-08-09)** : après re-export, la
différence de rendu perçue comme un problème de colorspace a disparu —
elle venait en réalité du bug de pivot de tuilage du Round 8 (texture
damier, donc très sensible à un mauvais alignement UV). Le système de
colorspace lui-même fonctionne correctement. **Décision de l'auteur : ne
plus y toucher** — il pourra être utile pour d'autres cas (textures avec
un colorspace explicitement différent de `"(default)"`, par exemple), mais
n'a pas besoin d'évoluer davantage pour l'instant.

#### Round 8, bug réel trouvé dans le pivot de tuilage `ND_tiledimage` — CONFIRMÉ CORRIGÉ DANS HOUDINI (2026-08-09)

L'auteur signale que la couleur diffère toujours entre Modo et Houdini,
mais surtout que **l'UV map n'est pas alignée pareil dès que `wrapU`/
`wrapV` ≠ 1** — l'hypothèse de l'auteur : le tuilage semble se faire depuis
le centre de l'UV map (0.5, 0.5) plutôt que depuis le coin bas-gauche
(0, 0).

Vérifié directement dans le vrai source MaterialX (`NG_tiledimage_*` dans
`stdlib_ng.mtlx`, le nodegraph d'implémentation, pas juste le nodedef) :
la formule réelle de `ND_tiledimage`, avec `realworldimagesize`/
`realworldtilesize` laissés à leur défaut `(1,1)` (jamais posés par ce
code), se réduit à `texcoord*uvtiling - uvoffset`. Le tuilage se fait donc
bien depuis l'origine `(0,0)`, **pas** depuis le centre — confirmant que
c'est `ND_tiledimage` qui a le mauvais pivot par rapport à Modo (dont le
`wrapU`/`wrapV` scale visiblement depuis le centre, cohérent avec le fait
que `txtrLocator` est un vrai système de locator/transform avec pivot).

Corrigé dans `_USD_create_UV_texture` (branche `ND_tiledimage`,
`ShaderTree.py`) : `uvoffset` reçoit maintenant `m02/m12 + 0.5*(uvtiling-1)`
par axe au lieu de juste `m02/m12`. Ce terme compensatoire recentre le
tuilage sur `(0.5, 0.5)` — vérifié algébriquement (`texcoord=0.5` reste
fixe à `0.5` quel que soit `uvtiling`) et se réduit exactement à l'ancien
comportement quand `uvtiling=(1,1)` (le cas le plus courant), donc pas de
régression pour ce cas. Le réseau glPreview n'a pas besoin du même fix :
depuis le Round 5, `"st"` y est laissé non connecté, aucun tuilage/offset
n'y est appliqué du tout pour l'instant (vérifié - `wrapU`/`wrapV` n'y
apparaissent nulle part).

**Confirmé par l'auteur après re-export (2026-08-09) : les UV maps sont
maintenant correctement alignées entre Modo et Houdini.** La différence de
"couleur" signalée en même temps par l'auteur n'était pas un symptôme
distinct — c'était le même bug de pivot : la texture de test était un
damier de couleurs, donc un mauvais alignement UV change directement les
couleurs échantillonnées à chaque texel. Un seul bug, pas deux (voir aussi
Round 6/7 ci-dessus, tous deux expliqués par celui-ci).

#### Round 9, sélection de l'UV map par couche — SOLUTION VALIDÉE À LA MAIN DANS HOUDINI, PAS ENCORE RECONFIRMÉE VIA UN EXPORT (2026-08-09)

L'auteur pointe un problème que le Round 4 avait introduit sans s'en rendre
compte : un mesh peut avoir plusieurs UV maps dans Modo (nommées par
chaîne, ex. `"Texture"`, `"texture2"`), et chaque couche de texture choisit
la sienne via `txtrLocator/channels/uvMap` — déjà extrait en XML brut
depuis le début, mais jamais lu par la construction USD. Depuis le
Round 4, `"texcoord"` est systématiquement laissé non connecté sur le
graphe mtlx, donc **toutes** les couches d'un mesh lisent la même UV map
(celle que Karma résout par défaut), quelle que soit la couche
sélectionnée dans Modo — silencieusement faux dès qu'un mesh a plus d'une
UV map utilisée.

Hypothèse initiale de l'auteur : peut-être que `ND_texcoord_vector2` (le
nœud MaterialX déjà écarté au Round 3) permettait de sélectionner l'UV map
via son input `"index"` (entier) ? **Écartée par l'auteur lui-même après
vérification** : côté Houdini, le mesh arrive via un fichier Alembic
exporté depuis Modo, où les UV maps deviennent des attributs de vertex
(`vector2`) nommés **à l'identique** des noms Modo (`"Texture"`,
`"texture2"`, etc.) — pas d'indirection par index du tout. C'est
exactement la conclusion déjà tirée au Round 3 (`ND_texcoord_vector2`/
`"index"` non résolvable dans la traduction MaterialX-vers-Hydra de Karma,
remplacé par `UsdPrimvarReader_float2`/`"varname"`) — cohérent, pas une
contradiction.

Implémenté : nouvelle fonction `_USD_create_UV_texcoord_reader`
(`ShaderTree.py`) — lit `txtrLocator/channels/uvMap` ; si non vide,
construit un nœud lecteur et retourne son `outputs:out` ; sinon retourne
`None` (comportement du Round 4 inchangé : `"texcoord"` reste non
connecté, Karma résout vers l'UV set par défaut). Branché dans
`_USD_create_texture_output` (branche `usdProjType == "uv"`), qui passe le
résultat à `_USD_create_UV_texture` via son paramètre
`textureTransformInput` déjà existant.

**Correction après test réel dans Houdini (2026-08-09)** : la première
version utilisait `UsdPrimvarReader_float2("varname"=...)`, qui avait déjà
fonctionné pour le réseau glPreview (Round 3) — mais l'auteur a constaté
que ce nœud, natif USD/Hydra et non un vrai nœud MaterialX, ne se résout
pas comme source d'UV à l'intérieur d'un graphe mtlx compilé. Le bon nœud,
confirmé fonctionnel par l'auteur : `ND_geompropvalue_vector2` — le
mécanisme MaterialX natif pour lire une propriété géométrique nommée dans
un graphe de matériau (vérifié contre la vraie librairie standard :
input `"geomprop"` (string), output `"out"` (vector2), pas `"varname"`/
`"result"`). Vérifié structurellement en construisant le nœud contre
`usd-core` : `inputs:texcoord.connect = </.../_uvmap.outputs:out>` avec
`inputs:geomprop = "texture2"` sur le lecteur, comme attendu (variable/
suffixe de prim path renommés de `stReader`/`_streader` à `uvmap`/`_uvmap`
sur demande de l'auteur, plus explicite). Ajouté à
`node_registry.py`/`tools/generate_node_registry.py` (catégorie
`FIXED_IDS`, un seul type utilisé) ; `UsdPrimvarReader_float2` retiré de
la liste des ids "pas des nœuds MaterialX" du même fichier, plus utilisé
nulle part dans `ShaderTree.py`.

**Portée délibérément limitée au graphe mtlx** (le sujet du jour, cf.
clarification de périmètre en tête de fichier) — le réseau glPreview
(`_USD_create_preview_UV_texture`) n'a pas été retouché et laisse toujours
`"st"` non connecté, y compris pour les couches avec un `uvMap` explicite.
À étendre au glPreview si besoin un jour.

**Pas encore testé dans Houdini au moment d'écrire ceci.** Le fichier de
test "PF_ShaderBall_base" a un cas concret pour vérifier : `rainbowh_Image_2`
(`Shaderball_Material`, la seconde des deux couches empilées sur
`diffColor`) utilise `"texture2"`, différent de `"Texture"` utilisé
partout ailleurs.

### Limites connues, acceptées (pas d'équivalent natif dans le catalogue de preview de Storm)

- **Projection triplanaire** : aucun nœud natif équivalent à
  `ND_triplanarprojection`. Une couche `imageMap` en projection triplanaire
  n'aura pas de connexion preview ; l'input du preview garde sa valeur
  littérale par défaut.
- **`<noise>` (texture procédurale 3D)** : aucun équivalent natif. Avant
  cette session, sa sortie mtlx était (à tort) connectée au preview ; elle
  ne l'est plus du tout maintenant (`previewOutputs` n'est jamais rempli
  pour `<noise>`) — un défaut/valeur littérale au pire, jamais un mauvais
  rendu.
- **`contrast` et le remap min/max** (ajustements par couche) : pas
  d'équivalent natif sur `UsdUVTexture`. Le preview lit la texture sans ces
  corrections ; le graphe mtlx garde sa pleine fidélité.

## Package `ShaderFilters/` — FAIT (2026-08-08)

`ShaderFilters.py` (345 lignes, 5 tables sans rapport entre elles, formatage
incohérent) est devenu `Scripts/python_modules/ShaderFilters/`, un fichier
par table, même formalisme que `normalize/` (en-tête expliquant le rôle et
les consommateurs de chaque table). `ShaderTree.py` n'a rien eu à changer —
`from .ShaderFilters import usdTypeMap` continue de marcher via le
`__init__.py` qui réexporte tout, comme `normalize/__init__.py`.

- **Tables vivantes** (réellement importées par `ShaderTree.py`) :
  `channel_types.py` (`channelTypeMap`), `usd_types.py` (`usdTypeMap`),
  `std_mat_channel_map.py` (`stdMatChannelMap`).
- **Tables mortes, découvertes en faisant le tri** : `filters.py`
  (`filters` — jamais consultée nulle part ; le docstring de
  `_JSON_get_channels` mentionne encore un mécanisme `preFilterChannels`
  qui n'existe plus dans le code) et `input_map.py` (`usdInputMap` —
  `uvTile`/`effect_gl`, déjà remplacées par `normalize_uv_wrap_modes.py`/
  `normalize_effect_channel_names.py` plus tôt en session). **Conservées
  volontairement** (pas supprimées), marquées clairement "NOT CURRENTLY
  USED ANYWHERE" — décision de l'auteur en attente : les relancer un jour,
  ou les supprimer pour de bon.
- Fidélité du contenu vérifiée par comparaison du multiset de littéraux
  string entre l'ancien fichier et les nouveaux (identique, à un doublon de
  clé mort près dans `stdMatChannelMap[...]['principled']` — `"tranRough"`
  était assigné deux fois, la première valeur silencieusement écrasée par
  la seconde ; supprimé et documenté).
- **Bug trouvé en généralisant** : `reload_modules()` rechargeait
  `ShaderFilters` comme un module simple — devenu un package, ça ne
  rechargeait plus que son `__init__.py`, pas ses sous-modules (même
  problème déjà résolu pour `normalize/`, voir "Environnement de dev").
  Corrigé avec la même liste explicite de sous-modules.
- `index.xml`/le `.lpk` régénérés via `build_lpk.py` pour refléter les 6
  nouveaux fichiers du package à la place de l'ancien `ShaderFilters.py`.

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
2. **Où vivent les tables de `ShaderFilters.py`** : partiellement clarifié le
   2026-08-08 — `ShaderFilters.py` est devenu le package
   `Scripts/python_modules/ShaderFilters/`, un fichier par table, même
   formalisme que `normalize/` (voir section dédiée plus bas). Les tables
   `blend`/`effect`/`uvTile`/`effect_gl` restent **dupliquées** dans
   `normalize/` (risque de drift si les originaux changent) — ce n'est pas
   résolu, juste réorganisé plus lisiblement. À trancher si ça devient un
   problème réel, pas avant.
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
  `tests/normalize/` : 107 tests couvrant les 6 passes (`specular_ior`,
  `blend_operators`, `projection_defaults`, `effect_channel_names`,
  `uv_wrap_modes`, `colorspace`) + le registre de nœuds. Zéro dépendance
  Modo.
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

0. **PRIORITAIRE** : voir le paragraphe "PRIORITAIRE pour la prochaine
   session" en tête de fichier (re-exporter et confirmer le Round 9 dans
   Houdini, trancher le compromis rotation/scale/offset du Round 4, rester
   vigilant sur bump/normal/`<constant>`).

Le reste, aucune urgence, à discuter avec l'auteur :

1. Trancher la décision n°2 (duplication des tables entre `ShaderFilters/`
   et `normalize/`) si elle devient gênante. Décider aussi du sort de
   `ShaderFilters/filters.py` et `input_map.py` (code mort conservé).
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
