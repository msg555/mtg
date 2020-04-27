import collections
import enum
import json
import re
import pprint

from adjustable_heap import AdjustableHeap

COLORS = "WUBRG"
COLOR_TO_INDEX = {color: ind for ind, color in enumerate(COLORS)}
ALL_COLORS_SET = (2 ** len(COLORS)) - 1
MARDU_COLOR_SET = sum(2 ** COLOR_TO_INDEX[col] for col in "WBR")


class LandTypes(enum.IntEnum):
  BASIC = 0
  SHOCK = 1
  SCRY = 2
  TAP_DUAL = 3
  ADAMANT = 4
  CASTLE = 5
  COLORLESS = 6
  FABLED_PASSAGE = 7
  BEACON = 8
  TAP_TRI = 9
  LOTUS = 10
  EVOLVING_WILDS = 11
  GATEWAY_PLAZA = 12
  FILTERING = 13
  COMMAND_TOWER = 14
  TOURNAMENT_GROUNDS = 15
  PLAZA_OF_HARMONY = 16
  GUILDGATE = 17


SIMPLE_LAND_TYPES = (
  LandTypes.BASIC,
  LandTypes.ADAMANT,
  LandTypes.CASTLE,
  LandTypes.SHOCK,
  LandTypes.SCRY,
  LandTypes.TAP_DUAL,
  LandTypes.GUILDGATE,
  LandTypes.TAP_TRI,
  LandTypes.COLORLESS,
)


def _categorize_land(name, text, color_identity, supertypes):
  if "Basic" in supertypes:
    return LandTypes.BASIC
  if "Guildgate" in name:
    return LandTypes.GUILDGATE
  if "Castle" in name:
    return LandTypes.CASTLE
  if name == "Fabled Passage":
    return LandTypes.FABLED_PASSAGE
  if name == "Evolving Wilds":
    return LandTypes.EVOLVING_WILDS
  if name == "Interplanar Beacon":
    return LandTypes.BEACON
  if "gain 1 life" in text:
    return LandTypes.TAP_DUAL
  if name.startswith("Temple of "):
    return LandTypes.SCRY
  if name.endswith(" Triome"):
    return LandTypes.TAP_TRI
  if "pay 2 life" in text:
    return LandTypes.SHOCK
  if "control three or more" in text:
    return LandTypes.ADAMANT

  COLORLESS_LANDS = {
    "Blast Zone",
    "Cryptic Caves",
    "Emergence Zone",
    "Field of Ruin",
    "Karn's Bastion",
    "Labyrinth of Skophos",
    "Mobilized District",
    "Bonders' Enclave",
  }
  if name in COLORLESS_LANDS:
    return LandTypes.COLORLESS
  if name == "Lotus Field":
    return LandTypes.LOTUS
  if name == "Gateway Plaza":
    return LandTypes.GATEWAY_PLAZA
  if name in ("Guildmages' Forum", "Unknown Shores"):
    return LandTypes.FILTERING
  if name == "Command Tower":
    return LandTypes.COMMAND_TOWER
  if name == "Tournament Grounds":
    return LandTypes.TOURNAMENT_GROUNDS
  if name == "Plaza of Harmony":
    return LandTypes.PLAZA_OF_HARMONY
  raise Exception("Unknown land {}".format(name))


def lower_mobius_transform(freq):
  """
  Computes the lower mobius transform of freq, mapping color bitsets to
  counts.

  Returns g(s) = sum(f(t) for t \subseteq s)
  """
  result = [freq.get(index, 0) for index in range(2 ** len(COLORS))]
  for index in range(len(COLORS)):
    col = 2 ** index
    iter_st = ALL_COLORS_SET ^ col
    st = iter_st
    while True:
      result[st | col] += result[st]
      if st == 0:
        break
      st = (st - 1) & iter_st
  return result


def can_cast_simple(cost, lands, offset=0):
  """
  Given only simple lands that tap for one of a selection of colors. Determine
  if the cost can be met.

  Uses Hall's theorem to verify for every set of colors `S` that the number of
  lands that produce a color in `S` exceeds the number of cost pips that are
  contained within `S`.

  Uses the lower mobius transform to do this in O(N 2**N) where N is the number
  of colors. (i.e. this function runs in constant time)
  """
  cost_g = lower_mobius_transform(cost)
  land_g = lower_mobius_transform(lands)
  land_g[0] = 0 # Minor hack to let colorless lands be used to pay generic mana
  total_lands = land_g[ALL_COLORS_SET]
  return all(c + offset <= total_lands - g for c, g in zip(cost_g, land_g[::-1]))


