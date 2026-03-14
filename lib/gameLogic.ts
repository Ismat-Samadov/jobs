import { Monster, Direction, GameState, Level, StarPosition } from './types';

let monsterIdCounter = 0;

export function createMonster(
  color: Monster['color'],
  rowStart: number,
  rowEnd: number,
  colStart: number,
  colEnd: number
): Monster {
  return {
    id: `monster-${++monsterIdCounter}`,
    color,
    rowStart,
    rowEnd,
    colStart,
    colEnd,
  };
}

export function initGameState(level: Level): GameState {
  const monsters = level.monsters.map((m) =>
    createMonster(m.color, m.rowStart, m.rowEnd, m.colStart, m.colEnd)
  );
  return {
    currentLevel: level,
    monsters,
    moves: 0,
    isComplete: false,
    isPaused: false,
    selectedMonsterId: null,
    history: [],
  };
}

/** Check if two monsters overlap in a given axis */
function rowsOverlap(a: Monster, b: Monster): boolean {
  return a.rowStart <= b.rowEnd && a.rowEnd >= b.rowStart;
}

function colsOverlap(a: Monster, b: Monster): boolean {
  return a.colStart <= b.colEnd && a.colEnd >= b.colStart;
}

/** Merge two monsters into one */
function mergeMonsters(a: Monster, b: Monster): Monster {
  return {
    id: a.id, // keep the first monster's id
    color: a.color,
    rowStart: Math.min(a.rowStart, b.rowStart),
    rowEnd: Math.max(a.rowEnd, b.rowEnd),
    colStart: Math.min(a.colStart, b.colStart),
    colEnd: Math.max(a.colEnd, b.colEnd),
  };
}

