# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH)
binarypilot_root = project_root / 'binarypilot'

datas = []

for md_file in binarypilot_root.rglob('skills/**/*.md'):
    rel_path = md_file.relative_to(project_root)
    datas.append((str(md_file), str(rel_path.parent)))

for jinja_file in binarypilot_root.rglob('agents/**/*.jinja'):
    rel_path = jinja_file.relative_to(project_root)
    datas.append((str(jinja_file), str(rel_path.parent)))

for xml_file in binarypilot_root.rglob('*.xml'):
    rel_path = xml_file.relative_to(project_root)
    datas.append((str(xml_file), str(rel_path.parent)))

for tcss_file in binarypilot_root.rglob('*.tcss'):
    rel_path = tcss_file.relative_to(project_root)
    datas.append((str(tcss_file), str(rel_path.parent)))

# Prebuilt local-viewer SPA (served by `binarypilot view`).
viewer_static = binarypilot_root / 'interface' / 'viewer' / 'static'
for asset in viewer_static.rglob('*'):
    if asset.is_file():
        rel_path = asset.relative_to(project_root)
        datas.append((str(asset), str(rel_path.parent)))

datas += collect_data_files('textual')

datas += collect_data_files('tiktoken')
datas += collect_data_files('tiktoken_ext')

datas += collect_data_files('litellm')

datas += collect_data_files('agents', includes=['**/*.md', '**/*.jinja', '**/*.json'])

hiddenimports = [
    # Core dependencies
    'litellm',
    'litellm.llms',
    'litellm.llms.openai',
    'litellm.llms.anthropic',
    'litellm.llms.vertex_ai',
    'litellm.llms.bedrock',
    'litellm.utils',
    'litellm.caching',

    # Textual TUI
    'textual',
    'textual.app',
    'textual.widgets',
    'textual.containers',
    'textual.screen',
    'textual.binding',
    'textual.reactive',
    'textual.css',
    'textual._text_area_theme',

    # Rich console
    'rich',
    'rich.console',
    'rich.panel',
    'rich.text',
    'rich.markup',
    'rich.style',
    'rich.align',
    'rich.live',

    # Pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic_core',
    'email_validator',

    # Docker
    'docker',
    'docker.api',
    'docker.models',
    'docker.errors',

    # HTTP/Networking
    'httpx',
    'httpcore',
    'requests',
    'urllib3',
    'certifi',

    # Jinja2 templating
    'jinja2',
    'jinja2.ext',
    'markupsafe',

    # XML parsing
    'xmltodict',
    'defusedxml',
    'defusedxml.ElementTree',

    # Syntax highlighting
    'pygments',
    'pygments.lexers',
    'pygments.styles',
    'pygments.util',

    # Tiktoken (for token counting)
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',

    # Tenacity retry
    'tenacity',

    # CVSS scoring
    'cvss',

    # BinaryPilot modules
    'binarypilot',
    'binarypilot.interface',
    'binarypilot.interface.main',
    'binarypilot.interface.cli',
    'binarypilot.interface.tui',
    'binarypilot.interface.tui.app',
    'binarypilot.interface.tui.history',
    'binarypilot.interface.tui.live_view',
    'binarypilot.interface.tui.messages',
    'binarypilot.interface.tui.renderers',
    'binarypilot.interface.tui.renderers.agent_message_renderer',
    'binarypilot.interface.tui.renderers.agents_graph_renderer',
    'binarypilot.interface.tui.renderers.base_renderer',
    'binarypilot.interface.tui.renderers.finish_renderer',
    'binarypilot.interface.tui.renderers.notes_renderer',
    'binarypilot.interface.tui.renderers.proxy_renderer',
    'binarypilot.interface.tui.renderers.registry',
    'binarypilot.interface.tui.renderers.reporting_renderer',
    'binarypilot.interface.tui.renderers.thinking_renderer',
    'binarypilot.interface.tui.renderers.todo_renderer',
    'binarypilot.interface.tui.renderers.user_message_renderer',
    'binarypilot.interface.tui.renderers.web_search_renderer',
    'binarypilot.interface.utils',
    'binarypilot.agents',
    'binarypilot.agents.factory',
    'binarypilot.agents.prompt',
    'binarypilot.config.models',
    'binarypilot.core',
    'binarypilot.core.agents',
    'binarypilot.core.execution',
    'binarypilot.core.inputs',
    'binarypilot.core.paths',
    'binarypilot.core.runner',
    'binarypilot.core.sessions',
    'binarypilot.report',
    'binarypilot.report.dedupe',
    'binarypilot.report.state',
    'binarypilot.report.writer',
    'binarypilot.interface.viewer',
    'binarypilot.interface.viewer.auth',
    'binarypilot.interface.viewer.cli',
    'binarypilot.interface.viewer.report_pdf',
    'binarypilot.interface.viewer.server',
    'binarypilot.interface.viewer.transcript',

    # PDF report generation + encryption
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfbase',
    'reportlab.lib',
    'reportlab.platypus',
    'pypdf',
    'cryptography',
    'binarypilot.runtime',
    'binarypilot.runtime.backends',
    'binarypilot.runtime.caido_bootstrap',
    'binarypilot.runtime.docker_client',
    'binarypilot.runtime.session_manager',
    'binarypilot.telemetry',
    'binarypilot.telemetry.logging',
    'binarypilot.telemetry.posthog',
    'binarypilot.tools',
    'binarypilot.tools.agents_graph.tools',
    'binarypilot.tools.finish.tool',
    'binarypilot.tools.notes.tools',
    'binarypilot.tools.proxy._calls',
    'binarypilot.tools.proxy.tools',
    'binarypilot.tools.python.tool',
    'binarypilot.tools.reporting.tool',
    'binarypilot.tools.thinking.tool',
    'binarypilot.tools.todo.tools',
    'binarypilot.tools.web_search.tool',
    'binarypilot.skills',
]

hiddenimports += collect_submodules('litellm')
hiddenimports += collect_submodules('textual')
hiddenimports += collect_submodules('rich')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pygments')
# reportlab loads renderers/fonts dynamically, so pull its whole tree in.
hiddenimports += collect_submodules('reportlab')

# reportlab ships bundled fonts (.pfb/.afm) it needs at runtime.
datas += collect_data_files('reportlab')

# reportlab imports PIL (pillow) lazily for image handling, so it must be
# bundled explicitly and kept out of the excludes list below.
hiddenimports += collect_submodules('PIL')
datas += collect_data_files('PIL')

excludes = [
    # Sandbox-only packages
    'playwright',
    'playwright.sync_api',
    'playwright.async_api',
    'IPython',
    'ipython',
    'libtmux',
    'pyte',
    'openhands_aci',
    'openhands-aci',
    'numpydoc',

    # Google Cloud / Vertex AI
    'google.cloud',
    'google.cloud.aiplatform',
    'google.api_core',
    'google.auth',
    'google.oauth2',
    'google.protobuf',
    'grpc',
    'grpcio',
    'grpcio_status',

    # Test frameworks
    'pytest',
    'pytest_asyncio',
    'pytest_cov',
    'pytest_mock',

    # Development tools
    'mypy',
    'ruff',
    'black',
    'isort',
    'pylint',
    'pyright',
    'bandit',
    'pre_commit',

    # Unnecessary for runtime
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'cv2',
]

a = Analysis(
    ['binarypilot/interface/main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='binarypilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
