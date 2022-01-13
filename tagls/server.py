import asyncio
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

from pygls.capabilities import ServerCapabilitiesBuilder
from pygls.lsp import (
    types,
    LSP_METHODS_MAP
)
from pygls.lsp.methods import *
from pygls.lsp.types import window as window_types
from pygls.lsp.types.basic_structures import Trace
from pygls.protocol import LanguageServerProtocol
from pygls.server import LanguageServer
import pygls.uris
from pygls.uris import from_fs_path
from pygls.workspace import Workspace

logger = logging.getLogger(__name__)


def get_cache_root(gtags_provider: str, custom_cache_root: Optional[str]) -> str:
    if custom_cache_root:
        cache_root = custom_cache_root
    else:
        if gtags_provider == 'tagls':
            cache_root = "~/.cache/gtags"
        elif gtags_provider == 'leaderf':
            cache_root = "~/.LfCache/gtags"
        else:
            raise ValueError(f"Unknown gtags_provider {gtags_provider}")
    return os.path.expanduser(cache_root)


def get_cache_dir(project_root: str, gtags_provider: str, custom_cache_root: Optional[str]) -> str:
    cache_root = get_cache_root(gtags_provider, custom_cache_root)

    if gtags_provider == 'tagls':
        filenameified_project_root = project_root.replace(os.path.sep, "_")
    elif gtags_provider == 'leaderf':
        filenameified_project_root = project_root.replace(os.path.sep, "_")
    else:
        raise ValueError(f"Unknown gtags_provider {gtags_provider}")

    cache_dir = os.path.join(cache_root, filenameified_project_root)

    if gtags_provider == 'tagls':
        os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def show_message_log(log: Union[str, bytes]):
    if isinstance(log, bytes):
        log = log.decode("utf-8")
    server.show_message_log(log)


async def spawn_shell(
    cmd: str, cwd: str, env: Optional[Dict[str, str]] = None, check_return_code=True
):
    show_message_log(f"run cmd {cmd} at {cwd} with env {env}")
    if env is None:
        env = {}
    # NOTE: $HOME/.globalrc is one of the gtags configuration file positions.
    # but 'HOME' environment variable doesn't exist in the shell
    # triggered by asyncio.create_subprocess_shell unless we pass it explicitly.
    if "HOME" not in env:
        env["HOME"] = os.path.expanduser("~")
    p = await asyncio.create_subprocess_shell(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    stdout, stderr = await p.communicate()
    show_message_log(stderr)
    if check_return_code:
        assert p.returncode == 0, cmd
    return stdout, stderr


async def run_global(args: str, root: str, check_return_code=True):
    return await spawn_shell(
        cmd=f"global --verbose {args}",
        cwd=root,
        env={"GTAGSROOT": root, "GTAGSDBPATH": cache_dir},
        check_return_code=check_return_code,
    )


async def run_global_and_parse_from_cscope_format_result(
    ls: LanguageServer, args: str,
) -> List[Tuple[str, types.Location]]:
    assert ls.workspace.root_path is not None

    stdout, stderr = await run_global(args=args, root=ls.workspace.root_path)
    show_message_log(f"stdout: {stdout}, stderr: {stderr}")
    stdout = stdout.strip()
    if len(stdout) == 0:
        return []
    res = []
    for stdout_line in stdout.split(b"\n"):
        show_message_log(stdout_line)
        filename, tag_name, lineno, _ = stdout_line.split(b" ", maxsplit=3)
        show_message_log(
            f"tag_name: {tag_name}, lineno: {lineno}, filename: {filename}"
        )
        # pygments parser discards the leading space of code text (called line image in gtags)
        # in some cases. So the only way to get the precise column number is get source code
        # from local disk / language server buffer
        tag_name, lineno, filename = (
            tag_name.decode("utf-8"),
            int(lineno),
            filename.decode("utf-8"),
        )
        lineno -= 1
        uri = pygls.uris.from_fs_path(filename)
        assert uri is not None
        line = ls.workspace.get_document(uri).lines[lineno]
        show_message_log(f"line: {line}")
        col_start = line.find(tag_name)
        col_end = col_start + len(tag_name)
        show_message_log(f"col_start: {col_start}, col_end: {col_end}")
        pos_start = types.Position(line=lineno, character=col_start)
        pos_end = types.Position(line=lineno, character=col_end)
        loc = types.Location(
            uri=pygls.uris.from_fs_path(filename),
            range=types.Range(start=pos_start, end=pos_end),
        )
        res.append((tag_name, loc))
    return res


async def get_locations(
    ls: LanguageServer,
    params: Union[types.TextDocumentPositionParams, types.ReferenceParams],
    references: bool,
) -> List[types.Location]:
    doc = ls.workspace.get_document(params.text_document.uri)
    word = doc.word_at_position(params.position)
    if len(word) == 0:
        return []
    if references:
        args = f"--result=cscope -ar {word}"
    else:
        args = f"--result=cscope -a {word}"

    return list(
        map(
            lambda x: x[1],
            await run_global_and_parse_from_cscope_format_result(ls, args),
        )
    )


class TagLSProtocol(LanguageServerProtocol):
    # override lsp_initialize by a function without @lsp_method decorator,
    # so it will not be treated as a built-in feature
    def lsp_initialize(self):
        pass


server = LanguageServer(protocol_cls=TagLSProtocol)


def tagls_feature(method_name: str, custom_types: Optional[Tuple[Any, Any, Any]]=None):
    def deco(f):
        async def f_if_register_official_methods(ls: LanguageServer, *args, **kwargs):
            if register_official_methods != 'all' and method_name not in register_official_methods:
                return
            return await f(ls, *args, **kwargs)
        server.feature(method_name)(f_if_register_official_methods)

        nonlocal custom_types
        if custom_types is None:
            custom_types = LSP_METHODS_MAP[method_name]
        server.feature(f"$tagls/{method_name}", types=custom_types)(f)
        return f

    return deco


def only_available_on_tagls_provider(f):
    async def decoed_f(ls: LanguageServer, *args, **kwargs):
        show_message_log(gtags_provider)
        if gtags_provider != 'tagls':
            return
        return await f(ls, *args, **kwargs)

    return decoed_f


@tagls_feature(WORKSPACE_SYMBOL)
async def workspace_symbol(
    ls: LanguageServer, params: types.WorkspaceSymbolParams
) -> List[types.SymbolInformation]:
    assert ls.workspace.root_path is not None
    args = f"--result=cscope -a .*{params.query}.*"
    tag_name_and_locations = await run_global_and_parse_from_cscope_format_result(
        ls, args
    )
    return [
        types.SymbolInformation(
            name=tag_name, kind=types.SymbolKind.Null, location=location
        )
        for tag_name, location in tag_name_and_locations
    ]


@tagls_feature(DOCUMENT_SYMBOL)
async def document_symbol(
    ls: LanguageServer, params: types.DocumentSymbolParams
) -> List[types.SymbolInformation]:
    assert ls.workspace.root_path is not None
    args = f"--result=cscope -af {pygls.uris.to_fs_path(params.text_document.uri)}"
    tag_name_and_locations = await run_global_and_parse_from_cscope_format_result(
        ls, args
    )
    return [
        types.SymbolInformation(
            name=tag_name, kind=types.SymbolKind.Null, location=location
        )
        for tag_name, location in tag_name_and_locations
    ]


@tagls_feature(DEFINITION)
async def definition(
    ls: LanguageServer, params: types.DefinitionParams
) -> List[types.Location]:
    return await get_locations(ls, params, False)


@tagls_feature(REFERENCES, custom_types=(None, types.TextDocumentPositionParams, Optional[List[types.Location]]))
async def references(
    ls: LanguageServer, params: types.ReferenceParams
) -> List[types.Location]:
    return await get_locations(ls, params, True)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
@only_available_on_tagls_provider
async def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)
    assert ls.workspace.root_path is not None
    await run_global(f"--single-update {doc.path}", ls.workspace.root_path)
    show_message_log("single update succeeded")


