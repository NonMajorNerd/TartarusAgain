from __future__ import annotations

import random
from telnetlib import theNULL
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING

import tcod

import entity_factories
from game_map import GameMap
import tile_types


if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


max_items_by_floor = [
    (1, 1),
    (4, 2),
]

max_monsters_by_floor = [
    (1, 2),
    (4, 3),
    (6, 5),
]

item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.health_potion, 35)],
    2: [(entity_factories.confusion_scroll, 10)],
    4: [(entity_factories.lightning_scroll, 25), (entity_factories.sword, 5)],
    6: [(entity_factories.fireball_scroll, 25), (entity_factories.chain_mail, 15)],
}

enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.orc, 80)],
    3: [(entity_factories.troll, 15)],
    5: [(entity_factories.troll, 30)],
    7: [(entity_factories.troll, 60)],
}


def get_max_value_for_floor(
    max_value_by_floor: List[Tuple[int, int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value


def get_entities_at_random(
    weighted_chances_by_floor: Dict[int, List[Tuple[Entity, int]]],
    number_of_entities: int,
    floor: int,
) -> List[Entity]:
    entity_weighted_chances = {}

    for key, values in weighted_chances_by_floor.items():
        if key > floor:
            break
        else:
            for value in values:
                entity = value[0]
                weighted_chance = value[1]

                entity_weighted_chances[entity] = weighted_chance

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())

    chosen_entities = random.choices(
        entities, weights=entity_weighted_chance_values, k=number_of_entities
    )

    return chosen_entities


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


def place_entities(room: RectangularRoom, dungeon: GameMap, floor_number: int,) -> None:
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )
    number_of_items = 0
    #number_of_items = random.randint(
    #    0, get_max_value_for_floor(max_items_by_floor, floor_number)
    #)

    monsters: List[Entity] = get_entities_at_random(
        enemy_chances, number_of_monsters, floor_number
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )

    for entity in monsters + items:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            entity.spawn(dungeon, x, y)


def tunnel_between(
    start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:  # 50% chance.
        # Move horizontally, then vertically.
        corner_x, corner_y = x2, y1
    else:
        # Move vertically, then horizontally.
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y


def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Generate a new dungeon map."""
    player = engine.player

    dungeon = GameMap(engine, map_width, map_height, entities=[player])

    rooms: List[RectangularRoom] = []

    x = 1
    y = 1
    
    room_width = 38
    room_height = 39

    width, height = 37, 37
    a, b = 18, 18
    r = 18
    EPSILON = 4.1

    # "RectangularRoom" class makes rectangles easier to work with
    new_room = RectangularRoom(x, y, room_width, room_height)

    coords = []

    # outline the circle
    for y in range(height):
        for x in range(width):
            # see if we're close to (x-a)**2 + (y-b)**2 == r**2
            if abs((x-a)**2 + (y-b)**2 - r**2) < EPSILON**2:
                coords.append ([x,y])

    # fill the circle
    for y in range(0, height):
        rowlist = []
        for coord in coords:
            if coord[1] == y:
                rowlist.append(coord)

        minx = rowlist[0][0]
        maxx = rowlist[len(rowlist)-1][0]

        for i in range(minx, maxx):
            dungeon.tiles[i+1, y+1] = tile_types.floor
 
    player.place(*new_room.center, dungeon)

    place_entities(new_room, dungeon, engine.game_world.current_floor)

    rooms.append(new_room)

    return dungeon



#     (x - a)**2 + (y - b)**2 = r**2
# Where (x, y) is a point, (a, b) is the center of the circle and r is the radius.

def make_circle(width, height, a, b, r, EPSILON):
    #width, height = 11, 11
    #a, b = 5, 5
    #r = 5
    #EPSILON = 2.2

    coords = []

    map_ = [['.' for x in range(width)] for y in range(height)]

    # draw the circle
    for y in range(height):
        for x in range(width):
            # see if we're close to (x-a)**2 + (y-b)**2 == r**2
            if abs((x-a)**2 + (y-b)**2 - r**2) < EPSILON**2:
                coords.append ([x,y])
                map_[y][x] = '#'

    # print the map
    for line in map_:
        print(' '.join(line))

    for y in range(0, height):
        print('')
        print('y ' + str(y))

        rowlist = []
        for coord in coords:
            if coord[1] == y:
                rowlist.append(coord)
                print(str(coord))

        minx = rowlist[0][0]
        maxx = rowlist[len(rowlist)-1][0]

        for i in range(minx, maxx):
            map_[i][y] = '#'

        # print the map
        for line in map_:
            print(' '.join(line))    

    return