"""Compatibility entry point for the registry-driven World Bank pipeline.

New automation should invoke ``build_world_bank_series.py`` directly.  This
filename remains runnable so existing local commands do not break.
"""

from build_world_bank_series import main


if __name__ == "__main__":
    main()