def can_cast(spell, lands, X=0):
  # Replace X costs with the a resolved generic mana cost.
  cost = collections.Counter(spell.cost)
  if cost.get(0):
    cost[ALL_COLORS_SET] += cost[0] * X
    del cost[0]

  # Separate out simple lands and lands that require manual logic.
  simple_lands = collections.Counter()
  other_lands = []
  plaza_count = 0
  gate_colors = 0
  for land in lands:
    if land.land_type in (LandTypes.FABLED_PASSAGE, LandTypes.EVOLVING_WILDS):
      continue
    if land.land_type in SIMPLE_LAND_TYPES:
      if land.land_type == LandTypes.GUILDGATE:
        gate_colors = gate_colors | land.color_identity_set
      simple_lands[land.color_identity_set] += 1
    elif land.land_type == LandTypes.GATEWAY_PLAZA:
      gate_colors = ALL_COLORS_SET
      simple_lands[ALL_COLORS_SET] += 1
    elif land.land_type == LandTypes.COMMAND_TOWER:
      # Assume spell is within our commander's color identity.
      simple_lands[ALL_COLORS_SET] += 1
    elif land.land_type == LandTypes.TOURNAMENT_GROUNDS:
      if "Equipment" in spell.subtypes or "Knight" in spell.subtypes:
        simple_lands[MARDU_COLOR_SET] += 1
      else:
        simple_lands[0] += 1
    elif land.land_type == LandTypes.PLAZA_OF_HARMONY:
      plaza_count += 1
    elif land.land_type == LandTypes.BEACON:
      if "Planeswalker" in spell.types:
        other_lands.append(land)
      else:
        simple_lands[0] += 1
    else:
      other_lands.append(land)
  if plaza_count:
    simple_lands[gate_colors] += plaza_count

  # If we can cast this spell using only simple lands exit early.
  if can_cast_simple(cost, simple_lands):
    return True

  # If we only have simple lands we know it's now impossible.
  if not other_lands:
    return False

  # Need to handle the below land types via backtracking.
  #  *) Beacon
  #  *) Lotus
  #  *) Filtering

  # Do a quick "optimistic" check to see if we can rule out being able to cast
  # this spell entirely without doing backtracking.
  optimistic_cost = collections.Counter(cost)
  optimistic_lands = collections.Counter(simple_lands)
  for land in other_lands:
    if land.land_type == LandTypes.BEACON:
      optimistic_cost[ALL_COLORS_SET] += 1
      optimistic_lands[ALL_COLORS_SET] += 2
    elif land.land_type == LandTypes.LOTUS:
      optimistic_lands[ALL_COLORS_SET] += 3
    elif land.land_type == LandTypes.FILTERING:
      optimistic_lands[ALL_COLORS_SET] += 1
    else:
      raise Exception("Unsupported land type")

  if not can_cast_simple(optimistic_cost, optimistic_lands):
    return False

  max_colors = tuple(
    sum(cnt for color_set, cnt in cost.items() if color_set != ALL_COLORS_SET and (2 ** color & color_set) != 0)
    for color in range(len(COLORS))
  )
  total_cost = sum(cost.values())

  class SearchState:
    def __init__(self, colors=None, filter_colors=None, total=0, filter_total=0, filter_cost=0, land_index=0):
      if filter_colors is None:
        self.filter_colors = tuple(0 for _ in range(len(COLORS)))
      else:
        self.filter_colors = tuple(min(col, max_color) for col, max_color in zip(filter_colors, max_colors))

      if colors is None:
        self.colors = tuple(0 for _ in range(len(COLORS)))
      else:
        self.colors = tuple(min(col, max_color - col_filter) for col, col_filter, max_color in zip(colors, self.filter_colors, max_colors))

      self.filter_total = min(filter_total, total_cost)
      self.total = total

      self.filter_cost = filter_cost
      self.land_index = land_index

      color_req = sum(max_colors) - sum(self.filter_colors) - sum(self.colors)
      total_req = total_cost - self.filter_total - self.total
      self.huer_dist = (max(color_req, total_req) + land_index + self.filter_cost, color_req, self.filter_total)

    def add(self, *cols, is_filtered=False, land_weight=1, colorless=0, filter_cost=0):
      normal_cols, filter_cols = cols, ()
      normal_total, filter_total = len(cols) + colorless, 0
      if is_filtered:
        normal_cols, filter_cols = filter_cols, normal_cols
        normal_total, filter_total = filter_total, normal_total
      
      return SearchState(
        colors=tuple(
          cnt + sum(1 for col in normal_cols if col == color)
          for color, cnt in enumerate(self.colors)
        ),
        filter_colors=tuple(
          cnt + sum(1 for col in filter_cols if col == color)
          for color, cnt in enumerate(self.filter_colors)
        ),
        total=self.total + normal_total,
        filter_total=self.filter_total + filter_total,
        filter_cost=self.filter_cost + filter_cost,
        land_index=self.land_index + land_weight,
      )

    def _ident(self):
      return (self.land_index, self.total, self.filter_total, self.filter_cost, self.colors, self.filter_colors)

    def __eq__(self, obj):
      return self._ident() == obj._ident()

    def __hash__(self):
      return hash(self._ident())

  simple_land_count = sum(simple_lands.values())
  other_lands.sort(key=lambda card: card.name)

  visited_states = set()
  queue = AdjustableHeap(lambda state: state.huer_dist)

  def _try_queue(state):
    if state in visited_states:
      return
    visited_states.add(state)
    queue.push(state)

  _try_queue(SearchState())
  while queue:
    state = queue.pop()

    # Test if we can solve from this state.
    colored_mana, colored_filter_mana = 0, 0
    state_lands = collections.Counter(simple_lands)
    state_filter_lands = collections.Counter()
    for col, (cnt, filter_cnt) in enumerate(zip(state.colors, state.filter_colors)):
      state_lands[2 ** col] += cnt + filter_cnt
      state_filter_lands[2 ** col] += filter_cnt
      colored_mana += cnt + filter_cnt
      colored_filter_mana += filter_cnt
    state_lands[0] += state.filter_total + state.total - colored_mana
    state_filter_lands[0] += state.filter_total - colored_filter_mana

    # Verify for all color sets `s`
    #  filtered_lands[s] >= colored_pips[s] + filter_cost - normal_lands
    #  lands[s] >= colored_pips[s]
    if can_cast_simple(cost, state_lands) and \
       can_cast_simple(cost, state_filter_lands, offset=state.filter_cost - simple_land_count - state.total):
      return True

    # Test if we've already tried all the lands.
    if state.land_index == len(other_lands):
      continue

    # Visit adjacent states for each land type.
    land = other_lands[state.land_index]

    if land.land_type == LandTypes.BEACON:
      _try_queue(state.add(colorless=1))
      for color_a in range(len(COLORS)):
        for color_b in range(color_a):
          _try_queue(state.add(color_a, color_b, is_filtered=True, filter_cost=1))
    elif land.land_type == LandTypes.LOTUS:
      for color in range(len(COLORS)):
        _try_queue(state.add(color, color, color))
    elif land.land_type == LandTypes.FILTERING:
      _try_queue(state.add(colorless=1))
      for color in range(len(COLORS)):
        _try_queue(state.add(color, filter_cost=1))

  return False

