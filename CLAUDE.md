# Contexte projet — ShaderTreeToUSD

Ce fichier résume les décisions prises lors d'une session de conception (hors
Claude Code, sur claude.ai) portant sur la refonte de la complexité du plugin,
puis le travail effectué dans Claude Code pour la mettre en œuvre. Il sert de
point de reprise : lis-le avant de proposer des changements pour rester
cohérent avec la direction déjà validée par l'auteur du projet.

**Dernière mise à jour : 2026-08-13. Les 3 étages du pipeline sont câblés de
bout en bout et validés dans Modo (voir plus bas). Session du 2026-08-11/12 :
corrections de bugs trouvés en testant "PF_ShaderBall_base" dans Modo/Houdini
(Rounds 28-36 - stencil, bump/normal, displacement scalaire et vectoriel,
fuite de câblage inter-effets), puis chantier sur le support des couches
`Gradient` : extraction XML complète et validée à l'étage 1 (Rounds 37-42 -
vraies clés/valeurs/type d'interpolation/`minPos`/`maxPos`), mais la
traduction côté USD/mtlx (Rounds 43-53) a été **abandonnée au Round 54** -
aucune des 3 familles de nœuds de rampe essayées (`ND_ramp_gradient`,
`ND_ramplr_float`, `ND_hinvlinear_float`/`ND_huniformramp_float`) ne
s'est avérée fonctionner dans Karma malgré des graphes structurellement
corrects. Une couche `Gradient` ne produit donc actuellement rien côté
USD, seulement un XML normalisé fidèle.**

**Session du 2026-08-13 : tous les Rounds 28-42 retestés et confirmés avec
un export réel dans Modo/Houdini** (stencil dont l'alpha PNG, bump, normal,
swizzling, fuite de câblage inter-effets, `displace`+`vectorDisplace`
combinés, extraction XML des Gradients) - clôt la priorité de retest
ouverte depuis le Round 28. Deux nouveaux bugs trouvés et corrigés au
passage : `displace`+`vectorDisplace` combinés sur le même matériau
s'écrasaient l'un l'autre sur `mtlx:displacement` (Round 56, corrigé via
`ND_mix_displacementshader`) ; `alpha="only"` (stencil sur PNG à alpha)
était cassé par un bug de remap qui écrasait le canal alpha à une
constante avant extraction (Round 57). Les nœuds `invert`/`round`/
`convert` du stencil ont aussi été regroupés dans un `NodeGraph` dédié
(Round 58). Une légère différence de spécularité entre Modo et Karma
repérée en testant le bump a ensuite été investiguée via une longue série
de matrices de shader balls isolant chaque paramètre BRDF (Round 59, clos) :
deux bugs réels trouvés et corrigés, tous les deux des valeurs hors
domaine physique passées sans validation à `standard_surface` - un IOR
dérivé de `specAmt` qui explose vers l'infini près de `specAmt=1.0`
(`_MAX_DERIVED_IOR=20.0`) et un `refIndex` brut `< 1.0` (`_MIN_IOR=1.0`),
tous les deux dans `specular_ior.py`, tous les deux confirmés par
l'auteur après retest. Toutes les branches sauf une (`useRefIdx=1`+
`specRefIdx=1`) rendent maintenant de façon cohérente entre Modo et
Karma - cette dernière montre un écart de forme de courbe (pas une valeur
invalide) que l'auteur a choisi d'accepter comme limite connue plutôt que
de poursuivre la calibration, la différence d'interprétation de
l'environnement lumineux entre les deux moteurs rendant la comparaison
visuelle difficile à trancher plus finement sans outillage de mesure
dédié. Documenté dans le README.

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
colorspace. **Décision de l'auteur (2026-08-09) : ne plus toucher à ce
système, il fonctionne correctement et pourra servir dans d'autres cas.**
**Revenu dessus au Round 19 (2026-08-10)** : le système à 4 préférences
Modo décrit ci-dessous a été retiré, remplacé par une table de mapping
directe bien plus simple - voir Round 19 pour le raisonnement.

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

**Toutes les transformations UV (sélection d'UV map, rotation à pivot
centré, tuilage, pan) sont confirmées correctes dans Houdini (Round 9-15,
clos).** Les 4 wrap modes mtlx (`periodic`/`clamp`/`mirror`/`constant`)
sont aussi tous testés dans Houdini (Round 10/11/17, clos) :
`periodic`/`clamp` fonctionnent, `mirror`/`constant` sont des limitations
Houdini connues et diagnostiquées (`_DEBUG_diag`), pas des bugs de ce kit.
**Retest du 2026-08-13, CLOS** : "PF_ShaderBall_base" re-exporté et tous les
Rounds 28-42 confirmés se comporter comme attendu (stencil dont l'alpha
PNG, bump, normal, swizzling, `vectorDisplace`, fuite de câblage
inter-effets, extraction XML des Gradients - voir la note en tête de
fichier et chaque round individuel pour le détail). Deux bugs
supplémentaires trouvés et corrigés pendant ce retest (Round 56 et 57).
**Round 59 clos le 2026-08-13** : deux bugs réels trouvés et corrigés
(`_MAX_DERIVED_IOR`, `_MIN_IOR`, tous les deux dans `specular_ior.py`).
`useRefIdx=1`/`specRefIdx=1` reste avec un écart de forme de courbe non
corrigé - accepté par l'auteur comme limite connue (voir Round 59 pour le
détail complet et le raisonnement), documenté dans le README, pas de
piste de correction retenue pour l'instant. Plus de priorité ouverte
issue de cette session à ce stade - voir "Prochaines étapes possibles" en
fin de fichier pour la suite envisagée sur les gradients (traduction
USD/mtlx, abandonnée au Round 54, pas de nouvelle piste depuis) et les
autres points sans urgence.

**Priorité précédente (toujours pas résolue)** : le système de colorspace a été
simplifié aux Round 19-21 (table directe `MODO_COLORSPACE_TO_USD`, système
à 4 préférences du Round 7 retiré). 9 entrées sont posées (`"(default)"`
+ 8 dérivées du vrai `cmlib` mtlx pour la config `foundry-v1`), aucune
encore confirmée en rendu réel dans Houdini - à vérifier. Les 5 autres
configs OCIO de Modo (`aces`/`Foundry-WideGamut`/`nuke-default`/
`spi-anim`/`spi-vfx`) résolvent sur `""` (diagnostiqué en console/XML,
Round 21) jusqu'à ce qu'elles soient ajoutées à la table. Le bug d'origine
qui a lancé
cette discussion (mtlx ne force pas `"raw"`/l'équivalent pour les normal
maps, contrairement à glPreview - voir la session du 2026-08-10 avant le
Round 19) reste **non résolu**. `<constant>` reste toujours non exercé par
le fichier de test "PF_ShaderBall_base". Bump/normal/stencil, en
revanche, ont depuis été testés et confirmés (Rounds 29/33/34/57/58,
retest du 2026-08-13) - plus une priorité.

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

#### Round 10, réconciliation ND_image/ND_tiledimage — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS HOUDINI (2026-08-10)

Entre la fin du Round 9 et cette session, une modification jamais tracée
dans ce fichier (faite hors session Claude Code suivie, jamais commit)
avait supprimé la branche `ND_image` entièrement au profit d'un unique
chemin `ND_tiledimage` (commentaire "author's call" laissé dans le code,
mais la décision elle-même n'a jamais été documentée ici) — au prix de
perdre tout wrap mode edge/mirror/reset sur le graphe mtlx. L'auteur a
reposé la question en session : ce compromis (`ND_image` = pas de tuilage
indépendant par axe sans skew, `wrapU`/`wrapV` ignorés ; `ND_tiledimage` =
pas de wrap mode) est-il une vraie limite MaterialX, ou un manque
d'implémentation côté Houdini ?

Vérifié directement contre le paquet `MaterialX` standalone dans `.venv`
(nodedefs réels, pas les stubs) :
- `ND_image_*` a bien `uaddressmode`/`vaddressmode` avec les 4 valeurs
  `constant`/`clamp`/`periodic`/`mirror` dans son enum — un vrai wrap mode
  par axe existe au niveau du schéma.
- Le vrai *nodegraph* d'implémentation de `ND_tiledimage_*`
  (`NG_tiledimage_*` dans `stdlib_ng.mtlx`, pas juste le nodedef) est
  strictement : `multiply`(texcoord, uvtiling) → `subtract`(uvoffset) →
  `image` avec `uaddressmode`/`vaddressmode` **codés en dur à
  `"periodic"`**. Autrement dit `ND_tiledimage` **n'est rien de plus qu'un
  `ND_image` précédé de ce calcul de tuilage**, avec le wrap mode figé — la
  dichotomie observée par l'auteur n'est pas une limite structurelle de
  MaterialX, c'est un artefact du nœud de confort `ND_tiledimage`,
  contournable en reconstruisant soi-même ce calcul en amont d'un
  `ND_image`. Composer une échelle non-uniforme puis une rotation (l'ordre
  utilisé ici et dans `ND_tiledimage`) ne produit d'ailleurs pas de skew —
  une matrice `rotation × échelle` préserve l'orthogonalité — donc pas de
  risque théorique à reconstruire ce calcul à la main.
- L'implémentation GLSL de référence de `mx_image_color3` (livrée avec le
  paquet `MaterialX`, `stdlib/genglsl/mx_image_color3.glsl`) ne fait
  **aucun** calcul de wrap en shader — elle appelle `texture(...)` tel quel
  et délègue entièrement le wrap mode à l'état du sampler GPU, posé par le
  générateur de shader hôte au moment du binding. Ça confirme que le
  support de `mirror`/`constant` (par opposition à `clamp`/`periodic`, les
  deux modes GPU quasi universels) dépend de ce que l'implémentation
  MaterialX-vers-Hydra de Houdini/Karma câble réellement — pas garanti par
  la spec elle-même. Cohérent avec l'observation de l'auteur (seuls
  `clamp`/`periodic` fonctionnaient jusqu'ici).

Implémenté dans `_USD_create_UV_texture` (`ShaderTree.py`) : reconstruit
explicitement le calcul de `ND_tiledimage` (`ND_multiply_vector2` puis
`ND_subtract_vector2`, même formule `texcoord*uvtiling - uvoffset` avec la
compensation de pivot du Round 8 inchangée) en amont d'un `ND_image`, au
lieu d'appeler `ND_tiledimage` directement. `uaddressmode`/`vaddressmode`
posés depuis `usdWrapMode` (nouvel attribut, résolu par
`normalize_uv_wrap_modes` dans `uv_wrap_modes.py` — `USD_WRAP_MODE_BY_TILE`
réintroduite : `reset`→`constant`, `repeat`→`periodic`, `edge`→`clamp`,
`mirror`→`mirror`, distincte de `USD_NATIVE_WRAP_MODE_BY_TILE` qui reste
côté glPreview, `reset`→`"black"`, un token `UsdUVTexture`-spécifique
invalide dans l'enum `ND_image`), laissés non posés (donc défaut
`"periodic"` du nodedef) si le mode ne résout pas. `node_registry.py`/
`tools/generate_node_registry.py` mis à jour :
`ND_image_{float,color3,color4}`, `ND_multiply_vector2`,
`ND_subtract_vector2` ajoutés ; `ND_tiledimage_*` retiré (plus utilisé
nulle part). 4 tests ajoutés dans `tests/normalize/test_uv_wrap_modes.py`
pour `usdWrapMode`, 107 tests toujours verts.

**Pas encore testé dans Houdini au moment de l'écriture ci-dessus.**
`uvRotation` reste porté par le chaînage à deux nœuds `ND_UsdTransform2d`
(recenter/rotate), inchangé par ce round - voir Round 14 pour la
documentation de ce mécanisme, ajouté hors session suivie avant ce round
et jamais tracé ici jusqu'alors (pas "du Round 4", qui disait l'inverse).

#### Round 11, test réel dans Houdini du Round 10 — TUILAGE CONFIRMÉ CORRECT, `mirror` CONFIRMÉ NON SUPPORTÉ PAR HOUDINI (2026-08-10)

Testé par l'auteur dans Houdini juste après le Round 10 : **le calcul de
tuilage reconstruit à la main (point a) ci-dessus) rend correctement** —
la reconstruction `ND_multiply_vector2`/`ND_subtract_vector2` en amont de
`ND_image` est équivalente en pratique, pas seulement algébriquement, à
l'ancien `ND_tiledimage`.

