# Publicar una versión

Lista de lo que hay que actualizar al lanzar una versión de evo8-linux. El
tag `vX.Y.Z` dispara todo lo automático: PyPI y la release de GitHub.

## 0. Una sola vez (ya hecho)

- PyPI: *trusted publisher* del proyecto `evo8-linux` → repo
  `wh01s17/evo8-linux`, workflow `release.yml`, entorno `pypi`
  (https://pypi.org/manage/project/evo8-linux/settings/publishing/).
- GitHub: el entorno `pypi` se crea solo en la primera ejecución. Si quieres
  aprobar cada publicación a mano, agrega una regla en
  *Settings → Environments → pypi*.

## 1. Elegir el número

[SemVer](https://semver.org/lang/es/). Mientras estemos en `0.x`:

| Cambio | Ejemplo | Sube |
|---|---|---|
| Solo arreglos | un fader que no responde | parche: `0.1.0 → 0.1.1` |
| Funciones nuevas o cambios que rompen algo (comandos de `evoctl`, formato de `state.json`, rutas instaladas) | nueva pestaña, `evoctl` renombra un comando | menor: `0.1.1 → 0.2.0` |

Una versión publicada en PyPI **no se puede reemplazar** ni volver a subir.

## 2. Antes del tag

1. `main` al día y el CI del último commit en verde
   (https://github.com/wh01s17/evo8-linux/actions).
2. Probar en tu equipo: `make test`, abrir la ventana y recorrer las tres
   pestañas. Si cambió algo del USB, probarlo con la EVO siguiendo las reglas
   de seguridad de `plan.md` (§6). **Nunca durante una llamada.**
3. **`CHANGELOG.md`**:
   - Pasa lo que está en `## [Sin publicar]` a una sección nueva
     `## [X.Y.Z] - AAAA-MM-DD`, y deja `## [Sin publicar]` vacía arriba.
   - Escribe para quien usa la app: qué puede hacer ahora o qué se arregló,
     no los nombres de los commits.
   - Al pie, actualiza los enlaces:
     `[Sin publicar]: …/compare/vX.Y.Z...HEAD` y agrega
     `[X.Y.Z]: …/releases/tag/vX.Y.Z`.
   - El workflow se detiene si falta esta sección, y la usa como texto de la
     release de GitHub.
4. **Versión**: `src/evo8/__init__.py` → `__version__ = "X.Y.Z"`. Es el
   único lugar (`pyproject.toml`, `evoctl --version` y ACERCA DE la leen de
   ahí). Un test falla si `CHANGELOG.md` no tiene la sección de esa versión.
5. Revisa si cambió alguna de estas cosas y actualiza **todos** los lugares:

   | Si cambió… | Actualiza |
   |---|---|
   | Dependencias del sistema | `packaging/arch/PKGBUILD` (`depends`), `.github/workflows/ci.yml` (`pacman` y `apt-get`), README (requisitos), `src/evo8/user_setup.py` (`TOOLS`) |
   | Dependencias de Python | `pyproject.toml` (`optional-dependencies`), PKGBUILD |
   | Archivos en `src/evo8/data/` | `pyproject.toml` (`package-data`), PKGBUILD (`package()`), `Makefile` (`install`/`uninstall`), `user_setup.plan()`, comprobaciones de los dos CI |
   | Firmware probado | `src/evo8/about.py` (`TESTED_FIRMWARE`), README |
   | Funciones visibles | README (*Qué hace*, *Uso*), `plan.md` §4 |

6. Commit `chore(release): vX.Y.Z` (con `/commit:commit`, que hace el push) y
   espera el CI en verde.

## 3. El tag

```sh
git tag -a vX.Y.Z -m "evo8-linux X.Y.Z"
git push origin vX.Y.Z
```

`.github/workflows/release.yml` entonces:

1. Comprueba que el tag coincide con `__version__` y que `CHANGELOG.md` tiene
   la sección.
2. Compila sdist y wheel (`twine check`).
3. Publica en PyPI (trusted publishing, con atestaciones).
4. Crea la release de GitHub con las notas del changelog y los archivos.

## 4. Después

- [ ] https://pypi.org/project/evo8-linux/ muestra X.Y.Z, con el README bien.
- [ ] https://github.com/wh01s17/evo8-linux/releases tiene la release con
      sus notas y los dos archivos.
- [ ] Instalación limpia:
      `pipx install --force "evo8-linux[gui,usb]==X.Y.Z"`, luego
      `evoctl --version` y `evoctl setup --dry-run`.
- [ ] ACERCA DE muestra la versión nueva.
- [ ] **AUR** (si el paquete está publicado ahí): `evo8-linux-git` toma la
      versión de git solo; sube `pkgrel` solo si cambió el PKGBUILD, regenera
      `.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`) y haz push al repo del
      AUR.
- [ ] `plan.md` §4 al día.

## 5. Si algo sale mal

| Qué falló | Qué hacer |
|---|---|
| El workflow falla **antes** de publicar en PyPI (tag ≠ versión, falta el changelog, build) | Corrige en `main`, borra el tag y vuelve a crearlo: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z` |
| Se publicó en PyPI con un error | No se puede reemplazar. Marca la versión como *yanked* en PyPI (Manage → Releases) y publica `X.Y.Z+1` |
| Solo falló la release de GitHub | Reintenta el job desde Actions, o: `python tools/release_notes.py vX.Y.Z > notas.md && gh release create vX.Y.Z --notes-file notas.md --verify-tag` |
