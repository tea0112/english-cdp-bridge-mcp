# Vue 3 Custom Component JS Operations SOP

## Problem
Vue 3 custom components (e.g., OxdSelect) bind events via `addEventListener`. Events produced by JS `dispatchEvent` have `isTrusted: false`, and the component does not respond.
- `element.click()` has no effect (component may bind mousedown instead of click)
- `dispatchEvent(new MouseEvent('mousedown'))` has no effect (isTrusted:false)
- `element.focus()` does not trigger Vue-bound focus handler

## Solution: Direct Vue Component Instance Manipulation

### 1. Get Vue 3 Root Entry
```javascript
const rootVnode = document.getElementById('app')._vnode;
```

### 2. Traverse vnode Tree to Match DOM Element
```javascript
function findCompByEl(vnode, targetEl, depth = 0) {
    if (depth > 50 || !vnode) return null;
    const comp = vnode.component;
    if (comp) {
        if (comp.vnode?.el === targetEl || comp.subTree?.el === targetEl) return comp;
        if (comp.vnode?.el?.contains?.(targetEl)) {
            const result = findCompByEl(comp.subTree, targetEl, depth + 1);
            if (result) return result;
            return comp;
        }
        const subResult = findCompByEl(comp.subTree, targetEl, depth + 1);
        if (subResult) return subResult;
    }
    if (vnode.children && Array.isArray(vnode.children)) {
        for (const child of vnode.children) {
            const result = findCompByEl(child, targetEl, depth + 1);
            if (result) return result;
        }
    }
    if (vnode.dynamicChildren) {
        for (const child of vnode.dynamicChildren) {
            const result = findCompByEl(child, targetEl, depth + 1);
            if (result) return result;
        }
    }
    return null;
}
```

### 3. Call Component Methods
```javascript
// parentElement of the target DOM is typically the component root element
const comp = findCompByEl(rootVnode, targetElement.parentElement);
const ctx = comp.proxy;

// View available methods
Object.keys(ctx).filter(k => !k.startsWith('_') && !k.startsWith('$'));

// Select components: call onSelect directly
ctx.onSelect({id: 'USD', label: 'United States Dollar'});

// Get option list
ctx.computedOptions; // [{id, label, _selected}, ...]
```

## Component Hierarchy Notes
- **Display layer** (e.g., OxdSelectText): only has onToggle/onFocus/onBlur, calling them has no practical effect
- **Logic layer** (e.g., OxdSelectInput, parent of display layer): has openDropdown/onSelect/computedOptions/onCloseDropdown
- Locate the logic layer: use `targetElement.parentElement` rather than targetElement itself

### Select Inside Dialog Also Prefers Pure JS (Verified)
- `.oxd-select-text` inside dialogs (`.oxd-dialog-sheet`) can also hit `OxdSelectInput` via upward traversal, and `onSelect` works normally.
- CDP fallback is not needed. Only consider CDP to open + JS-click option when component is still not found after 8 levels of traversal.

### Upward Traversal Pattern (Recommended)
A single `parentElement` may not be enough; a loop is more robust:
```javascript
function findSelectComp(selectTextEl) {
  for (let el = selectTextEl, up = 0; el && up < 8; el = el.parentElement, up++) {
    const comp = findCompByEl(rootVnode, el);
    if (comp?.proxy?.onSelect && comp.proxy.computedOptions?.length) return comp;
  }
  return null; // fallback to CDP if not found
}
```

## Normal Input/Textarea Operations (nativeSetter)

Vue 3's `v-model` listens for input events; directly setting `el.value = x` does not trigger reactivity. Use the prototype setter:

```javascript
// Input
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(inputEl, 'new value');
inputEl.dispatchEvent(new Event('input', {bubbles: true}));
inputEl.dispatchEvent(new Event('change', {bubbles: true}));

// Textarea
const taSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
taSetter.call(textareaEl, 'content');
textareaEl.dispatchEvent(new Event('input', {bubbles: true}));
```

### Date Input Special Handling
Date components usually have blur validation, requiring a complete focus→assign→blur chain:
```javascript
dateInput.focus();
setter.call(dateInput, '2026-08-05');
dateInput.dispatchEvent(new Event('input', {bubbles: true}));
dateInput.dispatchEvent(new Event('change', {bubbles: true}));
dateInput.dispatchEvent(new Event('blur', {bubbles: true}));
```

### Button
Regular `.click()` works; Vue 3 does not check isTrusted for button click.

### File Upload (input[type="file"])
Browser security model prohibits JS from directly setting `input.value='path'`, but DataTransfer API can be used to construct a FileList:
```javascript
const fileInput = document.querySelector('input[type="file"]');
const content = 'file content';
const file = new File([content], 'filename.txt', { type: 'text/plain', lastModified: Date.now() });
const dt = new DataTransfer();
dt.items.add(file);
fileInput.files = dt.files;  // Supported in Chrome 62+
fileInput.dispatchEvent(new Event('input', { bubbles: true }));
fileInput.dispatchEvent(new Event('change', { bubbles: true }));
```
- Works for any framework (not Vue3-specific), pure browser API
- Can construct any file type (Blob/ArrayBuffer can both be passed to File constructor)
- ⚠ CDP `DOM.setFileInputFiles` only sets the files property without triggering events (common Chrome behavior); DataTransfer+dispatch is the only pure-JS solution
- ⚠ Ensure the dialog/container is open before querySelector, otherwise the input is not in the DOM

## Generalizing to Other Vue3 Sites (Not Verified Individually, Principles Only)

The core method of this SOP (root vnode → findCompByEl → proxy) is universal for Vue3, but specific method/property names vary by UI library.

Probe approach for unfamiliar Vue3 sites:

1. **Confirm Vue3** — check if `document.getElementById('app')?.__vue_app__` exists
2. **Locate target DOM** — use a selector to find the element to operate on (e.g., some select wrapper)
3. **Reverse-lookup component from DOM** — use findCompByEl to search upward from the target element and its parents, get the component
4. **Probe component capabilities** — after getting comp, examine:
   - `Object.keys(comp.proxy.$options.methods || {})` → component method names
   - `Object.keys(comp.props || {})` → props
   - `Object.keys(comp.setupState || {})` → reactive data and functions exposed by setup
   - Focus on methods like onSelect/handleSelect/select/setValue and option list properties like options/items/computedOptions
5. **Trial call** — after finding a possible selection method, pass an option object to try it, observe if DOM updates
6. **Option format** — option structures differ between libraries (could be `{id, label}`, `{value, text}`, or plain strings); take a complete object from the option list data and pass it in

Notes:
- Some libraries use `emits` instead of methods; selection logic may be in parent component rather than child
- Some libraries minify method names in prod build; keys in setupState may be short names, need to infer from behavior
- Composition API component logic is mainly in setupState rather than $options.methods
- If a method is not found on proxy, try `comp.exposed` (exposed via defineExpose in `<script setup>`)

## Applicable Scenarios
- Vue 3 custom Select/Dropdown/Autocomplete components → vnode instance methods
- Vue 3 normal Input/Textarea (v-model) → nativeSetter + input event
- Date components → nativeSetter + focus/blur chain
- File Upload → DataTransfer + change event
- Scenarios requiring bypass of isTrusted checks

## Verified On
- OrangeHRM (opensource-demo.orangehrmlive.com) Vue 3 + OXD component library
- 2026-05-08