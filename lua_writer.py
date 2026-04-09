import os
import time
from datetime import datetime, timezone


def _lua_string(s) -> str:
    if s is None:
        return "nil"
    return '"{}"'.format(str(s).replace("\\", "\\\\").replace('"', '\\"'))


def _lua_bool(b) -> str:
    return "true" if b else "false"


def _lua_number(n) -> str:
    if n is None:
        return "nil"
    return str(n)


def _lua_timestamp(val) -> str:
    """Konvertiert ISO-8601-String oder Unix-Zahl sicher in einen Lua-Integer-Timestamp."""
    if val is None:
        return "nil"
    if isinstance(val, (int, float)):
        return str(int(val))
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return str(int(dt.timestamp()))
        except (ValueError, AttributeError):
            pass
    return "nil"


# --------------------------------------------------
# RAID DATA
# --------------------------------------------------
def _raid_block(raid: dict) -> str:
    prio_lines = []
    for item in (raid.get("prioItems") or []):
        prio_lines.append(
            "      {{ itemID = {}, itemName = {}, priority = {}, difficulty = {} }}".format(
                _lua_number(item.get("itemID")),
                _lua_string(item.get("itemName")),
                _lua_number(item.get("priority")),
                _lua_string(item.get("difficulty")),
            )
        )
    return (
        "  {{\n"
        "    raidID       = {raidID},\n"
        "    raidName     = {raidName},\n"
        "    difficulty   = {difficulty},\n"
        "    scheduledAt  = {scheduledAt},\n"
        "    signupStatus = {signupStatus},\n"
        "    prioFilled   = {prioFilled},\n"
        "    prioItems    = {{\n{prioItems}\n    }},\n"
        "  }}"
    ).format(
        raidID=_lua_number(raid.get("raidID")),
        raidName=_lua_string(raid.get("raidName")),
        difficulty=_lua_string(raid.get("difficulty")),
        scheduledAt=_lua_number(raid.get("scheduledAt")),
        signupStatus=_lua_string(raid.get("signupStatus")),
        prioFilled=_lua_bool(raid.get("prioFilled", False)),
        prioItems=",\n".join(prio_lines),
    )


def write_raid(data: dict, addon_path: str) -> bool:
    """Schreibt data/raid_data.lua in den Addon-Ordner."""
    out_path = os.path.join(addon_path, "data", "raid_data.lua")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    raids = data.get("raids", [])
    raid_blocks = ",\n".join(_raid_block(r) for r in raids)

    lua = """-- Automatisch generiert von WeltenWandler Companion App.
-- Nicht manuell bearbeiten.

WRT_RaidData = {{
  version     = {version},
  generatedAt = {generatedAt},
  raids = {{
{raids}
  }},
}}
""".format(
        version=_lua_number(data.get("version", 1)),
        generatedAt=_lua_number(int(time.time())),
        raids=raid_blocks,
    )

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(lua)
        return True
    except Exception as e:
        print(f"[LuaWriter] Fehler beim Schreiben von raid_data.lua: {e}")
        return False