`mirror` (point b), en revanche, confirmé **non fonctionnel côté
Houdini** — exactement le genre de manque prédit par l'analyse GLSL du
Round 10 (le mode de wrap est délégué à l'état du sampler GPU posé par
l'hôte, pas calculé dans le shader `ND_image` lui-même). Symptôme précis :
la texture apparaît **transparente** sur les bords tuilés en mode mirror
dans Houdini, alors que le même fichier rend `mirror` correctement dans
Modo — donc bien un manque de l'implémentation MaterialX-vers-Hydra de
Houdini, pas un problème dans le graphe généré par ce kit. `constant`
(Modo "reset") reste à tester séparément, pas encore fait.

Décision de l'auteur : **garder `uaddressmode`/`vaddressmode="mirror"`
tel quel dans le graphe généré** (ne pas retomber sur `clamp` en
substitution) — le graphe est correct vis-à-vis de la spec MaterialX, le
bug est chez Houdini, pas la peine de le masquer en dégradant le graphe.
À la place, un diagnostic explicite a été ajouté dans
`_USD_create_UV_texture` (`ShaderTree.py`), déclenché quand `uaddressmode`
ou `vaddressmode` résout à `"mirror"` :
`_DEBUG_diag("Unsupported", "UV mapping", ...)` — même mécanisme que les
autres limitations connues déjà signalées de cette façon (ex. projection
triplanaire, effets sans équivalent glPreview).

#### Round 12, regroupement des opérateurs UV dans un NodeGraph "UV_Transform" — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS HOUDINI (2026-08-10)

Demande de l'auteur : les 5 nœuds impliqués dans la transformation UV côté
mtlx (sélection d'UV map, recenter/rotate, tiling, offset - jusque là des
prims frères sous le matériau, nommés par préfixe partagé) encombrent le
graphe. Regroupés dans un unique prim `NodeGraph` nommé
`<nom_de_la_couche>_UV_Transform`, avec les paramètres Modo-facing exposés
comme ses propres interface inputs (`uvMap`/`rotation`/`tiling`/`offset`)
plutôt que posés en dur sur chaque nœud interne — même convention
d'authoring que `_USD_create_texture_adjust_nodegraph`, déjà en place et
validée ailleurs dans ce fichier pour le post-traitement de texture
(contrast/remap/invert). Purement structurel : les formules/le câblage
interne sont inchangés, seul l'emplacement des prims change (nœuds
imbriqués sous le `NodeGraph`, une seule boîte repliable dans l'éditeur de
graphe de matériau d'un DCC, au lieu de 5 nœuds frères sous le matériau).

`_USD_create_UV_texcoord_reader` et `_USD_create_UV_texture_transform`
fusionnées dans une nouvelle fonction unique, `_USD_create_UV_transform`
(`ShaderTree.py`) — plus utilisées/référencées nulle part ailleurs,
supprimées plutôt que laissées en code mort. `_USD_create_UV_texture` ne
construit plus les nœuds de tiling/offset elle-même (déplacés dans
`_USD_create_UV_transform`) ; elle se contente de connecter son
`"texcoord"` à la sortie unique du `NodeGraph`.

Vérifié structurellement en construisant le graphe directement contre
`usd-core` dans `.venv` (pas juste une relecture de texte) : les 5 nœuds
apparaissent bien imbriqués sous le prim `NodeGraph`, ses interface inputs
sont correctement référencés par les nœuds internes
(`inputs:rotation.connect = .../UV_Transform.inputs:rotation`, etc.), et
`ND_image` à l'extérieur ne référence que la sortie unique du graphe
(`inputs:texcoord.connect = .../UV_Transform.outputs:out`). **Pas encore
testé visuellement dans Houdini** — aucune raison de s'attendre à une
différence de rendu (le calcul est strictement identique, seule
l'organisation des prims change), mais pas confirmé.

#### Round 13, `ND_geompropvalue_vector2` sorti du NodeGraph — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS HOUDINI (2026-08-10)

Ajustement de l'auteur sur le Round 12 : le nœud de sélection d'UV map
(`ND_geompropvalue_vector2`) ne doit pas être imbriqué dans le `NodeGraph`
"UV_Transform", pour plus de cohérence — c'est une lecture de propriété
géométrique (quelle UV map lire), pas un opérateur de *transformation* UV
(recenter/rotate/tiling/offset), donc regroupés dans la même boîte ça
brouille ce qu'elle représente. Redéplacé en prim frère du `NodeGraph`
(`<couche>_uvmap`, comme avant le Round 12), avec sa valeur `geomprop`
reposée en dur (`.Set(uvMapName)`) plutôt que via l'interface input
`uvMap` du graphe (supprimée - elle n'avait plus de raison d'être une fois
le nœud qui la consommait sorti). Le nœud interne `recenter` (toujours
dans le graphe) connecte directement son `"in"` à ce nœud externe -
traverser la frontière du `NodeGraph` par une connexion directe est
parfaitement valide en USD (l'encapsulation n'est pas imposée), et c'est
exactement le même genre de connexion que celle vue plus haut entre
`ND_image` et la sortie du graphe. Vérifié structurellement contre
`usd-core` : `rainbowh_Image_2_uvmap` apparaît bien en frère de
`rainbowh_Image_2_UV_Transform`, et `recenter.inputs:in.connect` pointe
correctement dessus à travers la frontière du graphe. Reste, comme le
Round 12, à confirmer visuellement dans Houdini (aucun changement de
calcul, seulement d'emplacement de prim).

#### Round 14, `uvRotation` routé via l'interface input du NodeGraph + nettoyage des commentaires (2026-08-10)

Deux choses dans cette session :

**1. Correction du Round 13** : le nœud `recenter` (interne au `NodeGraph`)
connectait son `"in"` directement au nœud externe `ND_geompropvalue_vector2`,
traversant la frontière du graphe sans passer par une interface input —
valide en USD mais incohérent avec la convention déjà établie dans ce
fichier (`_USD_create_texture_adjust_nodegraph` route toute donnée entrante
via une interface input, jamais par connexion directe à un nœud interne).
Corrigé : le `NodeGraph` expose maintenant sa propre interface input
`"texcoord"` (vector2, non connectée par défaut) ; `ND_geompropvalue_vector2`
(resté en dehors du graphe, Round 13 inchangé sur ce point) connecte sa
sortie sur cette interface input, et `recenter` lit `"texcoord"` comme il
lit déjà `"rotation"`/`"tiling"`/`"offset"`. Quand `uvMap` est vide,
l'interface input reste simplement créée sans connexion ni valeur — même
effet en aval (aucune valeur ne se propage) que l'ancien "laisser `"in"`
totalement non connecté". Vérifié structurellement contre `usd-core` :
`inputs:texcoord.connect` sur le `NodeGraph` pointe vers le nœud externe,
et `recenter.inputs:in.connect` pointe vers cette interface input, pas
vers le nœud externe directement.

**2. Comblement d'un trou de documentation** : en simplifiant les
commentaires de `_USD_create_UV_transform`/`_USD_create_UV_texture` (à la
demande de l'auteur, voir point 3), il est apparu que le mécanisme de
rotation à pivot centré (deux nœuds `ND_UsdTransform2d` chaînés,
recenter → rotate → recenter inverse) n'avait **jamais été documenté
comme son propre round** dans ce fichier — seul le code le racontait. Le
Round 4 dit explicitement l'inverse ("plus aucun mécanisme ne porte
`uvRotation` côté mtlx"), et le Round 12 le mentionne en passant
("`uvRotation` reste porté par le chaînage `ND_UsdTransform2d` du
Round 4" — attribution erronée, ce chaînage n'existe pas au Round 4). Le
mécanisme a donc été ajouté entre le Round 9 et le Round 10, hors session
suivie, comme le retrait de `ND_image` déjà rencontré avant le Round 10.
Pour mémoire, la logique (inchangée, seulement redocumentée ici) :
`ND_UsdTransform2d` (le vrai nodedef MaterialX-wrapped, vérifié contre la
librairie standard — le schéma natif `"UsdTransform2d"` ne se résout pas
comme nœud dans un graphe mtlx compilé dans Karma, même échec que
`UsdPrimvarReader_float2`) tourne toujours autour de l'origine UV (0,0),
et sa propre `"translation"` s'applique *après* la rotation — donc un seul
nœud ne peut pas fournir le décalage pré-rotation qu'un pivot centré
demande. Modo pivote `uvRotation` depuis le centre de la tuile (0.5,0.5),
confirmé par l'auteur. Chaîner un recentrage (-0.5,-0.5) → rotation →
recentrage inverse (+0.5,+0.5) reproduit ça : à `uvRotation=0` les deux
recentrages s'annulent exactement, donc no-op pour le cas (très courant)
sans rotation. `m02`/`m12` reste hors de cette chaîne (posé sur le nœud
`"offset"` à la place, *après* le multiply de tiling — voir Round 8) ;
`"scale"` reste à son défaut (1,1) sur les deux nœuds puisque le tiling
est le travail du nœud `"tiling"`, pas de celui-ci.

**3. Simplification des commentaires** (demande explicite de l'auteur) :
les longs commentaires narratifs de `_USD_create_UV_transform`/
`_USD_create_UV_texture` (répétant l'historique déjà couvert ici) ont été
réduits à une ligne pointant vers le round CLAUDE.md correspondant. Rien
n'a été perdu — chaque fait qui n'était encore documenté nulle part
ailleurs (le mécanisme du point 2 ci-dessus) a été migré ici avant d'être
raccourci dans le code.

#### Round 15, direction de `m02`/`m12` inversée par rapport à Modo — CONFIRMÉ DANS HOUDINI (2026-08-10)

L'auteur signale, tiling actif (`wrapU`/`wrapV` ≠ 1), que le pan (offset)
part dans la direction opposée à Modo. Proposition initiale de l'auteur :
inverser le signe du terme de recentrage `0.5*(wrapU-1)` lui-même
(`uvoffsetU = m02 - 0.5*(wrapU-1)` au lieu de `+`). Écartée après analyse :
ce terme est exactement celui validé empiriquement dans Houdini au
Round 8 (alignement de tuilage correct avec `wrapU`/`wrapV` ≠ 1, sans pan
`m02`/`m12` impliqué à ce moment-là) — l'inverser risquait de réintroduire
ce bug déjà corrigé, tout en ne changeant *rien* au cas le plus courant
(tiling par défaut, `wrapU=wrapV=1`) où ce terme vaut exactement zéro quel
que soit son signe.

Correction appliquée à la place, plus ciblée : seul le signe de
`m02`/`m12` est inversé, le terme de recentrage du Round 8 reste
intact :

```python
uvoffsetU = -m02 + 0.5 * (wrapU - 1.0)
uvoffsetV = -m12 + 0.5 * (wrapV - 1.0)
```

Cohérent avec le fait que le terme de recentrage a déjà été validé
indépendamment (sans pan) — si l'alignement de tuilage était correct sans
pan et devient faux uniquement quand un pan `m02`/`m12` non nul s'ajoute,
c'est `m02`/`m12` qui a le mauvais signe, pas le terme de recentrage.

**Confirmé par l'auteur après re-export/test dans Houdini** : toutes les
transformations UV (sélection d'UV map, rotation à pivot centré, tuilage,
pan) fonctionnent maintenant correctement — clôt la série de rounds
9-15 sur ce sujet.

#### Round 16, nettoyage final des commentaires "what vs why" (2026-08-10)

Demande de l'auteur, une fois le Round 15 confirmé : dans
`_USD_create_UV_transform`/`_USD_create_UV_texture`, les commentaires ne
doivent plus décrire que **ce que** fait chaque bloc (une ligne, factuel),
pas **comment**/**pourquoi** — cette rationale vit entièrement dans ce
fichier (Round 3, 4, 7, 8, 10, 11, 13, 14, 15) et n'a pas besoin d'être
dupliquée dans le code. Rien à migrer : tout ce qui restait dans les
commentaires "why" avant ce round était déjà couvert par un round
existant, donc trim pur, aucune information nouvelle perdue.

L'auteur a ensuite repris cette passe directement dans le code (un
commentaire "quoi" en une ligne par bloc dans `_USD_create_UV_transform` :
sélection d'UV map, création du `NodeGraph`, lecture des channels Modo,
tiling-pivot pan offset, interface inputs, recenter/rotate/tiling/offset,
sortie finale) — même intention que ci-dessus, rien à contester. Seul fait
nouveau qui en ressort et qui ne vivait encore nulle part dans ce fichier :
**`m02`/`m12` proviennent de la matrice de transform 3x3 du
`txtrLocator`** de Modo (convention `mRC` = ligne R, colonne C ; `m02`/
`m12` sont donc les termes de translation des lignes 0/1) — explique
l'origine du nommage des deux channels, jusqu'ici jamais explicitée dans
ce fichier (seule leur valeur/usage l'était, voir Round 2 et 8).

#### Round 17, `"constant"` (Modo "reset") confirmé non supporté par Houdini — CONFIRMÉ, MÊME LIMITATION QUE `mirror` (2026-08-10)

Dernier point ouvert de la section "PRIORITAIRE" : testé par l'auteur dans
Houdini, `uaddressmode`/`vaddressmode="constant"` (résolu depuis le tile
mode Modo `"reset"`) affiche les bords hors tuile en **noir pur**, alors
que Modo les affiche en **transparent**. Exactement le même symptôme de
fond que `mirror` au Round 11 : le graphe généré est correct vis-à-vis de
la spec MaterialX (`constant` est une valeur valide de l'enum
`uaddressmode`/`vaddressmode`, vérifié Round 10), mais l'implémentation
MaterialX-vers-Hydra de Houdini ne le respecte pas — cohérent avec
l'analyse GLSL du Round 10 (le wrap mode est délégué à l'état du sampler
GPU posé par l'hôte, pas calculé dans le nœud `ND_image` lui-même;
`clamp`/`periodic` sont les deux modes GPU quasi universels, `mirror`/
`constant` beaucoup moins souvent câblés correctement par les
intégrations tierces).

Même décision que pour `mirror` : le graphe reste tel quel (pas de
repli sur `clamp`), avec un diagnostic explicite au lieu d'une correction
silencieuse. Ajouté dans `_USD_create_UV_texture` (`ShaderTree.py`), même
mécanisme que le `mirror` du Round 11 :
`_DEBUG_diag("Unsupported", "UV_mapping", ...)` déclenché quand
`uaddressmode`/`vaddressmode` résout à `"constant"`.

Ferme le dernier point ouvert de la section "PRIORITAIRE" en tête de
fichier sur le sujet des wrap modes mtlx — les 4 valeurs de l'enum
(`periodic`/`clamp`/`mirror`/`constant`) sont maintenant toutes testées
dans Houdini : `periodic`/`clamp` fonctionnent, `mirror`/`constant` sont
des limitations Houdini connues et diagnostiquées.

#### Round 18, sélection d'UV map ajoutée au réseau glPreview — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS HOUDINI (2026-08-10)

Discussion sur une possible fusion des deux réseaux (mtlx et glPreview) :
l'auteur propose de câbler `_UV_Transform:out` (le `NodeGraph` mtlx complet
— sélection d'UV map, rotation, tuilage, offset) directement sur
`UsdUVTexture:st`, et de réutiliser `_USD_create_texture_adjust_nodegraph`
(post-traitement mtlx : contrast/remap/invert/brightness) pour le
post-traitement preview. Écarté après analyse : les deux graphes sont
construits entièrement à partir de nœuds `ND_`-préfixés (`ND_UsdTransform2d`,
`ND_multiply_vector2`, `ND_remap`, `ND_contrast`...), hors du vocabulaire
natif figé que Storm sait résoudre pour son réseau `UsdPreviewSurface`
(`UsdUVTexture`/`UsdPrimvarReader_float2`/`UsdTransform2d` **natif**, sans
aucun nœud de math générique — confirmé par la section "Limites connues"
ci-dessous, où `contrast`/le remap min/max sont déjà documentés comme sans
équivalent natif pour cette raison précise). Réutiliser ces graphes pour
`UsdPreviewSurface` risquait donc de reproduire la même classe de bug que
le "blanc" originel (voir section "Shader glPreview"), déplacée du calcul
de couleur vers le calcul d'UV/post-traitement.

**Décision de l'auteur** : seul Karma compte pour lui (il ne sait pas/ne
veut pas tester Storm/autres DCCs), et Karma sait déjà inférer son propre
shader de preview directement depuis le graphe `standard_surface` (mtlx) -
observation cohérente avec la note "Contexte important" en tête de ce
fichier et le comportement déjà noté pour `ND_tiledimage`. Le réseau
`UsdPreviewSurface` explicite compte donc peu pour le rendu réel vu par
l'auteur ; pas la peine d'investir dans la fusion proposée. Seule
correction retenue, plus restreinte : câbler la sélection d'UV map
(`ND_geompropvalue_vector2`, sans aucun nœud de math) sur `UsdUVTexture:st`
- un simple lookup de propriété géométrique, pas une évaluation de graphe
de nœuds de calcul, donc un risque bien plus limité que la fusion complète, même si
`ND_geompropvalue_vector2` reste techniquement hors du vocabulaire natif
figé de Storm.

Implémenté dans `_USD_create_preview_texture_output` (`ShaderTree.py`) :
construit un second nœud `ND_geompropvalue_vector2` (`<couche>_preview_uvmap`,
distinct de celui du réseau mtlx - le réseau glPreview reste entièrement
autonome/dupliqué, comme le reste de son architecture) quand `uvMap` est
renseigné, et le passe à `_USD_create_preview_UV_texture` comme
`textureTransformInput` (paramètre déjà existant depuis le Round 5, mais
jusqu'ici toujours appelé avec `None`) - connecté sur `UsdUVTexture:st`
via la logique déjà en place. `None` (donc `"st"` non connecté) reste le
comportement si `uvMap` est vide - le cas le plus courant, inchangé.
Vérifié structurellement contre `usd-core`. **Pas encore testé dans
Houdini.**

#### Round 19, simplification du système de colorspace — table de mapping directe, système à 4 préférences retiré (2026-08-10)

En discutant d'un bug séparé (glPreview force `"raw"` pour les normal maps,
pas le graphe mtlx — jamais réellement creusé plus loin ce round), l'auteur
demande d'explorer `/Applications/.../Modo*.app/Contents/Resources/ocio_configs/`
pour voir si les `make.py`/`makeconfig_anim.py`/`make_vfx_ocio.py` de chaque
config pourraient aider à construire "une table de mapping colorspace
solide". Ces scripts se sont révélés être les générateurs Python 2 du
projet OCIO amont lui-même (`import PyOpenColorIO`, chemins dev codés en
dur) — pas exécutés par Modo, pas utilisables tels quels. En revanche,
lire directement les 6 `config.ocio` a révélé un fait solide et nouveau :
chaque config déclare un rôle `roles: data: <nom>` (la colorspace destinée
aux données non-couleur - normales, points... - confirmé par la
description "Raw Data. Used for normals, points, etc." partagée par tous)
— et ce nom **n'est pas toujours `"raw"`** : `Foundry-WideGamut` n'a même
aucune colorspace nommée `"raw"`, son rôle `data` pointe vers `"linear"` ;
`spi-anim`/`spi-vfx` (déjà notés Round 7 sans nomenclature `raw`/`sRGB`)
pointent vers `"ncf"`. Une piste (table `OCIO_DATA_COLORSPACE_BY_CONFIG`
par config, en plus de retenir le nom de la config active) a été explorée
en discussion mais **pas retenue** — l'auteur a recadré l'objectif entre
temps.

**Recadrage de l'auteur** : le vrai besoin n'est pas de reproduire la
config OCIO active de Modo, c'est simplement de remplir la métadonnée
`colorSpace` d'`ND_image` avec une valeur que MaterialX/le renderer en
face (Houdini/Karma) reconnaît réellement - une table directe
`valeur-choisie-dans-Modo -> valeur-acceptée-côté-USD`, construite et
affinée empiriquement plutôt que dérivée des configs OCIO de Modo (qui
décrivent ce que *Modo* appelle chaque colorspace, pas ce que *Houdini*
en face reconnaît). Décision explicite de l'auteur en le demandant : ceci
**réintroduit et remplace** le système à 4 préférences du Round 7 (`"(default)"`
résolu via `colormanagement.<catégorie>_default_colorspace`) plutôt que de
coexister avec lui — `"(default)"` devient une simple entrée de plus dans
la nouvelle table, mappée sur `""` (aucune métadonnée `colorSpace` posée
du tout, laissé au renderer/à mtlx de décider), au lieu d'être résolu.

Implémenté :
- **`normalize/colorspace.py`** entièrement réécrit : `MODO_COLORSPACE_TO_USD`,
  une seule table `{valeur brute Modo: valeur usd}`, avec pour l'instant
  une seule entrée confirmée par l'auteur (`"(default)"` → `""`) - le reste
  passe tel quel (valeur Modo inchangée) en attendant d'autres entrées
  confirmées (voir Round 20, juste après, pour la suite). `normalize_colorspace(xml)`
  n'a plus de paramètre - retrouve la signature uniforme `xml -> xml` des
  5 autres passes, et rejoint `NORMALIZATION_PASSES` dans
  `normalize/__init__.py` (n'a plus besoin d'être appelée à part). Toute
  la logique du Round 7 (`MODO_FORMAT_COLORSPACE_CATEGORY`,
  `MODO_DEFAULT_COLORSPACE`, `USD_RAW_COLORSPACE`) supprimée, pas laissée
  en code mort.
- **`ShaderTree.py`** : `colorspaceDefaultByCategory`/
  `_initialize_colormanagement_defaults()` (l'appel `lx.eval()` du
  Round 7, Stage 1) supprimés entièrement - plus besoin de requêter les 4
  préférences Modo. `normalize_shadertree(xml_shadertree)` appelée sans
  second argument.
- `tests/normalize/test_colorspace.py` réécrit pour la nouvelle API (plus
  de `colorspaceDefaultByCategory` en paramètre de test) - 106 tests
  toujours verts (107 → 106, quelques tests Round 7 devenus sans objet
  consolidés plutôt que remplacés un-pour-un).

**Ce que ça ne couvre pas** : le bug d'origine de la discussion (mtlx ne
force pas `"raw"`/l'équivalent pour les normal maps, contrairement à
glPreview) reste ouvert, non traité ce round - la conversation a bifurqué
vers cette simplification avant d'y revenir. La table
`MODO_COLORSPACE_TO_USD` n'a qu'une entrée confirmée à la fin de ce round
(`"(default)"`) ; le reste passe tel quel - voir Round 20, juste après,
pour l'avoir étoffée.

#### Round 20, table `MODO_COLORSPACE_TO_USD` étoffée avec le vocabulaire réel du CMS mtlx (2026-08-10)

Suite du Round 19 : l'auteur demande d'extraire tous les `name:` du bloc
`colorspaces:` de `foundry-v1/config.ocio` (13 colorspaces : `linear`,
`sRGB`, `sRGBf`, `AdobeRGB`, `ProPhoto`, `rec709`, `Cineon`, `Gamma1.8`,
`Gamma2.2`, `AlexaV3LogC`, `PLogLin`, `SLog`, `raw`) comme candidats côté
Modo pour la table, puis de leur trouver un équivalent mtlx.

Plutôt que de deviner, vérifié directement contre le vrai `cmlib` de la
librairie standard MaterialX (`cmlib_defs.mtlx`, livré avec le paquet
`MaterialX` standalone dans `.venv`) : le `DefaultColorManagementSystem`
de mtlx n'a de nœud de conversion réel (`ND_<nom>_to_lin_rec709_color3/4`)
que pour un vocabulaire fixe et restreint : `acescg`, `adobergb`,
`g18_rec709`, `g22_ap1`, `g22_rec709`, `lin_adobergb`, `lin_displayp3`,
`lin_rec709` (l'espace de référence lui-même), `rec709_display`,
`srgb_texture`, `srgb_displayp3`. Toute valeur `colorSpace` posée sur
`ND_image` en dehors de cette liste n'a donc structurellement aucune
chance d'être reconnue par le CMS par défaut de mtlx, quel que soit ce que
Houdini/Karma utilise par ailleurs.

Table complétée en croisant les 13 noms Modo contre ce vocabulaire (par
nom et par description du `.ocio`, pas par supposition) :

```python
MODO_COLORSPACE_TO_USD = {
    "(default)": "",
    "linear": "lin_rec709",
    "sRGB": "srgb_texture",
    "sRGBf": "srgb_texture",       # même courbe que sRGB, juste plage flottante étendue - pas de variante mtlx dédiée
    "rec709": "rec709_display",
    "Gamma1.8": "g18_rec709",      # suppose les primaires Rec709 (seule variante Gamma1.8 de mtlx)
    "Gamma2.2": "g22_rec709",      # idem, pas la variante ACES-AP1 (g22_ap1)
    "AdobeRGB": "adobergb",        # suppose la version gamma-encodée, pas lin_adobergb
    "raw": "raw",                  # pas une transformation CMS - le token standard "pas de gestion couleur"
    "ProPhoto": "",
    "Cineon": "",
    "AlexaV3LogC": "",
    "PLogLin": "",
    "SLog": "",
}
```

**Correction au passage** : l'exemple `"linear"` → `"Linear Displayp3"`
donné par l'auteur en tête de cette discussion (Round 19) ne correspond à
rien dans le vocabulaire mtlx réel - remplacé par `"lin_rec709"` sur
confirmation explicite de l'auteur, qui a confirmé qu'il s'agissait d'un
exemple illustratif, pas d'une valeur testée en dur dans Houdini.

**Décision de l'auteur pour les 5 valeurs sans équivalent** (`ProPhoto`
et les 4 courbes log `Cineon`/`AlexaV3LogC`/`PLogLin`/`SLog`) : mappées
sur `""` (pas de métadonnée `colorSpace` posée du tout) plutôt que
laissées passer telles quelles - un nom que mtlx ne reconnaît de toute
façon pas ne vaut pas mieux qu'aucune métadonnée.

`tests/normalize/test_colorspace.py` étendu en conséquence (paramétré sur
les 8 entrées confirmées + les 5 sans équivalent) - 116 tests toujours
verts. **Portée limitée à `foundry-v1`** (la config par défaut de Modo) -
les valeurs propres aux 5 autres configs (`aces`, `Foundry-WideGamut`,
`nuke-default`, `spi-anim`, `spi-vfx`) ne sont pas dans cette table (voir
Round 21, juste après, pour ce qui leur arrive maintenant). **Pas encore
testé dans Houdini** - ces 8 mappings sont dérivés du vrai code source
mtlx, pas observés en rendu.

#### Round 21, repli uniforme sur `""` + diagnostic pour les colorspaces sans équivalent (2026-08-10)

L'auteur retire lui-même les 5 entrées `"": ""` du Round 20 (`ProPhoto`,
`Cineon`, `AlexaV3LogC`, `PLogLin`, `SLog`) de `MODO_COLORSPACE_TO_USD`,
et demande que le repli (toute valeur absente de la table, plus large que
ces 5-là - couvre aussi les 5 configs OCIO de Modo jamais mappées) devienne
`usdColorSpace=""` de façon générale, avec un diagnostic
`_DEBUG_diag("Unsupported", "Color_Management", ...)` à chaque fois que ça
se produit.

`_normalize_colorspace_channel` (`normalize/colorspace.py`) simplifiée en
conséquence : `MODO_COLORSPACE_TO_USD.get(colorspace, "")` - un seul
repli, qu'une valeur soit explicitement absente de la table (cas des 5
retirées, ou de toute config autre que `foundry-v1`) ou qu'elle soit
`"(default)"` (déjà `""` explicitement dans la table, Round 19).

**Le diagnostic lui-même ne peut pas vivre dans `normalize/colorspace.py`** -
`_DEBUG_diag` est définie dans `ShaderTree.py`, qui fait `import lx, modo`
en tête de fichier ; l'appeler depuis `normalize/` casserait la
testabilité pytest sans Modo de tout le package (l'invariant "zéro
dépendance lx/modo/fnpxr" documenté en tête de chaque passe). Précédent
déjà en place pour ce genre de cas : `normalize_projection_defaults`
résout `usdProjType` silencieusement, et c'est `_USD_create_texture_output`
(`ShaderTree.py`) qui compare `usdProjType != projType` et diagnostique -
le calcul reste dans `normalize/`, le diagnostic reste dans `ShaderTree.py`.
Même découpage appliqué ici : `normalize_colorspace` reste
diagnostic-free, et `_DEBUG_diag` est appelé directement (pas de fonction
utilitaire dédiée - demande explicite de l'auteur, plus simple qu'un
`_UTIL_diag_colorspace_fallback` séparé) aux deux points de consommation
de `usdColorSpace` dans `ShaderTree.py` : `_USD_create_UV_texture` (mtlx)
et `_USD_create_preview_UV_texture` (glPreview - au Round 21, uniquement
dans la branche `else`, `isNormal` forçant encore `'raw'` sans jamais lire
`usdColorSpace` ; ce forçage a depuis été retiré, voir Round 22
juste après).

**Effet secondaire accepté, pas un bug** : le diagnostic se déclenche
aussi pour `"(default)"`, qui résout légitimement sur `""` depuis le
Round 19 (pas d'entrée manquante, un choix délibéré). Pas de distinction
faite entre les deux cas - le message ("Colorspace (default) has no mtlx
equivalent...") est légèrement imprécis pour ce cas précis, mais
c'est le comportement demandé : plus simple qu'un test à part pour
exclure `"(default)"`, et voir ce diagnostic pour `"(default)"` reste une
information correcte (aucune métadonnée `colorSpace` n'est effectivement
posée). 116 tests toujours verts (aucun test ne dépend de `ShaderTree.py`,
qui n'est pas exécutable hors Modo - le comportement du diagnostic
lui-même reste donc non testé par pytest, comme tout `_DEBUG_diag`).

#### Round 22, forçage `"raw"`/`sourceColorSpace` retiré du réseau glPreview, mtlx et glPreview alignés (2026-08-10)

L'auteur demande de retirer, côté glPreview (`_USD_create_preview_UV_texture`)
**et** côté mtlx (`_USD_create_UV_texture`), tout ce qui teste
spécifiquement "normal" ou "sRGB" dans la résolution de colorspace, pour
ne garder que l'évaluation générique déjà posée au Round 21 :

```python
colorspaceChannel = xml.find('videoStill/channels/colorspace')
usdColorSpace = colorspaceChannel.get('usdColorSpace') if colorspaceChannel != None else None
if colorspaceChannel != None and not usdColorSpace:
    _DEBUG_diag("Unsupported", "Color_Management", f"Colorspace {colorspaceChannel.get('value')} has no mtlx equivalent, switching to default (empty value)")
if usdColorSpace:
    fileInput.GetAttr().SetColorSpace(usdColorSpace)
```

Concrètement, côté glPreview : le branchement `if isNormal: usdColorSpace
= 'raw' else: ...` (qui forçait `raw` pour les couches bump/normal,
introduit avant le Round 7) supprimé - la résolution de colorspace passe
maintenant toujours par le chemin générique, sans distinction d'effet. Le
bloc `sourceColorSpace` (`UsdUVTexture.inputs:sourceColorSpace`, l'enum
`raw`/`sRGB`/`auto` calculé à partir de `usdColorSpace`) supprimé
entièrement - plus jamais posé sur le nœud `UsdUVTexture`, quel que soit
l'effet. Seule la métadonnée `colorSpace` sur `"file"` reste câblée,
maintenant identique aux deux endroits. `isNormal` (variable) reste
utilisée ailleurs dans la fonction (unpacking scale/bias pour les normal
maps 8-bit, sans rapport avec la colorspace) - non touchée.

**Ce round ne traite volontairement pas le bug d'origine** qui a lancé
toute cette série (mtlx ne force pas `raw`/l'équivalent pour les normal
maps, glPreview le faisait avant ce round mais plus maintenant) - les deux
réseaux traitent maintenant les couches bump/normal exactement comme
n'importe quelle autre couche pour la colorspace, en attendant. Noté
explicitement par l'auteur comme un compromis temporaire : **à
retraiter dans une session future** (voir "Prochaines étapes possibles"
en fin de fichier) - décider comment forcer `raw`/l'équivalent mtlx pour
bump/normal des deux côtés à la fois, probablement dans
`normalize/colorspace.py` (qui connaît déjà `usdInputName`/
`usdPreviewInputName` via `normalize_effect_channel_names`, exécutée
avant elle dans `NORMALIZATION_PASSES`) plutôt que dupliqué dans
`ShaderTree.py`. 116 tests toujours verts (aucun test ne couvre ce
chemin, `ShaderTree.py` non exécutable hors Modo).

#### Round 23, préfixe `"<config OCIO>:"` retiré avant lookup dans la table — CONFIRMÉ PAR L'AUTEUR (2026-08-10)

En regardant un vrai export (`PF_ShaderBall_base_normalized.xml`),
l'auteur ajoute une variable globale `ocioConfig` dans
`export_basic_execute` (`ocioConfig = scene.sceneItem.channel("ocioConfig").get()`,
`ShaderTree.py` ~ligne 161) et remarque que
`imageMap/videoStill/channels/colorspace/@value`, pour un choix explicite,
est toujours préfixé par le nom de la config OCIO active suivi de `":"` -
ex. `"nuke-default:sRGB"` - exactement la même forme
`"<config>:<colorspace>"` déjà rencontrée au Round 7 pour les 4
préférences `pref.value colormanagement.*_default_colorspace`. Sans ce
retrait, `MODO_COLORSPACE_TO_USD.get("nuke-default:sRGB")` ne matchait
jamais rien (clés de la table = noms bruts, sans préfixe) et retombait
silencieusement sur `""` avec le diagnostic du Round 21/22 - un faux
"pas d'équivalent mtlx" alors que `sRGB` est bien dans la table.

Corrigé dans `_normalize_colorspace_channel` (`normalize/colorspace.py`) :
tout ce qui précède le premier `":"` est retiré avant le lookup
(`colorspace.split(":", 1)[1]` si un `":"` est présent). Fait exprès
**sans** threader `ocioConfig` en paramètre de `normalize_colorspace` -
retirer un préfixe ne demande pas de connaître le nom de la config, juste
de savoir qu'il y a un `":"` ; garde la passe uniforme/sans argument du
Round 19. La valeur brute (`value`, avec son préfixe) reste inchangée,
seul `usdColorSpace` (calculé) est affecté.

**Deux valeurs sentinelles jusqu'ici inconnues, repérées dans ce même
export réel** : `"(none)"` et `"auto"`, ni l'une ni l'autre préfixées,
aux côtés de `"(default)"`/des valeurs explicites déjà connues. Pas
encore d'entrée dédiée dans `MODO_COLORSPACE_TO_USD` - retombent sur `""`
via le repli générique du Round 21 (diagnostiquées comme "pas
d'équivalent mtlx", ce qui est un peu trompeur pour ces deux-là aussi -
même nature que `"(default)"`, ce sont probablement des sentinelles
légitimes, pas des noms de colorspace réels). Sens exact de `"(none)"`
et `"auto"` pas encore investigué - à faire si ça devient gênant.

**Autre chose repérée en passant, pas traitée ce round** : la config OCIO
active sur ce fichier de test réel est `nuke-default`, pas `foundry-v1`
(celle utilisée pour dériver `MODO_COLORSPACE_TO_USD` au Round 20) - les
deux configs partagent la plupart des noms de colorspace concernés ici
(`sRGB`, `linear`...) donc la table reste correcte pour ce cas précis,
mais rien ne garantit que ce soit vrai pour toutes les entrées ou pour
les 4 autres configs jamais vérifiées (`aces`/`Foundry-WideGamut`/
`spi-anim`/`spi-vfx`).

`ocioConfig` (variable globale ajoutée par l'auteur) n'est pour l'instant
utilisée nulle part - le retrait de préfixe n'en a pas eu besoin. Garde sa
raison d'être si une table par-config devient nécessaire plus tard (voir
le point ci-dessus). Tests étendus dans `test_colorspace.py` (préfixe
retiré avant lookup, sentinelles sans préfixe laissées telles quelles) -
122 tests toujours verts.

**Confirmé par l'auteur** : ça fonctionne (`"nuke-default:sRGB"` résout
bien vers `"srgb_texture"` sur le fichier de test réel). Les points notés
ci-dessus comme "pas encore investigués" (`"(none)"`/`"auto"`, couverture
des 4 autres configs OCIO) restent ouverts, mais le retrait de préfixe
lui-même est validé.

#### Round 24, `LookupError: attribute 0 not found` sur le bouton d'export quand verbose est off — CORRIGÉ, CONFIRMÉ PAR L'AUTEUR (2026-08-10)

Bug sans rapport avec la série colorspace, remonté par l'auteur en testant
depuis le bouton d'export dans l'UI Modo : `LookupError`,
`"attribute 0 not found"`, systématiquement quand `USDExport_verbose`
**et** `USDExport_verboseModifyTree` sont tous les deux désactivés (jamais
quand au moins l'un des deux est actif). Trace fournie par l'auteur :

```
|Python|...|Info| .. .../lxu/attributes.py: 118
|Python|...|Info| .. .../lxu/attributes.py: 101
|Python|...|Failed|Unhandled exception "LookupError"; attribute 0 not found.
```

Les deux frames pointent dans `lxu/attributes.py`, livré avec Modo lui-même
(`Contents/Resources/python3kit/.../Scripts/lxu/attributes.py`) - pas du
code de ce kit. "attribute 0" est un index, pas un nom - dans
`Cmd_ExportShaderTree.__init__` (`Scripts/lxserv/ExportShaderTree.py`),
`self.dyna_Add('item', '&item')` déclarait un unique argument dynamique
optionnel (`self.basic_SetFlags(0, lx.symbol.fCMDARG_OPTIONAL)`, donc
index 0 = `'item'`) - jamais lu nulle part (confirmé par grep sur tout le
repo ; `export_basic_execute`'s propre docstring dit déjà "`Cmd_obj`: not
used in this function"). Hypothèse (pas prouvée, `.venv` ne peut pas
exécuter de code dépendant de Modo) : le mécanisme d'écho/log de commande
interne de Modo tente de lire cet argument optionnel jamais assigné pour
logger la commande, et échoue - les `print()` de `_DEBUG_diag` (actifs
seulement quand verbose+verboseModifyTree sont tous les deux vrais)
changeraient par effet de bord l'état interne du système de log de Modo
d'une façon qui évite ce bug, expliquant pourquoi il ne se produit que
quand les deux sont désactivés. Corrélation solide (confirmée par
l'auteur : seulement quand les deux sont off), mécanisme exact non
vérifié.

Corrigé en supprimant les deux lignes (`dyna_Add`/`basic_SetFlags`) -
argument mort, sa suppression ne peut rien casser côté fonctionnel
puisqu'il n'était lu nulle part. **Confirmé par l'auteur : ne crashe plus**
avec les deux flags désactivés - le vrai mécanisme interne de Modo qui
causait le `LookupError` reste une hypothèse non vérifiée (`.venv` ne peut
pas exécuter de code dépendant de Modo pour le confirmer autrement), mais
le correctif fonctionne.

#### Round 25, `_DEBUG_diag` : un flag verbose par catégorie au lieu de deux flags combinés — CONFIRMÉ PAR L'AUTEUR (2026-08-10)

Suite du Round 24 : l'auteur redemande, indépendamment du bug corrigé,
une vraie refonte du système de verbosité. Avant ce round,
`_DEBUG_diag` n'avait que deux flags (`verbose`/`verboseModifyTree`,
tous les deux requis pour imprimer quoi que ce soit) sans lien avec la
catégorie du message (`sectionName`). L'auteur demande un flag dédié par
catégorie de message, à la place :

- `USDExport_verbose` renommé `USDExport_logValueChange`, ne gate plus
  que `"SetValue"`.
- `USDExport_verboseModifyTree` renommé `USDExport_logTreeChange`, gate
  `"USD_Connect"`/`"USD_Create"`/`"USD_CreateShader"` (ce dernier renommé
  depuis `"createUsdShader"` au Round 26, pour rester cohérent avec le
  préfixe `USD_*` des deux autres).
- Nouveau `USDExport_logFileManagement`, gate
  `"Files"`/`"Renaming"`/`"Consolidate"` (ce dernier absorbe
  `"copy_and_clean_files"` au Round 27, un doublon du même rôle).
- Nouveau `USDExport_logUndefined`, gate `"Undefined"`/`"Unsupported"`.

Ce découpage par catégorie couvre les 10 `sectionName` réellement utilisés
dans `ShaderTree.py` (vérifié par grep sur tous les appels `_DEBUG_diag`
avant d'implémenter, pas deviné) - `_DEBUG_diag` (`ShaderTree.py`)
reconstruit maintenant, à chaque appel, un petit dict
`logEnabledBySection` référençant directement les 4 globals (pas de
lookup dynamique par nom de variable façon `globals()[...]`, essayé puis
écarté - plus indirect que le reste du fichier, qui n'utilise
métaprogrammation nulle part ailleurs) ; `logEnabledBySection.get(sectionName)`
décide seul de l'impression console. L'écriture dans le XML diagnostic
(`export_diagnostic`) reste inchangée, indépendante de ces 4 flags -
seule la sortie console est concernée par ce découpage.

`_initialize_preferences()` mis à jour (4 `lx.eval('user.value
USDExport_log*  ?')` au lieu de 2) - les deux `print(f"verbose = ...")`
de debug ajoutés par l'auteur pendant le diagnostic du Round 24 ont été
retirés au passage (plus nécessaires, le bug étant résolu). Valeurs par
défaut des 4 préférences (`Cmd_ExportShaderTree.__init__`,
`ExportShaderTree.py`) : **toutes à `True`**, sur demande explicite de
l'auteur (les anciens défauts, `verbose=False`/`verboseModifyTree=True`,
n'ont pas été reconduits).

`Configs/preferences.CFG` (section `ShaderTreeExport_eventLogOptions:sheet`)
et `Configs/toolbar.cfg` (popup `SYB_USD_ShaderTreeExport_OutputOptions:sheet`,
que l'auteur avait lui-même déjà étoffé avec les 2 anciens toggles entre
deux rounds) mis à jour en parallèle : les 2 entrées existantes renommées,
2 nouvelles ajoutées, mêmes labels/tooltips dans les deux fichiers pour
rester cohérent. Choix de portée (pas demandé explicitement par
l'auteur, jugement pris en écrivant ce round) : les 4 toggles sont
présents dans les deux fichiers, pas seulement les 2 nouveaux - pour
éviter que le popup toolbar et le panneau de préférences divergent sur
lesquels des 4 sont exposés. Les deux XML validés (`ET.parse` en `.venv`,
pas juste une relecture). 122 tests toujours verts (aucun test ne couvre
`_DEBUG_diag`/les `.cfg`, tous dépendants de Modo ou hors du domaine de
pytest). **Confirmé par l'auteur dans Modo : les 4 toggles fonctionnent.**

#### Round 26, `"createUsdShader"` renommé `"USD_CreateShader"` (2026-08-10)

Nettoyage mineur demandé par l'auteur en relisant le fichier diagnostic
généré : `sectionName` mélangeait des styles de nommage
(`"USD_Create"`/`"USD_Connect"` vs `"createUsdShader"`, casse et ordre des
mots différents pour un rôle comparable). Renommé en `"USD_CreateShader"`
pour rester cohérent avec le préfixe `USD_*` des deux autres - 3 sites
dans `ShaderTree.py` (l'entrée `logEnabledBySection` de `_DEBUG_diag` et
ses 2 points d'appel, création du shader preview et du shader mtlx). 122
tests toujours verts (aucun test ne couvre ce nom directement).

#### Round 27, `"copy_and_clean_files"` fusionné dans `"Consolidate"` (2026-08-10)

Même genre de nettoyage que le Round 26 : `"copy_and_clean_files"`
(2 sites, dans `_UTIL_copy_and_clean_files`) et `"Consolidate"` (3 sites,
dans la fonction voisine qui copie/consolide les textures) couvraient le
même rôle sous deux noms différents. Auteur : remplacer
`"copy_and_clean_files"` par `"Consolidate"` partout, puis retirer
l'entrée devenue redondante dans `logEnabledBySection`. Les deux noms
gardaient de toute façon le même flag (`logFileManagement`), donc aucun
changement de comportement - purement un nettoyage de nommage. 122 tests
toujours verts.

#### Round 28, effet "stencil" : trois bugs mtlx corrigés + glPreview ajouté — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO/HOUDINI (2026-08-10)

L'auteur demande de travailler sur l'effet "stencil" (`_USD_connect_texture_output_to_shader_input`,
`ShaderTree.py`). Trois bugs réels trouvés en investigation (vérifiés contre le
vrai paquet `MaterialX` standalone et `usd-core` dans `.venv`, pas supposés) :

1. **Id de nœud invalide** : `'ND_invert' + str(outputType)` produisait
   `"ND_invertfloat"` (pas de underscore) au lieu de `"ND_invert_float"` -
   même famille de bug que `ND_normalmap`→`ND_normalmap_float` (étage 3).
   Corrigé en réutilisant `_UTIL_get_node_type_prefix`, déjà utilisé partout
   ailleurs dans le fichier pour construire ce genre d'id (`ND_mix`,
   `ND_multiply`, l'invert générique de `_USD_create_texture_adjust_nodegraph`...) -
   le code stencil ne le faisait pas, seul endroit du fichier à construire
   son id à la main.
2. **Le trick invert+round était mort** : le code générique juste après le
   bloc `if effectName == "stencil":` (partagé par tous les effets)
   reconnectait inconditionnellement l'input `"opacity"` du shader vers
   `output` (la texture brute, non traitée) - écrasant la connexion vers
   `roundShader` que le bloc stencil venait de faire. Vérifié avec
   `usd-core` : `UsdShade.Input.Get()` retourne `None` sur un input
   fraîchement connecté (pas de valeur par défaut authored), donc ce code
   partait toujours dans la branche qui recrée la connexion depuis
   `output`. Résultat concret : une couche stencil rendait comme un masque
   d'opacité en niveaux de gris continu, pas le cutout dur (0 ou 1)
   qu'implémentait le trick. Corrigé en réassignant la variable locale
   `output` vers la sortie du nœud traité (même pattern déjà utilisé par la
   branche `displace`, qui n'avait pas ce bug pour cette raison précise) au
   lieu de connecter manuellement `shader` dans le bloc stencil - le code
   générique fait maintenant le travail correctement.
3. **Découvert en creusant le bug 2, plus large que "stencil"** :
   `usdTypeMap["opacity"]` (`ShaderFilters/usd_types.py`) vaut `Float`,
   mais l'input `"opacity"` réel de `ND_standard_surface_surfaceshader` est
   `color3f` (vérifié directement contre le vrai nodedef MaterialX,
   confirmé par `node_registry.py` qui l'avait déjà correctement catalogué -
   `usd_types.py` n'avait jamais été croisé avec ce registre pour cette
   entrée précise). `usdTypeMap` est une table **partagée** entre le shader
   mtlx et `UsdPreviewSurface` (le commentaire en tête du fichier le dit
   explicitement) - et `UsdPreviewSurface.inputs:opacity`, lui, est bien
   `float` (vérifié dans `shaderDefs.usda`). Les deux schémas utilisent
   donc le même nom `"opacity"` pour deux types différents - la seule
   collision de ce genre trouvée dans la table. Comme "stencil" pointe
   aussi vers `"opacity"` dans `stdMatChannelMap['principled'/'gtr']`, ce
   bug ne touchait pas que les couches stencil : le channel `"opacity"`
   propre de **tout** matériau Principled (le slider de transparence
   générique de Modo) créait déjà un input mal typé. Resté invisible
   jusqu'ici parce que `standard_surface` défaut `opacity` à `(1,1,1)`
   (opaque) et que Modo défaut aussi à opaque - la valeur mal typée
   coïncidait avec le défaut la plupart du temps.

   Corrigé **sans** changer `usdTypeMap["opacity"]` (ça casserait le côté
   glPreview, qui a raison) : le type `color3f` est spécialisé localement,
   aux deux seuls points de construction de l'input mtlx `"opacity"`
   (`_USD_create_mtlx_standard_surface_shader` pour la valeur littérale du
   channel, le code générique de `_USD_connect_texture_output_to_shader_input`
   pour la connexion texture-driven), avec `isPreview`/le nom d'input comme
   discriminant. `_USD_create_shader_input` (le convertisseur `value string
   -> sdfValue`) élargi pour diffuser un scalaire en `(v, v, v)` quand la
   chaîne ne ressemble pas déjà à un tuple - nécessaire parce que
   `opacity`/`stencil` sont de vrais scalaires côté Modo (sliders
   d'amount), contrairement à `diffCol` etc. dont la chaîne est déjà
   tuple-formatée ; vérifié que `.Set()` plante net sur un mismatch de
   type scalaire/color3f (`usd-core`), donc ce cas devait être géré, pas
   juste supposé fonctionner. Le bloc stencil pont Float->Color3f avec un
   nouveau nœud `ND_convert_float_color3` (vérifié qu'il existe dans le
   vrai stdlib, `float -> color3`) juste avant le point de connexion
   générique - toute la chaîne interne (texture, invert, round) reste en
   Float, seule la toute dernière étape convertit.

**glPreview ajouté pour stencil** (absent avant ce round - `"stencil"`
manquait de `USD_PREVIEW_INPUT_NAME_BY_EFFECT`, donc une couche stencil
n'avait strictement aucun effet sur le matériau preview) : `"stencil":
"opacity"` ajouté à la table (`normalize/effect_channel_names.py`).
`UsdPreviewSurface` a un vrai input `opacityThreshold` natif pour le
cutout dur - pas besoin de reproduire le trick round() côté preview, donc
`_USD_create_preview_UV_texture` n'ajoute que l'inversion (1-x) (même
convention hardcodée que le trick mtlx, composée par-dessus l'invert/
brightness déjà géré par la couche - même pattern que `isNormal`), et le
bloc stencil de `ShaderTree.py` pose un littéral `opacityThreshold = 0.5`
sur `previewShader` quand une texture stencil est effectivement connectée
(`effectName in context.previewOutputs`) - la connexion `opacity`
elle-même passe par le mécanisme générique déjà en place
(`context.previewOutputs`/`context.effectPreviewInputNames`), pas de code
dédié en plus.

**Décision de conception, pas dérivée de faits vérifiés (pas de Modo pour
tester)** : `opacityThreshold = 0.5` est un choix arbitraire (seuil de
cutout à mi-chemin) - raisonnable mais pas testé en rendu. Aussi non
vérifié : que la sémantique "inverser le canal stencil brut" (le trick
existant côté mtlx, appliqué tel quel côté glPreview par ce round) soit
effectivement ce que fait Modo - c'était déjà une hypothèse non
documentée avant ce round, seulement héritée du code existant.

Toute la chaîne de nœuds (ids, types, connexions) vérifiée directement
contre le vrai paquet `MaterialX` standalone et `usd-core` en construisant
le graphe stencil complet dans `.venv` (pas juste une relecture). 123 tests
pytest verts (`tests/normalize/test_effect_channel_names.py` mis à jour :
`stencil` déplacé vers la liste des effets glPreview résolus, remplacé par
`objectNormal` pour le test "pas d'équivalent glPreview"). **Rien de tout
ça n'est testé dans Modo/Houdini** - priorité pour la prochaine session
avec un fichier de test contenant une couche stencil (absente de
"PF_ShaderBall_base" jusqu'ici, comme bump/normal/`<constant>`).

Deux corrections faites en aparté dans ce round, sur demande de l'auteur :
- Un `_` en trop ajouté à la main par l'auteur dans
  `'ND_invert_' + _UTIL_get_node_type_prefix(outputType)` (le helper
  retourne déjà `"_float"` avec son propre underscore) produisait
  `"ND_invertfloat"` → `"ND_invert__float"`, toujours invalide. Revenu à
  `'ND_invert' + _UTIL_get_node_type_prefix(outputType)`.
- `_UTIL_get_node_type_prefix` appliqué à `displace` (id résultant
  identique à l'id déjà en dur, `ND_displacement_float` - vérifié sûr) sur
  demande de l'auteur, mais **pas** à `bump`/`normal` : vérifié contre le
  vrai stdlib MaterialX que le helper produirait `"ND_bump_color3"` (le
  helper n'a pas de variante `vector3`, seulement `_float`/`_color3`/
  `_color4`) au lieu du seul id réel `ND_bump_vector3`, et que le suffixe
  de `ND_normalmap` reflète le type du paramètre `scale` (float vs
  vector2), pas le type de sortie - les deux restent donc en dur,
  commentés pour expliquer pourquoi.

#### Round 29, `bump` cassait à l'export réel dans Modo (`AttributeError`) + même bug de fallthrough que stencil corrigé pour bump/normal — CONFIRMÉ DANS HOUDINI POUR `bump` (2026-08-11, retest confirmé 2026-08-13)

Premier test réel dans Modo d'une couche bump (jusqu'ici jamais exercée par
"PF_ShaderBall_base") : crash immédiat,
`AttributeError: 'Output' object has no attribute 'GetOutput'` sur
`shader.CreateInput("normal", ...).ConnectToSource(textureOutput.GetOutput('out'))`
(`_USD_connect_texture_output_to_shader_input`, branche `bump`).
`textureOutput` est un `UsdShade.Output` (pas un `UsdShade.Shader`/
`ConnectableAPI`) - `.GetOutput()` n'existe pas sur ce type, seul
`.ConnectToSource()` a un sens dessus. La ligne visait en fait la sortie de
`normalShader` (le nœud `ND_bump_vector3` qui vient d'être créé juste
au-dessus), pas `textureOutput` (la texture brute, non traitée par le
bump map).

En corrigeant, même bug que le stencil du Round 28 (bug #2) trouvé dans
`bump` **et** `normal` : même après avoir fixé la ligne pour cibler
`normalShader.GetOutput('out')`, le code générique juste après le bloc
`if/elif` (celui qui reconnecte toujours `shader.GetInput(inputName)`
depuis la variable locale `output`) écrase cette connexion avec la texture
brute, puisque `output` n'était jamais réassigné dans ces deux branches
(contrairement à `displace`, qui le faisait déjà - c'est précisément pour
ça que `displace` n'avait pas ce bug). Concrètement : le nœud
`ND_bump_vector3`/`ND_normalmap_float` était construit dans le graphe mais
jamais réellement utilisé par le shader - `"normal"` recevait la couleur
brute de la texture, pas une normal map décodée.

Corrigé pour les deux branches, même pattern que `displace`/`stencil` :
suppression de la connexion manuelle à `shader`, `output` réassigné vers
la sortie du nœud traité (`normalShader.CreateOutput(...)`) pour que le
code générique fasse la connexion correctement. Vérifié en reconstruisant
la chaîne contre `usd-core` : `shader.inputs:normal` pointe bien vers
`..._bumpMap` (le nœud `ND_bump_vector3`), pas vers la texture. 123 tests
toujours verts. **`normal` n'a pas encore été testée dans Modo** (seul
`bump` a crashé/été testée ce round) - même classe de bug, donc corrigée
par cohérence, mais pas confirmée en rendu.

**Retesté et confirmé par l'auteur le 2026-08-13** pour `bump` : le rendu
est correct. L'auteur note au passage une **légère différence sur la
spécularité** entre Modo et Houdini sur ce même test - pas creusée ce
round (hors sujet du bump lui-même), voir Round 59 juste après pour le
suivi dédié. `normal` reste non testée - voir la liste de tests toujours
ouverte en tête de fichier.

#### Round 59, différence de spécularité repérée en testant le bump (Round 29) — DEUX BUGS RÉELS CORRIGÉS ET CONFIRMÉS, UNE LIMITE CONNUE ACCEPTÉE, CLOS POUR L'INSTANT (2026-08-13)

En retestant le Round 29 (bump), l'auteur remarque une légère différence
sur les réflexions spéculaires entre le rendu Modo et le rendu Karma - pas
assez caractérisée sur le coup pour en tirer une cause. Décision : au lieu
de deviner, construire une matrice de test isolée (14 shader balls, un seul
paramètre spéculaire varié par bille, base `diffCol` neutre) couvrant
`brdfType` (gtr/principled) × `useRefIdx` × `specRefIdx` × `metallic` ×
`specTint`/`specCol` - même discipline que le reste de cette session
(isoler une variable à la fois plutôt que de chasser un rendu qui mélange
tout).

**Fichiers de test réels fournis par l'auteur** (scène "Specular tests_01",
"PF_ShaderBall") : `Specular tests_01_normalized.xml` et
`Specular tests_01.usda`, plus un rendu Modo et un rendu Karma des 14
billes côte à côte. Comparaison directe des trois (XML normalisé, `.usda`
construit, rendus) - 13 des 14 cellules correspondaient exactement à la
matrice demandée. Deux billes se sont démarquées visuellement dans les
deux rendus : `M_Ball_principled_4` (chrome brillant dans Modo, noir pur
dans Houdini) et `M_Ball_principled_8` (sombre dans Modo, chrome/miroir
éclatant dans Houdini) - `M_Ball_principled_9` un peu moins marqué mais
dans le même sens.

**Cause 1, `M_Ball_principled_4`** : la bille a été montée avec
`refIndex="0.2"` dans Modo, pas `1.2` comme demandé - une valeur d'IOR
inférieure à 1.0 est hors du domaine physique valide (rien n'a un indice
de réfraction inférieur au vide). Probablement une faute de frappe de
configuration, pas un bug de l'export - **à corriger dans Modo (remettre
1.2) et re-tester** pour obtenir une lecture propre du passthrough direct
d'IOR à cette valeur.

**Cause 2, `M_Ball_principled_8`/`9`, bug réel trouvé et corrigé** :
les deux ont `specAmt="1.0"` (leur max) en brut, et `_ior_from_spec_amt`
(`normalize/specular_ior.py`) avec sa saturation par défaut (`.99999`)
envoie ça vers un IOR **quasi infini** - confirmé dans le `.usda` :
`specular_IOR = 399998`. Vérifié algébriquement : le dénominateur
`1 - sqrt(specAmt * saturation)` tend vers zéro quand `specAmt` tend vers
`1/saturation`, donc le résultat explose - le garde-fou existant
(`saturation=.99999`) évite seulement une vraie division par zéro, pas
une valeur absurde. `M_Ball_GTR_2` (`specAmt=0.8` avec la même formule,
même saturation par défaut) donne un IOR ≈ 17.9 et **rend de façon
cohérente entre Modo et Houdini** dans ce même test - preuve empirique
qu'un IOR dérivé "élevé mais borné" est sans problème, seul l'emballement
vers l'infini près de `specAmt=1.0` casse l'accord entre les deux moteurs
(probablement une divergence dans la façon dont chacun gère un Fresnel à
IOR extrême en flottant).

Corrigé : nouvelle constante `_MAX_DERIVED_IOR = 20.0` dans
`specular_ior.py`, valeur choisie **empiriquement** (pas arbitraire) -
c'est précisément la plage déjà confirmée cohérente entre les deux moteurs
par le cas `GTR_2` ci-dessus, pas un chiffre rond choisi au hasard.
`_ior_from_spec_amt` retourne maintenant `min(..., _MAX_DERIVED_IOR)`.
Un seul point de correction protège les 3 sites d'appel (`gtr`/`not
useRefIdx`, `principled`/`useRefIdx=0`, et `principled`/`specRefIdx=1` -
ce dernier était déjà à l'abri grâce à sa saturation `.8`, mais bénéficie
du même filet de sécurité). 2 nouveaux tests ajoutés
(`tests/normalize/test_specular_ior.py`, un par branche gtr/principled,
`specAmt="1.0"` → `refIndex` capé à `_MAX_DERIVED_IOR`) - 125 tests pytest
toujours verts.

**Retest 1 confirmé par l'auteur** (même scène, `refIndex` de
`M_Ball_principled_4` corrigé à `1.2`) : les billes 4, 8 et 9 rendent
maintenant de façon nettement plus cohérente entre Modo et Karma - plus
d'écart flagrant. **Un écart subsiste sur `M_Ball_principled_7`**
(`useRefIdx=1`/`specRefIdx=1`/`specAmt=0.8`, `refIndex` dérivé = `9.0`,
donc largement sous le cap) - sombre dans Modo, chrome/miroir éclatant
dans Karma. Comme son `refIndex` n'est pas extrême, ce n'est pas
(seulement) le bug du cap - cause encore non identifiée à ce stade.

**Retest 2 (scène "Specular tests_02"), suite à une proposition de
l'auteur** : dupliquer les 5 billes GTR déjà confirmées cohérentes
(1-5) en changeant uniquement `brdfType` vers `principled`, mêmes valeurs
brutes sinon (`specRefIdx=0`, `specTint=0`, `metallic=0` sur les 5
doublons, `diffCol` changé de `(0,0,0)` à `(0.5,0.5,0.5)` par l'auteur -
pour que le test `specTint` reste valide si repris plus tard). Objectif :
isoler si une éventuelle divergence Modo/Karma vient du *brdfType*
lui-même ou des formules d'override propres à `normalize_specular_ior`.

Deux asymétries de formule identifiées et signalées **avant** le test (pas
des bugs - des différences déjà présentes dans le code, à connaître pour
interpréter le résultat) : pour les billes `useRefIdx=1` (jumelles des
GTR 3/4), `specAmt` reste brut côté gtr (`0.04`, jamais touché dans cette
branche) mais est **toujours** recalculé côté principled via
`_saturating_curve(refIndex, 20)` (`0.8`/`0.94`) - confirmé exactement
dans le XML exporté. Malgré cet écart de valeur exportée, **les rendus
Modo et Karma sont restés cohérents entre les deux rangées** (gtr vs
principled) et entre les deux moteurs pour chaque bille - aucune nouvelle
divergence détectée par ce test, contrairement à P4/P7/P8/P9. Ce test
utilisait `specRefIdx=0` partout (sur suggestion explicite pour rester
dans la branche la plus proche du passthrough gtr) - **ne couvre donc
toujours pas** la branche `specRefIdx=1` du P7 non résolu.

**Retest 3 (même fichiers, écrasés), suite à une nouvelle proposition de
l'auteur** : 5 billes GTR + 5 Principled jumelles, `useRefIdx=0` partout,
balayage complet de `specAmt` (`0.0`/`0.2`/`0.4`/`0.6`/`0.8`). Confirmé
dans le XML : `refIndex` dérivé strictement identique bille à bille entre
gtr et principled (même formule exacte dans cette branche, pas
d'asymétrie ici) - de `1.0` (à `specAmt=0`, IOR du vide, aucune réflexion
Fresnel attendue) jusqu'à `17.9` (à `specAmt=0.8`, sous le cap). Rendu :
progression cohérente et fluide dans les 4 images (Modo/Karma ×
gtr/principled), y compris à `specAmt=0` (bille plate/mate dans les 4,
comme attendu physiquement) - **confirme la branche `useRefIdx=0` sur
toute sa plage, pour les deux `brdfType`**.

**Bilan à ce stade** : la branche `useRefIdx=0` (les deux `brdfType`) est
confirmée cohérente sur toute sa plage de `specAmt`. Seule la branche
`useRefIdx=1`/`specRefIdx=1` (celle de `M_Ball_principled_7`, formule
`_ior_from_spec_amt(specAmt, .8)` puis `_saturating_curve(x, k=100)`)
reste non isolée et est la seule piste encore ouverte pour expliquer P7.
Prochain test proposé : dupliquer P6/P7 (`specRefIdx=1`) à côté d'un
équivalent `specRefIdx=0` à `refIndex` assorti, pour isoler si c'est
spécifiquement la courbe `k=100`/la double dérivation qui casse l'accord
avec le rendu natif de Modo.

**Retest 4 (même fichiers, écrasés), résultat d'une erreur de configuration
- bug réel trouvé et corrigé quand même** : en essayant de monter le test
`specRefIdx=1` proposé ci-dessus (5 billes GTR + 5 Principled), l'auteur a
laissé `specRefIdx=0` sur les 5 billes Principled et posé `refIndex=0.1`
à `0.9` (au lieu de `specAmt`) - donc en réalité un balayage de la branche
`useRefIdx=1`/`specRefIdx=0` **déjà confirmée cohérente**, mais avec des
valeurs de `refIndex` **hors du domaine physique valide** (`< 1.0` - rien
n'a un indice de réfraction inférieur au vide). Confirmé dans le XML :
`refIndex` brut = `0.1`/`0.3`/`0.5`/`0.7`/`0.9`, `specAmt` brut resté à
`0.0`-`0.8` (copié de la rangée GTR, sans effet dans cette branche).

Résultat, sans rapport avec le test prévu mais précieux : **les 5 billes
Principled rendent en gris plat, aucune spécularité visible, dans Karma -
sur toute la rangée**, alors que Modo montre encore une réponse graduée
(pas nulle) sur la même plage. Le même symptôme que la faute de frappe du
Round 59/retest 1 (`M_Ball_principled_4`, `refIndex=0.2`), mais confirmé
cette fois sur un balayage complet de 5 points plutôt qu'un seul cas
isolé - la coïncidence n'est plus plausible, c'est un vrai effet de seuil.
Vérifié algébriquement : dans cette branche, `specAmt` est **dérivé** de
`refIndex` via `_saturating_curve(refIndex, 20)` - avec `refIndex < 1.0`,
cette formule produit aussi un `specAmt` **supérieur à 1.0** (jusqu'à
`2.0` à `refIndex=0.9`) - une seule cause racine, deux symptômes hors
domaine.

Corrigé (`specular_ior.py`), sans attendre de confirmation sur la valeur
(contrairement à `_MAX_DERIVED_IOR`, `1.0` n'est pas un chiffre choisi
empiriquement - c'est le plancher physique littéral) : nouvelle constante
`_MIN_IOR = 1.0`. Deux points de clampage, aux deux seuls endroits où un
`refIndex` brut (potentiellement invalide, jamais validé côté Modo) entre
dans le pipeline sans être re-dérivé depuis `specAmt` (qui lui reste
toujours `>= 1.0` par construction de `_ior_from_spec_amt`, donc jamais
besoin d'un clamp bas) :
- gtr, branche `useRefIdx=1` (jusqu'ici totalement intouchée - aucune
  override n'était calculée, `refIndex` traversait tel quel via le repli
  `updates.get(...)` de `_normalize_material`) - ajout d'un `elif`
  explicite qui pose `updates['refIndex'] = max(float(refIndex),
  _MIN_IOR)`.
- principled, branche `useRefIdx=1`/`specRefIdx=0` - `x = refIdx` devient
  `x = max(refIdx, _MIN_IOR)`, clampé **avant** d'alimenter à la fois
  `_saturating_curve` (pour `specAmt`) et `updates['refIndex']` - corrige
  les deux symptômes en un seul point, plutôt que de clamper la sortie
  `refIndex` après coup sans corriger le `specAmt` déjà mal dérivé.

**Vérifié** : les 5 valeurs `refIndex` du retest 4 (`0.1`-`0.9`) donnent
maintenant toutes `refIndex(usd)=1.0`/`specAmt(usd)=0.0` une fois repassées
dans `normalize_specular_ior` - cohérent physiquement (IOR = celui du
milieu environnant → réflectance de Fresnel nulle → specular amount nul
aussi, pas juste "plus cassé"). Aucune régression sur les valeurs déjà
confirmées (`refIndex >= 1.0` reste inchangé, `max(x, 1.0)` est une
identité dans ce cas). 2 nouveaux tests ajoutés (un par branche gtr/
principled) - 127 tests pytest toujours verts.

**Pas encore retesté dans Houdini** - le test `specRefIdx=1` initialement
prévu (P6/P7, toujours la seule branche non isolée) reste à refaire, cette
fois avec `specRefIdx` effectivement mis à `1` sur la rangée Principled et
`specAmt` (pas `refIndex`) comme variable balayée - voir le tableau déjà
donné à l'auteur pour les valeurs exactes.

**Retest 5, `specRefIdx=1` finalement testé mais valeur d'entrée trop
faible pour être concluant** : l'auteur reproduit la config de P7 avec un
balayage de `diffCol` (noir à gris), mais `specAmt` brut vaut `0.008` (pas
`0.8` demandé - coquille de saisie). À `specAmt=0.008`, `specRefIdx=1`
dérive un `refIndex` à peine `1.17` - une réflectivité trop faible pour
qu'un éventuel écart Modo/Karma soit visible, quel que soit `diffCol`.
Résultat sans valeur diagnostique, corrigé au retest suivant.

**Retest 6, `specAmt=0.8` correctement appliqué cette fois (identique à
P7), `diffCol` toujours balayé de noir à gris clair** : **écart confirmé,
et présent sur tout le balayage de `diffCol`, pas seulement au noir pur**.
Ça élimine l'hypothèse `diffCol` posée après le Retest 4/5 - la cause
réelle est bien la branche `specRefIdx=1` elle-même (formule
`_ior_from_spec_amt(specAmt, .8)` puis `_saturating_curve(x, k=100)`,
tous les deux qualifiés de "magic number" dans leurs propres commentaires
depuis le début, jamais validés).

**Retest 7, balayage de `specAmt` (`0.1`→`0.9`) à l'intérieur de
`specRefIdx=1`, `diffCol` fixe cette fois, rangée GTR de référence avec
`refIndex` posé directement aux mêmes valeurs cibles** : l'auteur note
d'abord un "bon accord" GTR/Principled **dans Karma** - mais la vraie
question (Modo vs Karma pour Principled) restait à vérifier séparément.
Comparaison directe demandée : **`Principled 1` (le `refIndex` dérivé le
plus bas, `1.79`) rend ~20% plus lumineux dans Modo que dans Karma ;
`Principled 5` (`refIndex` dérivé le plus haut, `12.2`) rend à peu près
pareil dans les deux**. Diagnostic : **la plage dynamique de Karma pour
cette branche est plus large que celle de Modo** - Karma part plus sombre
au bas de la plage et rejoint Modo seulement en haut, alors que le rendu
natif de Modo pour son propre curseur `specAmt` (0.1→0.9) reste
comparativement plat/compressé sur toute la plage. Confirme que ce n'est
pas seulement un problème de valeur extrême (le Round 59 initial, à
`specAmt=1.0` donnant un IOR quasi infini) - c'est la forme entière de la
courbe de conversion `specAmt` → `(specular, specular_IOR)` qui ne
reproduit pas fidèlement la réponse native de Modo pour cette branche
précise.

**Décision de l'auteur (2026-08-13)** : contrairement aux deux bugs
précédents (blowup près de `specAmt=1.0`, `refIndex < 1.0`) - tous les
deux clairement des valeurs hors domaine physique, corrigées avec
confiance - cet écart de forme de courbe n'a pas de correction évidente
sans un vrai travail de calibration empirique (échantillonnage de
luminance pixel par pixel, pas à l'œil, potentiellement une refonte de la
stratégie de traduction plutôt qu'un simple ajustement de constante). Vu
que l'environnement lumineux (HDRI/colorspace/interprétation) diffère
déjà entre Modo et Karma indépendamment de ce code (confirmé par plusieurs
faux-positifs de cette même session - Round 6/7/8 avaient déjà attribué à
tort des différences de rendu à des bugs de blend/colorspace alors que
c'était un bug de pivot de tuilage), l'auteur juge le résultat actuel
"suffisamment bon pour l'instant" et clôt ce point - **`useRefIdx=1`/
`specRefIdx=1` reste une limite connue et acceptée**, pas retravaillée
plus avant cette session.

**Bilan complet du Round 59** : deux bugs réels trouvés et corrigés,
confirmés en rendu réel - le blowup de l'IOR dérivé près de `specAmt=1.0`
(`_MAX_DERIVED_IOR=20.0`) et le passthrough d'un `refIndex < 1.0`
physiquement invalide (`_MIN_IOR=1.0`), tous les deux dans
`specular_ior.py`. Toutes les branches sauf `useRefIdx=1`/`specRefIdx=1`
sont confirmées cohérentes entre Modo et Karma après une série de tests
isolant chaque variable (brdfType, `useRefIdx`, `metallic`, `specTint`,
`diffCol`, et enfin `specRefIdx` lui-même). `useRefIdx=1`/`specRefIdx=1`
reste la seule branche avec un écart résiduel (forme de courbe, pas une
valeur invalide) - accepté comme limite connue, à documenter dans le
README, pas de piste de correction retenue pour l'instant.

#### Round 30, crash `AttributeError: 'NoneType' object has no attribute 'GetFullName'` dans `_USD_connect_operator` — CORRIGÉ, CONFIRMÉ PAR L'AUTEUR DANS MODO (2026-08-11)

Nouveau crash à l'export réel dans Modo, repéré par l'auteur juste après le
Round 29, sur un effet dont la pile a au moins une couche texture.
Traceback : `_USD_connect_effect_stack` → `_USD_connect_operator`, plante
sur `input.GetFullName()` dans la ligne de diagnostic (`input` est le
paramètre nommé `input`, en réalité l'`output` accumulé passé par
l'appelant).

Cause : dans `_USD_connect_effect_stack`, `output` (la valeur de base sur
laquelle la première couche de la pile doit se blender) part à `None`
(ligne 796) et n'est réassigné que si
`context.advancedMaterialChannels.find(modoInputName) != None` (ligne
804) - c'est-à-dire seulement si l'`advancedMaterial` courant a
effectivement un channel litéral correspondant au `usdInputName` de cet
effet (via le lookup inverse déjà connu comme fragile, décision ouverte
n°4 en fin de fichier - **pas confirmé que ce soit la cause exacte de
l'absence de match ici**, juste le mécanisme par lequel `output` peut
rester `None`). Quand ce channel n'existe pas dans les channels de ce
matériau précis, `output` reste `None` et part tel quel dans
`_USD_connect_operator` comme `input` - qui jusqu'ici supposait toujours
recevoir un vrai `UsdShade.Output`, aussi bien pour la ligne de
diagnostic (`.GetFullName()`, le crash observé) que plus loin pour
construire le nœud de mix (`_USD_set_or_connect(..., input)` aurait
ensuite planté différemment, sur `eval(None)`, si le diagnostic n'avait
pas planté en premier).

Corrigé dans `_USD_connect_operator` (`ShaderTree.py`) : un `input is
None` en entrée de fonction fait maintenant un retour anticipé qui laisse
passer la texture de la couche telle quelle (`return output`, où `output`
ici est `connector.output` - la sortie déjà traitée de cette couche),
sans tenter de construire un nœud de mix contre rien - même pattern déjà
utilisé juste en dessous pour un blend mode non supporté (ligne
749-751). Sémantiquement cohérent : blender une texture contre "aucune
valeur de base" n'a pas de sens, donc la première couche devient
directement le résultat, comme si elle était seule dans la pile.

**Confirmé par l'auteur dans Modo : le crash a disparu.** Le comportement
visuel résultant (est-ce que "passer la texture telle quelle" est
effectivement ce qui est attendu pour l'effet concerné) n'a pas fait
l'objet d'un retour séparé - seule la disparition du crash a été
confirmée. Reste ouverte la question de fond, pas traitée ce round :
*pourquoi* le channel de fallback était absent pour ce cas précis -
possiblement liée à la décision n°4 (lookup inverse toujours basé sur
`'principled'`, jamais sur le `brdfType` réel du matériau), possiblement
une toute autre raison - à creuser si un symptôme visuel lié à ça
apparaît.

#### Round 31, icônes `‼️`/`⁉️` de `LOG_ICON_BY_SECTION` invisibles dans la console live de Modo — CORRIGÉ, CONFIRMÉ PAR L'AUTEUR DANS MODO (2026-08-11)

L'auteur signale, en comparant le log d'événements Modo exporté (`.md`,
complet et correct) à ce qui s'affiche réellement dans la console live de
Modo : les lignes utilisant l'icône `‼️` ("Unsupported") sont absentes de
l'affichage live, alors qu'elles sont bien présentes dans l'export - donc
pas un message jamais généré (le seul `print()` du fichier,
`_DEBUG_diag`, ligne 130, est un simple f-string mono-ligne, aucun moyen
d'y produire une chaîne vide ou un `\n` supplémentaire), mais un problème
d'affichage propre au widget console de Modo pour ce caractère précis.

Cause probable (pas vérifiable sans Modo, mais cohérente avec le seul
point commun entre les deux icônes cassées et absent des 7 autres qui
s'affichent bien) : `‼️` (`U+203C` + `U+FE0F`) et `⁉️` (`U+2049` +
`U+FE0F`) sont des caractères du bloc "Dingbats/ponctuation" (hérités de
l'ère pré-emoji), qui n'ont **pas** la présentation emoji par défaut - le
sélecteur de variante `U+FE0F` est *nécessaire* pour forcer leur rendu en
emoji plutôt qu'en glyphe texte. Les 7 autres icônes de la table
(`💾📦📍🎱🔗`, sans sélecteur de variante, et `🎚️`/`🏷️`, qui en portent un
mais sur un caractère déjà emoji par défaut du bloc pictogrammes
`U+1F300+`, où le sélecteur ne fait rien) n'ont pas ce besoin. Le rendu de
console de Modo semble ne pas savoir gérer cette conversion
texte-vers-emoji forcée par sélecteur de variante sur un caractère du
bloc ponctuation, et affiche une ligne vide au lieu de se rabattre sur le
glyphe texte.

Corrigé dans `LOG_ICON_BY_SECTION` (`ShaderTree.py`) : proposé initialement
avec deux icônes distinctes (`"Unsupported"` → `🚫`, `"Undefined"` → `🧩`,
toutes deux `U+1F300+`, bloc pictogrammes, comme les 7 icônes qui
fonctionnent déjà) ; l'auteur a ensuite simplifié lui-même à une seule
icône partagée, `🚫` pour les deux catégories. Purement cosmétique (la
table de diagnostic XML n'est pas affectée, seul l'affichage console
l'est - voir le commentaire déjà présent au-dessus de la table). 123 tests
toujours verts (aucun test ne couvre `_DEBUG_diag`/cette table,
dépendante de Modo). **Confirmé par l'auteur dans Modo** : les lignes
`Unsupported`/`Undefined` s'affichent maintenant correctement dans la
console live - l'hypothèse du sélecteur de variante sur un caractère
hors du bloc pictogrammes était la bonne cause.

#### Round 32, `displace` : attribut `inputs:displacement` mort sur le shader mtlx — CORRIGÉ, CONFIRMÉ DÉJÀ CORRECT DANS HOUDINI PAR L'AUTEUR (2026-08-11)

Chantier ouvert par l'auteur sur l'effet displacement. Confirmé par
l'auteur en premier lieu : **la branche `displace` fonctionne déjà
correctement** - elle crée un nœud `ND_displacement_float`, reconnu par
le graphe Houdini, connecté sur `material.outputs:mtlx:displacement` (pas
sur le shader `standard_surface`) - c'est le comportement attendu, pas un
bug (le displacement MaterialX n'est jamais un input du surface shader,
toujours une sortie séparée du matériau - confirmé contre le vrai
nodedef `ND_standard_surface_surfaceshader` via `node_registry.py` :
aucun input `"displacement"` dans sa liste réelle d'inputs).

Ce qui a été trouvé et corrigé, indépendant du fonctionnement ci-dessus :
le code générique juste après le bloc `if/elif` de
`_USD_connect_texture_output_to_shader_input` (celui qui câble
normalement `shader.GetInput(inputName)` pour bump/normal/stencil)
s'exécutait aussi, sans condition, pour `"displace"` - créant un
`inputs:displacement` sur le shader `standard_surface` lui-même. Comme ce
nom n'existe pas dans le vrai nodedef, USD ne plante pas mais n'en fait
rien (même famille de piège que le bug `wrapS`/`wrapT` sur `ND_image`
documenté plus haut) - un attribut mort, jamais lu par personne, en plus
de la connexion déjà correcte faite dans la branche `displace` elle-même.
Sans conséquence sur le rendu (confirmé par l'auteur, le graphe rendait
déjà correctement dans Houdini avant ce round), donc traité comme un
nettoyage de graphe, pas un bug fonctionnel.

Corrigé dans `_USD_connect_texture_output_to_shader_input` (`ShaderTree.py`) :
le code générique de câblage mtlx est maintenant sauté pour `"displace"`
(`if effectName != "displace":`) - la branche `displace` capture
elle-même le résultat de sa propre connexion (`result =
material.CreateOutput(...).ConnectToSource(output)`) plutôt que de
laisser la variable `result` être écrasée (ou, dans une version
intermédiaire de ce fix rejetée par l'auteur, mise à `None` - l'auteur a
fait remarquer à raison que `result` doit refléter la connexion
réellement faite pour cet effet, pas une valeur arbitraire). Le câblage
glPreview generique (plus bas, séparé, basé sur `context.previewOutputs`)
n'est pas concerné et continue de s'exécuter pour `"displace"` comme
avant - `UsdPreviewSurface` a bien un vrai input `"displacement"`,
contrairement à `standard_surface`. 123 tests toujours verts (aucun test
ne couvre cette fonction, dépendante de Modo).

#### Round 33, `_USD_create_texture_adjust_nodegraph` : le mécanisme d'extraction alpha/swizzling n'a probablement jamais fonctionné, pour aucun effet — CORRIGÉ, CONFIRMÉ DANS HOUDINI (2026-08-11, retest confirmé 2026-08-13)

Parti d'une question simple de l'auteur sur le displacement ("quel type de
texture peut alimenter un nœud `mtlx:displacement`"), l'investigation a
débordé sur un bug bien plus large que le displacement lui-même, une fois
la question de conception sur `_USD_connect_texture_output_to_shader_input`
close (Round 32).

Deux couches de bug empilées, trouvées en traçant précisément les types
USD à travers `_USD_create_texture_adjust_nodegraph` :

1. **Couche visible** : la fin de la fonction réassignait `outType` à
   `Color3f` par défaut (`alphaMode` `"ignore"` ou tout autre valeur que
   `"only"`), **quel que soit le type réellement demandé par l'effet
   appelant** - correct par coïncidence pour les effets déjà `Color3f`
   (diffColor, specColor...), mais faux pour tout effet `Float`
   (displacement, roughness, specular amount, metallic, sheen, sheen
   roughness, transmission amount, stencil/opacity) : la sortie exposée du
   `NodeGraph` se retrouvait déclarée `color3f` alors que sa vraie source
   (la chaîne `ND_remap_float`/`ND_contrast_float`/`ND_multiply_float`)
   restait `float`. Vérifié avec `usd-core` que USD accepte ce genre de
   connexion `ConnectToSource` silencieusement (pas d'erreur, juste un
   attribut dont le type déclaré ment sur sa vraie source) - même famille
   de piège que le bug `wrapS`/`wrapT` déjà documenté, et que le
   `inputs:displacement` mort du Round 32.
2. **Couche plus profonde, trouvée en creusant la première** : les deux
   mécanismes d'extraction de canal (`alpha="only"` et `"swizzling"`)
   passent tous les deux par `ND_separate4_color4`, dont l'input `"in"`
   est réellement `color4f` (vérifié contre le vrai nodedef standalone).
   Mais **`Color4f` n'est jamais utilisé comme type de lecture nulle part
   dans le pipeline** - `usdTypeMap` (la table qui décide du type demandé
   à `_USD_create_texture_output`) ne contient que `Float`/`Color3f`, donc
   le nœud `ND_image` lui-même n'est jamais construit en 4 canaux. Résultat :
   `ND_separate4_color4` recevait toujours une source `float` ou `color3f`,
   jamais `color4f` - **ce mécanisme d'extraction de canal n'a
   probablement jamais fonctionné correctement, pour aucun effet, qu'il
   soit couleur ou scalaire.** Rien dans l'historique de ce fichier
   n'indique qu'une couche utilisant "Alpha: Only" ou "Swizzling" dans
   Modo ait jamais été testée en rendu réel - tous les cas confirmés
   jusqu'ici (rainbowh_Image, MetalDented01, Candle_Flame, Pixel_Panda)
   utilisaient la lecture par défaut.

Corrigé par un remaniement de `_USD_create_texture_output` et
`_USD_create_texture_adjust_nodegraph` (`ShaderTree.py`) :

- `_USD_create_texture_output` calcule maintenant un `readType` distinct
  du type cible (`outType`, inchangé dans sa signature/ses appelants) :
  `Color4f` si la couche a besoin d'extraire un canal (`alpha == "only"`
  ou `swizzling` activé), sinon `outType` tel quel (comportement
  identique à avant pour le cas par défaut, déjà confirmé correct dans
  Houdini). `readType` est ce qui construit réellement le nœud `ND_image`
  (via `_USD_create_UV_texture`/`_USD_create_triplanar_texture`) - donc la
  lecture se fait bien en 4 canaux quand une extraction est prévue.
- `_USD_create_texture_adjust_nodegraph` prend maintenant `readType`
  (le type réel de la chaîne remap/contrast/brightness) et un nouveau
  paramètre `targetType` (le type final voulu par l'effet) séparément.
  Plus aucune réassignation arbitraire : un nouveau `currentType` local
  suit fidèlement le vrai type de `adjustedTextureOutput` à chaque étape.
  Après une extraction (alpha ou swizzle, désormais alimentée par un vrai
  `color4f`), si `currentType` (toujours `Float` après extraction) diffère
  de `targetType` (ex. un effet couleur swizzlé sur un seul canal), un
  nœud `ND_convert_float_<type>` diffuse le scalaire vers le type cible -
  réutilise le même mécanisme que le bridge opacity du Round 28
  (`ND_convert_float_color3`), plus `ND_convert_float_vector3` pour une
  cible `Vector3f` (normal/objectNormal) - les deux confirmés exister dans
  le vrai stdlib MaterialX standalone. Le cas par défaut (pas
  d'extraction) est structurellement identique à avant : `readType ==
  targetType` dès le départ, `currentType` ne change jamais, aucun nœud de
  conversion ajouté - zéro régression attendue sur tout ce qui est déjà
  confirmé fonctionner.

**Les trois scénarios clés vérifiés structurellement contre `usd-core`**
(reconstruits nœud par nœud, en dehors de Modo) : effet `Float` par défaut
sans extraction (displacement) - chaîne `float` de bout en bout, identique
à avant ; effet `Color3f` avec swizzling (ex. diffColor sur le canal rouge)
- lecture `color4f` → `ND_separate4_color4` → `float` → `ND_convert_float_color3`
→ sortie `color3f`, chaque connexion type-cohérente ; effet `Float` avec
`alpha="only"` et invert (ex. stencil) - lecture `color4f` → extraction
alpha → `float` → `ND_invert_float` → sortie `float`. Dans les trois cas,
chaque `.connect` pointe vers un attribut dont le type déclaré correspond
exactement à son type réel - ce qui n'était vrai dans aucun des deux cas
d'extraction avant ce round.

**Limite connue, pas traitée ce round** : si `alpha="only"` **et**
`swizzling` sont activés simultanément sur la même couche, le code
exécute les deux blocs d'extraction l'un après l'autre - le second
tenterait à nouveau `ND_separate4_color4` sur une source déjà réduite à
`float` par le premier, remismatché. Comportement préexistant, inchangé
par ce round (déjà présent avant, sous une forme différente) - pas de
preuve que cette combinaison soit un état atteignable dans l'UI de Modo
(probablement des modes mutuellement exclusifs), donc pas de garde ajoutée
sans confirmation.

123 tests pytest toujours verts (aucun test ne couvre cette fonction,
dépendante de Modo).

**Retesté et confirmé par l'auteur le 2026-08-13** : le mécanisme
d'extraction de canal fonctionne ("pass the test") - `alpha="only"`
confirmé via le stencil (Round 57, qui a aussi corrigé un second bug de
remap sur le canal alpha découvert en le testant) et le swizzling
red/green/blue confirmé fonctionnel sur ce même passage. La limite
`alpha="only"` + `swizzling` simultanés (ci-dessus) reste non vérifiée,
probablement pas un état atteignable dans l'UI de Modo.

#### Round 34, `AttributeError: type object 'ValueTypeNames' has no attribute 'color3f'` sur la branche `"normal"` — CORRIGÉ, CONFIRMÉ DANS HOUDINI (2026-08-11, retest confirmé 2026-08-13)

Crash à l'export réel dans Modo, sur une modification faite par l'auteur
lui-même hors session Claude Code suivie (pas un des rounds précédents) :
la branche `elif effectName == "normal":` de
`_USD_connect_texture_output_to_shader_input` avait été éditée pour poser
`outputType = Sdf.ValueTypeNames.color3f` (minuscule) et construire l'id
du nœud dynamiquement (`"ND_normalmap" + _UTIL_get_node_type_prefix(outputType)`),
sur le modèle de ce que fait déjà la branche `"displace"` voisine.
`Sdf.ValueTypeNames` n'a pas d'attribut `color3f` (l'API réelle est
`Color3f`, majuscule) - `AttributeError` immédiat.

Au-delà de la casse, le type visé était aussi le mauvais : contrairement à
`ND_displacement`, dont le suffixe reflète le type de sortie,
**le suffixe de `ND_normalmap` reflète le type de son input `"scale"`**
(vérifié contre le vrai stdlib MaterialX, documenté à l'étage 3/Round 28-29
- seuls `ND_normalmap_float` et `ND_normalmap_vector2` existent). Ce code
crée `"scale"` en `Float` (`normalShader.CreateInput("scale",
Sdf.ValueTypeNames.Float)`, ligne juste en dessous, inchangée) - le bon
type pour `outputType` est donc `Float`, pas `Color3f`/`color3f`. Corrigé
en `outputType = Sdf.ValueTypeNames.Float`, ce qui reproduit exactement
l'ancien id posé en dur (`"ND_normalmap_float"`) tout en gardant la
construction dynamique voulue par l'auteur. 123 tests toujours verts.

**Retesté et confirmé par l'auteur le 2026-08-13** : la couche `normal`
("Normal layer looks perfect") - premier test réel de cette branche,
jamais exercée avant ce round (voir aussi Round 29, qui avait corrigé le
même bug de fallthrough pour `normal` en même temps que `bump`, mais sans
jamais avoir testé `normal` elle-même jusqu'ici).

#### Round 35, fuite de `output` entre effets dans `_USD_connect_effect_stack` — CORRIGÉ, CONFIRMÉ DANS HOUDINI (2026-08-11, retest confirmé 2026-08-13)

L'auteur repère, en reconstruisant le graphe mtlx dans l'éditeur "Edit
Material" de Houdini sur un export réel de "PF_ShaderBall_base", une
connexion qui n'a pas de sens : le nœud `MetalDented01_Image_2_ND_mix`
(l'opérateur de blend de la couche `displace`) a un de ses deux inputs
connecté à `displacedment_to_normal_Image_adjust:out` - la sortie d'une
**autre** couche, sur un **autre** effet (`normal`), qui n'a rien à voir
avec `displace`. Confirmé en relisant directement le `.usda` généré
(`PF_ShaderBall_base.usda`) :

```
def Shader "MetalDented01_Image_2_ND_mix"
{
    float inputs:bg.connect = </shadertree/Shaderball/displacedment_to_normal_Image_adjust.outputs:out>
    float inputs:fg.connect = </shadertree/Shaderball/MetalDented01_Image_2_adjust.outputs:out>
}
```

`fg` (la couche courante, `MetalDented01_Image_2`) est correct - `bg` (la
pile accumulée) pointe à tort vers la sortie de `displacedment_to_normal_Image`,
la couche de l'effet `normal` traitée juste avant dans la boucle. Bonus :
`bg` est déclaré `float` (le type de `displace`) mais sa vraie source est
`vector3f` (le type de `normal`) - encore un mismatch de type du même
genre que ceux déjà documentés (Round 28/32/33), lui aussi une
conséquence du bug ci-dessous, pas une cause séparée.

Cause : dans `_USD_connect_effect_stack`, la variable accumulatrice
`output` est déclarée **une seule fois, avant** la boucle `for effectName
in context.effectsStack.keys()`, jamais réinitialisée à chaque nouvel
effet - elle ne se remet à `None` que si le lookup de fallback vers la
valeur littérale de l'`advancedMaterial` réussit (`context.advancedMaterialChannels.find(modoInputName)`).
Sur ce fichier de test, ni `normal` ni `displace` n'ont de channel de
fallback exact sur `Material_5` (`.find("normal")`/`.find("disp")`
retournent tous les deux `None` - `disp` n'existe pas comme tel, seuls
`dispVal`/`displace`/`disperse` existent, aucun ne matche le nom exact),
donc le lookup échoue pour les deux, et `output` n'est jamais remis à
`None` entre les deux itérations : la sortie de la couche `normal`
(laissée dans `output` après son propre traitement) fuit tout droit dans
le traitement de `displace`, où `_USD_connect_operator` la reçoit comme
`input` (donc `bg`) - un effet totalement sans rapport devient
accidentellement "la pile accumulée" d'un autre effet.

**Lien avec le Round 30** : avant ce round-là, ce scénario précis (aucun
fallback pour un effet, `output` valant encore `None` à l'entrée de sa
boucle de connecteurs) plantait immédiatement dans `_USD_connect_operator`
(`input.GetFullName()` sur `None`) - c'est exactement le crash corrigé au
Round 30. Le fix du Round 30 (passer la texture telle quelle quand `input
is None`) a débloqué l'export, mais a du même coup rendu ce bug de fuite
inter-effets observable pour la première fois : avant, il n'avait jamais
l'occasion de produire un mauvais câblage silencieux, il faisait planter
l'export avant d'y arriver.

Corrigé : `output = None` déplacé à l'intérieur de la boucle, en tout
début de chaque itération sur `effectName` (`ShaderTree.py`,
`_USD_connect_effect_stack`) - chaque effet repart de zéro, et n'hérite
une valeur de base que de son propre lookup de fallback sur
l'`advancedMaterial`, jamais de la sortie d'un effet précédent sans
rapport. La valeur de retour de la fonction (déjà ignorée par son unique
appelant, `_USD_export_shadertree` ligne 533) n'a pas d'implication
au-delà de cette fonction. 123 tests toujours verts (aucun test ne couvre
cette fonction, dépendante de Modo). **Retesté et confirmé par l'auteur le
2026-08-13** ("This one doesn't occurs anymore") - la fuite ne se
reproduit plus sur un nouvel export.

#### Round 36, ajout de l'effet `vectorDisplace` + correction du typage `displacementshader` — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO/HOUDINI (2026-08-11)

Demande de l'auteur : ajouter le support de l'effet Modo `vectorDisplace`
(displacement map vectorielle, pas juste une hauteur scalaire), sur le
même modèle que la branche `"normal"` existante - une branche dédiée dans
`_USD_connect_texture_output_to_shader_input`, mais connectée à
`mtlx:displacement` (comme `"displace"`) plutôt qu'à un input du shader,
cette fois en `Vector3f`.

En vérifiant les vrais nodedefs MaterialX avant d'implémenter (comme
d'habitude cette session), trouvé un bug préexistant plus large que la
seule nouvelle fonctionnalité : **`ND_displacement_float` et
`ND_displacement_vector3` n'ont ni l'un ni l'autre une sortie `float`/
`vector3` - leur vrai type de sortie est `displacementshader`** (un type
de rôle, comme `surfaceshader`, représenté en USD par `token` - exactement
la convention déjà utilisée correctement ailleurs dans ce fichier pour la
sortie du shader `standard_surface` lui-même,
`shader.CreateOutput('surface', Sdf.ValueTypeNames.Token)`). La branche
`"displace"` existante posait `outputType` (donc `Float`) sur la sortie du
nœud `ND_displacement_float` - un type déclaré qui ne correspond pas au
vrai nodedef, même famille de piège que les bugs déjà documentés
(wrapS/wrapT, `inputs:displacement` mort du Round 32). Confirmé par
l'auteur : à corriger dans les deux branches en même temps, pas seulement
la nouvelle.

Implémenté (`ShaderTree.py`) :
- `elif effectName == "vectorDisplace":` (nouvelle branche, calquée sur
  `"displace"`) : lit le même channel `<displace>` de l'`advancedMaterial`
  pour `"scale"` (une seule distance de displacement globale, qu'elle
  s'applique à une carte scalaire ou vectorielle - pas encore confirmé
  dans Modo que c'est bien le même channel qui pilote les deux, mais c'est
  la seule source disponible, cohérent avec l'usage déjà fait pour
  `"displace"`), connecte la texture (`Vector3f`, donc lue via
  `ND_image_color3` par le mécanisme déjà générique du Round 33) à
  l'input `"displacement"` (`vector3`, vérifié) d'un nœud
  `ND_displacement_vector3` - id **codé en dur**, pas construit via
  `_UTIL_get_node_type_prefix(outputType)` (qui retourne `"_color3"` pour
  `Vector3f`, produirait le nom invalide `ND_displacement_color3` - même
  piège déjà documenté pour `ND_bump_vector3`/`ND_normalmap`, Round 28/29).
  Connecte le résultat à `material.outputs:mtlx:displacement`, exactement
  comme `"displace"`.
- Les deux branches (`"displace"` et `"vectorDisplace"`) posent maintenant
  `Sdf.ValueTypeNames.Token` sur la sortie du nœud `ND_displacement_*`
  (au lieu de `outputType`) - corrige le bug de typage trouvé ci-dessus
  pour l'existant en même temps que la nouvelle branche.
- Le garde qui saute le câblage générique d'input shader mtlx (déjà en
  place pour `"displace"` depuis le Round 32, la sortie va directement
  vers le output du matériau, pas un input de `standard_surface`) étendu
  à `"vectorDisplace"` : `if effectName not in ("displace", "vectorDisplace"):`.
- **Bug annexe trouvé et corrigé en implémentant** : le lookup inverse de
  `_USD_connect_effect_stack` (`_UTIL_get_key_from_value(...)`, déjà
  identifié comme fragile - décision ouverte n°4, et cause du Round 30)
  peut retourner `None` si `usdInputName` n'a **aucune** correspondance
  dans `stdMatChannelMap[...]['principled']` - ce qui est le cas pour le
  nouvel `usdInputName` `"vectorDisplacement"` (aucun channel Modo direct
  de ce nom). `context.advancedMaterialChannels.find(None)` lève un
  `TypeError` (vérifié avec `usd-core` : `find()` exige une chaîne, pas
  `None`) - donc sans ce fix, **toute** couche `vectorDisplace` aurait
  planté l'export à coup sûr. Corrigé en gardant l'appel à `.find()`
  derrière `modoInputName != None`, en plus du test déjà existant sur son
  résultat - traite maintenant "aucune correspondance inverse" exactement
  comme "correspondance trouvée mais channel absent" (`output` reste sans
  valeur de fallback), au lieu de planter. Défensif pour toute future
  extension de `usdInputName`, pas seulement `vectorDisplace`.

`normalize/effect_channel_names.py` : `"vectorDisplace": "vectorDisplacement"`
ajouté à `USD_INPUT_NAME_BY_EFFECT` ; **absent** de
`USD_PREVIEW_INPUT_NAME_BY_EFFECT` (commenté pourquoi, même endroit que
`lumiAmount`) - l'input `"displacement"` d'`UsdPreviewSurface` est un
simple scalaire le long de la normale, pas de vraie displacement
vectorielle possible côté preview. `ShaderFilters/usd_types.py` :
`"vectorDisplacement": Sdf.ValueTypeNames.Vector3f` ajouté à `usdTypeMap`.

Graphe reconstruit et vérifié type-cohérent contre `usd-core`
(`ND_image_color3` → `ND_displacement_vector3` → `material.outputs:mtlx:displacement`,
tous les types déclarés correspondent à leur vraie source). 123 tests
toujours verts (aucun test ne couvre `ShaderTree.py`, dépendant de Modo).
**Rien de tout ça n'est testé dans Modo/Houdini** - premier test réel à
faire avec un fichier ayant une vraie couche `vectorDisplace`.

#### Round 37, support des couches Gradient (`iCHANTYPE_GRADIENT`) — étage 1 seulement (extraction XML), PAS CÂBLÉ CÔTÉ USD (abandonné, voir Round 54), CONFIRMÉ DANS MODO (2026-08-11, retest confirmé 2026-08-13)

Chantier ouvert par l'auteur : `_UTIL_format_channel_value` (étage 1,
extraction Modo → XML brut) traitait tout channel `iCHANTYPE_GRADIENT`
comme une boîte noire, retournant juste le littéral `"gradient"` sans
jamais lire ses vraies clés/valeurs - même chose pour un
`modo.ChannelTriple` gradient (ex. `color`), où `_UTIL_format_channel`
se contentait de `str(channel.get())`, produisant la chaîne inutilisable
déjà vue dans les exports réels : `"(<lx.object.Unknown object at
0x...>, ...)"`. Objectif de l'auteur, en deux temps : d'abord rendre
cette donnée disponible dans le XML (ce round), puis voir comment la
traduire en nœuds USD/mtlx (pas fait ce round, voir plus bas).

**Investigation, faite via un script de diagnostic dédié**
(`explore_tools/gradient_diag.py`, gitignoré, hors `.lpk` via
`build_lpk.py` - lecture seule, jamais committé/distribué), exécuté par
l'auteur dans la console Python de Modo sur "PF_ShaderBall_base" (une
couche `Gradient` ajoutée pour l'occasion, effet `diffColor`) :

1. **`"gradient"` est un vrai type d'item du shader tree**, frère direct
   de `imageMap`/`mask`/`advancedMaterial` (`item.type == "gradient"`) -
   confirmé en énumérant tous les `item.type` uniques sous le render
   item. Pas encore de branche `elif elementName == "gradient":` dans
   `_USD_export_shadertree` - une couche Gradient dans le shader tree ne
   produit donc actuellement **rien** côté USD (aucun diagnostic non
   plus, silencieusement ignorée par la boucle `for child in
   xml.findall('*')` qui ne reconnaît que les tags qu'elle sait traiter).
2. **Cast `lx.object.Envelope` échoue ("no interface"), cast
   `lx.object.GradientFilter` réussit** sur la valeur brute
   (`lx.object.Unknown`) retournée par `channel.get()` d'un channel
   gradient - pas d'énumération de clés discrètes possible/nécessaire.
   `GradientFilter.Generate(t)` évalue directement la courbe déjà
   interpolée à la position `t` - confirmé par un vrai balayage lisse
   (`1.0 → 0.84 → 0.49 → 0.14 → 0.0` sur `t=0..1`), pas des valeurs de
   clés brutes.
3. **Deux channels gradient distincts et indépendants sur un item
   `gradient`** : `value` (un `modo.Channel` simple, une seule rampe -
   utilisée quand l'effet cible est scalaire) et `color` (un
   `modo.ChannelTriple`, 3 rampes indépendantes R/G/B - utilisée quand
   l'effet cible est une couleur) - **confirmé par l'auteur** : "les deux
   peuvent être évaluées séparément, elles ont chacune une rampe unique".
4. **Channels réels d'une couche Gradient** (lus depuis un export réel de
   "PF_ShaderBall_base", couche `Gradient` sous `Shaderball_Material`) :
   `effect`/`blend`/`opacity`/`invert`/`enable` - identiques à `imageMap`
   (même mécanisme de blend/effect stack déjà en place, réutilisable tel
   quel). **Absents**, contrairement à `imageMap`: `min`/`max`/
   `brightness`/`contrast`/`swizzling`/`rgba`/`alpha` - `_USD_create_texture_adjust_nodegraph`
   (conçue pour `imageMap`) ne pourra donc pas être réutilisée telle
   quelle, une couche Gradient aura besoin de son propre chemin
   d'ajustement (plus simple, `invert` seul). Nouveau : `param` (ex.
   `"distanceX"` - le paramètre d'entrée qui pilote l'axe horizontal de
   la rampe, l'équivalent d'un "Input Parameter" côté Modo) et `inVal`
   (rôle encore incertain, peut-être une valeur utilisée seulement en
   mode "constant" - pas encore élucidé).

**Questions encore ouvertes, pas résolues ce round** (bloquent l'étage
USD, pas l'étage XML) : la liste complète des valeurs possibles de
`param` (le menu déroulant "Input Parameter" de Modo - seule
`"distanceX"` vue jusqu'ici) et si un paramètre a un domaine/intervalle
explicite ailleurs, ou si Modo normalise tout en `[0,1]` avant que ça
n'atteigne le gradient (hypothèse actuelle, cohérente avec le balayage
`Generate(0..1)` déjà observé, mais pas confirmée).

**Implémenté ce round** (`ShaderTree.py`, étage 1 uniquement, sur
consigne explicite de l'auteur - "juste extraire ce qu'on peut dans le
XML pour l'instant") :

- Nouvelle fonction `_UTIL_sample_gradient(rawValue, count=64)` :
  cast défensif vers `lx.object.GradientFilter` (retourne `None` si le
  cast échoue, jamais d'exception qui remonte), puis échantillonne
  `Generate(t)` à `count` positions régulières sur `[0,1]` et retourne un
  tuple de floats. `GRADIENT_SAMPLE_COUNT = 64` - résolution choisie
  arbitrairement (assez pour reconstruire fidèlement une rampe une fois
  bakée en LUT plus tard, sans faire exploser la taille du XML), pas
  encore validée visuellement.
- `_UTIL_format_channel_value` (channel gradient simple, ex. `value`) :
  appelle `_UTIL_sample_gradient`, sérialise le tuple obtenu en chaîne
  Python littérale (`str(tuple)`, ex. `"(1.0, 0.84, ..., 0.0)"`) -
  parsable par un `eval()` en aval, même convention que les autres
  valeurs tuple déjà utilisées partout dans ce fichier (couleurs, etc.).
  Retombe sur l'ancien littéral `"gradient"` si l'échantillonnage échoue.
- `_UTIL_format_channel` (branche `modo.ChannelTriple`, ex. `color`) :
  nouveau cas spécial quand `ctype == iCHANTYPE_GRADIENT` - échantillonne
  les 3 composantes R/G/B séparément puis les recombine (`zip`) en un
  tuple de `count` triplets `(r, g, b)`, sérialisé de la même façon
  (`"((r0,g0,b0), (r1,g1,b1), ...)"`). Le comportement pour un
  `ChannelTriple` non-gradient (couleurs littérales classiques) est
  inchangé.

**Ce qui n'est PAS fait ce round, volontairement** : aucune branche
`"gradient"` dans `_USD_export_shadertree`/`_USD_connect_texture_output_to_shader_input` -
les données sont maintenant disponibles dans le XML mais rien ne les
consomme encore côté USD. La traduction envisagée (bake en LUT image
plutôt que reconstruire les nœuds `ramp4`/`splitlr` du stdlib mtlx, qui
ne couvrent que des formes simples à 2-4 points) reste à concevoir, en
attendant les réponses sur `param`/domaine ci-dessus.

123 tests pytest toujours verts (aucun test ne couvre ce chemin, dépendant
de Modo). **Retesté et confirmé par l'auteur le 2026-08-13** (voir la note
consolidée à la fin du Round 42 pour l'ensemble de l'arc Round 37-42).

#### Round 38, gradient : extraction des vraies clés (position/valeur) au lieu d'un échantillonnage `Generate(t)` — étage 1 seulement, CONFIRMÉ DANS MODO (2026-08-11, retest confirmé 2026-08-13)

Suite du Round 37 : l'auteur préfère récupérer les vraies clés discrètes
(position + valeur) qui définissent une rampe plutôt qu'un échantillonnage
uniforme de `GradientFilter.Generate(t)` - fidélité exacte plutôt qu'une
LUT à résolution fixe.

**Investigation, via un second script de diagnostic**
(`explore_tools/gradient_keys_diag.py`, même statut que le premier -
gitignoré, exclu du `.lpk`, lecture seule) :

1. **`Item.ChannelGradient(index)` retourne `('percent', 'percent'/'color1')`**
   (input, output) pour les 5 channels gradient trouvés (`value`,
   `color.R/G/B/A`) - confirme que l'axe horizontal d'un gradient est
   toujours exprimé en `"percent"` (donc normalisé) côté Modo, quel que
   soit le paramètre d'entrée réel choisi (`param`, ex. `"distanceX"`) -
   répond à la question de domaine restée ouverte au Round précédent :
   pas besoin d'aller chercher un intervalle min/max séparé, l'axe est
   déjà en `[0,1]`.
2. **Chemin d'accès confirmé pour une vraie `Envelope`** (le cast direct
   `lx.object.Envelope(rawValue)` échouait au Round 37 - "no interface") :
   passer par `Item.Context()` → `lx.object.Scene` →
   `Scene.Channels('edit', 0.0)` → `lx.object.ChannelRead` →
   `ChannelRead.Envelope(item, index)` (l'`index` venant de
   `Item.ChannelLookup(nomDeChannelComplet)`) donne un vrai objet
   `Envelope`, cette fois walkable via `Envelope.Enumerator()` →
   `Keyframe` (`First()`/`Next()`/`GetTime()`/`GetValueF(0/1)`/
   `GetSlope()`). Confirmé avec de vraies données : `value` a 2 clés
   (`pos=0.0→val=1.0`, `pos=0.985→val=0.0`), `color.R`/`color.G` 2 clés
   chacun (transition à `pos=0.065`), `color.B` 2 clés (petite variation
   constante), `color.A` 1 seule clé (alpha constant à 1.0). `GetSlope()`
   à 0.0 partout dans ce test (pas assez de cas pour distinguer
   linéaire/palier/bezier - resté non exploré, capturé tel quel).
3. **`color.A` (alpha) est un 4ᵉ channel gradient distinct**, séparé du
   triplet R/G/B - `item.channel("color")` (le `ChannelTriple`) ne
   retourne que 3 composantes, jamais l'alpha. **Pas géré ce round** (la
   boucle de collecte de `_JSON_get_channels` regroupe tout par
   `nom.split(".")[0]`, donc les 4 itérations R/G/B/A retombent toutes
   sur la même clé `"color"` et recalculent 3 fois la même chose sans
   jamais lire `.A`) - gap connu, pas comblé, pas demandé par l'auteur ce
   round.
4. **Le nœud `Gradient` a bien un `txtrLocator` lié par graphe**
   (`sGRAPH_SHADELOC`, comme `imageMap`) - `_XML_export_item` ne
   vérifiait ce graphe que pour `imageMap`/`noise`/`cellular`/`falloff`,
   pas pour `gradient` : ce locator (transform UV/3D) était donc
   silencieusement absent du XML jusqu'ici. Corrigé (voir plus bas).

**Implémenté ce round** (`ShaderTree.py`, toujours étage 1 seulement -
extraction XML, rien côté USD) :

- Nouvelles fonctions `_UTIL_get_channel_read()` (cache paresseux de
  l'interface `lx.object.ChannelRead`, construite une seule fois via le
  chemin ci-dessus) et `_UTIL_get_gradient_keys(item, channelName)`
  (résout l'`Envelope` réel d'un channel et retourne un tuple de
  `(position, valueIn, valueOut)` par clé - `valueIn`/`valueOut` gardées
  toutes les deux, même si identiques dans tous les cas observés jusqu'ici,
  pour ne pas perdre l'info si un futur gradient a une clé en palier).
  Toutes les deux entièrement défensives (`try/except`, ne lèvent jamais),
  retournent `None` en cas d'échec.
- `_UTIL_format_channel_value`/`_UTIL_format_channel` (branche
  `ChannelTriple` gradient) essaient maintenant `_UTIL_get_gradient_keys`
  en premier ; si ça échoue, retombent sur l'échantillonnage
  `_UTIL_sample_gradient` du Round 37 ; si ça échoue aussi, sur l'ancien
  littéral `"gradient"`. Trois niveaux de repli, aucun ne lève. Pour
  `color`, les 3 composantes R/G/B sont lues séparément puis recombinées
  par index en suppposant qu'elles partagent les mêmes positions de clé
  (vérifié vrai sur le seul cas réel observé - Modo semble toujours clé
  R/G/B ensemble par "stop" de gradient) - pas de fusion par union de
  positions si elles diffèrent un jour, juste un `zip()` qui tronque à la
  plus courte.
- **Format XML revu sur demande de l'auteur** (2026-08-11, après un
  premier passage en littéral Python stringifié) : `chan['value']` est
  maintenant une **liste de dicts** (une entrée par clé) plutôt qu'une
  chaîne, et `_XML_get_channels` a un nouveau cas `type(att) is list` qui
  développe chaque entrée en élément enfant `<Key .../>` (à côté du cas
  `dict` déjà existant pour `Matrix4`, tous deux avant le cas générique
  "attribut simple"). Résultat, par clé de gradient :
  `<value ...><Key pos="0.0" value="1.0"/><Key pos="0.985" value="0.0"/></value>`
  et `<color ...><Key pos="0.0" color="(r,g,b)"/>...</color>` - la couleur
  de chaque `<Key>` combine les 3 composantes R/G/B à cette position en un
  seul attribut tuple. Le repli sur l'échantillonnage produit la même
  forme (juste avec ~64 `<Key>` au lieu de 2-3) - schéma XML uniforme
  quel que soit le chemin d'extraction qui a réussi. Vérifié en simulant
  le pipeline complet (`_JSON_get_channels` → `_XML_get_channels`) hors
  Modo avec des données factices calquées sur le vrai diagnostic - produit
  exactement la forme demandée. `json.dump` (export JSON, `_JSON_write_file`)
  n'est pas affecté - une liste de dicts se sérialise nativement en JSON,
  aucun changement nécessaire là.
- Signatures élargies pour faire passer `item`/`chanName` jusqu'à ces deux
  fonctions (nécessaires pour `ChannelLookup`) : `_JSON_get_channels` →
  `_UTIL_format_channel(item, chanName, ...)` → `_UTIL_format_channel_value(item, chanName, ...)`.
  Seul site d'appel de chacune, pas de rupture d'API ailleurs.
- `_XML_export_item` : `lx.symbol.sITYPE_GRADIENT` ajouté à la liste des
  types déclenchant le suivi du graphe `sGRAPH_SHADELOC` (même liste que
  `imageMap`/`noise`/`cellular`/`falloff`) - le `txtrLocator` d'un
  gradient sera maintenant exporté comme pour un `imageMap`. **Nom du
  symbole assumé par convention à l'époque** (`item.type` vaut
  littéralement `"gradient"`, confirmé réel ; `lx.symbol.sITYPE_GRADIENT`
  lui-même n'apparaissait pas dans le stub incomplet utilisé pour
  l'analyse statique) - **confirmé exister et valoir `'gradient'` au
  Round 41**, via `explore_tools/dump_modo_api.py`.

**Toujours pas fait, volontairement** : aucune branche `"gradient"` dans
`_USD_export_shadertree` - la traduction USD/mtlx reste à concevoir.

123 tests pytest toujours verts (aucun test ne couvre ce chemin, dépendant
de Modo). **Retesté et confirmé par l'auteur le 2026-08-13** (voir la note
consolidée à la fin du Round 42).

#### Round 39, `color.A` extrait + forme XML revue en groupes indépendants par composante + type d'interpolation par clé — CONFIRMÉ DANS MODO (2026-08-11, retest confirmé 2026-08-13)

Deux demandes de l'auteur juste après le Round 38 :

1. **Forme XML revue** : au lieu de fusionner R/G/B en une seule liste de
   `<Key pos=".." color="(r,g,b)"/>` (hypothèse du Round 38, jamais
   confirmée en pratique), chaque composante garde sa **propre** liste de
   clés indépendante, imbriquée sous des éléments `<red>`/`<green>`/
   `<blue>`/`<alpha>` à l'intérieur de `<color>` :
   ```xml
   <color ...>
      <red><Key pos=".." value=".."/>...</red>
      <green>...</green>
      <blue>...</blue>
      <alpha>...</alpha>
   </color>
   ```
   Comble au passage le gap connu du Round 38 (`color.A` jamais lu) -
   l'alpha est maintenant extrait comme les 3 autres composantes, via le
   même chemin `_UTIL_get_gradient_keys(item, "color.A")` déjà confirmé
   fonctionner par le diagnostic (une seule clé, alpha constant à 1.0 sur
   le fichier de test). `_XML_get_channels` gagne un nouveau cas :
   `type(att) is dict` **et** toutes ses valeurs sont des listes → un
   élément enfant par clé du dict (nommé `red`/`green`/etc.), chacun
   rempli de `<Key>` comme le cas `list` déjà existant - vérifié à ne pas
   entrer en collision avec le cas `dict` simple déjà en place pour
   `Matrix4` (celui-ci reste un dict-de-scalaires, pas un dict-de-listes,
   testé en premier dans l'ordre des `elif`).
2. **Type d'interpolation par clé** : l'auteur demande explicitement
   s'il y a d'autres valeurs à extraire pour définir la forme de la
   courbe. Confirmé dans le stub : `Keyframe.GetSlopeType(side)` (type
   d'interpolation + drapeau "weighted") et `Keyframe.GetSlope(side)`/
   `GetWeight(side)` (tangente/poids), par côté (`0`=entrant, `1`=sortant).
   `_UTIL_get_gradient_keys` lit maintenant `slopeType`/`slope`/`weighted`
   côté sortant (`side=1`) en plus de `pos`/`value`, ajoutés comme
   attributs supplémentaires sur chaque `<Key>`. **Valeurs numériques
   brutes, sens pas encore décodé** - aucune valeur de test observée
   jusqu'ici n'a permis de distinguer linéaire/bezier/palier (toutes les
   clés du fichier de test ont `slope=0.0`) ; à décoder empiriquement le
   jour où un vrai cas d'usage l'exige (créer des clés avec des types
   d'interpolation visiblement différents dans Modo et comparer les
   valeurs lues).

**Simplification assumée, pas testée** : `_UTIL_get_gradient_keys` ne lit
plus que le côté sortant (`valueOut`/`side=1`) pour `value`/`slope`/
`slopeType`/`weighted` - `valueIn` (côté entrant) n'est plus lu du tout,
perdant la capacité de détecter une clé "en palier" (in ≠ out,
discontinuité). Aucune clé observée jusqu'ici n'avait cette forme ; à
revoir si un futur test en révèle une. Lecture de `slopeType`/`slope`
individuellement protégée par son propre `try/except` (retombe sur `None`)
pour qu'un éventuel échec ne fasse pas perdre `pos`/`value`, qui eux
restent lus séparément et fiables.

Nouvelle fonction partagée `_UTIL_gradient_keys_to_xml_dicts(keys)` -
convertit la sortie de `_UTIL_get_gradient_keys` en liste de dicts
`{"pos", "value", "slopeType", "slope", "weighted"}`, réutilisée à
l'identique pour `value` (ramp simple) et chacune des 4 composantes de
`color`. Le repli sur `_UTIL_sample_gradient` (Round 37, si l'extraction
de vraies clés échoue) reste RGB seulement, sans alpha ni info de pente -
seul le chemin "vraies clés" est complet.

Vérifié en simulant le pipeline complet (`_JSON_get_channels` →
`_XML_get_channels`) hors Modo avec des données factices calquées sur le
vrai diagnostic - produit exactement la forme demandée, avec `red`/
`green`/`blue`/`alpha` et les attributs `slopeType`/`slope`/`weighted` sur
chaque `<Key>`. 123 tests pytest toujours verts. **Rien de tout ça n'est
testé dans Modo** - même priorité que le Round 38 pour la prochaine
session (re-exporter et lire le XML résultant).

#### Round 40, `slopeType` écrit en toutes lettres dans le XML + `weighted` traité comme booléen — CONFIRMÉ DANS MODO (2026-08-12, retest confirmé 2026-08-13)

Demande de l'auteur : écrire `slopeType` sous forme de chaîne
(`slopeType="DIRECT"`, pas l'entier brut) dans le XML, et vérifier si
`weighted` est aussi un enum nommé du même genre (l'auteur proposait par
exemple `["auto", "manual"]`).

Confirmé dans le stub (`lx/symbol.py`) : `slopeType` a bien 8 constantes
nommées réelles - `iSLOPE_AUTO`, `iSLOPE_AUTOFLAT`, `iSLOPE_DIRECT`,
`iSLOPE_FLAT`, `iSLOPE_LINEAR_IN`, `iSLOPE_LINEAR_OUT`,
`iSLOPE_SMOOTHFLAT`, `iSLOPE_STEPPED` - mais le stub ne donne que les
noms (valeurs toutes à `None`, un simple placeholder pour l'analyse
statique), pas les vrais entiers. Plutôt que de deviner ou d'attendre un
troisième aller-retour de diagnostic Modo pour coder ces entiers en dur,
`_UTIL_get_slope_type_name` construit la table de correspondance
**directement depuis les vraies constantes `lx.symbol.iSLOPE_*` à
l'exécution** (`getattr(lx.symbol, "iSLOPE_" + name)`), mise en cache
paresseusement - reste correct quelle que soit la valeur entière réelle
sous-jacente, y compris si elle diffère d'une version de Modo à l'autre,
sans dépendre du diagnostic déjà écrit
(`explore_tools/gradient_slopetype_diag.py`, toujours utile pour une
vérification visuelle mais plus strictement nécessaire à l'implémentation
elle-même).

**`weighted` : cherché, rien trouvé d'équivalent.** Contrairement à
`slopeType`, aucune constante nommée dans `lx/symbol.py` ne correspond au
second élément retourné par `GetSlopeType()` (les seules correspondances
pour "weight" dans le stub sont sans rapport - poids de déformeur, de
vmap, etc.). Cohérent avec la signature de l'API (`SetWeight(weight,
reset, side)`/`GetWeight(side) -> float` existent séparément) : `weighted`
est très probablement un simple booléen ("cette clé a-t-elle une tangente
à poids explicite, ou pas"), pas un enum à plusieurs valeurs nommées comme
`slopeType`. Traité comme tel - `str(bool(weighted))` (`"True"`/`"False"`)
plutôt que d'inventer un vocabulaire non vérifié comme `"auto"`/`"manual"`
(hypothèse de l'auteur, plausible mais aucune preuve dans le SDK pour la
confirmer).

`_UTIL_gradient_keys_to_xml_dicts` mis à jour en conséquence. Vérifié hors
Modo avec des symboles factices (0-7 assignés arbitrairement à
`iSLOPE_AUTO..iSLOPE_STEPPED`) que la résolution nom↔valeur fonctionne
correctement. 123 tests pytest toujours verts. **Retesté et confirmé par
l'auteur le 2026-08-13** : `slopeType` apparaît bien en toutes lettres
dans le XML (voir la note consolidée à la fin du Round 42).

#### Round 41, nouvel outil `explore_tools/dump_modo_api.py` + confirmations sur les gradients (2026-08-12)

L'auteur signale l'existence d'une commande Modo déjà installée en dehors
de ce kit, `~/Library/Application Support/Luxology/Scripts/lxserv/cmd_dumpapi.py`
(`python.dumpAPI`, d'origine Luxology/Foundry) qui dump la structure de
`lx`/`lxu`/`modo` via `inspect` pour l'auto-complétion IDE - mais qui
neutralise volontairement la valeur de chaque constante à `None`
(`do_constants()`), exactement la limite qui a coûté plusieurs allers-retours
de diagnostic cette session (`sITYPE_GRADIENT`, `iSLOPE_*`...).

Nouvel outil écrit sur ce modèle mais qui corrige ce point,
`explore_tools/dump_modo_api.py` : même technique (`inspect.getmembers`
sur `lx.symbol`/`lx.object`/`modo`), mais écrit directement dans
`explore_tools/` (3 fichiers texte, gitignorés, hors `.lpk`) au lieu
d'imprimer dans la console - donc lisibles directement par Claude Code
sans copier-coller manuel :
- `lx_symbol_dump.txt` - chaque constante `lx.symbol.*` avec sa **vraie**
  valeur (int/float/str/bytes/bool uniquement - le reste, objets/types
  complexes, filtré).
- `lx_object_dump.txt` - chaque classe `lx.object.*`, ses méthodes, et
  leur docstring réelle (les docstrings des méthodes builtin de Modo
  encodent déjà la signature complète, ex.
  `"(integer type,integer weighted) = GetSlopeType(integer side)"`).
- `modo_dump.txt` - pareil pour le wrapper `modo.*`, sous-module par
  sous-module.

Exécuté une première fois par l'auteur, confirme plusieurs points laissés
ouverts :
- **`sITYPE_GRADIENT = 'gradient'`** - confirme l'hypothèse "assumée par
  convention" du Round 38 (jamais vérifiée jusqu'ici faute de symbole
  dans le stub tiers utilisé pour l'analyse statique).
- **Vraies valeurs `iSLOPE_*`** : `DIRECT=0`, `AUTO=1`, `LINEAR_IN=2`,
  `LINEAR_OUT=3`, `FLAT=4`, `AUTOFLAT=5`, `STEPPED=6`, `SMOOTHFLAT=7`.
  Le code n'en a pas besoin en dur (`_UTIL_get_slope_type_name` les
  résout déjà dynamiquement via `getattr` - Round 40), mais confirme que
  cette approche est la bonne plutôt que de coder les entiers en dur.
- **`sICHAN_GRADIENT_PARAM`/`_VALUE`/`_COLOR` = `'param'`/`'value'`/`'color'`** -
  confirme que les noms de channel trouvés empiriquement sont bien les
  constantes canoniques Modo, pas une coïncidence.
- **Découverte non anticipée, pas encore explorée** : `sITYPE_GRADIENTLAYER
  = 'gradientlayer'`, relié via un graphe `sGRAPH_GRADIENTLINKS` distinct
  de `sGRAPH_SHADELOC` (celui déjà câblé pour le `txtrLocator`), avec ses
  propres channels `sICHAN_GRADIENTLAYER_ENABLE`/`sICHAN_GRADIENTLAYER_OBJ`
  et une commande `gradientFilter.addLayer`. Suggère qu'un item `gradient`
  peut potentiellement empiler **plusieurs** couches de gradient
  (chacune activable indépendamment, chacune avec son propre
  `GradientFilter`), au-delà du modèle simple à une seule enveloppe
  `value`/`color` implémenté jusqu'ici (Round 37-40). Le fichier de test
  actuel n'utilise pas ce mécanisme (une seule couche implicite) - donc
  l'extraction actuelle reste valide pour ce cas, mais **pas encore
  vérifié** ce qui se passe pour un gradient à plusieurs couches - à
  creuser si un cas réel se présente (chercher `sGRAPH_GRADIENTLINKS`
  dans `lx_symbol_dump.txt`/tester `item.itemGraph(lx.symbol.sGRAPH_GRADIENTLINKS)`
  sur l'item Gradient).

Aucun changement de code ce round - uniquement de la documentation/outillage
et des confirmations. `explore_tools/dump_modo_api.py` reste disponible
pour toute future question sur l'API Modo (constantes, signatures) sans
repasser par un script de diagnostic dédié à chaque fois.

#### Round 42, `_UTIL_get_gradient_keys` réécrite pour utiliser `modo.Channel.envelope` au lieu de `lx.object` à la main — corrige un vrai bug de action layer, CONFIRMÉ DANS MODO (2026-08-12, retest confirmé 2026-08-13)

Suite directe du Round 41 : au-delà des dumps `inspect`-based, l'auteur
signale que le vrai code source du package `modo` est lisible directement
sur disque (`.../Modo17.1v1_FINAL_ARM.app/Contents/Resources/python3kit/extra/Python/Scripts/modo/channel.py`) -
bien plus fiable qu'un dump réfléchi (qui ne capture que les signatures,
pas l'implémentation, et rate les `@property` puisque `dump_modo_api.py`
ne filtre que sur `inspect.isroutine`). Lu intégralement.

Deux découvertes qui remettent en cause l'implémentation du Round 38 :

1. **Bug de action layer trouvé** : `modo.Channel.envelope` (la vraie
   propriété officielle) lit l'enveloppe via `ChannelWrite.Envelope(item,
   index)` avec l'action `lx.symbol.s_ACTIONLAYER_SETUP` - **pas `EDIT`** -
   spécifiquement pour les channels gradient (`evalType == "gradstack"`).
   Le commentaire du code source cite explicitement un bug Modo connu
   (#47584) : "keyframe edits lost after re-opening scene... happens when
   the keys were inserted with the 'edit' action and the scene is saved
   while the scene is still in flux". `_UTIL_get_channel_read` (Round 38)
   utilisait `ChannelRead` avec l'action `'edit'` codée en dur - sans ce
   contournement, l'extraction pourrait lire des données de gradient
   obsolètes/fausses dans exactement ce scénario. Fonctionnait sur le
   fichier de test (scène pas dans cet état particulier), mais le bug
   restait latent.
2. **Chemin d'accès bien plus simple que `lx.object` à la main** :
   `modo.Channel(channelName, item).envelope` fait tout le travail
   (résolution d'index, action layer correcte, cast `ChannelWrite`) en
   une ligne. `Envelope.keyframes` retourne un objet `Keyframes` itérable
   (`for pos, value in keyframes: ...`), avec `GetSlopeType`/`GetSlope`
   directement accessibles dessus (relayés vers le `lx.object.Keyframe`
   sous-jacent via `__getattr__`). Explique au passage pourquoi le tout
   premier essai du Round 37 (caster la valeur brute du channel
   directement en `lx.object.Envelope`) échouait ("no interface") : la
   vraie enveloppe ne s'obtient jamais depuis la valeur brute du channel,
   seulement via `ChannelWrite.Envelope(item, index)`.

Corrigé : `_UTIL_get_channel_read`/`_channelRead` (Round 38, la
plomberie `lx.object.Item.Context() → Scene → ChannelRead`) entièrement
supprimés - plus nécessaires. `_UTIL_get_gradient_keys` réécrite pour
utiliser `modo.Channel(channelName, item).envelope.keyframes` - même
signature de retour qu'avant (tuple de `(pos, value, slopeType, slope,
weighted)`), donc `_UTIL_gradient_keys_to_xml_dicts`/les appelants dans
`_UTIL_format_channel`/`_UTIL_format_channel_value` n'ont pas eu besoin
de changer. Le repli `_UTIL_sample_gradient` (Round 37,
`GradientFilter.Generate(t)`) conservé tel quel comme filet de sécurité
si `modo.Channel(...).envelope` lève malgré tout.

123 tests pytest toujours verts (aucun test ne couvre ce chemin,
dépendant de Modo).

**Rounds 37-42 retestés et confirmés par l'auteur le 2026-08-13** ("the
xml is conform to what expected") : l'étage 1 (extraction XML) des couches
Gradient produit bien de vraies clés `<Key pos=".." value=".."
slopeType=".."/>` par composante (`value` et `red`/`green`/`blue`/`alpha`
sous `<color>`), avec `slopeType` en toutes lettres et `minPos`/`maxPos`
posés correctement, et le `txtrLocator` du Gradient apparaît dans le XML -
conforme à ce qui était attendu depuis le Round 37. Clôt la dernière
priorité de test ouverte en tête de fichier sur ce sujet. L'étage 3
(traduction USD/mtlx) reste abandonné depuis le Round 54 - aucune couche
Gradient ne produit de nœuds côté USD, uniquement ce XML normalisé fidèle.

#### Round 43, étage 3 (USD/mtlx) pour les couches Gradient — premier cas concret `incidenceAngle`, IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO (2026-08-12)

Suite des Rounds 37-42 (étage 1, extraction XML uniquement) : première
traduction USD/mtlx réelle d'une couche `Gradient`, sur le seul cas
d'entrée confirmé par l'auteur - `param="incidenceAngle"` (chaîne exacte
confirmée dans un vrai export, pas devinée).

**Recherche préalable, avant tout code** (même discipline que le reste de
la session) :
- `<viewdirection>`/`<facingratio>`/`<dotproduct>`/`<acos>` confirmés
  exister dans le vrai stdlib MaterialX standalone. `facingratio` écarté
  au profit de `dotproduct`+`acos` : l'auteur a confirmé que
  `incidenceAngle` expose un **angle en degrés**, pas juste le cosinus
  (`facingratio` s'arrête au cosinus). Pas de nœud radians→degrés natif
  dans le stdlib - un `multiply` par `180/π` fait le travail.
- **`<ramp>` (10 points fixes) et `<ramp_gradient>` (chaînable, illimité)
  confirmés exister** - dépassent largement les `ramp4`/`ramplr`/`ramptb`
  (2-4 points) déjà découverts au Round 36, qui avaient motivé le plan de
  repli "bake en LUT" évoqué avant ce round. Les deux ont un type de
  sortie figé `color4` (aucune variante `float`/`color3` contrairement à
  `ramp4`/`ramplr`/`ramptb`) - une conversion finale est donc toujours
  nécessaire.
- **Aucun fichier `.glsl` d'implémentation pour `ramp`/`ramp_gradient`**
  dans le stdlib (contrairement à la plupart des autres nœuds) - signal
  qu'ils sont probablement implémentés en pur nodegraph plutôt qu'en
  shader source natif. Vérifié en lisant directement
  `stdlib_ng.mtlx` (le fichier de nodegraphs d'implémentation, déjà
  consulté aux Rounds 8/10 pour `ND_tiledimage`) : `NG_ramp` (l'implémentation
  réelle de `<ramp>`) est elle-même construite comme **9 `ramp_gradient`
  chaînés** - confirme à la fois que l'approche "chaîner `ramp_gradient`"
  est la bonne, et donne le patron de câblage exact à reproduire (au lieu
  de deviner la sémantique de `prev_color`/`interval_num`/`num_intervals`) :
  le nœud N a `interval1`/`color1` = `interval2`/`color2` du nœud N-1,
  `prev_color` connecté à la sortie du nœud N-1 (le tout premier nœud a
  `prev_color` = son propre `color1`, rien avant lui), `interval_num`/
  `num_intervals` = position/nombre total de segments.

**Implémenté** (`ShaderTree.py`) :
- `MODO_SLOPE_TYPE_TO_MTLX_INTERPOLATION` - table de repli, les 8 types
  de pente Modo (Round 40/41) regroupés sur les 3 valeurs de
  `interpolation` de `ramp_gradient` (`linear`/`smooth`/`step`) - forcément
  approximatif (Modo a plus de granularité), un choix raisonnable mais
  **non vérifié visuellement** (`DIRECT`/`LINEAR_IN`/`LINEAR_OUT`→linéaire,
  `AUTO`/`AUTOFLAT`/`FLAT`/`SMOOTHFLAT`→smooth, `STEPPED`→step).
- `_USD_create_gradient_driver(stage, path, param)` - construit la chaîne
  `ND_normal_vector3`(space=**world**, pas le défaut "object" - piège déjà
  identifié en sketch)→`ND_viewdirection_vector3`(space=world)→
  `ND_dotproduct_vector3`→`ND_acos_float`→`ND_multiply_float`(×57.29578)
  pour `param == "incidenceAngle"` ; tout autre `param` déclenche
  `_DEBUG_diag("Unsupported", "Gradient_Param", ...)` et retourne `None`
  (la couche entière est alors ignorée) - même convention que toutes les
  autres tables "on ne traduit que ce qui est confirmé" du fichier.
- `_USD_read_gradient_keys(rampXml)` - relit les `<Key pos=".." value=".."
  slopeType=".."/>` déjà posés par l'étage 1 (Round 38/39) directement
  depuis le XML normalisé - **aucune dépendance Modo à ce stade**, cohérent
  avec l'architecture à 3 étages (la construction USD ne lit que le XML,
  jamais directement l'API Modo).
- `_USD_create_ramp_gradient_chain(stage, path, driverOutput, keys)` -
  reproduit le patron `NG_ramp` ci-dessus pour un nombre de clés
  arbitraire (pas de plafond à 10, contrairement à `<ramp>`) ; une seule
  clé se réduit à un simple `ND_constant_color4` (pas de rampe possible
  avec un seul point).
- `_USD_convert_gradient_output(stage, path, color4Output, targetType)` -
  `ND_separate4_color4` puis soit `outr` direct (Float, ex. un effet
  scalaire), soit `ND_combine3_color3` sur `outr`/`outg`/`outb` (Color3f,
  alpha jetée).
- `_USD_create_gradient_output(stage, materialPath, xml, targetType)` -
  orchestrateur : lit `param`, construit le driver (retourne `None` tôt
  si non supporté), choisit `value` (cible Float) ou `color`/`red`+`green`+
  `blue` zippés par index (cible autre, assume les mêmes positions de clé
  entre composantes - vrai dans tous les cas observés jusqu'ici, un
  `_DEBUG_diag` prévient si les comptes de clés diffèrent), construit la
  chaîne de rampe, convertit vers `targetType`.
- Nouvelle branche `elif elementName == "gradient":` dans
  `_USD_export_shadertree`, calquée sur `constant`/`imageMap` - réutilise
  **sans aucune modification** `_USD_add_shader_connector_to_context`/
  `_USD_connect_effect_stack` (déjà entièrement génériques sur n'importe
  quelle source d'`UsdShade.Output`) pour le blend/opacity/empilement de
  couches. Pas de câblage glPreview (aucun équivalent natif possible,
  même famille de limite que triplanaire/noise/contrast déjà documentée).

**Vérifié structurellement contre `usd-core`** (reconstruit le graphe
complet hors Modo avec du XML factice calqué sur un vrai export - un
gradient `value` à 2 clés et un `color` à 3 clés) : chaîne driver
correctement typée de bout en bout, rampe `value` (1 segment) et `color`
(2 segments chaînés, `prev_color` bien connecté au nœud précédent)
conformes au patron `NG_ramp`, conversions finales `Float`/`Color3f`
correctement typées. 123 tests pytest toujours verts (aucun ne couvre ce
chemin, dépendant de Modo).

**Pas testé dans Modo/Houdini.** À faire en priorité : réexporter avec la
couche `Gradient` de test (`param="incidenceAngle"`) et confirmer dans
Houdini que le résultat ressemble à ce que Modo affiche. Points
spécifiquement incertains, à surveiller en premier si le rendu diverge :
la table d'approximation `slopeType`→`interpolation`, et si Karma
supporte réellement `ND_ramp_gradient`/`ND_viewdirection`/`ND_acos`
(vérifiés exister dans le stdlib MaterialX, mais comme pour `mirror`/
`constant` côté wrap modes - Round 11/17 - le support réel d'un moteur
de rendu tiers pour un nœud stdlib n'est jamais garanti par sa seule
présence dans la spec).

#### Round 44, deux `NodeGraph` distincts pour la traduction Gradient (driver + rampe) — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO (2026-08-12)

Demande de l'auteur juste après le Round 43 : regrouper la chaîne
d'évaluation `incidenceAngle` (`normal`/`viewdirection`/`dotproduct`/
`acos`/`multiply`) dans son propre `NodeGraph`, séparé de la rampe elle-même
(qui a aussi son propre `NodeGraph`) - même logique de rangement que
`UV_Transform` (Round 12) : une chaîne de calcul cohérente devient une
seule boîte repliable dans l'éditeur de graphe, plutôt que des nœuds
frères éparpillés sous le matériau.

Implémenté en suivant exactement le patron déjà établi par
`_USD_create_UV_transform` (interface inputs créées sur le `NodeGraph`,
nœuds internes qui lisent `nodeGraph.GetInput(...)`, sortie unique exposée
via `nodeGraph.CreateOutput('out', type).ConnectToSource(...)`) :

- `_USD_create_gradient_driver` : la chaîne `incidenceAngle` est maintenant
  posée dans un `NodeGraph` nommé `<gradient>_incidenceAngle` (le nom du
  `param` en suffixe - un futur `param` supporté aurait son propre
  `NodeGraph` nommé de la même façon), sans aucun input d'interface
  (rien ne vient de l'extérieur - normal/viewdirection sont purement
  procéduraux). Une seule sortie `out` (float, degrés) exposée.
- `_USD_create_gradient_output` : la chaîne de rampe (`ND_ramp_gradient`
  chaînés) + la conversion vers `targetType` sont maintenant posées dans
  un second `NodeGraph`, nommé `<gradient>_Gradient`, avec un seul input
  d'interface `x` (float) connecté à la sortie du premier `NodeGraph` -
  `_USD_create_ramp_gradient_chain` reçoit maintenant `nodeGraph.GetInput('x')`
  au lieu de la sortie brute du driver (`UsdShade.Input` accepté par
  `ConnectToSource()` au même titre qu'un `UsdShade.Output`, déjà utilisé
  ainsi par `_USD_create_UV_transform`). Sortie unique `out` (typée
  `targetType`) exposée.

Aucun changement dans `_USD_create_ramp_gradient_chain`/
`_USD_convert_gradient_output` eux-mêmes (toujours des fonctions "plates"
qui posent des nœuds à un `path` donné - c'est maintenant le chemin du
`NodeGraph` "_Gradient" plutôt que celui du layer directement, mais leur
logique interne est inchangée).

**Vérifié structurellement contre `usd-core`** (même XML factice que le
Round 43) : les deux `NodeGraph` apparaissent bien comme deux prims
distincts, `Gradient_Gradient.inputs:x.connect` pointe correctement vers
`Gradient_incidenceAngle.outputs:out`, et les nœuds internes de la rampe
référencent bien l'input d'interface `x` du `NodeGraph` englobant plutôt
qu'une connexion directe traversant la frontière. Un premier passage de
vérification a montré un résultat `color3f` incorrect (`"float"` au lieu
de `"color3f"`) - retracé à un artefact du script de vérification
lui-même (deux appels de test réutilisant le même nom de gradient, donc
le même chemin de prim, le second écrasant/réutilisant le `NodeGraph` du
premier sans retyper son output) - **pas un bug du code réel**, qui
construit toujours un nom de gradient unique par couche
(`xml.get('name')`, jamais réutilisé). Reconfirmé avec des noms
distincts : les deux types de sortie (`float`/`color3f`) sont corrects
indépendamment. 123 tests pytest toujours verts.

**Pas testé dans Modo/Houdini** - mêmes points d'incertitude que le
Round 43 (table `slopeType`, support réel de Karma pour ces nœuds),
inchangés par cette réorganisation purement structurelle (aucun calcul
ne change, seul l'emplacement des prims).

#### Round 45, `x`/`interval1`/`interval2` de `ND_ramp_gradient` normalisés en [0,1] — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO (2026-08-12)

L'auteur repère un problème dans le Round 43/44 : "the mtlx:ramp node's
interval values are limited between 0 and one". Vérifié directement dans
le vrai nodedef (`stdlib_defs.mtlx`, paquet `MaterialX` standalone
`.venv`) :

```
<nodedef name="ND_ramp_gradient" node="ramp_gradient" nodegroup="procedural2d">
  <input name="x" type="float" value="0" uimin="0" uimax="1" />
  <input name="interval1" type="float" value="0" uimin="0" uimax="1" />
  <input name="interval2" type="float" value="1" uimin="0" uimax="1" />
  ...
```

(`ND_ramp`'s `interval1..interval10` portent la même contrainte). Avant ce
round, le driver `incidenceAngle` (Round 43) posait des **degrés bruts**
(0-180) sur `x`, et les positions de clé extraites (`pos`, également en
degrés, cf. "les gradients Modo ne sont pas normalisés en [0,1]" noté par
l'auteur plus tôt) étaient posées telles quelles sur `interval1`/
`interval2` - en dehors de la plage `[0,1]` déclarée par le nodedef dès
qu'un angle dépasse 1°.

Corrigé en normalisant les deux côtés par la même référence (180°), pour
que la position relative de `x` par rapport aux intervalles reste
mathématiquement identique, seulement ramenée dans la plage `[0,1]` :

- `_USD_create_gradient_driver` (`ShaderTree.py`) : le dernier nœud de la
  chaîne `incidenceAngle` (`normal`→`viewdirection`→`dotproduct`→`acos`)
  ne convertit plus radians→degrés (`× 57.29577951308232`) mais
  radians→`[0,1]` normalisé (`× 1/π`, puisque `θ_rad/π == θ_deg/180`) -
  nœud et variable Python renommés de `degreesShader`/`degreesOutput` à
  `normalizeShader`/`normalizeOutput` pour refléter ce nouveau rôle.
- Nouvelle table `GRADIENT_PARAM_KEY_SCALE` (`ShaderTree.py`, à côté de
  `MODO_SLOPE_TYPE_TO_MTLX_INTERPOLATION`) : `{"incidenceAngle": 180.0}` -
  facteur par lequel diviser les positions de clé brutes (dans l'unité
  native du `param`) pour rester cohérent avec la normalisation du driver.
  Consultée dans `_USD_create_gradient_output`, appliquée à `pos` avant de
  construire `keys` (branche `value`/Float **et** branche `color`/
  Color3f-Color4f), avec un repli à `1.0` (no-op) pour tout `param` sans
  entrée dans la table.

Choix délibéré de garder ce facteur **par param** (pas une constante
globale) : un futur `param` avec une plage native différente (ex. une
distance sans borne fixe à 180) aurait besoin d'un facteur différent, pas
forcément même de cette forme "diviser par une constante" - `1.0` par
défaut (no-op) reste sûr pour tout `param` pas encore dans la table.

**Vérifié structurellement contre `usd-core`** : reconstruit la chaîne
complète avec des clés de test à 0°/90°/180°, confirmé que les positions
normalisées atterrissent exactement à 0.0/0.5/1.0 - à la fois `x` (sortie
du driver) et `interval1`/`interval2` (positions de clé) restent dans
`[0,1]`, et la position relative (0.5 = le milieu) est préservée. 123
tests pytest toujours verts (aucun ne couvre ce chemin encore -
`GRADIENT_PARAM_KEY_SCALE` n'a pas de test dédié, comme le reste de la
traduction Gradient côté USD).

**Pas testé dans Modo/Houdini** - reste dans la même situation que les
Rounds 43/44 (rien de la traduction Gradient n'a encore tourné en dehors
de la vérification structurelle `usd-core`).

#### Round 46, `GRADIENT_PARAM_KEY_SCALE` (Round 45) remplacé par `minPos`/`maxPos` calculés sur les vraies clés — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO (2026-08-12)

L'auteur propose une approche plus générale que la table par-param du
Round 45 : plutôt que de deviner/coder en dur la plage native de chaque
`param` (`180.0` pour `incidenceAngle`, une constante qui ne dit rien sur
ce qu'un futur `param` pourrait avoir besoin), calculer `minPos`/`maxPos`
directement à partir de toutes les vraies positions de clé trouvées à
l'étage 1 (extraction XML), les poser en attributs sur l'élément
`<gradient ...>` lui-même, et s'en servir à l'étage 3 pour normaliser à la
fois les intervalles et la sortie du driver - entièrement dérivé des
données réelles de la couche, pas d'une table figée à maintenir par
`param`.

Implémenté :
- **`_XML_export_item`** (`ShaderTree.py`, étage 1) : juste après avoir
  attaché `channels` à `out_xml` pour un item `gradient`
  (`item.type == lx.symbol.sITYPE_GRADIENT`), `channels.findall('.//Key')`
  récupère **tous** les `<Key pos=".."/>` du sous-arbre - `value` **et**
  les 4 `<color>/<red|green|blue|alpha>` combinés (ils partagent le même
  domaine de `param`, pas de raison de les traiter séparément). `minPos`/
  `maxPos` (min/max de ces positions) posés en attributs sur l'élément
  `<gradient ...>` lui-même - pas sur `<channels>` ni sur une clé
  particulière, pour rester au niveau de la couche entière. Repli
  `xml.get('minPos', "0.0")`/`xml.get('maxPos', "1.0")` côté étage 3 si
  l'attribut est absent (aucune clé trouvée) ou si le XML vient d'une
  version antérieure à ce round.
- **`_USD_create_gradient_driver`** : revient à produire des **degrés
  bruts** (`× 57.29577951308232`, comme au Round 43) au lieu du `[0,1]`
  normalisé du Round 45 - le driver ne connaît plus la normalisation, elle
  est maintenant entièrement portée par le graphe consommateur, qui seul
  connaît `minPos`/`maxPos` (propriété de la couche, pas du driver).
- **`_USD_create_gradient_output`** : `keyScale`/`GRADIENT_PARAM_KEY_SCALE`
  retirés. `minPos`/`maxPos` lus depuis `xml` (l'élément `<gradient>`),
  gardés contre une plage dégénérée (`maxPos == minPos` → `maxPos =
  minPos + 1.0`, évite une division par zéro si toutes les clés partagent
  la même position). Les positions de clé extraites sont normalisées en
  Python (`(pos - minPos) / (maxPos - minPos)`, un simple calcul sur des
  floats déjà connus à la construction). La sortie brute (en degrés) du
  driver, elle, ne peut pas être normalisée en Python (c'est une valeur
  évaluée au rendu, pas une constante) - un nouveau nœud `ND_remap_float`
  (déjà utilisé ailleurs dans ce fichier pour le post-traitement de
  texture, `_USD_create_texture_adjust_nodegraph`) fait ce travail dans le
  graphe mtlx lui-même : `inlow`/`inhigh` = `minPos`/`maxPos`, `outlow`/
  `outhigh` = `0`/`1`. Posé dans le `NodeGraph` "_Gradient" (Round 44),
  juste après l'interface input `x` ; la chaîne de rampe consomme
  maintenant la sortie de ce remap plutôt que `x` directement.

**Vérifié structurellement contre `usd-core`** : simulé le calcul
`minPos`/`maxPos` de l'étage 1 sur un XML factice (3 clés à
20°/60°/140°), confirmé `minPos=20.0`/`maxPos=140.0`, puis reconstruit le
graphe complet de l'étage 3 - la clé du milieu (60°) atterrit exactement à
`(60-20)/(140-20) = 0.3333...`, et `ND_remap_float.inputs:inlow/inhigh`
portent bien `20`/`140` (les vraies bornes des données, pas une constante
théorique comme `0`/`180`). 123 tests pytest toujours verts (aucun ne
couvre ce chemin, dépendant de Modo pour l'étage 1).

**Pas testé dans Modo/Houdini** - mêmes réserves que les Rounds 43-45.
Point à surveiller en particulier : le repli `minPos=0.0`/`maxPos=1.0` (si
aucune clé n'est trouvée) n'a jamais été exercé par un cas réel - à
vérifier si un gradient sans clé authored (littéral `"gradient"`, tout en
bas de la chaîne de repli du Round 38) atteint un jour cette branche.

#### Round 47, `red`/`green`/`blue` traités comme 3 rampes indépendantes (pas une seule zippée par index) + normalisées sur un `minPos`/`maxPos` partagé — IMPLÉMENTÉ, PAS ENCORE TESTÉ DANS MODO (2026-08-12)

L'auteur repère un problème de fond dans le Round 43 : `_USD_create_gradient_output`
lisait bien `red`/`green`/`blue` séparément (chacun avec ses propres clés,
conformément au Round 39 - Modo permet des positions de clé indépendantes
par composante), mais les recombinait ensuite en **zippant par index** -
supposant implicitement que les trois composantes partagent les mêmes
positions de clé. Faux dès qu'une composante a un nombre de clés différent
ou des positions différentes des deux autres - exactement le cas que le
Round 39 avait pris soin d'extraire correctement puis que le Round 43
ignorait à la construction.

**Partie 1 - une rampe mtlx par composante.** `ND_ramp_gradient` n'a de
toute façon qu'une sortie `color4` figée (pas de variante scalaire, déjà
noté Round 43) - rien n'empêchait de construire **trois rampes
indépendantes** (une par composante, chacune avec ses propres clés/
positions), d'en extraire le canal `outr` de chacune (`ND_separate4_color4`,
en empaquetant la valeur scalaire de chaque composante en `(v,v,v,1)`
comme le fait déjà le chemin `value`/Float), puis de recombiner les trois
`Float` obtenus via `ND_combine3_color3` - au lieu d'essayer de faire
porter les trois composantes par une seule rampe `color4`.

**Partie 2 - alignement du domaine, signalé par l'auteur juste après**
la partie 1 : si chaque composante est normalisée sur son **propre**
`minPos`/`maxPos` (le Round 46 appliqué indépendamment à chacune), une clé
à la position absolue 50 dans `red` et une clé à la position absolue 50
dans `green` atterriraient à des `x` normalisés différents (puisque leurs
plages diffèrent) - cassant l'alignement entre composantes et avec le
driver, qui produit une seule valeur brute partagée pour les trois. La
vraie sémantique : `red`/`green`/`blue` vivent sur le **même** axe de
paramètre partagé (le `param`, ex. `incidenceAngle`), simplement avec des
clés placées à des positions différentes sur cet axe commun - pas trois
axes indépendants. Il faut donc les normaliser tous les trois contre la
**même** plage.

Implémenté :
- **`_XML_get_channels`** (`ShaderTree.py`, étage 1) : chaque groupe
  (`red`/`green`/`blue`/`alpha`) garde son propre `minPos`/`maxPos` (utile
  comme métadonnée, pas relu en aval pour l'instant), **et** un
  `minPos`/`maxPos` **combiné** (union des 4 plages - min des mins, max
  des maxs) est maintenant posé sur l'élément parent `<color>` lui-même -
  c'est celui-là que l'étage 3 consomme pour `red`/`green`/`blue`.
  `<value>` (rampe scalaire seule, pas décomposée en composantes) garde sa
  propre plage sans combinaison - rien à réconcilier puisqu'il n'y a pas
  de composantes sœurs. Nouveau petit utilitaire partagé
  `_UTIL_set_key_pos_range(el, positions)` (remplace la logique dupliquée
  du Round 46, maintenant appelée à 3 endroits : `value`, chaque groupe,
  `color` combiné) - retiré le hook `_XML_export_item`/`sITYPE_GRADIENT`
  du Round 46 (plus nécessaire, le calcul se fait maintenant directement
  là où chaque liste de `<Key>` est construite, sans reparcourir l'arbre
  après coup ni connaître le type de l'item).
- **`_USD_create_gradient_channel_ramp`** (nouvelle fonction,
  `ShaderTree.py`, étage 3) : construit une rampe complète pour **une**
  composante (`normalize` remap → chaîne `ND_ramp_gradient` → `separate4`→
  `outr`), prenant `minPos`/`maxPos` en paramètres explicites plutôt que
  de les lire sur son propre élément XML - permet à l'appelant de décider
  si la plage vient de la composante elle-même (`value`) ou d'un parent
  partagé (`color`). Chaque composante a son propre sous-espace de prims
  (`<gradient>_Gradient/red/...`, `/green/...`, `/blue/...`) - pas de
  collision de noms entre les trois chaînes de segments.
- **`_USD_convert_gradient_output`** simplifiée : ne fait plus que
  l'extraction `color4 -> Float` (`ND_separate4_color4.outr`) - les
  branches `Color3f`/`Color4f` (recombinaison) sont devenues mortes avec
  la nouvelle architecture (chaque appel se fait maintenant toujours avec
  une seule composante scalaire) et ont été retirées ; le paramètre
  `targetType` disparaît de sa signature.
- **`_USD_create_gradient_output`** restructurée : pour un target `Float`,
  un seul appel à `_USD_create_gradient_channel_ramp` ("value", avec la
  plage de `<value>`). Pour tout autre target (`Color3f` - le seul autre
  cas réel, confirmé par `usdTypeMap` qui ne contient aucune entrée
  `Color4f`), trois appels ("red"/"green"/"blue", tous avec la plage
  **combinée** de `<color>`), puis `ND_combine3_color3` posé directement
  ici (déplacé hors de `_USD_convert_gradient_output`, plus besoin d'y
  vivre séparément). Le diagnostic Round 43 "red/green/blue key counts
  differ" retiré - plus nécessaire, chaque composante est maintenant
  authentiquement indépendante, aucune hypothèse de comptage égal.

**Vérifié structurellement contre `usd-core`** : simulé le calcul de
plage combinée à l'étage 1 avec des positions volontairement différentes
par composante (`red` 0-100, `green` 20-140, `blue` 50-90, `alpha` 0-0),
confirmé `<color>` combiné = `minPos=0.0`/`maxPos=140.0` (l'union). Puis
reconstruit le graphe complet de l'étage 3 : les trois `normalize`
(`ND_remap_float`) portent bien tous `inlow=0`/`inhigh=140` (identiques,
pas la plage propre de chaque composante), les positions de clé de chaque
composante sont correctement normalisées contre cette plage partagée
(ex. `red` à pos=100 -> `x=100/140≈0.714`, `green` à pos=20 -> `x=20/140≈
0.143`), et `combine` recombine bien les trois sorties `outr` de chaque
`separate` en un seul `color3f`. 123 tests pytest toujours verts (aucun ne
couvre ce chemin, dépendant de Modo pour l'étage 1).

**Pas testé dans Modo/Houdini** - mêmes réserves que les Rounds 43-46.

#### Round 48, connexion `Gradient_incidenceAngle` -> `Gradient_Gradient` invisible dans Houdini — CORRIGÉ (2026-08-12)

Premier test réel dans Houdini de la structure à 2 `NodeGraph` du Round 44 :
l'auteur importe et constate que la sortie du `NodeGraph` `Gradient_incidenceAngle`
n'est **pas** connectée à l'input `x` de `Gradient_Gradient` - le fil n'apparaît
pas dans l'éditeur de graphe de matériau.

Cause identifiée par comparaison avec le reste du fichier : cette connexion
était la **seule** de tout `ShaderTree.py` où la sortie exposée d'un
`NodeGraph` (`nodeGraph.CreateOutput('out', ...)`) alimente directement
l'input d'un **autre** `NodeGraph` (`nodeGraph.CreateInput('x',
...).ConnectToSource(driverOutput)`, avec `driverOutput = nodeGraph.GetOutput("out")`
du driver). Partout ailleurs où un `NodeGraph` reçoit une donnée de
l'extérieur, la source est la sortie d'un vrai `Shader` - jamais celle d'un
autre `NodeGraph` : `_USD_create_UV_transform`'s input `"texcoord"` est
alimenté par `ND_geompropvalue_vector2` (un `Shader`), confirmé fonctionner
dans Houdini depuis les Rounds 13/14. Cohérent avec plusieurs précédents
déjà documentés dans ce fichier (Round 3 : `ND_texcoord_vector2`/
`UsdPrimvarReader_float2` ne se résolvaient pas non plus comme source à
l'intérieur d'un graphe mtlx compilé) - la traduction MaterialX-vers-Hydra
de Houdini semble ne pas résoudre de façon fiable une connexion directe
sortie-de-NodeGraph -> entrée-de-NodeGraph entre deux `NodeGraph` frères,
même si c'est parfaitement valide en USD pur (vérifié à nouveau contre
`usd-core`, aucune erreur, structure cohérente).

Corrigé dans `_USD_create_gradient_driver` (`ShaderTree.py`) : la fonction
retourne maintenant directement la sortie du dernier `Shader` de la chaîne
(`degreesOutput`, le nœud `multiply`) au lieu de `nodeGraph.GetOutput("out")`.
Le `NodeGraph` `Gradient_incidenceAngle` garde sa propre sortie `outputs:out`
posée et connectée en interne (utile pour l'inspection/regroupement visuel
dans l'éditeur de graphe d'un DCC) - elle n'est simplement plus ce que
`_USD_create_gradient_output` utilise pour câbler l'input `"x"` de
`Gradient_Gradient`. Les deux `NodeGraph` demandés par l'auteur au Round 44
restent en place, seule la cible réelle de la connexion change.

**Vérifié structurellement contre `usd-core`** : reconstruit la chaîne
complète, confirmé via `UsdShade.Input.GetConnectedSource()` que
`Gradient_Gradient.inputs:x` pointe maintenant vers le prim `Shader`
`Gradient_incidenceAngle/multiply` (pas vers le prim `NodeGraph`
`Gradient_incidenceAngle` lui-même). 123 tests pytest toujours verts.

**Pas encore reconfirmé dans Houdini** - la correction elle-même n'a pas
encore été retestée par un nouvel export/import, seul le bug d'origine a
été confirmé par l'auteur.

#### Round 49, les 2 `NodeGraph` (driver + rampe) fusionnés en un seul — CORRIGÉ, PAS ENCORE RETESTÉ DANS HOUDINI (2026-08-12)

Retest du Round 48 dans Houdini : l'auteur signale que les nœuds de la
chaîne `incidenceAngle` ne sont plus regroupés dans leur propre
`NodeGraph` du tout - Houdini les a "aplatis" hors de `Gradient_incidenceAngle`.

Cause : le fix du Round 48 faisait toujours pointer `Gradient_Gradient.inputs:x`
vers un nœud **interne** à `Gradient_incidenceAngle` (`.../multiply`), en
traversant sa frontière depuis un `NodeGraph` frère complètement séparé -
un cas de figure différent de `_USD_create_UV_transform`'s `"texcoord"`
(alimenté par `ND_geompropvalue_vector2`, un `Shader` qui n'est **enveloppé
dans aucun `NodeGraph`** - un simple prim frère). En comparant les deux
cas, la règle qui se dégage de tout ce qui fonctionne réellement dans ce
fichier : referencer un `Shader` depuis l'extérieur ne pose problème que
si ce `Shader` est encapsulé dans un **second** `NodeGraph` distinct -
Houdini semble alors "casser" cette encapsulation (en aplatissant) plutôt
que de simplement résoudre la connexion. Aucune des deux tentatives
(Round 44 : référencer la sortie déclarée du second `NodeGraph` ; Round 48 :
référencer un nœud interne du second `NodeGraph`) n'a survécu intacte à la
traduction MaterialX-vers-Hydra de Houdini - le problème de fond est
d'avoir **deux** `NodeGraph` de haut niveau qui se référencent l'un
l'autre, pas le choix précis de la cible référencée.

Corrigé en fusionnant les deux `NodeGraph` en un seul : `_USD_create_gradient_driver`
ne crée plus son propre `NodeGraph` - ses 5 nœuds (`normal`/`viewdirection`/
`dotproduct`/`acos`/`multiply`) sont maintenant posés directement sous le
`path` passé par l'appelant (imbriqués dans un sous-espace `<path>/incidenceAngle/...`,
même convention de nommage que les sous-espaces `red`/`green`/`blue`/`value`
déjà utilisés pour les rampes). `_USD_create_gradient_output` crée
maintenant le `NodeGraph` "_Gradient" **avant** d'appeler le driver, et lui
passe son propre chemin - driver et rampes vivent donc tous les deux à
l'intérieur du même unique `NodeGraph`. La connexion `remap.inputs:in` (dans
`_USD_create_gradient_channel_ramp`, renommé `xInput`->`driverOutput` pour
refléter que ce n'est plus un input d'interface mais la sortie brute du
`Shader` driver) devient une connexion `Shader`-vers-`Shader` purement
interne au `NodeGraph`, exactement comme le chaînage des segments de rampe
entre eux (déjà éprouvé) - plus aucune frontière de `NodeGraph` à
traverser à l'intérieur. Seule la sortie finale du `NodeGraph` (posée sur
`nodeGraph.outputs:out`, consommée par le shader `standard_surface` via
`_USD_add_shader_connector_to_context`) reste une frontière traversée -
et c'est exactement le patron `NodeGraph`-sortie -> `Shader`-entrée déjà
éprouvé partout ailleurs (`UV_Transform`, Round 4-18).

**Vérifié structurellement contre `usd-core`** : reconstruit la chaîne
complète, confirmé qu'un seul prim `NodeGraph` existe sur tout le stage,
que `remap.inputs:in` pointe vers `.../incidenceAngle/multiply` (un
`Shader`, connexion purement interne au même `NodeGraph`), et que la
sortie externe du `NodeGraph` pointe vers `.../value/separate` (un
`Shader`, le patron déjà éprouvé). 123 tests pytest toujours verts.

**Pas encore retesté dans Houdini** - deux tentatives précédentes (Round
44, Round 48) ont chacune paru correctes contre `usd-core` mais ont
échoué une fois testées en conditions réelles ; cette fusion en un seul
`NodeGraph` élimine la classe de problème identifiée (deux `NodeGraph` se
référençant l'un l'autre), mais reste à confirmer par un vrai
export/import avant de la considérer close.

#### Round 50, `ND_ramp_gradient` diagnostiqué comme n'évaluant pas dans Karma + remplacé par un seul `ND_ramplr_float` par canal (2026-08-12)

Le Round 49 a corrigé la structure du graphe (un seul `NodeGraph`,
confirmé par capture d'écran de l'éditeur "Edit Material" de Houdini :
`normal`/`viewdirection`/`dotproduct`/`acos`/`multiply` alimentent bien
les 3 `normalize` (un par canal), chacun sa propre chaîne de
`ramp_gradient`, `separate`, jusqu'à `combine` → `out`) - **mais le rendu
restait un rond blanc/chrome sans aucune couleur**, fond noir au lieu de
vert sur le stencil. Diagnostic par bissection, fait par l'auteur
directement dans Houdini :

1. Remplacer l'entrée de `normalize` (driver) par une constante littérale
   (`1.0`) sur les 3 canaux → **aucun changement** dans le rendu. Élimine
   la chaîne `normal`/`viewdirection`/`dotproduct`/`acos`/`multiply` comme
   coupable.
2. Câbler 3 constantes littérales différentes (`0.5`/`0.772`/`0.192`)
   directement sur `combine.in1/in2/in3` (court-circuitant tout le reste,
   `ramp_gradient`+`separate` compris) → **rendu vert-jaune correctement
   visible**, confirmant que `combine` → `out` → `bound_out` → `diffColor`
   fonctionne bien dans Karma.

Les deux tests combinés isolent le problème à la chaîne `ramp_gradient`/
`separate4` elle-même - **`ND_ramp_gradient` (ou `ND_separate4_color4`)
n'évalue pas correctement dans Karma**, malgré un graphe structurellement
valide (vérifié à plusieurs reprises contre `usd-core`) et visible/éditable
dans l'éditeur de graphe de matériau de Houdini (l'éditeur n'a besoin que
du nodedef pour dessiner un nœud, pas d'une implémentation shader
fonctionnelle derrière - donc un graphe qui *a l'air* correct dans
l'éditeur ne garantit pas qu'il s'évalue). Cohérent avec la classe de
limite déjà rencontrée pour `mirror`/`constant` (wrap modes, Round 11/17) -
un nœud valide selon la spec MaterialX mais dont le support réel côté
Houdini/Karma n'est pas garanti.

**Solution proposée par l'auteur, plutôt que de creuser plus loin lequel
des deux nœuds est en cause** : remplacer la chaîne de `ND_ramp_gradient`
par un **unique** `ND_ramplr_float` par canal - une rampe gauche-droite à
2 points seulement (`valuel`/`valuer`, interpolés linéairement selon
`texcoord.x`, vérifié dans le vrai `mx_ramplr_float.glsl` du stdlib :
`mix(valuel, valuer, clamp(texcoord.x, 0, 1))`), en ne gardant que la
**première et la dernière** clé de chaque canal (les clés intermédiaires
sont perdues) - compromis explicitement accepté par l'auteur pour
avancer. Contrairement à `ND_ramp_gradient`/`ND_ramp` (tous deux figés en
sortie `color4`, Round 43), `ND_ramplr_float` a une vraie sortie `float` -
plus besoin de `ND_separate4_color4` pour en extraire un scalaire.

Implémenté (`ShaderTree.py`) :
- `_USD_create_ramp_gradient_chain`/`_USD_convert_gradient_output`
  (chaîne `ramp_gradient` + extraction `separate4`) supprimées, remplacées
  par `_USD_create_gradient_ramp` : construit `texcoord` (`ND_combine2_vector2`,
  empaquette la sortie normalisée du driver en `vector2`, `y` inutilisé)
  puis un seul `ND_ramplr_float` (`valuel`/`valuer` = valeur de la
  première/dernière clé, triées par position). `_USD_create_gradient_channel_ramp`
  simplifiée en conséquence (plus d'appel à `_USD_convert_gradient_output`,
  la sortie de `_USD_create_gradient_ramp` est déjà un `Float`).
  `MODO_SLOPE_TYPE_TO_MTLX_INTERPOLATION` (Round 43) supprimée - `ND_ramplr_float`
  n'a pas d'input d'interpolation, la table n'a plus de consommateur.
- **Canal alpha ajouté**, sur demande explicite de l'auteur ("it may be
  important") : `_USD_create_gradient_output` construit maintenant 4
  rampes indépendantes (red/green/blue/alpha, toutes normalisées contre
  le même `minPos`/`maxPos` combiné de `<color>`, Round 47 inchangé) et
  les recombine via `ND_combine4_color4` (au lieu de `ND_combine3_color3`)
  en un `color4f`. Comme aucun effet réel n'a `Color4f` comme
  `usdTypeMap` cible aujourd'hui, un pont `ND_separate4_color4` +
  `ND_combine3_color3` (même mécanisme déjà éprouvé Round 28/33) réduit
  ce résultat à `Color3f` pour le cas réel actuel - alpha est donc bien
  calculé et alimente `combine`, mais reste actuellement jeté juste après
  faute de consommateur `Color4f`. Le chemin `Color4f` direct (si
  `targetType` en demandait un un jour) est géré sans ce pont.

**Vérifié structurellement contre `usd-core`** : reconstruit le graphe
complet avec des clés de test différentes par canal (red 0→100, green
20→140, blue 50→90, alpha à une seule clé) - chaque `ND_ramplr_float`
porte bien `valuel`/`valuer` égaux à la valeur de la première/dernière
clé de son propre canal (alpha, un seul point, se réduit correctement à
`valuel == valuer`, un canal plat), et la chaîne `combine4` → `separate4`
→ `combine3` → `Color3f` reste type-cohérente de bout en bout. 123 tests
pytest toujours verts.

**Pas encore testé en rendu réel** - cette approche est elle-même un test
diagnostique pour confirmer que le problème est bien spécifique à
`ND_ramp_gradient`/`ND_separate4_color4`, pas une hypothèse déjà
confirmée. Si `ND_ramplr_float` rend correctement, la perte des clés
intermédiaires (compromis accepté) devient le point à réévaluer ensuite -
si le nombre de clés réel dépasse 2 dans des cas d'usage courants, une
piste alternative (bake en LUT image, déjà envisagée en "Prochaines
étapes possibles") resterait à explorer pour retrouver la fidélité perdue
sans dépendre de `ND_ramp_gradient`.

**Rendu après ce round (capture d'écran fournie par l'auteur)** : toujours
aucune couleur - la sphère principale rend maintenant en **noir uni**
(différent du blanc/chrome du Round 49, mais toujours pas la couleur
attendue). Piste non encore creusée à ce stade : `ND_ramplr_float`'s
défaut de sortie est `0.0` (donc noir si jamais évalué) - un échec total
tomberait sur ce défaut, cohérent avec le noir observé. `ND_ramp_gradient`
**et** `ND_ramplr` partagent le même `nodegroup="procedural2d"` dans le
stdlib MaterialX - possible indice que la limite de Karma concerne toute
cette famille de nœuds, pas spécifiquement `ND_ramp_gradient`. Pas encore
investigué plus loin à ce round - voir Round 51.

#### Round 51, `normalize`/`texcoord` mutualisés entre canaux (2026-08-12)

En inspectant le graphe réel importé dans Houdini (capture d'écran de
l'éditeur "Edit Material"), l'auteur repère une redondance : puisque
`red`/`green`/`blue`/`alpha` normalisent tous contre le **même**
`minPos`/`maxPos` combiné de `<color>` (Round 47), les 4 paires
`normalize`(`ND_remap_float`)/`texcoord`(`ND_combine2_vector2`) construites
une par canal (Round 50) étaient strictement identiques - Houdini les
affichait d'ailleurs comme un seul nœud partagé en pratique (la capture
montre un seul `normalize` alimentant les 4 chaînes `texcoord`/`ramp`) une
fois le graphe flatteni/dédupliqué à l'import.

Corrigé (`ShaderTree.py`) : nouvelle fonction `_USD_create_gradient_texcoord`
(construit le `normalize`+`texcoord` **une seule fois**, à l'échelle du
`NodeGraph` `_Gradient` entier, pas par canal) ; `_USD_create_gradient_ramp`
simplifiée pour ne plus prendre qu'un `texcoordOutput` déjà construit (au
lieu de le reconstruire lui-même) et ne bâtir que le nœud `ramp`
(`ND_ramplr_float`) propre à son canal. `_USD_create_gradient_channel_ramp`
(le wrapper par-canal du Round 47/50, devenu un simple relais une fois
`normalize`/`texcoord` extraits) supprimée - `_USD_create_gradient_output`
appelle directement `_USD_create_gradient_texcoord` une fois puis
`_USD_create_gradient_ramp` une fois par canal (`value`, ou
`red`/`green`/`blue`/`alpha`), toutes partageant la même sortie `texcoord`.
Comportement/valeurs strictement identiques - purement une déduplication
de nœuds, aucun calcul ne change.

**Vérifié structurellement contre `usd-core`** : reconstruit le graphe
avec 4 canaux à positions de clé différentes - confirmé qu'un seul prim
`normalize` et un seul prim `texcoord` existent sur tout le stage, et que
les 4 nœuds `ramp` (un par canal) sourcent tous leur `texcoord` depuis ce
même nœud partagé. 123 tests pytest toujours verts.

**Toujours pas de couleur dans le rendu réel** (point ouvert du Round 50,
inchangé par cette déduplication purement structurelle) - à investiguer
si `ND_ramplr_float` s'avère lui aussi ne pas s'évaluer dans Karma.

#### Round 52, `ND_ramplr_float` confirmé lui aussi inerte dans Karma + remplacé par `ND_hinvlinear_float`/`ND_huniformramp_float` (nœuds Houdini) — IMPLÉMENTÉ, PAS ENCORE TESTÉ (2026-08-12)

Retest du Round 51 dans Houdini par l'auteur : toujours un rendu noir uni,
confirmant l'hypothèse posée en fin de Round 50 - `ND_ramplr_float` (comme
`ND_ramp_gradient`) ne s'évalue pas dans Karma. Les deux nœuds partagent
le même `nodegroup="procedural2d"` du stdlib MaterialX - deuxième nœud de
cette famille à échouer, renforçant l'hypothèse que la limite touche toute
la catégorie `procedural2d`, pas un nœud isolé.

L'auteur a testé d'autres nœuds directement dans Houdini et trouvé une
paire qui fonctionne : **`ND_hinvlinear_float`** → **`ND_huniformramp_float`**
- des définitions MaterialX **propres à Houdini** (préfixe `h`), absentes
du paquet `MaterialX` standalone installé dans `.venv` - impossible de les
vérifier contre le vrai nodedef comme d'habitude dans ce fichier ;
implémenté strictement sur la base du câblage décrit par l'auteur (testé
par lui dans Houdini, pas une supposition) :

- `ND_hinvlinear_float` : `inputs:ramp` (la valeur pilote, normalisée
  [0,1]) → `inputs:num` (nombre de clés) → `inputs:key0..key9` (position
  de chaque clé, jusqu'à 10) → `outputs:out`.
- `ND_huniformramp_float` : `inputs:ramp` (connecté à la sortie de
  `hinvlinear`) → `inputs:num` → `inputs:value0..value9` (valeur de
  chaque clé) → `outputs:out`.

Contrairement à `ND_ramplr_float` (2 points seulement, positions des clés
ignorées - Round 50), cette paire consomme **toutes** les positions et
valeurs réelles (jusqu'à 10 clés) - la perte de fidélité du Round 50 est
donc annulée, sans avoir besoin d'une piste LUT/image.

Implémenté (`ShaderTree.py`) :
- `_USD_create_gradient_texcoord` renommée `_USD_create_gradient_normalize`
  et simplifiée : ne construit plus que le `ND_remap_float` partagé (Round
  51 inchangé sur ce point) - le `ND_combine2_vector2`/"texcoord" du Round
  50 est retiré, `hinvlinear.inputs:ramp` étant un simple `float`, pas un
  `vector2` comme `ramplr.inputs:texcoord`. Le garde `maxPos == minPos`
  (span dégénéré) déplacé dans `_USD_create_gradient_output` (calculé une
  fois, avant d'appeler `_USD_create_gradient_normalize` **et**
  `_USD_create_gradient_ramp` - les deux ont besoin de la même valeur
  gardée).
- `_USD_create_gradient_ramp` réécrite : lit les vraies clés du canal
  (`_USD_read_gradient_keys`, inchangée), les normalise en `[0,1]` contre
  `minPos`/`maxPos` (logique du Round 47, réintroduite - devenue inutile
  au Round 50 puisque `ramplr` n'utilisait que la première/dernière
  valeur, à nouveau nécessaire ici puisque chaque position compte),
  plafonne à 10 clés avec un diagnostic (`_DEBUG_diag("Unsupported",
  "Gradient_KeyCount", ...)`, même convention que les autres limites
  connues de ce fichier) si dépassé, puis construit la paire
  `hinvlinear`→`huniformramp` avec `key0..key9`/`value0..value9` posés en
  boucle.

**Vérifié structurellement contre `usd-core`** : reconstruit la chaîne
avec un canal à 3 clés (0/50/100, sur un span combiné 0-140) - confirmé
que les 3 positions **et** les 3 valeurs sont toutes présentes et
correctement normalisées (`key0=0`, `key1=0.357≈50/140`,
`key2=0.714≈100/140`, `value0=1`/`value1=0.5`/`value2=0`) - contrairement
au Round 50/51 qui n'aurait gardé que `key0`/`key2` (deux points, milieu
perdu). 123 tests pytest toujours verts (aucun ne couvre ce chemin,
dépendant de Modo pour l'étage 1).

**Pas encore testé dans Houdini** - ces deux nœuds `h*` n'ont jamais été
essayés par ce kit avant que l'auteur ne les découvre en session ; le
câblage suit exactement sa description mais reste à confirmer une fois
réexporté. Si ça fonctionne, ça referme le sujet ouvert depuis le Round
43 (limite de `ND_ramp_gradient` à un nombre de clés arbitraire) sans
avoir eu besoin de la piste LUT/image envisagée en repli.

#### Round 53, canal alpha retiré + `combine4`/`separate4` supprimés (2026-08-12)

L'auteur demande de simplifier : trop de choses changées à la fois ces
derniers rounds. Le canal alpha (Round 50 : ramp dédiée + `ND_combine4_color4`
+ `ND_separate4_color4`/`ND_combine3_color3` pour le ramener en `Color3f`,
seul target réel aujourd'hui) est retiré entièrement - inutile tant
qu'aucun effet ne consomme un `Color4f` (confirmé via `usdTypeMap`, déjà
noté sans conséquence au Round 50). Les sorties `red`/`green`/`blue`
(`ND_huniformramp_float`, Round 52) alimentent maintenant directement
`ND_combine3_color3` - plus de `combine4`/`separate4` intermédiaires.

Implémenté (`ShaderTree.py`, branche `else` de `_USD_create_gradient_output`) :
`alphaOutput`/`colorXml.find('alpha')` retirés ; `combine` redevient un
unique `ND_combine3_color3` avec `in1`/`in2`/`in3` connectés directement
aux 3 sorties `ND_huniformramp_float` ; le bloc `Color4f`/`separate4`/
`dropAlpha` du Round 50 supprimé entièrement (plus de branche
`targetType == Color4f` à gérer - `_USD_create_gradient_output` ne
produit plus que du `Float`/`Color3f`, les deux seuls cas réels).

**Vérifié structurellement contre `usd-core`** : reconstruit le graphe
complet (3 canaux, positions de clé différentes par canal) - confirmé
qu'aucun `ND_combine4_color4`/`ND_separate4_color4` n'apparaît nulle part
sur le stage, et que `combine` (`ND_combine3_color3`, un seul exemplaire)
est connecté directement aux 3 sorties `ramp`. 123 tests pytest toujours
verts.

**Pas encore testé dans Houdini** - même statut que le Round 52 (le
câblage `hinvlinear`/`huniformramp` lui-même reste à confirmer en rendu
réel ; ce round est une simplification structurelle qui ne change aucun
calcul par ailleurs).

#### Round 54, traduction USD/mtlx des Gradients abandonnée - retour à l'étage 1 seul (2026-08-12)

Retest du Round 53 dans Houdini : toujours un rendu noir uni. Trois
familles de nœuds mtlx essayées pour porter la rampe (`ND_ramp_gradient`
chaîné, Round 43 ; `ND_ramplr_float`, Round 50 ; `ND_hinvlinear_float`/
`ND_huniformramp_float`, Round 52), toutes structurellement correctes
(vérifiées à chaque fois contre `usd-core`) et toutes sans effet visible
dans Karma. L'auteur tranche : voie sans issue pour l'instant, ne pas
continuer à chercher un quatrième nœud - revenir à l'état d'avant le
Round 43, où les couches `Gradient` n'étaient extraites que dans le XML
normalisé (étage 1), sans aucune tentative de traduction USD/mtlx (étage
3).

Retiré de `ShaderTree.py` :
- La branche `elif elementName == "gradient":` dans `_USD_export_shadertree`
  (câblait `_USD_create_gradient_output` dans le graphe mtlx réel) -
  supprimée. Une couche `Gradient` dans le shader tree ne produit donc à
  nouveau **rien** côté USD - silencieusement ignorée par la boucle
  `for child in xml.findall('*')`, comme documenté avant le Round 43.
- Les 5 fonctions de construction USD des Rounds 43-53 : `_USD_create_gradient_driver`,
  `_USD_read_gradient_keys`, `_USD_create_gradient_normalize`,
  `_USD_create_gradient_ramp`, `_USD_create_gradient_output` - supprimées
  entièrement (pas laissées en code mort).

**Conservé intact** - tout l'étage 1 (extraction XML, Rounds 37-42) : `_UTIL_sample_gradient`,
`_UTIL_get_gradient_keys`, `_UTIL_get_slope_type_name`,
`_UTIL_gradient_keys_to_xml_dicts`, `_UTIL_set_key_pos_range`, le
traitement `iCHANTYPE_GRADIENT` dans `_UTIL_format_channel`/
`_UTIL_format_channel_value`, le suivi du graphe `sGRAPH_SHADELOC` pour
`sITYPE_GRADIENT` dans `_XML_export_item`, et le calcul `minPos`/`maxPos`
(par groupe et combiné) dans `_XML_get_channels` (Rounds 46/47). Une
couche `Gradient` continue donc à produire un XML normalisé fidèle -
vraies clés, positions, valeurs, type d'interpolation, `minPos`/`maxPos` -
exactement comme avant le chantier étage 3, cohérent avec le principe déjà
établi dans ce fichier que la fidélité d'extraction à l'étage 1 est une
valeur en soi, indépendante de ce qui est fait (ou pas) ensuite avec cette
donnée.

123 tests pytest toujours verts (aucun ne couvrait le chemin USD des
Rounds 43-53, tous dépendants de Modo/`fnpxr`).

**Point ouvert, pas résolu** : aucune des 3 familles de nœuds essayées ne
fonctionne dans Karma pour porter une rampe pilotée par une valeur
procédurale (`incidenceAngle`) - reste à déterminer si c'est spécifique à
la combinaison driver procédural + nœud de rampe, ou si Karma a un
problème plus large avec ces nœuds. Piste non essayée : la sortie d'une
rampe alimentée par une source **texture-based** (`UsdUVTexture`/coord
UV réelles) plutôt que procédurale - pourrait démêler si le problème vient
du nœud de rampe lui-même ou de sa combinaison avec `viewdirection`/
`normal`. Piste alternative déjà envisagée (bake en LUT image, voir
"Prochaines étapes possibles") reste la plus prometteuse si ce chantier
reprend un jour - elle contourne entièrement la question de savoir quel
nœud de rampe procédural Karma supporte, en s'appuyant sur `ND_image`
(déjà éprouvé extensivement dans ce kit) plutôt que sur un nœud de rampe
dédié.

#### Round 55, nettoyage général post-Round 54 : code mort et commentaires périmés retirés (2026-08-12)

Demande explicite de l'auteur après l'abandon du chantier Gradient étage 3 :
passe de nettoyage sur tout `ShaderTree.py` - commentaires à jour, code
mort retiré. Fait par comptage d'occurrences de chaque `def` top-level
dans le fichier (une seule occurrence = jamais appelée ailleurs que sa
propre définition = candidate morte), puis vérification au cas par cas.

Retiré :
- **`_UTIL_remove_chars`** - jamais appelée nulle part (ni dans ce
  fichier, ni ailleurs dans `Scripts/`) ; `_UTIL_clean_name` utilise
  `_UTIL_replace_chars` (remplacement par chaîne vide) pour le même
  effet depuis le début - `_UTIL_remove_chars` a toujours été redondante.
- **`xrange`/`long`** (bloc de compatibilité Python 2, tête de fichier) -
  jamais référencés ailleurs dans le fichier (`basestring`, dans le même
  bloc, reste utilisé à 2 endroits réels - conservé).
- Bloc de code mort en commentaire dans `_USD_create_texture_output`
  (choix d'`outType` selon le format de fichier texture - `PNG`/`TGA`/
  `EXR`) - jamais activé, `outType` est de toute façon déjà un vrai
  paramètre passé par l'appelant (documenté dans le docstring de la
  fonction) depuis longtemps.
- Docstring placeholder jamais rempli (`"""_summary_ ... _description_
  ..."""`) sur `_UTIL_clean_name` - un commentaire une-ligne juste
  au-dessus décrit déjà correctement la fonction.
- Deux commentaires devenus faux après le Round 54 dans `_XML_get_channels`
  (calcul de `minPos`/`maxPos`) : mentionnaient encore "lets stage 3
  normalize into ND_ramp_gradient's [0,1] domain" / "stage 3 normalizes
  every group against this SAME shared span" - l'étage 3 gradient
  n'existe plus, ces phrases décrivaient une consommation qui a disparu.
  Recoupés pour ne garder que le "quoi" (toujours vrai : ces attributs
  sont posés pour la fidélité de l'extraction), plus le pointeur vers le
  round CLAUDE.md concerné.

**Vérifié** : aucun autre `def` top-level du fichier n'a une seule
occurrence (hormis `export_basic_execute`, le point d'entrée public
appelé depuis `ExportShaderTree.py`, hors de ce fichier - confirmé par
grep). 123 tests pytest toujours verts, fichier toujours syntaxiquement
valide (`ast.parse`).

**Pas touché délibérément** : les docstrings Google-style verbeux mais
**exacts** de plusieurs fonctions plus anciennes (`_JSON_export_item`,
`_USD_export_shadertree`, `_USD_add_shader_connector_to_context`...) -
verbeux au regard de la convention "une ligne, le quoi" adoptée plus tard
dans le fichier (Round 16), mais pas faux/périmés comme les deux
commentaires ci-dessus - une réécriture systématique de style n'a pas été
demandée et aurait été un diff large à faible valeur ajoutée par rapport
au risque d'en altérer le sens par erreur.

#### Round 56, `displace` + `vectorDisplace` combinés sur le même matériau (au lieu du dernier qui écrase le premier) — CONFIRMÉ DANS HOUDINI (2026-08-13)

Retest du Round 36 par l'auteur : `displace` seul fonctionne, `vectorDisplace`
seul fonctionne, mais **les deux combinés sur le même matériau** produisent un
résultat faux - un seul des deux effets semble avoir de l'effet, alors que les
deux couches existent bien côté Modo.

Cause : les branches `"displace"` et `"vectorDisplace"` de
`_USD_connect_texture_output_to_shader_input` appellent chacune,
indépendamment :

```python
material.CreateOutput("mtlx:displacement", Sdf.ValueTypeNames.Token).ConnectToSource(output)
```

`material.outputs:mtlx:displacement` est un unique attribut sur le prim
matériau - `CreateOutput` avec le même nom retourne le même attribut, donc le
second effet traité dans la boucle (`_USD_connect_effect_stack`, l'ordre
d'itération d'`OrderedDict`) reconnecte silencieusement cet attribut,
écrasant la connexion faite par le premier. Aucun crash, aucun diagnostic -
un des deux nœuds `ND_displacement_*` reste construit dans le graphe mais
n'est plus jamais réellement branché sur la sortie du matériau.

Vérifié contre le vrai stdlib MaterialX standalone (`.venv`) : aucun
`add_displacementshader` n'existe. Le seul combinateur pour deux sorties de
type `displacementshader` est `ND_mix_displacementshader(fg, bg, mix) ->
displacementshader` - un blend, pas une somme. L'auteur confirme que
`mix=0.5` est une approximation raisonnable de ce que fait Modo dans ce cas
("more like a normalized add operation") - accepté comme solution
intérimaire plutôt que de deviner/reproduire l'addition vectorielle réelle
de Modo (qui demanderait de convertir la hauteur scalaire de `displace` en
vecteur via la normale avant de sommer avec `vectorDisplace`, non vérifié).

Implémenté (`ShaderTree.py`) :
- Nouveau `ShadingContext.displacementOutputs` (dict, `effectName ->
  UsdShade.Output` de type `displacementshader`) - reset à chaque mask,
  aux côtés de `effectsStack`/`previewOutputs`.
- Les branches `"displace"`/`"vectorDisplace"` ne connectent plus
  `material.outputs:mtlx:displacement` elles-mêmes - elles stockent
  seulement leur sortie dans `context.displacementOutputs[effectName]`.
- Nouvelle fonction `_USD_connect_displacement_outputs(stage, context)`,
  appelée une fois après la boucle complète sur `context.effectsStack` dans
  `_USD_connect_effect_stack` (donc après que `displace` et
  `vectorDisplace` aient tous les deux eu l'occasion de s'enregistrer) :
  si un seul effet de déplacement est présent, connecte directement sa
  sortie (comportement identique à avant pour ce cas, déjà confirmé
  fonctionner côté `displace` comme côté `vectorDisplace` séparément) ; si
  les deux sont présents, les combine via un nœud `ND_mix_displacementshader`
  (`mix=0.5`) avant de connecter sa sortie unique.

**Vérifié structurellement contre `usd-core`** : reconstruit le graphe à
deux sorties de déplacement - confirmé que `material.outputs:mtlx:displacement`
pointe vers le nœud `Displacement_mix`, dont `fg`/`bg` pointent chacun vers
un des deux nœuds `ND_displacement_*` d'origine (tous les deux restent
construits et réellement consommés, contrairement à avant). Le cas à un
seul effet de déplacement (le seul déjà confirmé en rendu réel jusqu'ici)
n'est pas affecté structurellement - `combined = outputs[0]` sans passer
par le nœud de mix, connexion identique à avant. 123 tests pytest toujours
verts.

**Confirmé par l'auteur dans Houdini** : les deux effets de déplacement,
combinés sur un même matériau, sont maintenant tous les deux visibles dans
le rendu ("this works perfectly") - clôt le point ouvert du Round 36 sur
la combinaison `displace`/`vectorDisplace`.

#### Round 57, `alpha="only"` (stencil sur alpha PNG) cassé par un bug de remap qui écrasait le canal alpha à une constante — CONFIRMÉ DANS HOUDINI (2026-08-13)

Suite du Round 28 : l'auteur teste un stencil avec image N&B (pas de mode
alpha spécifique) - fonctionne parfaitement. Le même stencil avec un PNG à
alpha et `alpha="only"` spécifié - **ne fonctionne pas** (comparaison
rendu Modo vs Karma fournie par l'auteur).

Cause trouvée en traçant le type `Color4f` à travers
`_USD_create_texture_adjust_nodegraph` (`ShaderTree.py`) : quand
`alphaMode == "only"` (ou `swizzling`), la texture est lue en `Color4f`
(`readType`, Round 33) et passe par la chaîne remap/contrast/brightness
**avant** l'extraction du canal (`ND_separate4_color4`). `_UTIL_float_to_out_type`
complétait systématiquement le 4ᵉ composant (alpha) à `1.0`, y compris pour
`outLow` du nœud `ND_remap_color4` :

```python
elif outType == Sdf.ValueTypeNames.Color4f:
    return f"({value}, {value}, {value}, 1.0)"
```

`outLow`/`outHigh` du remap avaient donc tous les deux leur composant alpha
à `1.0`. Vérifié contre le vrai nodedef standalone (`.venv`) :
`ND_remap_color4` a pour défauts réels `outlow=(0,0,0,0)`/`outhigh=(1,1,1,1)`
- une identité sur les 4 canaux. Avec `outlow_alpha == outhigh_alpha == 1.0`,
la sortie du remap pour le canal alpha devient **constante à 1.0**, quelle
que soit la valeur d'entrée - le vrai alpha du PNG est donc entièrement
écrasé avant même d'atteindre `ND_separate4_color4`. `alpha="only"`
extrayait donc toujours `1.0` (opaque uniforme), jamais le vrai alpha par
pixel - cohérent avec le symptôme observé (le stencil n'a plus aucun
découpage, comme si l'effet n'existait pas).

`brightness`/`contrast` (les deux autres consommateurs de
`_UTIL_float_to_out_type` en `Color4f`) n'ont pas ce problème - vérifié
contre `ND_multiply_color4`/`ND_contrast_color4` : leurs défauts réels ont
aussi `1.0` en 4ᵉ composant (`in2`/`amount`), donc le comportement actuel y
est correct (no-op sur alpha), pas une coïncidence à corriger.

Corrigé : `_UTIL_float_to_out_type` prend maintenant un paramètre
`alpha` (défaut `1.0`, inchangé pour `brightness`/`contrast`/`outHigh`) ;
le seul appel pour `outLow` (`ShaderTree.py`, `_USD_create_texture_adjust_nodegraph`)
passe maintenant `alpha=0.0` - reproduit exactement le défaut réel
`ND_remap_color4.outlow=(0,0,0,0)`, donc le canal alpha traverse le remap
inchangé (identité), quelles que soient les valeurs `min`/`max` réglées par
l'utilisateur pour RGB.

**Vérifié** : `eval(_UTIL_float_to_out_type(0.0, Color4f, alpha=0.0))` →
`(0.0, 0.0, 0.0, 0.0)`, `eval(_UTIL_float_to_out_type(1.0, Color4f))` →
`(1.0, 1.0, 1.0, 1.0)` - correspond exactement aux défauts réels de
`ND_remap_color4`. 123 tests pytest toujours verts (aucun ne couvre ce
chemin, dépendant de Modo/`fnpxr`).

**Confirmé par l'auteur dans Houdini** : le stencil piloté par l'alpha d'un
PNG (`alpha="only"`) découpe maintenant correctement, avec la vraie forme
de l'alpha ("Works perfectly"). Le même bug affectait aussi `swizzling`
avec `rgba="alpha"` (pas testé séparément par l'auteur ce round, mais
partage la même cause - probablement corrigé aussi, à confirmer si un cas
réel l'exerce).

#### Round 58, stencil : `invert`/`round`/`convert` regroupés dans un `NodeGraph` "_stencil" — CONFIRMÉ DANS HOUDINI (2026-08-13)

Demande de l'auteur, une fois le Round 57 confirmé : les trois nœuds mtlx de
la branche stencil (`invert`/`round`/`convert`) encombrent le graphe en
prims frères sous le matériau - les regrouper dans un `NodeGraph` nommé
`<nom_de_la_couche>_stencil`, même logique de rangement que `UV_Transform`
(Round 12) et `_adjust` (déjà en place pour le post-traitement de texture).

Implémenté (`ShaderTree.py`, branche `stencil` de
`_USD_connect_texture_output_to_shader_input`) : nouveau prim `NodeGraph`
`<name>_stencil`, avec une interface input `"in"` (Float) connectée à
`output` (la valeur accumulée en entrée de la branche stencil) ; les trois
nœuds internes (`invert`/`round`/`convert`, renommés depuis leurs anciens
noms de prims frères `_invert_color`/`_set_0_or_1`/`_opacity_color`)
lisent `nodeGraph.GetInput("in")` au lieu de `output` directement ; la
sortie du dernier nœud (`convert`, `Color3f`) est exposée comme
`nodeGraph.outputs:out`, et c'est cette sortie du `NodeGraph` que le
câblage générique juste après (inchangé) connecte à
`shader.inputs:opacity` - direction `NodeGraph`-sortie vers `Shader`-entrée,
le patron déjà éprouvé partout ailleurs dans ce fichier (`UV_Transform`,
`_adjust`).

**Vérifié structurellement contre `usd-core`** : les trois nœuds
apparaissent bien imbriqués sous le `NodeGraph`, `invert.inputs:in` pointe
vers l'interface input `"in"` du `NodeGraph` (pas directement vers la
source externe), et `standard_surface.inputs:opacity` pointe vers
`<name>_stencil.outputs:out`. 123 tests pytest toujours verts.

**Point de vigilance, pas vérifié** : l'interface input `"in"` du
`NodeGraph` est elle-même alimentée par `output` (la valeur accumulée
avant la branche stencil) - dans le cas courant (un opérateur de blend a
été construit, `_USD_connect_operator`), c'est la sortie d'un `Shader`
ordinaire, direction déjà sûre. Mais si aucune valeur de fallback n'existe
pour cet effet (`input is None`, retour anticipé du Round 30),
`output` peut être directement la sortie d'un **autre** `NodeGraph`
(`_adjust`, Round 33) - exactement la configuration qui a cassé
silencieusement dans Houdini aux Rounds 48/49 (deux `NodeGraph` de haut
niveau qui se référencent l'un l'autre), même si structurellement valide
contre `usd-core` à chaque fois. À surveiller si la connexion `"in"` du
`NodeGraph` "_stencil" semble absente dans l'éditeur de graphe de matériau
de Houdini malgré sa présence dans le `.usda`.

**Confirmé par l'auteur dans Houdini** : le stencil rend toujours
correctement après ce regroupement ("Perfect") - y compris le point de
vigilance ci-dessus (interface input `"in"` du `NodeGraph` "_stencil"),
qui ne s'est pas matérialisé en pratique pour ce cas de test.

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

0. ~~**PRIORITAIRE** : isoler la dernière branche encore ouverte du
   Round 59~~ — **CLOS le 2026-08-13** : deux bugs réels corrigés
   (`_MAX_DERIVED_IOR`, `_MIN_IOR`). `useRefIdx=1`/`specRefIdx=1` garde un
   écart de forme de courbe (pas une valeur invalide) que l'auteur a
   choisi d'accepter comme limite connue plutôt que de poursuivre la
   calibration - documenté dans le README. Les Rounds 28-42 sont tous
   confirmés depuis le retest du 2026-08-13 ; les couches `Gradient`
   restent confirmées à l'étage 1 (XML) seulement - voir item 7
   ci-dessous pour l'étage 3, abandonné au Round 54.

Plus de priorité ouverte à ce stade. Le reste, aucune urgence, à discuter
avec l'auteur :

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
6. **Colorspace des couches bump/normal** (laissé de côté au Round 22,
   compromis temporaire explicite) : forcer `raw`/l'équivalent mtlx
   (`OCIO_DATA_COLORSPACE_BY_CONFIG`-style ou plus simple, à revoir) pour
   ces couches, côté mtlx **et** glPreview à la fois - idéalement dans
   `normalize/colorspace.py` (qui a déjà accès à `usdInputName`/
   `usdPreviewInputName` via `normalize_effect_channel_names`, exécutée
   avant elle) plutôt que dupliqué dans `ShaderTree.py`.
7. **Traduction USD/mtlx des couches `Gradient`** - l'étage 1 (extraction
   XML des vraies clés/valeurs/type d'interpolation/`minPos`/`maxPos`,
   Rounds 37-42) reste en place et fonctionne. L'étage 3 (construction
   USD/mtlx, Rounds 43-53) a été **tenté puis abandonné au Round 54** :
   trois familles de nœuds de rampe essayées (`ND_ramp_gradient` chaîné,
   `ND_ramplr_float`, `ND_hinvlinear_float`/`ND_huniformramp_float` -
   ces deux derniers propres à Houdini) se sont toutes révélées
   structurellement correctes (vérifiées contre `usd-core` à chaque fois)
   mais sans effet visible dans un rendu Karma réel. Piste la plus
   prometteuse pour une reprise future : "baker" chaque gradient en une
   petite texture LUT 1D à l'export (échantillonner via les vraies clés,
   pas `Generate(t)`) et la lire via `ND_image` (déjà éprouvé
   extensivement dans ce kit) plutôt que de dépendre d'un nœud de rampe
   procédural dont le support dans Karma reste incertain. Reste aussi à
   mapper `param` (l'Input Parameter Modo, ex. `"distanceX"`) au-delà du
   seul `"incidenceAngle"` déjà traité - liste complète des valeurs
   possibles pas encore connue. Scripts de diagnostic Modo utilisés pour
   cette investigation dans `explore_tools/` (gitignoré, hors `.lpk`) -
   utile comme référence si `slopeType`/`weighted` ou `param` ont besoin
   d'être creusés davantage.

Ne pas réintroduire de logique de cas particulier dans la construction USD —
c'est précisément ce que cette refonte cherchait à éviter.
