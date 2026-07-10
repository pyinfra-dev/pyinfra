#   This file should be `source`d.

set -Eeuo pipefail

#   If uv is available, we will always use it. But if uv is not present, we
#   assume that the developer has set up her own virtualenv configuration
#   and run:
#       pip install --group=dev -e .
uvrun=
if uv --version >/dev/null 2>&1; then
    uvrun='uv run'
else
    [[ -z ${VIRTUAL_ENV:-} ]] && echo 1>&2 \
        "WARNING: no 'uv' and no \$VIRTUAL_ENV; trying in current environment."
fi
true
