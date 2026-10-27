# Explore integration contract

Keep the existing local theme browser. Add an **Explore** entry point to an online catalog screen. The local theme list must remain usable offline. Do not fetch full packages when opening the local library.

## Three separate actions

1. **Browse / Preview:** read catalog data and small preview media. No theme-preference writes. No Custom snapshot, replacement or application.
2. **Download:** fetch a selected ZIP to temporary storage, verify size/digest, validate the package, and store a new named local entry under an allocated local ID. Record `(catalog ID, entry ID, revision)` separately. Do not change the active theme, Custom manifest, live preference values, or keyboard geometry.
3. **Apply:** explicitly selected by the user after download. Only this action activates the installed theme. Normal existing local editing/save behavior can remain as it is.

For downloaded updates, retain the installed copy until the new package validates completely. Keep local customizations as their own library entries; do not silently overwrite edited themes. Distinct catalog document IDs avoid the reserved `custom` ID and named built-in IDs. Removing a download removes that installed package, not the catalog listing. If it is active, ask the user to choose a replacement before removal.

## Current app behavior to account for

At Keywi main commit `232070cbde42c9e7c893874bc50e2145140609b9`, `ThemeEngine.importPackage()` validates/extracts into staging and then stores into Custom and calls `apply()`. **Explore must not invoke that method for Download.** Extract its staging/validation and owned-asset storage operations into a side-effect-free installation path, keeping the existing file-picker import behavior separate if desired.

`ThemeEngine.saveCustomAs()` also applies a theme and resets Custom; it is not a suitable installation shortcut. A new download operation should write a named theme directly, then refresh the local list without applying it. Catalog download completion can offer an optional Apply button, but must not activate automatically.

## Group styling

Package `keys.keyGroups` and `keys.keyOverrides` are preserved as JSON data. Groups have an ID, positional key IDs, a design override, and `sharedGradientCanvas`. Later matching groups win; specific key overrides win over groups. Preserve group arrays and their ordering.

Group surface/border colors, surface/border gradients and `glyphColor` are meaningful fields. The current `KeyThemePreferences` group codec includes `glyphColor`; OilSlyck exercises that path. Schema-3 documents do not encode keyboard radius, border thickness or the character layout. Do not apply the preview's geometry metadata as part of installation.

The current group-canvas implementation fits explicitly assigned surface gradients to the group bounds even when `sharedGradientCanvas` is false. The shared flag also governs inherited surfaces and border sharing. Preview rendering follows those rules rather than restarting assigned group fills on each key.

## Acceptance checks for the app feature

- Browse and preview with unsaved Custom edits; compare Custom and live preferences before/after.
- Download successfully while a different theme is active; neither active ID nor Custom changes.
- Interrupted, bad-digest, missing-asset and incompatible downloads leave both current state and earlier downloads intact.
- OilSlyck's MainTools glyph color, positional membership and shared gradients survive installation and application.
- Downloaded themes work offline; catalog outages do not prevent local browsing.
- A theme update does not overwrite an edited/saved local derivative.

No Explore client or APK is included in this content-only catalog seed.