# --------------------------------------------------
# STATS DATA
# --------------------------------------------------
def write_stats(data: dict, addon_path: str) -> bool:
    """
    Schreibt data/stats_data.lua in den Addon-Ordner.
    data: dict vom /api/companion/stats Endpunkt
    """
    out_path = os.path.join(addon_path, "data", "stats_data.lua")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # --- Dropchance ---
    dc_blocks = []
    for boss in (data.get("dropchance") or []):
        item_lines = []
        for item in (boss.get("items") or []):
            item_lines.append(
                "      {{ itemID = {}, itemName = {}, drops = {}, kills = {}, chance = {} }}".format(
                    _lua_number(item.get("itemID")),
                    _lua_string(item.get("itemName")),
                    _lua_number(item.get("drops", 0)),
                    _lua_number(item.get("kills", 0)),
                    _lua_number(round(item.get("chance", 0), 1)),
                )
            )
        dc_blocks.append(
            "  {{\n    bossName = {},\n    items = {{\n{}\n    }},\n  }}".format(
                _lua_string(boss.get("bossName")),
                ",\n".join(item_lines),
            )
        )

    # --- Player Stats ---
    ps_blocks = []
    for ps in (data.get("playerStats") or []):
        hist_lines = []
        for h in (ps.get("history") or []):
            hist_lines.append(
                "      {{ itemID = {}, itemName = {}, boss = {}, raidName = {}, lootType = {}, timestamp = {} }}".format(
                    _lua_number(h.get("itemID")),
                    _lua_string(h.get("itemName")),
                    _lua_string(h.get("boss")),
                    _lua_string(h.get("raidName")),
                    _lua_string(h.get("lootType")),
                    _lua_timestamp(h.get("timestamp")),
                )
            )
        ps_blocks.append(
            "  {{\n"
            "    playerName  = {playerName},\n"
            "    wowClass    = {wowClass},\n"
            "    lootTotal   = {lootTotal},\n"
            "    lootMS      = {lootMS},\n"
            "    lootOS      = {lootOS},\n"
            "    raids       = {raids},\n"
            "    raidsTotal  = {raidsTotal},\n"
            "    avgPerRaid  = {avgPerRaid},\n"
            "    avgAttended = {avgAttended},\n"
            "    percentage  = {percentage},\n"
            "    history     = {{\n{history}\n    }},\n"
            "  }}".format(
                playerName=_lua_string(ps.get("playerName")),
                wowClass=_lua_string(ps.get("wowClass")),
                lootTotal=_lua_number(ps.get("lootTotal", 0)),
                lootMS=_lua_number(ps.get("lootMS", 0)),
                lootOS=_lua_number(ps.get("lootOS", 0)),
                raids=_lua_number(ps.get("raids", 0)),
                raidsTotal=_lua_number(ps.get("raidsTotal", 0)),
                avgPerRaid=_lua_number(round(ps.get("avgPerRaid", 0), 2)),
                avgAttended=_lua_number(round(ps.get("avgAttended", 0), 2)),
                percentage=_lua_number(round(ps.get("percentage", 0), 1)),
                history=",\n".join(hist_lines),
            )
        )

    # --- Loot History ---
    lh_blocks = []
    for raid in (data.get("lootHistory") or []):
        entry_lines = []
        for e in (raid.get("entries") or []):
            entry_lines.append(
                "      {{ timestamp = {}, boss = {}, itemID = {}, itemName = {}, player = {}, lootType = {} }}".format(
                    _lua_timestamp(e.get("timestamp")),
                    _lua_string(e.get("boss")),
                    _lua_number(e.get("itemID")),
                    _lua_string(e.get("itemName")),
                    _lua_string(e.get("player")),
                    _lua_string(e.get("lootType")),
                )
            )
        lh_blocks.append(
            "  {{\n"
            "    raidName  = {},\n"
            "    date      = {},\n"
            "    difficulty= {},\n"
            "    timestamp = {},\n"
            "    entries   = {{\n{}\n    }},\n"
            "  }}".format(
                _lua_string(raid.get("raidName")),
                _lua_string(raid.get("date")),
                _lua_string(raid.get("difficulty")),
                _lua_timestamp(raid.get("timestamp")),
                ",\n".join(entry_lines),
            )
        )

    lua = """-- Automatisch generiert von WeltenWandler Companion App.
-- Nicht manuell bearbeiten.

WRT_StatsData = {{
  version     = {version},
  generatedAt = {generatedAt},
  dropchance  = {{
{dropchance}
  }},
  playerStats = {{
{playerStats}
  }},
  lootHistory = {{
{lootHistory}
  }},
}}
""".format(
        version=_lua_number(data.get("version", 1)),
        generatedAt=_lua_number(int(time.time())),
        dropchance=",\n".join(dc_blocks),
        playerStats=",\n".join(ps_blocks),
        lootHistory=",\n".join(lh_blocks),
    )

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(lua)
        return True
    except Exception as e:
        print(f"[LuaWriter] Fehler beim Schreiben von stats_data.lua: {e}")
        return False
