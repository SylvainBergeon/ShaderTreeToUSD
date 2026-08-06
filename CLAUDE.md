# Contexte projet — ShaderTreeToUSD

Ce fichier résume les décisions prises lors d'une session de conception (hors
Claude Code, sur claude.ai) portant sur la refonte de la complexité du plugin.
Il sert de point de reprise : lis-le avant de proposer des changements pour
rester cohérent avec la direction déjà validée par l'auteur du projet.

## Le projet

Kit Modo qui exporte un shader tree Modo vers USD/MaterialX, pour être
réimporté dans Houdini (Karma). Point d'entrée : `Scripts/lxserv/ExportShaderTree.py`
(commande Modo `exportShaderTree`), qui délègue à
`Scripts/python_modules/ShaderTree.py` (~1820 lignes, le cœur du système)
et `Scripts/python_modules/ShaderFilters.py` (tables de correspondance
Modo <-> USD).

`fnpxr` = nom donné par Foundry à sa copie interne des bindings Python de
Pixar USD (`pxr`). Fonctionnellement identique à `pxr` standard.

## Environnement de dev (déjà en place, ne pas reconfigurer)

- Le repo est un kit Modo chargeable directement depuis ce dossier (présence
  d'`index.cfg` à la racine) : pas besoin de packager en `.lpk` pour
  développer, `build_lpk.py` sert uniquement à la distribution.
- `ExportShaderTree.py` appelle `reload_modules()` à chaque exécution de la
  commande dans Modo -> `ShaderTree.py` et `ShaderFilters.py` sont rechargés
  à chaud depuis le disque. Seul `ExportShaderTree.py` lui-même nécessite un
  restart de Modo si modifié.
- `.vscode/settings.json` configure déjà l'analyse statique (stubs `lx`/`modo`,
  `extraPaths` vers le Python de Modo, résolution `pxr`). Ça ne permet pas
  d'exécuter le code, juste de l'éditer avec autocomplétion.
- `.venv/` existe dans le repo mais ne contient que pip/setuptools pour
  l'instant — rien d'installé pour exécuter réellement `lx`/`modo`/`fnpxr`.

## Le problème identifié

