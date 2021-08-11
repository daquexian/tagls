import os
import asyncio
import subprocess
import logging
import argparse

from pygls.lsp.methods import *
from pygls.protocol import LanguageServerProtocol

from pygls.server import LanguageServer
from pygls.lsp import (
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    types,
)

from pygls.lsp.types import client as client_types
from pygls.lsp.types import window as window_types
from pygls.uris import from_fs_path
from pygls.capabilities import ServerCapabilitiesBuilder
from pygls.workspace import Workspace
from pygls.lsp.types.basic_structures import Trace

from typing import List, Union, Dict, Optional

logger = logging.getLogger(__name__)

RUN_TCP = True

CACHE_ROOT = os.path.expanduser("~/.cache/gtags")
os.makedirs(CACHE_ROOT, exist_ok=True)


def get_cache_dir(project_root: str):
    project_root = project_root.replace(os.path.sep, "_")
    cache_dir = os.path.join(CACHE_ROOT, project_root)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def print_if_tcp(*args, **kwargs):
    if RUN_TCP:
        print(*args, **kwargs)


async def spawn_shell(
    cmd: str, cwd: str, env: Optional[Dict[str, str]] = None, check_return_code = True
):
    print_if_tcp(f"run cmd {cmd} at {cwd}")
    p = await asyncio.create_subprocess_shell(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    stdout, stderr = await p.communicate()
    print_if_tcp(stderr)
    if check_return_code:
        assert p.returncode == 0, cmd
    return stdout, stderr


async def run_global(args: str, root: str, check_return_code=True):
    return await spawn_shell(
        cmd=f"global {args}",
        cwd=root,
        env={"GTAGSROOT": root, "GTAGSDBPATH": cache_dir},
        check_return_code=check_return_code,
    )


async def get_locations(
    ls: LanguageServer,
    params: Union[types.TextDocumentPositionParams, types.ReferenceParams],
    references: bool,
):
    def get_uri(path: str):
        return f"file://{path}"

    doc = ls.workspace.get_document(params.text_document.uri)
    word = doc.word_at_position(params.position)
    if references:
        # set the format to grep so that we do not need to skip the tag_name
        # when splitting
        args = f"--result=grep -ar {word}"
    else:
        args = f"--result=grep -a {word}"

    assert ls.workspace.root_path is not None

    stdout, _ = await run_global(args=args, root=ls.workspace.root_path)
    stdout = stdout.strip()
    if len(stdout) == 0:
        return []
    locs = []
    for stdout_line in stdout.split(b"\n"):
        print_if_tcp(stdout_line)
        print_if_tcp(stdout_line.split(b":", maxsplit=2))
        filename, lineno, _ = stdout_line.split(b":", maxsplit=2)
        print_if_tcp(lineno, filename)
        # pygments parser discards the leading space of code text (called line image in gtags)
        # in some cases. So the only way to get the precise column number is get source code
        # from local disk / language server buffer
        lineno, filename = int(lineno), filename.decode("utf-8")
        lineno -= 1
        line = ls.workspace.get_document(get_uri(filename)).lines[lineno]
        print_if_tcp(f"line: {line}")
        col_start = line.find(word)
        col_end = col_start + len(word)
        print_if_tcp(col_start, col_end)
        pos_start = types.Position(line=lineno, character=col_start)
        pos_end = types.Position(line=lineno, character=col_end)
        loc = types.Location(
            uri=get_uri(filename), range=types.Range(start=pos_start, end=pos_end)
        )
        locs.append(loc)
    return locs


class TagLSProtocol(LanguageServerProtocol):
    # override lsp_initialize by a function without @lsp_method decorator,
    # so it will not be treated as a built-in feature
    def lsp_initialize(self):
        pass


server = LanguageServer(protocol_cls=TagLSProtocol)


@server.feature(DEFINITION)
async def definition(
    ls: LanguageServer, params: types.TextDocumentPositionParams
) -> List[types.Location]:
    return await get_locations(ls, params, False)


@server.feature(REFERENCES)
async def references(
    ls: LanguageServer, params: types.ReferenceParams
) -> List[types.Location]:
    return await get_locations(ls, params, True)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)
    assert ls.workspace.root_path is not None
    await run_global(f" --single-update {doc.path}", ls.workspace.root_path)
    print_if_tcp("single update succeeded")


# Copied from parent class
def builtin_initialize(lsp: LanguageServerProtocol, params: types.InitializeParams):
    logger.info('Language server initialized %s', params)

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
    logger.debug('Server capabilities: %s', lsp.server_capabilities.dict())

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
    global cache_dir
    cache_dir = get_cache_dir(root_path)
    print_if_tcp(f'cache_dir: {cache_dir}')
    need_generate = False
    if os.path.exists(os.path.join(cache_dir, "GTAGS")):
        _, stderr = await run_global("-u", root_path, check_return_code=False)
        if b"seems corrupted" in stderr:
            ls.show_message("gtags files are corrupted. Generating again...", window_types.MessageType.Warning)
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
    print_if_tcp("initialized")


@server.feature(WORKSPACE_DID_CHANGE_WATCHED_FILES)
async def did_change_watched_files(ls: LanguageServer, params: types.DidChangeWatchedFilesParams):
    print_if_tcp(f'{params.changes[0].uri} changed!')


parser = argparse.ArgumentParser()
parser.add_argument("--tcp", action='store_true')
parser.add_argument("--port", type=int, default=9528)

args = parser.parse_args()

RUN_TCP = args.tcp

if RUN_TCP:
    server.start_tcp("127.0.0.1", args.port)
else:
    server.start_io()