# Copied from parent class
def builtin_initialize(lsp: LanguageServerProtocol, params: types.InitializeParams):
    logger.info("Language server initialized %s", params)

    lsp._server.process_id = params.process_id

    # Initialize server capabilities
    lsp.client_capabilities = params.capabilities
    lsp.server_capabilities = ServerCapabilitiesBuilder(
        lsp.client_capabilities,
        {**lsp.fm.features, **lsp.fm.builtin_features}.keys(),
        lsp.fm.feature_options,
        list(lsp.fm.commands.keys()),
        lsp._server.sync_kind,
    ).build()
    logger.debug("Server capabilities: %s", lsp.server_capabilities.dict())

    root_path = params.root_path
    root_uri = params.root_uri or from_fs_path(root_path)

    # Initialize the workspace
    workspace_folders = params.workspace_folders or []
    lsp.workspace = Workspace(root_uri, lsp._server.sync_kind, workspace_folders)

    lsp.trace = Trace.Off

    return types.InitializeResult(capabilities=lsp.server_capabilities)


@server.feature(INITIALIZE)
async def initialize(ls: LanguageServer, params: types.InitializeParams):
    assert isinstance(ls.lsp, LanguageServerProtocol)
    result = builtin_initialize(ls.lsp, params)
    root_path = ls.workspace.root_path
    assert root_path is not None
    if isinstance(params.initialization_options, dict):
        init_options: Dict[str, Any] = params.initialization_options
        show_message_log(f"initialization_options: {init_options}")
    else:
        raise ValueError(f"Wrong initialization_options {params.initialization_options}")
    global gtags_provider
    gtags_provider = init_options.get("gtags_provider", "tagls")
    show_message_log(f"gtags_provider: {gtags_provider}")
    custom_cache_root = init_options.get("cache_dir", None)
    show_message_log(f"custom_cache_root: {custom_cache_root}")
    global cache_dir
    cache_dir = get_cache_dir(root_path, gtags_provider, custom_cache_root)
    show_message_log(f"project_cache_dir: {cache_dir}")
    global register_official_methods
    register_official_methods = init_options.get("register_official_methods", "all")

    if gtags_provider == 'tagls':
        need_generate = False
        if os.path.exists(os.path.join(cache_dir, "GTAGS")):
            _, stderr = await run_global("-u", root_path, check_return_code=False)
            if b"seems corrupted" in stderr:
                ls.show_message(
                    "gtags files are corrupted. Generating again...",
                    window_types.MessageType.Warning,
                )
                need_generate = True
        else:
            need_generate = True
        if need_generate:
            await spawn_shell(
                cmd=f"gtags {cache_dir}", cwd=root_path,
            )
    return result


@server.feature(INITIALIZED)
def initialized(ls: LanguageServer, params: types.InitializedParams):
    show_message_log("initialized")

