# Dennis Development Notes

## Plugin Resolution and File Identity

### 1. Plugin precedence

Dennis supports built-in plugins and user-installed plugins located in
`~/.dennis/plugins/`.

Default behavior:
- User-installed plugins take precedence over built-in plugins for each
  file extension they support.
- If no user plugin claims an extension, Dennis falls back to a compatible
  built-in plugin when one exists.
- Installing a plugin for one extension must not disable built-in handling
  for unrelated extensions.

Explicit default mode:
- `dennis plan --use-default-plugins` prefers compatible built-in plugins
  over user-installed plugins for extensions handled by a built-in.
- User-installed plugins remain available for extensions without a
  compatible built-in plugin.

Conflict handling:
- If multiple user-installed plugins claim the same extension, Dennis must
  stop before scanning and report the extension and conflicting plugin names.
- Dennis must not guess based on filesystem discovery order.
- Conflict detection must be deterministic and must not produce partial
  scan results.

### 2. File identity and validation

- File extensions are routing hints, not proof of file format.
- Plugins must declare their supported extensions and MIME types.
- Format detection must examine file contents; it must not rely solely on
  the filename or an operating-system MIME guess.
- MIME detection is evidence, not definitive proof. Format-specific
  structural validation is required where appropriate.
- Container signatures alone are insufficient when multiple formats share
  the same container, such as DOCX and ODT ZIP packages.
- A clear mismatch or malformed input must not be silently processed as
  the requested format.
- Document extraction must use defensive parsing and reasonable limits
  on file size, archive entries, aggregate decompressed size, and
  decompression ratios.

### 3. Compatibility and determinism

- The plugin-resolution policy applies to scanning plugins.
- Existing transformation-plugin behavior and `--lang` semantics must
  remain unchanged.
- Plugin selection must be deterministic.
- The `--use-default-plugins` option must be propagated through the CLI,
  plan generation, and every relevant scanner call.
- Changes must preserve unrelated working-tree modifications and files.
- Regression tests must cover precedence, fallback, extension overlap,
  conflicts, format mismatches, and malformed inputs.

### 4. Implementation principle

Built-in plugins are defaults, not mandates. User-installed plugins allow
organizations to support proprietary formats and specialized conventions
without modifying Dennis core.

Do not silently choose between conflicting user plugins. Fail clearly and
let the user resolve the ambiguity.