def _parse_cost(cost):
  if cost is None:
    return None

  cost_dict = collections.Counter()
  parts = [part for part in re.split(r"[{}]+", cost) if part]
  for part in parts:
    if part == "X":
      cost_dict[0] += 1
      continue

    try:
      cost_dict[ALL_COLORS_SET] += int(part)
    except ValueError:
      color = sum(2 ** COLOR_TO_INDEX[ch] for ch in part.split("/"))
      cost_dict[color] += 1
  return cost_dict


class Card:
  def __init__(self, card_data):
    self.color = "".join(card_data["colors"])
    self.color_identity = "".join(card_data["colorIdentity"])
    self.color_identity_set = sum(2 ** COLOR_TO_INDEX[ch] for ch in self.color_identity)
    self.cmc = int(card_data["convertedManaCost"])
    self.loyalty = card_data.get("loyalty")
    self.cost = _parse_cost(card_data.get("manaCost"))
    self.name = card_data["name"]
    self.power = card_data.get("power")
    self.toughness = card_data.get("toughness")
    self.supertypes = card_data["supertypes"]
    self.subtypes = card_data["subtypes"]
    self.types = card_data["types"]
    self.text = card_data.get("text", "")
    self.uuid = card_data["uuid"]
    self.land_type = None

    if "Land" in self.types:
      self.land_type = _categorize_land(self.name, self.text, self.color_identity, self.supertypes)

  def __str__(self):
    if "Creature" in self.types:
      return "{} {}\n{}\n{}\n{}/{}".format(self.name, self.cost, " ".join(self.types), self.text, self.power, self.toughness)
    elif "Planeswalker" in self.types:
      return "{} {}\n{}\n{}\n{}".format(self.name, self.cost, " ".join(self.types), self.text, self.loyalty)
    else:
      return "{} {}\n{}\n{}".format(self.name, self.cost, " ".join(self.types), self.text)

  def __repr__(self):
    return self.name


class Decklist:
  def __init__(self, stream, cards):
    self.deck = []
    self.sideboard = []

    deck_section = ""
    for line in stream:
      line = line.rstrip()

      if line in ("Deck", "Sideboard"):
        deck_section = line
        continue

      match = re.match(r"^(\d+) ([^()]*)( \([A-Z]+\))?( \d+)$", line)
      if not match:
        continue

      card_count = int(match.group(1))
      card_name = match.group(2)
      card_set = match.group(3).strip()
      card_no = match.group(4).strip()

      card = cards[card_name]
      if deck_section == "Sideboard":
        self.sideboard.extend(card for _ in range(card_count))
      else:
        self.deck.extend(card for _ in range(card_count))


def read_set(fset):
  return {
    card_data["name"]: Card(card_data)
    for card_data in json.load(fset)["cards"]
  }


def read_format(fformat):
  return {
    card_data["name"]: Card(card_data)
    for card_data in json.load(fformat).values()
  }


def load_standard_cards():
  cards = {}
  with open("IKO.json", "r") as fset:
    cards.update(read_set(fset))
  with open("StandardCards.json", "r") as fformat:
    cards.update(read_format(fformat))
  return cards