Le point de douleur signalé par l'auteur : **le traitement des cas
particuliers est trop complexe**, en particulier dans `ShaderTree.py`.
`USD_export_shadertree()` (fonction principale, parcours récursif de l'arbre)
mélange trois responsabilités dans la même passe :

1. parcours de l'arbre (dispatch par tag XML)
2. interprétation métier (quel BRDF, quel type de blend, conversions
   physiques specular/IOR, résolution des noms d'effet...)
3. appels effectifs à l'API USD (`UsdShade`, `Sdf`)

Ce mélange rend les règles de cas particuliers difficiles à isoler, tester,
ou faire évoluer sans risquer de casser autre chose.

## Étape 1 déjà faite : refactor local de deux fonctions

Deux fonctions particulièrement denses en cas particuliers ont été
refactorisées (comportement identique, structure clarifiée) :

- `USD_apply_overrides` — conversions specular/IOR selon le BRDF
  (`gtr` / `principled`). Dupliquait 2 formules avec juste une constante
  différente (`_ior_from_spec_amt`, `_saturating_curve` extraites), et
  contenait une ligne morte (valeur assignée puis toujours écrasée juste
  après). Correction mineure documentée : protection division par zéro sur
  diffuse noir pur (`_tinted_spec_color`), qui plantait avant.
- `USD_connect_operator` — connexion des opérateurs de blend. Pattern
  "connecter si `UsdShade.Output`, sinon `eval()` + `Set()`" dupliqué 3 fois
  -> extrait dans `_set_or_connect()`. Les deux chemins (Multiply/Divide vs
  autres blends) partagent maintenant la création du premier nœud au lieu
  d'être entièrement dupliqués en parallèle.

**Statut : ces deux fonctions refactorisées existent dans un fichier à part
(`ShaderTree_refactored_sections.py`, remis à l'auteur), PAS ENCORE fusionnées
dans `Scripts/python_modules/ShaderTree.py`.** Si ce n'est pas déjà fait,
c'est une première tâche possible : les intégrer en remplaçant les fonctions
d'origine, sans changer le comportement.

## Étape 2 (direction validée, pas encore codée) : pipeline en 3 étages

L'auteur a validé l'approche générale suivante. Objectif : sortir toute la
logique de cas particuliers de la construction USD elle-même, vers une étape
de normalisation intermédiaire testable indépendamment.

```
Modo (item tree)  -->  XML brut          -->  XML canonique       -->  Stage USD
  XML_export_item()      (existe déjà)         (À CRÉER)               (à simplifier)
```

- **Étage 1 — extraction** (`XML_export_item`, existe déjà) : miroir fidèle
  de la hiérarchie Modo, vocabulaire Modo brut (noms de canaux, `brdfType`,
  `useRefIdx`...). Ne pas toucher pour l'instant.

- **Étage 2 — normalisation (nouveau)** : une série de *passes* pures,
  `Element -> Element`, chacune responsable d'un seul cas particulier,
  appliquées en séquence sur l'arbre XML brut. Résultat : un XML "déjà pensé
  USD" mais qui reste de la donnée (pas encore d'appels `UsdShade`).
  Exemple de squelette validé :

  ```python
  def normalize_specular_ior(xml: ET.Element) -> ET.Element:
      """Réécrit specAmt/refIndex/specCol en valeurs USD-ready selon brdfType.
      Pure transformation XML -> XML, aucune dépendance à pxr/USD."""
      ...

  NORMALIZATION_PASSES = [
      normalize_specular_ior,
      normalize_blend_operators,
      normalize_projection_defaults,   # fallback uv/triplanar
      normalize_effect_channel_names,  # résolution effect -> nom canal USD
  ]

  def normalize(xml: ET.Element) -> ET.Element:
      for pass_fn in NORMALIZATION_PASSES:
          xml = pass_fn(xml)
      return xml
  ```

  Les deux fonctions déjà refactorisées (`_gtr_override`, `_principled_override`,
  la logique de `USD_connect_operator`) sont les candidates naturelles pour
  devenir `normalize_specular_ior` et `normalize_blend_operators` : au lieu de
  retourner une valeur unique à la volée pendant la construction USD, elles
  réécrivent directement les attributs `value=` dans le XML.

- **Étage 3 — construction USD (à simplifier une fois l'étage 2 en place)** :
  un walker générique piloté par une table de dispatch (`tag -> builder`) qui
  ne fait plus que traduire mécaniquement le XML canonique en appels
  `CreateInput`/`ConnectToSource`/`CreateOutput`. Plus de règle métier à cet
  étage — tout a été résolu en amont par l'étage 2.

### Décisions encore ouvertes (à trancher avant/pendant l'implémentation)

1. **Vocabulaire canonique** : garder les noms de balises Modo actuels
   (`advancedMaterial`, `imageMap`...) en sortie de normalisation, ou les
   renommer vers un vocabulaire neutre découplé de Modo ? Direction
   recommandée (pas encore validée formellement) : garder les noms Modo,
   normaliser seulement les *valeurs* — migration plus sûre, moins de code à
   toucher.
2. **Où vivent les tables de `ShaderFilters.py`** (`usdInputMap`, `usdTypeMap`,
   `channelTypeMap`, `stdMatChannelMap`) : elles devraient migrer vers
   l'étage normalisation plutôt que d'être consultées à l'étage construction.
3. **Migration progressive** : une passe à la fois (specular d'abord, puis
   blend, puis projection/effect), en laissant `USD_export_shadertree`
   inchangé tant que toutes les passes concernées n'existent pas.

## Exécution/tests hors Modo (validé, pas encore mis en place)

- **Étage 2 (normalisation XML)** : zéro dépendance à `lx`/`modo`/`fnpxr`.
  Exécutable et testable nativement dans le `.venv` du repo (`pytest` +
  fixtures `ElementTree` construites à la main), sans jamais ouvrir Modo.
  C'est la priorité pour donner une vraie couverture de tests aux cas
  particuliers.
- **Étage 3 (construction USD)** : possible de tester hors Modo en
  installant `usd-core` (paquet PyPI, l'API `pxr` officielle open source)
  dans `.venv`, puis en créant un shim `fnpxr/__init__.py` qui fait
  `from pxr import *`. Permet de générer un vrai `Usd.Stage`, écrire un
  `.usda` sur disque, l'inspecter avec `usdview` — sans Modo.
- **Étage 1 (extraction Modo)** reste dépendant de l'interpréteur embarqué de
  Modo. Pour du debug interactif dessus : `debugpy.listen()` dans le script
  côté Modo + "Python Debugger: Remote Attach" côté VS Code (nécessite que
  `debugpy` soit importable depuis le Python de Modo).

## Prochaines étapes suggérées (à valider avec l'auteur avant de foncer)

1. Fusionner les deux fonctions déjà refactorisées dans `ShaderTree.py` (si
   pas déjà fait).
2. Créer le module d'étage 2 (ex. `Scripts/python_modules/normalize/`),
   migrer `_gtr_override`/`_principled_override` en `normalize_specular_ior`,
   et `USD_connect_operator` en `normalize_blend_operators`.
3. Mettre en place `pytest` + premières fixtures XML pour ces deux passes.
4. Seulement après : attaquer `normalize_projection_defaults` et
   `normalize_effect_channel_names`, puis simplifier `USD_export_shadertree`
   pour qu'il devienne un simple walker générique (étage 3).

Ne pas réintroduire de logique de cas particulier dans l'étage 3 — c'est
précisément ce que cette refonte cherche à éviter.
