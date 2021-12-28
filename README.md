# tagls

[![PyPI Version](https://img.shields.io/pypi/v/tagls.svg)](https://pypi.org/project/tagls/) 
![!pyversions](https://img.shields.io/pypi/pyversions/tagls.svg) 
![license](https://img.shields.io/pypi/l/tagls.svg) 
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/daquexian/tagls/pulls)


tagls is a language server based on gtags.

### Why I wrote it?

Almost all modern editors have great support to LSP, but language servers based on semantic are not always reliable (for example, in dynamic languages like Python). 

On the other hand, the good old gtags has more comprehensive (sometimes verbose, though) result, but it is not the first class citizen of modern editors and is usually poorly supported.

A **language server** based on **gtags** can give us the best of both worlds.

### Usage

Install tagls by `pip3 install tagls` and register it in your code editor. For example, in coc.nvim:

```jsonc
  "languageserver": {
    "tagls": {
      "command": "python3",
      "args": ["-m", "tagls"],
      "filetypes": [
        "c",
        "cpp",
        "python"
      ],
      "initializationOptions": {
        // Add the following line if you only want tagls as a fallback (also see "Custom LSP methods" section)
        // "register_official_methods": []
        // Add the following line for LeaderF support (https://github.com/daquexian/tagls/issues/1)
        // "gtags_provider": "leaderf"
      },
      "settings": {}
    }
  }
```

#### Custom LSP methods

Tagls provides custom LSP methods beginning with `$tagls/`, so if you want, you can keep tagls from registering official LSP methods and communicate with tagls only by these custom methods. For example, in coc.nvim, after setting `register_official_methods` to `[]`, add the following lines in your .vimrc:

```vim
nnoremap <silent> <leader>kd :call CocLocations('tagls','$tagls/textDocument/definition')<cr>
nnoremap <silent> <leader>kf :call CocLocations('tagls','$tagls/textDocument/references')<cr>
```

### Supported

- [x] initialize (Auto create/update gtags tag files when opening a project in the editor)
- [x] textDocument/didSave (auto update gtags tag files when a file is updated)
- [x] textDocument/definition
- [x] textDocument/references
- [x] textDocument/documentSymbol
- [x] workspace/symbol
- [x] Per-feature configuration (e.g. disable every feature but "textDocument/references")
- [x] Custom LSP methods ("$tagls/textDocument/definition" and so on)
- [x] Integrate with [LeaderF](https://github.com/Yggdroot/LeaderF)