export function slideMonsters(
  monsters: Monster[],
  direction: Direction,
  gridSize: number
): { monsters: Monster[]; moved: boolean } {
  let updated = monsters.map((m) => ({ ...m }));
  let anyMoved = false;

  const iterations = gridSize * gridSize;

  for (let iter = 0; iter < iterations; iter++) {
    let mergedThisPass = false;

    // Sort monsters based on direction (process in the direction of movement)
    if (direction === 'left') {
      updated.sort((a, b) => a.colStart - b.colStart);
    } else if (direction === 'right') {
      updated.sort((a, b) => b.colEnd - a.colEnd);
    } else if (direction === 'up') {
      updated.sort((a, b) => a.rowStart - b.rowStart);
    } else {
      updated.sort((a, b) => b.rowEnd - a.rowEnd);
    }

    const newMonsters: Monster[] = [];
    const merged = new Set<string>();

    for (const monster of updated) {
      if (merged.has(monster.id)) continue;

      let moved = { ...monster };

      if (direction === 'left') {
        // Find leftmost position
        let newColStart = 0;
        let hitMonster: Monster | null = null;

        for (const other of newMonsters) {
          if (rowsOverlap(monster, other) && other.colEnd < monster.colStart) {
            if (other.colEnd + 1 > newColStart) {
              newColStart = other.colEnd + 1;
              hitMonster = other;
            }
          }
        }

        const width = monster.colEnd - monster.colStart;
        moved = { ...monster, colStart: newColStart, colEnd: newColStart + width };

        if (moved.colStart !== monster.colStart) anyMoved = true;

        // Check if we should merge with hitMonster
        if (hitMonster && moved.colStart === hitMonster.colEnd + 1) {
          const mergedM = mergeMonsters(hitMonster, moved);
          const idx = newMonsters.findIndex((m) => m.id === hitMonster!.id);
          if (idx >= 0) newMonsters[idx] = mergedM;
          merged.add(monster.id);
          mergedThisPass = true;
          anyMoved = true;
          continue;
        }
      } else if (direction === 'right') {
        let newColEnd = gridSize - 1;
        let hitMonster: Monster | null = null;

        for (const other of newMonsters) {
          if (rowsOverlap(monster, other) && other.colStart > monster.colEnd) {
            if (other.colStart - 1 < newColEnd) {
              newColEnd = other.colStart - 1;
              hitMonster = other;
            }
          }
        }

        const width = monster.colEnd - monster.colStart;
        moved = { ...monster, colEnd: newColEnd, colStart: newColEnd - width };

        if (moved.colEnd !== monster.colEnd) anyMoved = true;

        if (hitMonster && moved.colEnd === hitMonster.colStart - 1) {
          const mergedM = mergeMonsters(hitMonster, moved);
          const idx = newMonsters.findIndex((m) => m.id === hitMonster!.id);
          if (idx >= 0) newMonsters[idx] = mergedM;
          merged.add(monster.id);
          mergedThisPass = true;
          anyMoved = true;
          continue;
        }
      } else if (direction === 'up') {
        let newRowStart = 0;
        let hitMonster: Monster | null = null;

        for (const other of newMonsters) {
          if (colsOverlap(monster, other) && other.rowEnd < monster.rowStart) {
            if (other.rowEnd + 1 > newRowStart) {
              newRowStart = other.rowEnd + 1;
              hitMonster = other;
            }
          }
        }

        const height = monster.rowEnd - monster.rowStart;
        moved = { ...monster, rowStart: newRowStart, rowEnd: newRowStart + height };

        if (moved.rowStart !== monster.rowStart) anyMoved = true;

        if (hitMonster && moved.rowStart === hitMonster.rowEnd + 1) {
          const mergedM = mergeMonsters(hitMonster, moved);
          const idx = newMonsters.findIndex((m) => m.id === hitMonster!.id);
          if (idx >= 0) newMonsters[idx] = mergedM;
          merged.add(monster.id);
          mergedThisPass = true;
          anyMoved = true;
          continue;
        }
      } else {
        // down
        let newRowEnd = gridSize - 1;
        let hitMonster: Monster | null = null;

        for (const other of newMonsters) {
          if (colsOverlap(monster, other) && other.rowStart > monster.rowEnd) {
            if (other.rowStart - 1 < newRowEnd) {
              newRowEnd = other.rowStart - 1;
              hitMonster = other;
            }
          }
        }

        const height = monster.rowEnd - monster.rowStart;
        moved = { ...monster, rowEnd: newRowEnd, rowStart: newRowEnd - height };

        if (moved.rowEnd !== monster.rowEnd) anyMoved = true;

        if (hitMonster && moved.rowEnd === hitMonster.rowStart - 1) {
          const mergedM = mergeMonsters(hitMonster, moved);
          const idx = newMonsters.findIndex((m) => m.id === hitMonster!.id);
          if (idx >= 0) newMonsters[idx] = mergedM;
          merged.add(monster.id);
          mergedThisPass = true;
          anyMoved = true;
          continue;
        }
      }

      newMonsters.push(moved);
    }

    updated = newMonsters;
    if (!mergedThisPass) break;
  }

  return { monsters: updated, moved: anyMoved };
}

export function checkWinCondition(monsters: Monster[], stars: StarPosition[]): boolean {
  return stars.every((star) =>
    monsters.some(
      (m) =>
        star.row >= m.rowStart &&
        star.row <= m.rowEnd &&
        star.col >= m.colStart &&
        star.col <= m.colEnd
    )
  );
}

export function applyMove(
  state: GameState,
  direction: Direction
): GameState {
  if (state.isComplete || state.isPaused) return state;

  const { monsters: newMonsters, moved } = slideMonsters(
    state.monsters,
    direction,
    state.currentLevel.gridSize
  );

  if (!moved) return state;

  const isComplete = checkWinCondition(newMonsters, state.currentLevel.stars);

  return {
    ...state,
    monsters: newMonsters,
    moves: state.moves + 1,
    isComplete,
    history: [...state.history, state.monsters],
  };
}

export function undoMove(state: GameState): GameState {
  if (state.history.length === 0) return state;
  const prevMonsters = state.history[state.history.length - 1];
  return {
    ...state,
    monsters: prevMonsters,
    moves: state.moves - 1,
    isComplete: false,
    history: state.history.slice(0, -1),
  };
}

export function isStarCovered(star: StarPosition, monsters: Monster[]): boolean {
  return monsters.some(
    (m) =>
      star.row >= m.rowStart &&
      star.row <= m.rowEnd &&
      star.col >= m.colStart &&
      star.col <= m.colEnd
  );
}
