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

    # Vollständige Prioliste aller Spieler (für Auto-Import im Addon, nur officer+)
    full_prio_lines = []
    for entry in (raid.get("prioList") or []):
        full_prio_lines.append(
            "      {{ character = {}, itemID = {}, priority = {}, wowClass = {} }}".format(
                _lua_string(entry.get("character")),
                _lua_number(entry.get("itemID")),
                _lua_number(entry.get("priority")),
                _lua_string(entry.get("wowClass")),
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
        "    superPrio    = {superPrio},\n"
        "    prioItems    = {{\n{prioItems}\n    }},\n"
        "    prioList     = {{\n{prioList}\n    }},\n"
        "  }}"
    ).format(
        raidID=_lua_number(raid.get("raidID")),
        raidName=_lua_string(raid.get("raidName")),
        difficulty=_lua_string(raid.get("difficulty")),
        scheduledAt=_lua_number(raid.get("scheduledAt")),
        signupStatus=_lua_string(raid.get("signupStatus")),
        prioFilled=_lua_bool(raid.get("prioFilled", False)),
        superPrio=_lua_bool(raid.get("superPrio", False)),
        prioItems=",\n".join(prio_lines),
        prioList=",\n".join(full_prio_lines),
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
    Enthält nur patches (mit itemIDs) und lootHistory.
    Dropchance und playerStats werden client-seitig im Addon aus der lootHistory aggregiert.
    """
    out_path = os.path.join(addon_path, "data", "stats_data.lua")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # --- Patches ---
    patch_lines = []
    for p in (data.get("patches") or []):
        item_ids = p.get("itemIDs") or []
        ids_lua  = "{{ {} }}".format(", ".join(str(i) for i in item_ids)) if item_ids else "{}"

        # bossItems: { ["BossName"] = {itemID, ...}, ... }
        boss_items = p.get("bossItems") or {}
        boss_lines = []
        for boss_name, b_ids in boss_items.items():
            ids_part = "{{ {} }}".format(", ".join(str(i) for i in b_ids)) if b_ids else "{}"
            boss_lines.append("      [{}] = {}".format(_lua_string(boss_name), ids_part))
        boss_items_lua = "{{\n{}\n    }}".format(",\n".join(boss_lines)) if boss_lines else "{}"

        patch_lines.append(
            "  {{ id = {}, name = {}, itemIDs = {}, bossItems = {} }}".format(
                _lua_number(p.get("id")),
                _lua_string(p.get("name")),
                ids_lua,
                boss_items_lua,
            )
        )

    # --- Loot History ---
    lh_blocks = []
    for raid in (data.get("lootHistory") or []):
        entry_lines = []
        for e in (raid.get("entries") or []):
            entry_lines.append(
                "      {{ timestamp = {}, boss = {}, itemID = {}, player = {}, lootType = {} }}".format(
                    _lua_timestamp(e.get("timestamp")),
                    _lua_string(e.get("boss")),
                    _lua_number(e.get("itemID")),
                    _lua_string(e.get("player")),
                    _lua_string(e.get("lootType")),
                )
            )
        patch_ids     = raid.get("patchIds") or []
        patch_ids_lua = "{{ {} }}".format(", ".join(str(p) for p in patch_ids)) if patch_ids else "{}"
        lh_blocks.append(
            "  {{\n"
            "    raidName   = {},\n"
            "    date       = {},\n"
            "    difficulty = {},\n"
            "    patchIds   = {},\n"
            "    entries    = {{\n{}\n    }},\n"
            "  }}".format(
                _lua_string(raid.get("raidName")),
                _lua_string(raid.get("date")),
                _lua_string(raid.get("difficulty")),
                patch_ids_lua,
                ",\n".join(entry_lines),
            )
        )

    lua = """-- Automatisch generiert von WeltenWandler Companion App.
-- Nicht manuell bearbeiten.

WRT_StatsData = {{
  version     = {version},
  generatedAt = {generatedAt},
  patches     = {{
{patches}
  }},
  lootHistory = {{
{lootHistory}
  }},
}}
""".format(
        version=_lua_number(data.get("version", 1)),
        generatedAt=_lua_number(int(time.time())),
        patches=",\n".join(patch_lines),
        lootHistory=",\n".join(lh_blocks),
    )

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(lua)
        return True
    except Exception as e:
        print(f"[LuaWriter] Fehler beim Schreiben von stats_data.lua: {e}")
        return False


# --------------------------------------------------
# BLACKLIST DATA
# --------------------------------------------------
def write_blacklist(blacklist: list, addon_path: str) -> bool:
    """Schreibt data/blacklist_data.lua in den Addon-Ordner."""
    out_path = os.path.join(addon_path, "data", "blacklist_data.lua")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    item_ids = [str(entry["item_id"]) for entry in blacklist if entry.get("item_id")]

    lua = """-- Automatisch generiert von WeltenWandler Companion App.
-- Nicht manuell bearbeiten.

WRT_BlacklistData = {{
  version     = {version},
  generatedAt = {generatedAt},
  items       = {{ {items} }},
}}
""".format(
        version=1,
        generatedAt=_lua_number(int(time.time())),
        items=", ".join(f"[{i}] = true" for i in item_ids),
    )

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(lua)
        return True
    except Exception as e:
        print(f"[LuaWriter] Fehler beim Schreiben von blacklist_data.lua: {e}")
        return False
