"""
Pipeline-wide constants and mappings.

Centralised definitions for:
- Environment variable names
- DCC file extension mappings
- Department-to-DCC default mapping
- Context field names
"""

# ── Pipeline Environment Variables ──
# These are injected into the DCC session by the launcher,
# and read by the publisher to auto-populate context.

ENV_PROJECT    = 'PIPELINE_PROJECT'     # Project name (e.g. 'test_03')
ENV_SEQUENCE   = 'PIPELINE_SEQUENCE'    # Sequence name (e.g. 'sq001')
ENV_SHOT       = 'PIPELINE_SHOT'        # Shot name (e.g. 'shot001')
ENV_DEPARTMENT = 'PIPELINE_DEPARTMENT'  # Department/工种 (e.g. 'fx', 'anim')
ENV_USER       = 'PIPELINE_USER'        # Username override
ENV_DCC        = 'PIPELINE_DCC'         # Explicit DCC override (optional)


# ── Context Dictionary Keys ──
# Consistent string keys used in context dicts throughout the app.

CTX_PROJECT    = 'project'
CTX_SEQUENCE   = 'sequence'
CTX_SHOT       = 'shot'
CTX_DEPARTMENT = 'department'   # Was 'role' — renamed for clarity
CTX_USER       = 'user'
CTX_DCC        = 'dcc'
CTX_PUBLISH_ROOT = 'publish_root'
CTX_PROJECT_ROOT = 'project_root'


# ── DCC File Extensions ──
# Used by source detector and file filters.
# Mapped by DCC name (DCCType.value), NOT by department.

DCC_EXTENSIONS = {
    'maya':     ('*.ma', '*.mb'),
    'houdini':  ('*.hip', '*.hipnc'),
    'nuke':     ('*.nk',),
    'standalone': ('*',),
}


# ── Department → Default DCC Mapping ──
# Which DCC a department typically uses.
# Used by the launcher to decide which app to start,
# and by source detector to guess the file extension.

DEPARTMENT_DCC_MAP = {
    'model':    'maya',
    'rig':      'maya',
    'anim':     'maya',
    'fx':       'houdini',
    'lighting': 'houdini',
    'layout':   'maya',
    'comp':     'nuke',
    'assets':   'maya',
    'design':   'maya',
}


def get_dcc_for_department(department: str) -> str:
    """Get the default DCC for a given department.

    Falls back to 'standalone' if no mapping exists.
    """
    return DEPARTMENT_DCC_MAP.get(department.lower(), 'standalone')


def get_extensions_for_dcc(dcc: str) -> tuple:
    """Get file extension patterns for a given DCC.

    Returns a tuple of glob patterns.
    """
    return DCC_EXTENSIONS.get(dcc.lower(), ('*',))
