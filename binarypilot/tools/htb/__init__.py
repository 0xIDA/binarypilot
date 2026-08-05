"""HackTheBox platform tools."""

from binarypilot.tools.htb.tool import (
    htb_download_challenge,
    htb_get_challenge_info,
    htb_get_machine_info,
    htb_list_challenges,
    htb_search_content,
    htb_spawn_challenge_container,
    htb_spawn_machine,
    htb_stop_challenge_container,
    htb_submit_challenge_flag,
    htb_submit_machine_flag,
)


__all__ = [
    "htb_download_challenge",
    "htb_get_challenge_info",
    "htb_get_machine_info",
    "htb_list_challenges",
    "htb_search_content",
    "htb_spawn_challenge_container",
    "htb_spawn_machine",
    "htb_stop_challenge_container",
    "htb_submit_challenge_flag",
    "htb_submit_machine_flag",
]
