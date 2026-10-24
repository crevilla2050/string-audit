# Dennis text extraction plugins

Dennis includes small, read-only extractors that produce deterministic UTF-8 JSON for downstream workflows. Extraction does not modify the source file, create dictionary tokens, or apply translations. Dictionary and token assignment remain with the existing i18n workflow.

## HTML

```bash
dennis-extract-html index.html --out html-strings.json
```

The HTML extractor supports `.html` and `.htm`. It extracts visible text nodes and the approved user-facing attributes `alt`, `title`, `placeholder`, `aria-label`, `aria-description`, and `aria-placeholder`. `value` is included only for `input` elements of type `submit` or `button`.

It ignores comments, `script` and `style` contents, `style` attribute contents, event handlers, identifiers, URLs, and other non-user-facing attributes. HTML character references are decoded in `text` for dictionary matching; `raw` and `start`/`end` preserve the exact source span. Offsets are zero-based Python string-character offsets; `line` and `column` are one-based. Ambiguous incomplete markup is skipped conservatively.

Each JSON array entry represents one occurrence, so duplicate text at different locations remains distinguishable.

## Microsoft Word and LibreOffice Writer

```bash
dennis-extract-document contract.docx --out contract-strings.json
dennis-extract-document document.odt --out document-strings.json
```

The document extractor supports `.docx` and `.odt`. It emits paragraph-level strings, joining text split across formatting runs. DOCX extraction covers the main document, tables, headers, and footers. ODT extraction covers paragraphs, headings, tables, and header/footer content represented in the package's `content.xml` and `styles.xml`.

Document `start`/`end` offsets refer to the logical extracted paragraph text, not byte offsets in the ZIP/XML package. `part`, `paragraph_index`, and `text_nodes` retain structural context for downstream tools. This is an extraction interface, not a round-trip document editor; unsupported structures are not rewritten.

## JSON and determinism

Both tools write UTF-8 JSON with stable indentation, a trailing newline, and deterministic source traversal. The HTML output records source spans directly. The document output records structural locations and logical paragraph spans. The two formats intentionally share the core `text`, `file`, `start`, and `end` concepts while retaining format-specific provenance fields.
