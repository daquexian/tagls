# tagls

[![PyPI Version](https://img.shields.io/pypi/v/tagls.svg)](https://pypi.org/project/tagls/) 
![!pyversions](https://img.shields.io/pypi/pyversions/tagls.svg) 
![license](https://img.shields.io/pypi/l/tagls.svg) 
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/daquexian/tagls/pulls)


tagls is a language server based on gtags.

### Why I wrote it?

Almost all editors have great support to LSP, but language servers based on semantic are not always reliable (for example, in dynamic languages like Python). 

On the other hand, the good old gtags can give more comprehensive (sometimes verbose, though) result, but it is not the first class citizen of modern code editors.

A language server based on gtags will give you the best of both worlds.

### Usage

Install tagls by `pip3 install tagls` and register it in your code editor. For example, in coc.nvim:

```json
  "languageserver": {
    "tagls": {
      "command": "python3",
      "args": ["-m", "tagls"],
      "filetypes": [
        "c",
        "cpp",
        "python"
      ],
      "initializationOptions": {},
      "settings": {}
    }
  }
```

### Supported

- [x] initialize (Auto create/update gtags tag files when opening a project in the editor)
- [x] textDocument/didSave (auto update gtags tag files when a file is updated)
- [x] textDocument/definition
- [x] textDocument/references
- [x] textDocument.documentSymbol
- [x] workspace/symbol

### Todo

- [ ] Per-feature configuration (e.g. disable every feature but 'textDocument/references')
